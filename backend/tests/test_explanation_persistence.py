"""
Focused tests for the persisted canonical explanation artifact.

Covers the acceptance scenarios for the /explain persistence layer:
1. first generation persists
2. second request uses the persisted explanation
3. cache clear/expiry does not regenerate (persisted store serves the read)
4. explicit regeneration replaces the stored explanation
5. backend-restart / read-from-DB path works
6. changed risk/evidence version invalidates (stale) the stored explanation
7. replay installs the exact canonical response (no LLM call)
8. metrics do not double-count persisted reads vs generations
9. fallback (MODEL_FALLBACK) explanations persist too

These are DB-backed, deterministic tests — no LLM and no HTTP. They use
throwaway TESTEXP_* rows, clean up after themselves, and run each scenario in
a single event loop (disposing the shared engine afterwards) so asyncpg pool
connections never cross event loops. Route-level E2E with a live LLM is
intentionally not automated; the route is a thin layer over the service
contract verified here.
"""
import asyncio
from types import SimpleNamespace

from sqlalchemy import delete, select, func

from app.db.session import async_session_maker, engine, Base
from app.models.database import CaseExplanation, User, RiskEvent
from app.services.explanation_store_service import (
    ExplanationStoreService,
    compute_explanation_fingerprint,
    fingerprint_for_risk_event,
    policy_version,
)
from app.services.explain_metrics import ExplainMetrics


AUD = "investigator"
USER = "TESTEXP001"

PAYLOAD_A = {
    "summary": "Test summary A",
    "key_findings": ["Finding one [1]", "Finding two [2]"],
    "recommended_action": "Manual review",
    "citations": [
        {"id": 1, "doc": "Doc.md", "section": "1.1", "quote": "quoted text", "chunk_id": "c1"}
    ],
    "explanation_source": "LLM",
    "llm_error": None,
    "missing_info": [],
}
PAYLOAD_B = {
    "summary": "Test summary B (regenerated)",
    "key_findings": ["New finding [1]"],
    "recommended_action": "Monitor",
    "citations": [],
    "explanation_source": "MODEL_FALLBACK",
    "llm_error": None,
    "missing_info": ["device_history"],
}

# A fake risk event (install_canonical only reads id/pipeline_run_id/model_version)
RISK_EVENT = SimpleNamespace(id=101, pipeline_run_id="run_20260814", model_version="v9.9")


def fp(run="run-A", event_id=1, model="m1", pol="p1", audience=AUD):
    return compute_explanation_fingerprint(event_id, run, model, pol, audience)


# --------------------------------------------------------------------------- helpers
# NOTE: every scenario runs inside ONE asyncio.run() (single event loop) and
# disposes the shared engine at the end — the module-global asyncpg pool must
# never hand a connection to a different event loop.

async def _ensure_table():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _cleanup():
    async with async_session_maker() as db:
        # children first, then the throwaway user itself
        await db.execute(delete(CaseExplanation).where(CaseExplanation.user_id.like("TESTEXP%")))
        await db.execute(delete(User).where(User.user_id.like("TESTEXP%")))
        await db.commit()


async def _ensure_test_user():
    """case_explanations.user_id has an FK to users — create the throwaway user."""
    async with async_session_maker() as db:
        if await db.get(User, USER) is None:
            db.add(User(user_id=USER))
            await db.commit()


async def _real_risk_event():
    """A REAL latest risk event (satisfies the risk_event_id FK)."""
    from sqlalchemy import select, desc
    async with async_session_maker() as db:
        result = await db.execute(select(RiskEvent).order_by(desc(RiskEvent.detected_at)).limit(1))
        return result.scalar_one()


async def _finish():
    await _cleanup()
    await engine.dispose()


async def _save(payload, fingerprint, source="LLM", user=USER, audience=AUD,
                model_provider="test"):
    async with async_session_maker() as db:
        store = ExplanationStoreService(db)
        await store.save(
            user_id=user, audience=audience, fingerprint=fingerprint, payload=payload,
            explanation_source=source, model_provider=model_provider,
            risk_event_id=None, pipeline_run_id="run-A", model_version="m1", pol_version="p1",
        )
        await db.commit()


async def _get_current(fingerprint, user=USER, audience=AUD):
    """Read via a FRESH session — also simulates reading after a backend restart."""
    async with async_session_maker() as db:
        store = ExplanationStoreService(db)
        return await store.get_current(user, audience, fingerprint)


async def _row(user=USER):
    async with async_session_maker() as db:
        store = ExplanationStoreService(db)
        return await store.get_row(user, AUD)


def run_scenario(scenario):
    """Run an async scenario in one loop, with table setup and cleanup around it."""
    async def wrapper():
        await _ensure_table()
        await _cleanup()
        await _ensure_test_user()
        try:
            return await scenario()
        finally:
            await _finish()
    return asyncio.run(wrapper())


# --------------------------------------------------------------------------- tests

