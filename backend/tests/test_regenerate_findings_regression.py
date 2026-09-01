"""
Regenerate endpoint findings regression tests.

Root cause this guards against (observed in the wild for U00010):
apply_narrative_contract() rebuilt key_findings ONLY from narrative lines
whose head matched a canonical finding name — a pure FILTER. When the
generator (LLM or deterministic fallback) omitted/rephrased titles, the
unmatched canonical findings silently disappeared from the rendered list
(worst case key_findings == [], since score-summary lines never match).

Architecture this enforces:
    Risk scoring      = detection layer (never touched by regenerate)
    Canonical evidence = authoritative findings layer
    LLM               = explanation layer
    Narrative contract = alignment layer (merge + COMPLETE, never drop)

Verified through the real route handler (httpx ASGI transport, live DB):
1. Regenerate does NOT change risk_score / risk_level / component scores.
2. Canonical evidence for the case is non-empty.
3. The regenerate response contains NON-EMPTY key_findings, and EVERY
   canonical finding is represented.
4. U00010 (opposite_trade_ratio = 0.3438) is rendered as
   "Opposite Trade Ratio" with below-threshold semantics;
   "Coordinated Trading Pattern" is NOT produced.
5. Findings survive persistence: the stored CaseExplanation payload and a
   subsequent ordinary read both return the same non-empty findings.
6. No raw threshold syntax leaks into user-facing findings.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient

from app.models.database import RiskEvent, FeatureTable, CaseExplanation
import app.main as main_module
from app.db import session as session_module


USER = "U00010"  # opposite_trade_ratio = 0.3438 (below 0.4 threshold)


def run(coro):
    return asyncio.run(coro)


async def _fresh_session_maker():
    """
    create_all + a session maker bound to the CURRENT loop, patched into the
    app module for the duration of one test.

    The app's module-global engine pools asyncpg connections that are bound
    to whatever event loop created them. Tests each run under their own
    asyncio.run() loop, so a pooled connection from a previous test's loop
    raises "Future attached to a different loop" on checkout. get_db()
    resolves `async_session_maker` as a module global at CALL time, so
    swapping it here routes the whole app through a loop-local engine;
    the original is restored afterwards, leaving other tests untouched.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        await conn.run_sync(session_module.Base.metadata.create_all)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False,
                         autocommit=False, autoflush=False)
    return engine, maker


async def _risk_event_snapshot(user_id, maker):
    async with maker() as db:
        from sqlalchemy import select, desc
        re_ = (await db.execute(
            select(RiskEvent).where(RiskEvent.user_id == user_id)
            .order_by(desc(RiskEvent.detected_at)).limit(1))).scalar_one()
        return {
            "id": re_.id,
            "risk_score": str(re_.risk_score),
            "ml_score": str(re_.ml_score),
            "rule_score": str(re_.rule_score),
            "graph_score": str(re_.graph_score),
            "risk_level": re_.risk_level,
            "primary_reason": re_.primary_reason,
        }


async def _opposite_trade_ratio(user_id, maker):
    async with maker() as db:
        from sqlalchemy import select
        row = (await db.execute(
            select(FeatureTable).where(FeatureTable.user_id == user_id))).scalars().first()
        return float(row.opposite_trade_ratio) if row and row.opposite_trade_ratio is not None else None


async def _persisted_payload(user_id, maker):
    async with maker() as db:
        from sqlalchemy import select
        row = (await db.execute(
            select(CaseExplanation).where(
                CaseExplanation.user_id == user_id,
                CaseExplanation.audience == "investigator"))).scalar_one_or_none()
        if row is None:
            return None
        import json
        return json.loads(row.explanation_payload)


