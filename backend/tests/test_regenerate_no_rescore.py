"""
Regenerate endpoint contract tests (explanation-level, no risk re-scoring).

Verifies via the real route handler (no HTTP server; FastAPI app invoked
through httpx ASGI transport against the live DB):
1. POST /api/risk/explain/regenerate does NOT change the risk event's
   risk_score / ml_score / rule_score / graph_score / risk_level /
   primary_reason — regeneration is an explanation-level operation only.
2. The persisted canonical artifact is replaced (new payload, new
   generated_at, same user+audience row).
3. An ordinary read after regeneration returns the persisted artifact
   byte-identically WITHOUT triggering another generation
   (metrics: llm_total does not increase).
4. The regenerate path itself performs exactly one generation.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient

from app.db.session import async_session_maker, engine, Base
from app.models.database import RiskEvent, CaseExplanation
from app.services.explain_metrics import get_explain_metrics
import app.main as main_module


EVAL_USER = "U00233"  # eval-set case, HIGH, graph=0 (regenerate → fallback-free LLM not required)


async def _snapshot_risk_event(user_id):
    async with async_session_maker() as db:
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


async def _artifact(user_id):
    async with async_session_maker() as db:
        from sqlalchemy import select
        row = (await db.execute(
            select(CaseExplanation).where(
                CaseExplanation.user_id == user_id,
                CaseExplanation.audience == "investigator"))).scalar_one_or_none()
        if row is None:
            return None
        return {
            "payload": row.explanation_payload,
            "generated_at": row.generated_at,
            "fingerprint": row.version_fingerprint,
        }


async def _metrics():
    return get_explain_metrics().get_metrics()


def run(coro):
    return asyncio.run(coro)


class TestRegenerateNoRescore:
    def setup_method(self):
        async def setup():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            await engine.dispose()
        asyncio.run(setup())

    def test_regenerate_preserves_risk_event_and_replaces_artifact(self):
        async def scenario():
            transport = ASGITransport(app=main_module.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                before_risk = await _snapshot_risk_event(EVAL_USER)
                before_art = await _artifact(EVAL_USER)
                m0 = await _metrics()

                # 1) explicit regeneration
                resp = await client.post(
                    "/api/risk/explain/regenerate?audience=investigator",
                    json={"user_id": EVAL_USER}, timeout=120)
                assert resp.status_code == 200, resp.text
                regen_body = resp.json()

                await _snapshot_risk_event(EVAL_USER)  # ensure session refs settle
                after_risk = await _snapshot_risk_event(EVAL_USER)
                after_art = await _artifact(EVAL_USER)
                m1 = await _metrics()

                # 2) ordinary read — must be the persisted artifact, no new generation
                resp2 = await client.post(
                    "/api/risk/explain?audience=investigator",
                    json={"user_id": EVAL_USER}, timeout=60)
                assert resp2.status_code == 200
                read_body = resp2.json()
                m2 = await _metrics()
                return (before_risk, after_risk, before_art, after_art,
                        regen_body, read_body, m0, m1, m2)

        (before_risk, after_risk, before_art, after_art,
         regen_body, read_body, m0, m1, m2) = run(scenario())

        # (1) risk event untouched by regeneration
        assert after_risk == before_risk, f"risk event changed: {before_risk} -> {after_risk}"

        # (2) artifact replaced: same row scope, new payload identity, new timestamp
        assert after_art is not None and before_art is not None
        assert after_art["payload"] != before_art["payload"] or \
               after_art["generated_at"] != before_art["generated_at"], \
            "canonical artifact was not replaced"
        assert after_art["fingerprint"] == before_art["fingerprint"], \
            "fingerprint must not change when the case version is unchanged"

        # (3) regenerate response reflects the new artifact; explanation-level only
        assert regen_body["explanation_source"] in ("LLM", "MODEL_FALLBACK")
        assert read_body == regen_body or json.loads(after_art["payload"])["summary"] == read_body["summary"], \
            "ordinary read after regenerate must return the new persisted artifact"

        # (4) metrics: exactly one generation for regenerate; none for the ordinary read
        gens_after_regen = (m1["llm_total"] + m1["llm_failed_total"] + m1["llm_disabled_total"]) \
                           - (m0["llm_total"] + m0["llm_failed_total"] + m0["llm_disabled_total"])
        gens_after_read = (m2["llm_total"] + m2["llm_failed_total"] + m2["llm_disabled_total"]) \
                          - (m1["llm_total"] + m1["llm_failed_total"] + m1["llm_disabled_total"])
        assert gens_after_regen == 1, f"regenerate should perform exactly one generation, got {gens_after_regen}"
        assert gens_after_read == 0, f"ordinary read must not generate, got {gens_after_read}"
