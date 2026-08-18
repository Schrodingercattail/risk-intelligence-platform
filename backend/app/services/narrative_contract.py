"""
Global Narrative Contract — case-invariant presentation layer.

Every explanation (LLM or fallback, any user, any score combination) passes
through `apply_narrative_contract()` before citation retrieval, so the final
payload obeys the same invariants:

SECTIONS (stable):   "What this means (Policy-backed)" / "Key Risk Findings" /
                     "Next Actions (SOP-aligned)" (section presence is the
                     response schema: summary / key_findings / recommended_action)
NUMBERING:           findings numbered 1..N by the BACKEND (never the model);
                     actions numbered 1..M independently (own scope, restarts at 1);
                     citation IDs are a THIRD, independent numbering.
SCORING DETAILS:     no contribution points (+N / "contributes N") in
                     user-facing narrative (kept in Canonical Evidence only).
GRAPH ZERO:          graph_score == 0 with no graph evidence is NOT a risk
                     finding: it is removed from the findings list and folded
                     into a neutral summary note; it never receives a citation.
PROVENANCE:          no "detected by <source>" user-facing wording.
FORMAT:              any bullet/bold/mixed list style normalized to plain
                     numbered lines; citation markers preserved verbatim.

Numbering is a renderer concern, not an LLM reasoning concern.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

# Patterns that must never appear in user-facing narrative text.
_CONTRIBUTION_RE = re.compile(
    r"(contributes\s*\+?\s*\d|\+\s*\d+\s*(?:to\s+the\s+)?(?:rule\s+)?score"
    r"|\bcontribution\s*[:=]|\brule\s+contribution|\(\+\d+\))",
    re.IGNORECASE,
)
_PROVENANCE_RE = re.compile(r"detected\s+by\s+(feature|rule|graph|ml)", re.IGNORECASE)
_RAW_FIELD_RE = re.compile(
    r"\b(account_age_days|trade_frequency_24h|withdrawal_frequency_24h"
    r"|first_withdrawal_flag|opposite_trade_ratio|shared_device_count"
    r"|linked_account_count|withdrawal_risk_score)\b"
)
_RAW_THRESHOLD_RE = re.compile(r"[a-z_0-9]+\s*[<>=!]+\s*[\d.]+(?:\s*(?:AND|and|OR|or)\s*[a-z_0-9]+\s*[<>=!]+\s*[\d.]+)*")
_CITATION_MARK_RE = re.compile(r"\[(\d+)\]")

# Findings whose subject is the ABSENCE of a graph signal: informational
# context, not a risk finding (never numbered, never cited).
_GRAPH_ZERO_RE = re.compile(
    r"(no\s+(?:detected\s+)?(?:graph|network)\s+(?:signal|relationship|network)"
    r"|graph\s+(?:detection\s+)?score\s*(?:of\s*)?(?:is\s*)?0(?:\.0)?\b"
    r"|graph_score\s*=\s*0"
    r"|no\s+connected\s+(?:graph|network)"
    r"|score\s*\(?(?:0|0\.0)\)?(?![\d.]))",
    re.IGNORECASE,
)

_LIST_MARKER_RE = re.compile(
    r"^[\s]*(?:(?:\*{0,2})\d+[\.\)](?:\*{1,2})?|[-•]+|\*(?![-•\d]))\s*")


def _strip_list_marker(line: str) -> str:
    """Remove any leading bullet/number marker (backend owns numbering)."""
    return _LIST_MARKER_RE.sub("", line).strip()


def _has_citation(text: str) -> Optional[int]:
    m = _CITATION_MARK_RE.search(text)
    return int(m.group(1)) if m else None


def normalize_findings(findings: List[str]) -> Tuple[List[str], Optional[str]]:
    """
    Normalize the findings list to the contract's canonical form.

    - strips model-generated list markers/bold numbering from every element
    - drops EMPTY elements
    - TITLE/EVIDENCE MERGE: when the model emits a short title line followed
      by an evidence sentence as separate elements (both un-cited titles or
      plain sentences), the evidence line is folded into the preceding finding
      as its supporting line — one conceptual finding, one number, one
      optional citation (taken from the TITLE line).
    - recognizes "graph-zero informational notes" and extracts them from the
      findings list (returned separately as a context note)
    - renumbers 1..N deterministically (the model never numbers)

    Returns (numbered_findings, graph_zero_note).
    """
    cleaned_elements: List[Tuple[str, Optional[int]]] = []  # (text, citation_id)
    for raw in findings or []:
        if not isinstance(raw, str):
            continue
        lines = raw.split("\n")
        cleaned_lines = []
        for i, line in enumerate(lines):
            cleaned = _strip_list_marker(line) if i == 0 or _LIST_MARKER_RE.match(line) else line.strip()
            if cleaned:
                cleaned_lines.append(cleaned)
        if not cleaned_lines:
            continue
        text = "\n".join(cleaned_lines)
        cleaned_elements.append((text, _has_citation(text)))

    # Title/evidence merge: an element that starts lowercase or with an
    # evidence-style prefix and follows a titled finding is a supporting line.
    merged: List[Tuple[str, Optional[int]]] = []
    for text, cid in cleaned_elements:
        first_line = text.split("\n")[0]
        is_support = (
            bool(merged)
            and not cid
            and not merged[-1][1] is None or bool(merged) and not cid
        )
        # simpler deterministic rule: evidence line = starts lowercase, a digit,
        # or an evidence prefix, and is NOT itself a known finding title
        evidence_style = bool(re.match(r"^[a-z0-9\"']|(An? |The )", first_line)) and len(
            [w for w in first_line.split() if w[0].isupper()]) <= 4
        if merged and not cid and evidence_style:
            merged[-1] = (merged[-1][0].rstrip() + "\n" + text, merged[-1][1])
        else:
            merged.append((text, cid))

    numbered: List[str] = []
    graph_zero_note: Optional[str] = None
    for text, cid in merged:
        if _GRAPH_ZERO_RE.search(text) and not cid:
            if graph_zero_note is None:
                graph_zero_note = text
            continue
        numbered.append(f"{len(numbered) + 1}. {text}")

    return numbered, graph_zero_note


def normalize_actions(action_text: str) -> str:
    """
    Normalize recommended_action into independently numbered steps 1..M.

    The model's own numbering (which may wrongly continue the findings count)
    is stripped; the backend renumbers deterministically. A leading theme line
    ("Escalate for review:") is preserved unnumbered before the steps.
    """
    if not action_text:
        return action_text

    raw_lines = [l for l in action_text.split("\n") if l.strip()]
    theme: List[str] = []
    steps: List[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if _LIST_MARKER_RE.match(stripped):
            step = _strip_list_marker(stripped)
            if step:
                steps.append(step)
        elif not steps:
            theme.append(stripped)  # prose before the first step = theme line
        else:
            steps[-1] = steps[-1].rstrip() + " " + stripped  # continuation

    if not steps:
        return "\n".join(theme)  # single paragraph action (fallback shape)

    out: List[str] = []
    if theme:
        out.append(" ".join(theme))
    out.extend(f"{i}. {s}" for i, s in enumerate(steps, start=1))
    return "\n".join(out)


def scrub_narrative_text(text: str) -> str:
    """
    Remove contract-violating fragments from user-facing text.

    Only presentation-level removals: contribution points and
    "detected by <source>" provenance. Raw field names / threshold syntax are
    guarded by tests (the prompt prevents them; a scrub would corrupt text).
    """
    if not text:
        return text
    text = _CONTRIBUTION_RE.sub("", text)
    text = _PROVENANCE_RE.sub("", text)
    return re.sub(r"\s{2,}", " ", text).replace(" — ", " — ").strip()


def _merge_by_canonical_names(
    findings: List[str], canonical_names: List[str]
) -> List[str]:
    """
    Rebuild the findings list as ONE element per canonical finding.

    Operates LINE-level, not element-level: the model may emit titles and
    evidence sentences as separate elements, as multiple lines inside one
    element, or mixed. Every physical line is classified as a TITLE iff its
    head (text before the first punctuation, list marker stripped) matches a
    canonical finding name head (exact or whole-word-prefix). TITLE lines
    start a new finding; all other lines append as evidence to the current
    finding. Lines before the first title are dropped as prose. This is a
    structural key — no per-sentence heuristics, no case specifics.
    """
    # Content-word signature: hyphens->spaces, drop articles, prefix each word
    # to 5 chars (handles singular/plural and "relationship(s)"), keep order.
    _STOP = {"a", "an", "the", "of", "with", "to", "and", "for", "in", "on"}

    def _signature(text: str) -> List[str]:
        text = _LIST_MARKER_RE.sub("", text.strip()).strip()
        head = re.split(r"[—–\.\[\(;:,]", text, maxsplit=1)[0]
        head = head.replace("-", " ").lower()
        return [w[:5] for w in head.split() if w and w not in _STOP]

    # signature per canonical name; keep them in a list for ordering checks
    name_sigs = [_signature(n) for n in canonical_names if n]
    name_sig_set = {tuple(s) for s in name_sigs if s}

    def _is_title_line(line: str) -> bool:
        sig = tuple(_signature(line))
        if len(sig) < 2:
            return False
        if sig in name_sig_set:
            return True
        # allow leading-signature match: the model title may carry extra
        # trailing descriptors ("Coordinated trading pattern indicator")
        for ns in name_sig_set:
            if sig[:len(ns)] == ns or ns[:len(sig)] == sig:
                return True
        return False

    merged: List[str] = []
    for raw in findings or []:
        if not isinstance(raw, str):
            continue
        for line in raw.split("\n"):
            line = line.rstrip()
            if not line.strip():
                continue
            if _is_title_line(line):
                merged.append(_LIST_MARKER_RE.sub("", line.strip()))
            elif merged:
                merged[-1] = merged[-1].rstrip() + "\n" + line.strip()
            # line before any title: prose intro — dropped
    return merged


def apply_narrative_contract(
    explanation: Dict[str, Any],
    canonical_finding_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Enforce the Global Narrative Contract on an explanation payload (in place).

    - findings: deterministic 1..N numbering, graph-zero extracted
    - summary: graph-zero note appended as neutral context if present,
      contribution/provenance fragments scrubbed
    - recommended_action: independent 1..M numbering

    canonical_finding_names: the finding NAMES from the canonical evidence
    (EvidenceService.get_canonical_evidence). When supplied, an element is a
    TITLE iff its first line starts with one of these names — everything else
    is an evidence line merged into the preceding title. This is a structural
    key (no wording heuristics) and guarantees the narrative's findings are
    exactly the canonical findings, each numbered once.
    """
    findings = explanation.get("key_findings") or []
    if canonical_finding_names:
        findings = _merge_by_canonical_names(findings, canonical_finding_names)
    numbered, graph_zero_note = normalize_findings(
        [scrub_narrative_text(f) for f in findings])
    explanation["key_findings"] = numbered

    summary = explanation.get("summary") or ""
    summary = scrub_narrative_text(summary)
    if graph_zero_note:
        note = (" No graph signal was detected (a graph score of 0 means no "
                "network relationship was found).")
        if "no graph signal" not in summary.lower():
            summary = summary.rstrip() + note
    explanation["summary"] = summary

    action = explanation.get("recommended_action") or ""
    explanation["recommended_action"] = normalize_actions(scrub_narrative_text(action))

    return explanation