class TestRegenerateFindingsRegression:
    def test_regenerate_keeps_canonical_findings_and_scores(self):
        async def scenario():
            engine, maker = await _fresh_session_maker()
            original_maker = session_module.async_session_maker
            session_module.async_session_maker = maker
            try:
                transport = ASGITransport(app=main_module.app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    before = await _risk_event_snapshot(USER, maker)
                    ratio = await _opposite_trade_ratio(USER, maker)

                    resp = await client.post(
                        "/api/risk/explain/regenerate?audience=investigator",
                        json={"user_id": USER}, timeout=120)
                    assert resp.status_code == 200, resp.text
                    regen = resp.json()

                    after = await _risk_event_snapshot(USER, maker)
                    persisted = await _persisted_payload(USER, maker)

                    read = await client.post(
                        "/api/risk/explain?audience=investigator",
                        json={"user_id": USER}, timeout=60)
                    assert read.status_code == 200
                    return before, after, ratio, regen, persisted, read.json()
            finally:
                session_module.async_session_maker = original_maker
                await engine.dispose()

        before, after, ratio, regen, persisted, read = run(scenario())

        # --- 1. Explanation-level only: risk event untouched ---
        assert after == before, f"risk event changed: {before} -> {after}"
        assert float(before["risk_score"]) == 87.02
        assert before["risk_level"] == "CRITICAL"

        # --- 2/3. Findings non-empty and complete ---
        findings = regen.get("key_findings") or []
        assert findings, "regenerate response must contain non-empty key_findings"
        # Every canonical finding for the case is represented exactly once.
        # The narrative contract aligns an LLM-authored title to a canonical
        # finding by content-word signature (prefix match), so the rendered
        # title may be a wording variant of the canonical name — assert with
        # the SAME signature logic the contract uses, not raw substring.
        from app.services.narrative_contract import _head_signature
        title_sigs = [
            (i, tuple(_head_signature(f.split("\n")[0])))
            for i, f in enumerate(findings)
        ]
        for name in (
            "ML Pattern Detection Signal",
            "New account with high activity",
            "High withdrawal frequency",
            "First withdrawal to new address",
            "Shared Device Relationships",
            "Linked Account Network",
            "High Trading Frequency",
            "Opposite Trade Ratio",
        ):
            name_sig = tuple(_head_signature(name))
            matching = [
                i for i, sig in title_sigs
                if sig[:len(name_sig)] == name_sig or name_sig[:len(sig)] == sig
            ]
            assert matching, f"canonical finding {name!r} missing from regenerate response"
            assert len(matching) == 1, \
                f"canonical finding {name!r} appears {len(matching)} times (must be once)"
        joined = "\n".join(findings)

        # --- 3b. Semantically redundant finding NOT emitted ---
        # withdrawal_risk_score (fraction of withdrawals to new addresses) is
        # the same observation as first_withdrawal_flag; it must not surface
        # as a second, separate finding.
        assert "abnormal withdrawal behavior" not in joined.lower(), \
            "redundant 'Abnormal Withdrawal Behavior' finding emitted alongside " \
            "'First withdrawal to new address'"
        assert "newly encountered addresses" in joined.lower(), \
            "the new-address ratio must still be stated on the surviving finding"

        # --- 4. U00010 threshold semantics ---
        assert ratio is not None and 0 < ratio <= 0.4, \
            f"precondition: U00010 opposite_trade_ratio should be in (0, 0.4], got {ratio}"
        # Normalize hyphens: the LLM may hyphenate ("Opposite-trade ratio")
        normalized = joined.lower().replace("-", " ").replace("‘", "'").replace("’", "'")
        assert "coordinated trading pattern" not in normalized, \
            "0.3438 must NOT be rendered as 'Coordinated Trading Pattern'"
        assert "opposite trade ratio" in normalized, \
            "the below-threshold observation must be rendered under the neutral name"
        assert "34" in joined  # observed percentage surfaces

        # --- 5. Findings survive persistence and ordinary read ---
        assert persisted is not None, "canonical artifact must be persisted"
        assert persisted.get("key_findings"), "persisted artifact findings must be non-empty"
        assert "\n".join(persisted.get("key_findings") or []) == joined or \
               set(persisted.get("key_findings") or []) == set(findings), \
            "persisted findings must match the regenerate response"
        read_findings = read.get("key_findings") or []
        assert read_findings, "ordinary read after regenerate must return non-empty findings"
        assert set(read_findings) == set(findings) or \
               "\n".join(read_findings) == joined, \
            "ordinary read must return the persisted findings"

        # --- 6. No raw threshold syntax in user-facing findings ---
        import re
        raw_threshold = re.compile(
            r"[a-z_0-9]+\s*[<>=!]+\s*[\d.]+")
        for f in findings:
            assert not raw_threshold.search(f), f"raw threshold syntax leaked: {f!r}"

        # --- 7. Opposite-trade threshold semantics in the narrative ---
        # Below threshold (0.3438): the narrative must state the ratio is
        # below the 40% threshold and must NOT imply the rule was triggered.
        from app.services.narrative_contract import _head_signature
        opp_finding = next(
            f for f in findings
            if _head_signature(f.split("\n")[0])[:3]
            == _head_signature("Opposite Trade Ratio")[:3]
        )
        opp_text = opp_finding.lower()
        assert "below the 40% threshold" in opp_text, (
            f"narrative must state the ratio is below the 40% threshold: {opp_finding!r}"
        )
        assert "34.38%" in opp_finding, (
            f"narrative should carry the observed percentage: {opp_finding!r}"
        )
        for forbidden in (
            "potentially coordinated trading behavior",
            "coordinated trading pattern detected",
            "may warrant further review for coordinated trading",
            "triggering the coordinated trading rule",
        ):
            assert forbidden not in opp_text, (
                f"below-threshold narrative must not imply the rule fired "
                f"({forbidden!r}): {opp_finding!r}"
            )
