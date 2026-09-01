"""
Pipeline reset regression tests.

Root cause this guards against (observed as a 500 on POST /api/pipeline/reset):

    clear_pipeline_data() / clear_all_data() deleted tables in dependency
    order but did NOT delete case_explanations, which holds FOREIGN KEYS to
    both users.user_id and risk_events.id. As soon as one persisted
    explanation existed (any case that had ever been explained/regenerated),
    delete(RiskEvent) raised a ForeignKeyViolation, aborting the whole
    transaction — so reset ALWAYS failed on any system with explanation
    persistence enabled, and the DB was left unchanged (rolled back).

The invariant to protect going forward: EVERY table holding a foreign key
into risk_events or users must be deleted before those parents, otherwise
reset breaks the moment that table has rows.

ISOLATION: the clear paths delete the ENTIRE database, so each scenario runs
on a loop-local engine (the shared asyncpg pool cannot cross event loops)
inside a transaction whose commit is stubbed out and then rolled back — the
development database is left exactly as it was. Seeded rows use the reserved
"U_TEST_RESET" id and are removed afterwards.
"""
import asyncio
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.config import settings
from app.models.database import User, RiskEvent, CaseExplanation
from app.services.pipeline_service import PipelineService

USER = "U_TEST_RESET"  # reserved for this module; never a real account id


def run(coro):
    return asyncio.run(coro)


async def _make_engine_and_maker():
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False,
                         autocommit=False, autoflush=False)
    return engine, maker


async def _seed(maker):
    """Seed the minimal graph that makes the FK violation reachable:
    a user -> risk event -> a PERSISTED EXPLANATION referencing both."""
    async with maker() as db:
        db.add(User(user_id=USER))
        await db.flush()
        ev = RiskEvent(user_id=USER, risk_score=50.0, risk_probability=0.5,
                       risk_level="MEDIUM", ml_score=50.0, rule_score=40.0,
                       graph_score=0.0)
        db.add(ev)
        await db.flush()
        db.add(CaseExplanation(
            user_id=USER, audience="investigator", risk_event_id=ev.id,
            version_fingerprint="test-fp", explanation_payload="{}",
            explanation_source="MODEL_FALLBACK"))
        await db.commit()


async def _cleanup(maker):
    async with maker() as db:
        await db.execute(delete(CaseExplanation).where(CaseExplanation.user_id == USER))
        await db.execute(delete(RiskEvent).where(RiskEvent.user_id == USER))
        await db.execute(delete(User).where(User.user_id == USER))
        await db.commit()


async def _run_clear_rolled_back(maker, method_name: str):
    """Execute a full-database clear path inside a rolled-back transaction.

    clear_pipeline_data/clear_all_data issue DELETEs across every table and
    then commit(). Neutralise commit by subclassing the session (instance
    attribute assignment on a Session is ignored — commit resolves through
    the class), so the service's commit() call becomes a no-op and the
    deletes stay inside the open transaction; capture the return value, then
    rollback — nothing is actually destroyed.
    """
    class _NoCommitSession(AsyncSession):
        async def commit(self):
            pass  # swallow: keep the deletes inside the rolled-back transaction

    no_commit_maker = sessionmaker(
        maker.kw["bind"], class_=_NoCommitSession, expire_on_commit=False,
        autocommit=False, autoflush=False)

    async with no_commit_maker() as db:
        svc = PipelineService(db)
        counts = await getattr(svc, method_name)()
        await db.rollback()
    return counts


async def _counts(maker):
    async with maker() as db:
        return {
            "users": await db.scalar(select(func.count()).select_from(User)),
            "risk_events": await db.scalar(select(func.count()).select_from(RiskEvent)),
            "case_explanations": await db.scalar(
                select(func.count()).select_from(CaseExplanation)),
        }