# ----------------------------------------------------------------------------
# Generic invariant validation (used by tests and live acceptance checks)
# ----------------------------------------------------------------------------

def validate_narrative_invariants(payload: Dict[str, Any]) -> List[str]:
    """
    Check a final explanation payload against the Global Narrative Contract.

    Returns a list of violation descriptions (empty == compliant). Designed to
    run on ANY case — no user-id or content-specific assertions.
    """
    violations: List[str] = []
    findings = payload.get("key_findings") or []
    action = payload.get("recommended_action") or ""
    citations = payload.get("citations") or []
    all_text = " ".join(findings) + " " + action + " " + (payload.get("summary") or "")
    low = all_text.lower()

    # 1. Findings numbered 1..N contiguously, no stray markers.
    for i, f in enumerate(findings, start=1):
        if not isinstance(f, str) or not f.strip():
            violations.append(f"finding {i}: empty/non-string")
            continue
        first = f.split("\n")[0]
        if not first.startswith(f"{i}. "):
            violations.append(f"finding {i}: bad numbering/prefix: {first[:40]!r}")
        if re.match(r"^[\s]*[-*•]", first):
            violations.append(f"finding {i}: bullet marker leaked: {first[:40]!r}")

    # 2. Actions numbered 1..M independently (own scope).
    action_lines = [l.strip() for l in action.split("\n") if l.strip()]
    step_lines = [l for l in action_lines if re.match(r"^\d+\.\s", l)]
    if step_lines:
        for expected, line in enumerate(step_lines, start=1):
            if not line.startswith(f"{expected}. "):
                violations.append(f"action step {expected}: bad numbering: {line[:40]!r}")

    # 3. No contribution leakage.
    m = _CONTRIBUTION_RE.search(all_text)
    if m:
        violations.append(f"contribution leakage: {m.group(0)!r}")

    # 4. No provenance wording.
    m = _PROVENANCE_RE.search(all_text)
    if m:
        violations.append(f"provenance wording: {m.group(0)!r}")

    # 5. No raw implementation thresholds / field names.
    m = _RAW_THRESHOLD_RE.search(all_text)
    if m:
        violations.append(f"raw threshold syntax: {m.group(0)!r}")
    m = _RAW_FIELD_RE.search(all_text)
    if m:
        violations.append(f"raw field name: {m.group(0)!r}")

    # 6. Graph-zero must not be a positive finding.
    for f in findings:
        if _GRAPH_ZERO_RE.search(f):
            violations.append(f"graph-zero appears as a numbered finding: {f[:40]!r}")

    # 7. Citation markers <-> citation entries bijection.
    cited_ids = {int(x) for x in _CITATION_MARK_RE.findall(all_text)}
    entry_ids = [c.get("id") for c in citations]
    if sorted(entry_ids) != sorted(set(entry_ids)):
        violations.append("duplicate citation entry IDs")
    if cited_ids != set(entry_ids):
        violations.append(f"marks {sorted(cited_ids)} != entries {sorted(entry_ids)}")
    if entry_ids and sorted(entry_ids) != list(range(1, len(entry_ids) + 1)):
        violations.append(f"citation IDs not contiguous from 1: {sorted(entry_ids)}")

    # 8. ML detector signal present when ML score is high (payload-agnostic:
    #    look for the /100 pattern with the not-a-probability qualifier).
    if "ml" in low and "/100" in all_text and "calibrated probability" not in low:
        violations.append("ML score shown without the not-a-calibrated-probability qualifier")

    return violations