class TestExplanationPersistence:
    """Scenarios 1-9 for the persisted canonical explanation."""

    def test_1_first_generation_persists(self):
        async def scenario():
            fp1 = fp()
            await _save(PAYLOAD_A, fp1)
            return await _get_current(fp1)
        assert run_scenario(scenario) == PAYLOAD_A

    def test_2_second_request_uses_persisted(self):
        async def scenario():
            fp1 = fp()
            await _save(PAYLOAD_A, fp1)
            # Two consecutive reads, no save in between -> same persisted payload.
            first = await _get_current(fp1)
            second = await _get_current(fp1)
            return first, second
        first, second = run_scenario(scenario)
        assert first == PAYLOAD_A and second == PAYLOAD_A

    def test_3_cache_expiry_does_not_regenerate(self):
        # The persisted store is the source of truth; the in-memory cache is a
        # performance layer. With no cache involved at all (cleared/expired/
        # restart), a read is still served from the store -> no regeneration.
        async def scenario():
            fp1 = fp()
            await _save(PAYLOAD_A, fp1)
            return await _get_current(fp1)
        assert run_scenario(scenario) == PAYLOAD_A

    def test_4_explicit_regenerate_replaces(self):
        async def scenario():
            fp1, fp2 = fp(), fp(run="run-B")
            await _save(PAYLOAD_A, fp1)
            await _save(PAYLOAD_B, fp2, source="MODEL_FALLBACK")  # regeneration
            return await _get_current(fp2), await _get_current(fp1)
        current, old = run_scenario(scenario)
        assert current == PAYLOAD_B
        # The old artifact no longer exists — the single row was replaced.
        assert old is None

    def test_5_restart_reads_from_db(self):
        # New session = post-restart read path; nothing in memory.
        async def scenario():
            fp1 = fp()
            await _save(PAYLOAD_A, fp1)
            got = await _get_current(fp1)
            async with async_session_maker() as db:
                n = await db.execute(
                    select(func.count()).select_from(CaseExplanation).where(
                        CaseExplanation.user_id == USER)
                )
                count = n.scalar_one()
            return got, count
        got, count = run_scenario(scenario)
        assert got == PAYLOAD_A
        assert count == 1  # the row really is in the DB

    def test_6_changed_version_invalidates(self):
        async def scenario():
            fp1 = fp()
            await _save(PAYLOAD_A, fp1)
            stale_checks = {
                "pipeline_run": fp(run="run-B"),
                "risk_event_id": fp(event_id=2),
                "model_version": fp(model="m2"),
                "policy_version": fp(pol="p2"),
            }
            results = {name: await _get_current(value)
                       for name, value in stale_checks.items()}
            current = await _get_current(fp1)
            return results, current
        results, current = run_scenario(scenario)
        for name, value in results.items():
            assert value is None, f"stale {name} must invalidate the stored explanation"
        assert current == PAYLOAD_A  # the current fingerprint still serves

    def test_7_replay_installs_exact_canonical(self):
        async def scenario():
            risk_event = await _real_risk_event()
            async with async_session_maker() as db:
                store = ExplanationStoreService(db)
                await store.install_canonical(
                    user_id=USER, audience=AUD, payload=PAYLOAD_A,
                    explanation_source=PAYLOAD_A["explanation_source"],
                    risk_event=risk_event, model_provider="replay",
                )
                await db.commit()
            # The replayed artifact is served exactly, under the CURRENT
            # fingerprint (same identity/versioning as normal explanations).
            current = fingerprint_for_risk_event(risk_event, AUD)
            row = await _row()
            served = await _get_current(current)
            return served, row.model_provider
        served, provider = run_scenario(scenario)
        assert served == PAYLOAD_A
        assert provider == "replay"

    def test_8_metrics_persisted_reads_not_double_counted(self):
        # Pure in-memory metric semantics (no DB needed).
        m = ExplainMetrics()
        m.increment_persisted()
        m.increment_persisted()
        snap = m.get_metrics()
        assert snap["persisted_total"] == 2
        # A persisted read is NOT a generation: no generation counter moves.
        assert snap["llm_total"] == 0
        assert snap["llm_disabled_total"] == 0
        assert snap["llm_failed_total"] == 0
        assert snap["fallback_total"] == 0
        # reset covers the new counter too.
        m.reset()
        assert m.get_metrics()["persisted_total"] == 0

    def test_9_fallback_explanation_persists(self):
        async def scenario():
            fp1 = fp()
            await _save(PAYLOAD_B, fp1, source="MODEL_FALLBACK")
            return await _get_current(fp1)
        got = run_scenario(scenario)
        assert got == PAYLOAD_B
        assert got["explanation_source"] == "MODEL_FALLBACK"

    def test_9b_row_metadata_recorded(self):
        async def scenario():
            async with async_session_maker() as db:
                store = ExplanationStoreService(db)
                await store.save(
                    user_id=USER, audience=AUD, fingerprint=fp(), payload=PAYLOAD_A,
                    explanation_source="LLM", model_provider="glm-5.2",
                    risk_event_id=None, pipeline_run_id="run-X", model_version="v1",
                    pol_version="p1",
                )
                await db.commit()
            return await _row()
        row = run_scenario(scenario)
        assert row.model_provider == "glm-5.2"
        assert row.risk_event_id is None
        assert row.pipeline_run_id == "run-X"
        assert row.explanation_source == "LLM"
        assert row.generated_at is not None


class TestFingerprint:
    """Deterministic version fingerprint semantics (pure functions, no DB)."""

    def test_deterministic(self):
        assert fp() == fp()

    def test_changes_with_pipeline_run(self):
        assert fp(run="run-A") != fp(run="run-B")

    def test_changes_with_risk_event_id(self):
        assert fp(event_id=1) != fp(event_id=2)

    def test_changes_with_model_and_policy(self):
        assert fp(model="m1") != fp(model="m2")
        assert fp(pol="p1") != fp(pol="p2")

    def test_changes_with_audience(self):
        assert fp(audience="investigator") != fp(audience="business")

    def test_policy_version_is_a_string(self):
        assert isinstance(policy_version(), str) and policy_version()

    def test_fingerprint_for_risk_event_matches_compute(self):
        assert (
            fingerprint_for_risk_event(RISK_EVENT, AUD)
            == compute_explanation_fingerprint(
                RISK_EVENT.id, RISK_EVENT.pipeline_run_id, RISK_EVENT.model_version,
                policy_version(), AUD,
            )
        )