class TestPipelineReset:
    def test_reset_succeeds_with_persisted_explanations(self):
        """The exact failing scenario: case_explanations rows present."""
        async def scenario():
            engine, maker = await _make_engine_and_maker()
            try:
                await _seed(maker)
                before = await _counts(maker)
                counts = await _run_clear_rolled_back(maker, "clear_pipeline_data")
                return before, counts, await _counts(maker)
            finally:
                await _cleanup(maker)
                await engine.dispose()

        before, counts, after = run(scenario())
        # the FK-holding child was deleted FIRST, so no violation was raised
        assert counts["case_explanations"] >= 1
        assert counts["risk_events"] >= 1
        # and the rollback restored everything (isolation held)
        assert after == before

    def test_clear_all_data_also_handles_persisted_explanations(self):
        """clear_models=true path (clear_all_data) must clear them too."""
        async def scenario():
            engine, maker = await _make_engine_and_maker()
            try:
                await _seed(maker)
                return await _run_clear_rolled_back(maker, "clear_all_data")
            finally:
                await _cleanup(maker)
                await engine.dispose()

        counts = run(scenario())
        assert counts["case_explanations"] >= 1
        assert counts["risk_events"] >= 1

    def test_database_untouched_after_rolled_back_clear(self):
        """The isolation contract itself: a clear that is rolled back leaves
        the seeded rows (and therefore any real data) in place."""
        async def scenario():
            engine, maker = await _make_engine_and_maker()
            try:
                await _seed(maker)
                before = await _counts(maker)
                await _run_clear_rolled_back(maker, "clear_pipeline_data")
                return before, await _counts(maker)
            finally:
                await _cleanup(maker)
                await engine.dispose()

        before, after = run(scenario())
        assert before == after, \
            f"rolled-back clear changed row counts: {before} -> {after}"

    def test_every_fk_child_of_risk_events_is_cleared_before_parents(self):
        """Structural guard: any model referencing risk_events/users must be
        deleted by EVERY full-database clear path, so adding a new child table
        (or a new clear path) cannot silently reintroduce the 500.

        The same constraint is enforced in three places: the two pipeline
        reset paths and the historical-training data reload. Each clears the
        whole database, so each must delete every FK child first.
        """
        from app.models import database as models
        from app.services.historical_training_service import HistoricalTrainingService

        clear_paths = {
            "PipelineService.clear_pipeline_data":
                PipelineService.clear_pipeline_data,
            "PipelineService.clear_all_data":
                PipelineService.clear_all_data,
            "HistoricalTrainingService._load_data_to_db":
                self._historical_reload_method(),
        }
        src = "\n".join(inspect.getsource(fn) for fn in clear_paths.values())

        child_models = []
        for name in dir(models):
            obj = getattr(models, name)
            if not (inspect.isclass(obj) and hasattr(obj, "__tablename__")):
                continue
            if obj.__tablename__ in ("risk_events", "users"):
                continue
            refs_parent = any(
                fk.target_fullname in ("risk_events.id", "users.user_id")
                for col in obj.__table__.columns
                for fk in col.foreign_keys
            )
            if refs_parent:
                child_models.append(obj.__name__)

        assert child_models, "expected at least one FK child of risk_events/users"

        missing = [m for m in sorted(child_models) if f"delete({m})" not in src]
        assert not missing, (
            f"models {missing} reference risk_events/users but are not deleted "
            f"by every clear path — any of them having rows makes the "
            f"reset/retrain 500 (ForeignKeyViolation)"
        )

    @staticmethod
    def _historical_reload_method():
        """The data-reload method that clears the database before training."""
        from app.services.historical_training_service import HistoricalTrainingService
        for name, fn in inspect.getmembers(
                HistoricalTrainingService, inspect.isfunction):
            if "delete(RiskEvent)" in (inspect.getsource(fn) if hasattr(fn, "__code__") else ""):
                return fn
        raise AssertionError(
            "no HistoricalTrainingService method found that clears risk_events "
            "— update this lookup if the reload was renamed")
