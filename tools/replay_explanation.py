#!/usr/bin/env python3
"""
Replay a saved explanation artifact into the canonical persisted store.

Development/evaluation utility: installs a saved raw explanation JSON (e.g.
eval/llm_raw_explanations_v2/U00299.json) as the CURRENT canonical explanation
for that case, so the frontend serves exactly that artifact — with NO LLM call.

This is a CLI tool, not a public API endpoint (deliberately: installing
arbitrary payloads is an unsafe cache-injection-style operation and must not be
exposed). It uses the same canonical identity/versioning logic as normal
persisted explanations (ExplanationStoreService): the artifact is installed
against the CURRENT risk event version fingerprint. If the underlying case is
later re-scored (new pipeline run) the replayed explanation becomes stale and
the next normal read regenerates, exactly like any persisted explanation.

The artifact file itself is read-only to this tool — it is never modified.

Usage (run from repo root with the backend venv active; DB must be reachable):
    python tools/replay_explanation.py --artifact eval/llm_raw_explanations_v2/U00299.json
    python tools/replay_explanation.py --artifacts-dir eval/llm_raw_explanations_v2
    python tools/replay_explanation.py --artifact <path> --user-id U00299 --audience investigator
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select, desc  # noqa: E402
from app.db.session import async_session_maker  # noqa: E402
from app.models.database import RiskEvent  # noqa: E402
from app.services.explanation_store_service import ExplanationStoreService  # noqa: E402


# Fields required for the payload to round-trip through ExplanationResponse.
REQUIRED_FIELDS = ("summary", "key_findings", "recommended_action", "citations")


def load_artifact(path: Path):
    """Load and validate an explanation artifact. Returns (user_id, payload) or exits."""
    try:
        payload = json.loads(path.read_text())
    except Exception as e:
        print(f"  ERROR reading {path.name}: {e}")
        return None, None

    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        print(f"  ERROR {path.name}: missing required fields {missing} — not replayed")
        return None, None

    user_id = path.stem  # artifacts are named <user_id>.json
    return user_id, payload


async def replay_one(artifact_path: Path, audience: str, user_id_override=None, commit=True) -> bool:
    """Install one artifact as the canonical explanation. Returns True on success."""
    user_id, payload = load_artifact(artifact_path)
    if user_id is None:
        return False
    if user_id_override:
        user_id = user_id_override

    async with async_session_maker() as db:
        result = await db.execute(
            select(RiskEvent)
            .where(RiskEvent.user_id == user_id)
            .order_by(desc(RiskEvent.detected_at))
            .limit(1)
        )
        risk_event = result.scalar_one_or_none()
        if risk_event is None:
            print(f"  ERROR {user_id}: no risk event found in DB — not replayed")
            return False

        store = ExplanationStoreService(db)
        await store.install_canonical(
            user_id=user_id,
            audience=audience,
            payload=payload,
            explanation_source=payload.get("explanation_source", "MODEL_FALLBACK"),
            risk_event=risk_event,
            model_provider="replay",
        )
        if commit:
            await db.commit()

    print(f"  {user_id}: installed as canonical ({audience}, "
          f"source={payload.get('explanation_source', 'MODEL_FALLBACK')})")
    return True


def main():
    p = argparse.ArgumentParser(
        description="Install saved explanation artifacts as canonical persisted explanations (no LLM call)"
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--artifact", help="Path to a single <user_id>.json artifact")
    g.add_argument("--artifacts-dir", help="Directory of <user_id>.json artifacts to replay")
    p.add_argument("--user-id", help="Override user_id (default: artifact filename stem)")
    p.add_argument("--audience", default="investigator", choices=["investigator", "business"],
                   help="Audience the artifact was generated for (default: investigator)")
    args = p.parse_args()

    paths = (
        [Path(args.artifact)] if args.artifact
        else sorted(Path(args.artifacts_dir).glob("*.json"))
    )
    if not paths:
        print(f"No artifacts found.")
        sys.exit(1)

    if args.user_id and args.artifacts_dir:
        p.error("--user-id is only valid together with --artifact (a directory replay derives user_id from each filename)")

    print(f"Replaying {len(paths)} artifact(s) as canonical explanations (audience={args.audience})...")
    ok = 0
    for path in paths:
        if asyncio.run(replay_one(path, args.audience, user_id_override=args.user_id)):
            ok += 1

    failed = len(paths) - ok
    print(f"Done: {ok}/{len(paths)} installed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
