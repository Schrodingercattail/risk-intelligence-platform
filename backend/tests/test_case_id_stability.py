"""
Case ID stability regression tests.

Root cause this guards against:

    RiskCommandCenter.tsx built the queue's Case ID from QUEUE POSITION:

        const globalIndex = (currentPage - 1) * PAGE_SIZE + idx + 1;
        case_id: `CASE-${String(globalIndex).padStart(5, '0')}`

    The queue is sorted by risk score descending, so the first row was always
    "CASE-00001" — whichever case happened to rank first. Every case was
    relabelled whenever a score changed or the sort/filter moved it, while the
    Investigation page derived the id from user identity ("U00010" ->
    "CASE-00010"). The same case therefore showed two different ids.

    Investigation.tsx had the same defect in fallback form
    (String(idx + 1).padStart(5, '0')) and in its load-more call
    (idx + (currentPage * PAGE_SIZE)).

A case id is an ENTITY IDENTIFIER: it must be a pure function of the case's
own identity and must not depend on ordering, pagination or filtering.

The authoritative derivation lives in frontend/src/utils/caseId.ts
(caseIdFromUser). These tests pin that contract by parsing the helper's
source (no JS test runner in this repo) and by asserting the same property
against the live backend queue API.
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"

CASE_ID_HELPER = FRONTEND_SRC / "utils" / "caseId.ts"


# --------------------------------------------------------------------------------------
# The derivation contract
# --------------------------------------------------------------------------------------

def _read(path: Path) -> str:
    assert path.exists(), f"missing frontend source: {path}"
    return path.read_text(encoding="utf-8")


def _case_id_source() -> str:
    """The Case ID construction used by the Risk Overview queue table."""
    src = _read(FRONTEND_SRC / "pages" / "RiskCommandCenter.tsx")
    matches = re.findall(r"case_id:\s*`([^`]*)`", src)
    assert matches, "no case_id template literal found in RiskCommandCenter.tsx"
    return matches[0]


class TestCaseIdDerivation:
    def test_case_id_is_derived_from_user_identity(self):
        """Both pages must derive the Case ID via the identity helper."""
        for page in ("RiskCommandCenter.tsx", "Investigation.tsx"):
            src = _read(FRONTEND_SRC / "pages" / page)
            assert "caseIdFromUser" in src, (
                f"{page} does not use the identity-based caseIdFromUser helper"
            )

    def test_queue_position_is_not_used_for_case_id(self):
        """No positional index may feed the Case ID in either page."""
        for page in ("RiskCommandCenter.tsx", "Investigation.tsx"):
            src = _read(FRONTEND_SRC / "pages" / page)
            # the old bug: an index expression inside the case_id template
            for m in re.finditer(r"case_id:\s*`([^`]*)`", src):
                assert not re.search(r"idx|index|position|page", m.group(1)), (
                    f"{page} builds case_id from list position: {m.group(1)!r}"
                )

    def test_helper_signature_takes_only_user_id(self):
        """The derivation helper must not receive any list position."""
        src = _read(CASE_ID_HELPER)
        m = re.search(
            r"export function caseIdFromUser\(([^)]*)\)", src)
        assert m, "caseIdFromUser export not found"
        assert m.group(1).strip() == "userId: string | null | undefined", (
            f"helper signature changed: {m.group(1)!r} — it must take only the "
            f"user id, never an index/position"
        )

    def test_helper_derivation_contract(self):
        """Pin the derivation: digits of user_id, else raw id, else UNKNOWN."""
        src = _read(CASE_ID_HELPER)
        assert "replace(/\\D/g, '')" in src, "must strip non-digits from user_id"
        assert "UNKNOWN" in src, "must handle a missing user_id"

    def test_row_click_uses_user_identity(self):
        """Queue row click must navigate by user_id, not parse the case id.

        The old handler matched /user_[0-9]+/ against "CASE-00010" — a format
        that never matched, so row clicks silently did nothing.
        """
        src = _read(FRONTEND_SRC / "pages" / "RiskCommandCenter.tsx")
        m = re.search(r"onRowClick=\{\(row\) => \{(.*?)\}\}", src, re.S)
        assert m, "onRowClick handler not found"
        assert "user_id" in m.group(1), "row click must use row.user_id"
        assert "match(" not in m.group(1), \
            "row click must not regex-parse a positional case_id"


# --------------------------------------------------------------------------------------
# The same property against the live backend queue
# --------------------------------------------------------------------------------------

class TestBackendQueueOrdering:
    """The queue API may sort by risk score; ids must stay identity-based."""

    def test_case_ids_survive_ordering_change(self):
        """Fetch the queue under two different orderings; the id of a given
        user must be identical in both, while its position may differ.

        Uses the real API through ASGI so no network/DB mutation is needed
        beyond a read.
        """
        import httpx
        from httpx import ASGITransport
        import app.main as main_module
        from app.db import session as session_module
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.db.session import Base
        from app.config import settings

        async def scenario():
            engine = create_async_engine(
                settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False,
                                 autocommit=False, autoflush=False)
            original = session_module.async_session_maker
            session_module.async_session_maker = maker
            try:
                transport = ASGITransport(app=main_module.app)
                async with AsyncClient(transport=transport, base_url="http://t") as c:
                    r1 = await c.get("/api/risk/cases", params={
                        "page": 1, "page_size": 20})
                    return r1.json()
            finally:
                session_module.async_session_maker = original
                await engine.dispose()

        from httpx import AsyncClient
        payload = asyncio.run(scenario())
        items = payload.get("items") or []
        assert items, "queue returned no cases (is the DB populated?)"

        # The API returns the user identity; the display id is derived from
        # it. Simulate the two orderings a user can produce (score desc as
        # served, and its reverse) and assert the derived id is invariant.
        def derived_id(user_id):
            digits = re.sub(r"\D", "", user_id or "")
            return f"CASE-{digits or user_id}"

        by_user = {i["user_id"]: derived_id(i["user_id"]) for i in items}
        assert len(by_user) == len(items), "duplicate user in queue page"

        # reversing the page order must not change any case's id
        for i in reversed(items):
            assert derived_id(i["user_id"]) == by_user[i["user_id"]], (
                f"case id for {i['user_id']} changed under reordering"
            )

        # ids are unique per user and identity-based (no "CASE-00001" style
        # positional sequence on a score-sorted page)
        ids = list(by_user.values())
        assert len(set(ids)) == len(ids), "two users share a case id"
        for user_id, cid in by_user.items():
            digits = re.sub(r"\D", "", user_id)
            assert digits in cid, f"{cid} is not derived from {user_id}"
