"""
Explanation Store Service — persisted canonical explanation artifacts.

Treats an explanation as a persisted case artifact rather than a transient
cached response. Responsibilities:

- Deterministic version fingerprinting of the inputs an explanation depends on
  (risk event identity, pipeline run, model version, policy version, audience).
- Reading the current canonical explanation for a (user_id, audience).
- Saving/replacing the canonical explanation (used by normal first generation,
  explicit regeneration, and the dev/eval replay tool).

The in-memory TTL cache in the /explain route is a read-through performance
layer only: a cache miss falls back to this store, never straight to the LLM.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import CaseExplanation, RiskEvent


def policy_version() -> str:
    """
    Derive the policy-document version from the latest mtime of policies/*.md.

    Moved from the /explain route so the fingerprint logic is defined in one
    place (route, replay tool, and tests all use this).
    """
    try:
        policies_dir = Path(__file__).resolve().parents[3] / "policies"
        if not policies_dir.exists():
            return "no-policies"

        latest_mtime = 0
        for p in policies_dir.glob("*.md"):
            mtime = p.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime

        return str(int(latest_mtime)) if latest_mtime > 0 else "empty-policies"
    except Exception:
        return "unknown"


def compute_explanation_fingerprint(
    risk_event_id: Any,
    pipeline_run_id: Optional[str],
    model_version: Optional[str],
    pol_version: Optional[str],
    audience: str,
) -> str:
    """
    Deterministic version fingerprint for an explanation.

    Inputs (joined with '|' and sha256-hashed):
      - audience            (explanations differ per audience)
      - risk_event_id       (a new pipeline run creates a new risk_event row)
      - pipeline_run_id     (per-run identifier)
      - model_version       (ML model version used for scoring)
      - policy_version      (mtime of policies/*.md)

    A stored explanation is valid iff its version_fingerprint equals the
    fingerprint computed from the CURRENT risk event. Any of the above inputs
    changing (re-run pipeline, retrain model, edit policy) invalidates the
    stored explanation: it is stale and must not be served as current.
    """
    parts = [
        audience or "",
        str(risk_event_id if risk_event_id is not None else ""),
        str(pipeline_run_id or ""),
        str(model_version or ""),
        str(pol_version or ""),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def fingerprint_for_risk_event(risk_event: RiskEvent, audience: str) -> str:
    """Convenience wrapper: fingerprint for a loaded RiskEvent ORM object."""
    return compute_explanation_fingerprint(
        risk_event_id=risk_event.id,
        pipeline_run_id=risk_event.pipeline_run_id,
        model_version=risk_event.model_version,
        pol_version=policy_version(),
        audience=audience,
    )


class ExplanationStoreService:
    """
    Persistence layer for canonical case explanations.

    One current row per (user_id, audience). save() replaces that row
    (select-then-update-or-insert), so explicit regeneration and replay both
    install a new canonical artifact. Only flush() is issued — the caller's
    session/commit lifecycle (route dependency or tool) owns the commit.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_row(self, user_id: str, audience: str) -> Optional[CaseExplanation]:
        """Return the stored row for (user_id, audience), or None."""
        result = await self.db.execute(
            select(CaseExplanation).where(
                CaseExplanation.user_id == user_id,
                CaseExplanation.audience == audience,
            )
        )
        return result.scalar_one_or_none()

    async def get_current(
        self, user_id: str, audience: str, fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        """
        Return the canonical explanation payload iff a row exists AND its
        version_fingerprint matches the given (current) fingerprint.

        Returns None when the row is absent OR stale — in both cases the caller
        (the /explain route) should generate a new explanation. Stale rows are
        never silently served as current.
        """
        row = await self.get_row(user_id, audience)
        if row is None:
            return None
        if row.version_fingerprint != fingerprint:
            return None  # stale: underlying case/version changed
        try:
            return json.loads(row.explanation_payload)
        except (ValueError, TypeError):
            return None  # corrupted payload — treat as absent

    async def save(
        self,
        user_id: str,
        audience: str,
        fingerprint: str,
        payload: Dict[str, Any],
        explanation_source: str,
        model_provider: Optional[str] = None,
        risk_event_id: Optional[int] = None,
        pipeline_run_id: Optional[str] = None,
        model_version: Optional[str] = None,
        pol_version: Optional[str] = None,
    ) -> CaseExplanation:
        """
        Persist the canonical explanation, replacing any existing row for
        (user_id, audience). Used by first generation, explicit regeneration,
        and the replay tool.
        """
        body = json.dumps(payload)
        row = await self.get_row(user_id, audience)
        if row is None:
            row = CaseExplanation(
                user_id=user_id,
                audience=audience,
                version_fingerprint=fingerprint,
                explanation_payload=body,
                explanation_source=explanation_source,
                model_provider=model_provider,
                risk_event_id=risk_event_id,
                pipeline_run_id=pipeline_run_id,
                model_version=model_version,
                policy_version=pol_version,
            )
            self.db.add(row)
        else:
            row.version_fingerprint = fingerprint
            row.explanation_payload = body
            row.explanation_source = explanation_source
            row.model_provider = model_provider
            row.risk_event_id = risk_event_id
            row.pipeline_run_id = pipeline_run_id
            row.model_version = model_version
            row.policy_version = pol_version
            # server_default only applies on INSERT — refresh explicitly on replace
            row.generated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def install_canonical(
        self,
        user_id: str,
        audience: str,
        payload: Dict[str, Any],
        explanation_source: str,
        risk_event: RiskEvent,
        model_provider: Optional[str] = None,
    ) -> CaseExplanation:
        """
        Install a payload as the canonical explanation for the CURRENT risk
        event version, using the same fingerprint logic as normal generation.

        Used by the dev/eval replay tool and tests — makes NO LLM call. After
        install, GET /explain returns exactly this payload until the case data
        changes or an explicit regeneration occurs.
        """
        return await self.save(
            user_id=user_id,
            audience=audience,
            fingerprint=fingerprint_for_risk_event(risk_event, audience),
            payload=payload,
            explanation_source=explanation_source,
            model_provider=model_provider,
            risk_event_id=risk_event.id,
            pipeline_run_id=risk_event.pipeline_run_id,
            model_version=risk_event.model_version,
            pol_version=policy_version(),
        )
