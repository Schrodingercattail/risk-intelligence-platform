/**
 * Pure display-formatting helpers for the explanation narrative.
 *
 * The API contract is `key_findings: string[]` and `recommended_action: string`
 * (frontend/src/services/api.ts). The current LLM output may use MULTIPLE array
 * elements to compose ONE conceptual finding (a numbered header line followed
 * by supporting lines), and may pack numbered action steps into a single
 * `recommended_action` string. These helpers recover that structure using
 * STRUCTURAL MARKERS ONLY, so they do not depend on any specific wording:
 *
 *   - a numbered header/step = "N. " at the start of a string (the dot must be
 *     followed by whitespace, so decimals like "96.24" or "(80.0)" never match;
 *     an optional opening bold marker "**N. " is tolerated)
 *   - citation markers "[n]" are left exactly where they appear — these helpers
 *     never touch citation text
 *
 * All transformations are frontend display-only; the API payload is unchanged.
 */

/**
 * Structural marker for a numbered item ("1. ", "**2. ", ...).
 * ^ start, optional bold opener, digits, dot, then whitespace.
 */
const NUMBERED_HEADER = /^\*{0,2}\d+\.\s+/;

export interface KeyFindingGroup {
  /** First line of the group — the numbered header when present. */
  title: string;
  /** Subsequent array elements belonging to this finding. */
  lines: string[];
  /** True when the title starts with a "N. " structural marker. */
  numbered: boolean;
}

/**
 * Group a key_findings array into conceptual findings.
 *
 * Two structural shapes are supported (markers only, no wording assumptions):
 *
 * 1. ONE-ELEMENT-PER-FINDING (current Global Narrative Contract shape): each
 *    array element is `"N. Title\nSupporting sentence"` — the backend merges
 *    the title and its evidence into a single string separated by a newline.
 *    The element is split on `\n`: the first line becomes the group title,
 *    the remaining lines its supporting evidence lines.
 *
 * 2. LEGACY MULTI-ELEMENT: a numbered header element ("1. ML Pattern
 *    Detection Signal** [1]") starts a group; following header-less elements
 *    belong to it. Elements before any header stand alone (bullet groups).
 *
 * Citation markers stay on the exact line where they appear.
 */
export function groupKeyFindings(findings: string[]): KeyFindingGroup[] {
  const groups: KeyFindingGroup[] = [];
  for (const finding of findings) {
    const text = finding.trim();
    if (!text) continue;

    // Split the element on newlines: first line = title, rest = evidence lines.
    const elementLines = text.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);
    const [firstLine, ...restLines] = elementLines;

    if (NUMBERED_HEADER.test(firstLine)) {
      groups.push({ title: firstLine, lines: restLines, numbered: true });
    } else if (restLines.length === 0) {
      // single-line header-less element: either joins the current numbered
      // group as evidence (legacy multi-element shape) or stands alone.
      const current = groups[groups.length - 1];
      if (current && current.numbered) {
        current.lines.push(firstLine);
      } else {
        groups.push({ title: firstLine, lines: [], numbered: false });
      }
    } else {
      // header-less MULTI-LINE element: treat as its own standalone finding
      // (title + evidence), matching the contract's one-element-per-finding shape.
      groups.push({ title: firstLine, lines: restLines, numbered: false });
    }
  }
  return groups;
}

/**
 * Split a recommended_action string into numbered action steps.
 *
 * Steps are detected by the "N. " structural marker starting the text or
 * following whitespace (spaces or newlines), for ANY starting number — the
 * LLM occasionally continues the findings count into the actions ("10. ..."),
 * and the steps must still be split and displayed separately. Step numbering
 * is NOT trusted from the model: steps are renumbered by the caller's list
 * index so the Next Actions section always reads 1., 2., 3. ...
 * If the text contains no numbered marker at all (e.g. the deterministic
 * fallback's "Immediate Investigation"), the whole string is returned as a
 * single element so it renders as one paragraph, exactly as before.
 */
export function splitNumberedSteps(action: string): string[] {
  const trimmed = (action || '').trim();
  if (!trimmed) return [];
  if (!/\*{0,2}\d+\.\s+/.test(trimmed)) return [trimmed];

  // Find where the first numbered step begins (there may be a leading theme
  // line before it, e.g. "Escalate for review:\n1. ..."). Steps may be
  // newline- OR space-separated ("1. A 2. B"). Text only counts as a leading
  // theme when the string does not itself START with a numbered step.
  const startsWithStep = /^\*{0,2}\d+\.\s+/.test(trimmed);
  const firstStep = startsWithStep ? -1 : trimmed.search(/\s\*{0,2}\d+\.\s+/);
  const hasLeadingText = firstStep > 0;
  const stepsBody = hasLeadingText ? trimmed.slice(firstStep + 1) : trimmed;

  const steps = stepsBody
    .split(/\s+(?=\*{0,2}\d+\.\s+)/)
    .map((step) => step.replace(/^\*{0,2}\d+\.\s+/, '').trim())
    .filter((step) => step.length > 0);

  if (steps.length === 0) return [trimmed];
  if (!hasLeadingText) return steps;

  // Keep the leading theme line as the first element; steps follow.
  return [trimmed.slice(0, firstStep).trim(), ...steps].filter((s) => s.length > 0);
}

export interface TextSegment {
  text: string;
  bold: boolean;
}

/**
 * Segment text by markdown emphasis for display: paired "**...**" becomes a
 * bold segment; ORPHAN "**" markers (e.g. a header line that lost its opening
 * marker) are dropped so no stray asterisks are shown. All other text —
 * including citation markers "[n]" — is preserved exactly.
 */
export function splitBoldSegments(text: string): TextSegment[] {
  if (!text) return [];
  const segments: TextSegment[] = [];
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  for (const part of parts) {
    if (!part) continue;
    const boldMatch = part.match(/^\*\*([^*]+)\*\*$/);
    if (boldMatch) {
      segments.push({ text: boldMatch[1], bold: true });
    } else {
      const cleaned = part.replace(/\*\*/g, '');
      if (cleaned) segments.push({ text: cleaned, bold: false });
    }
  }
  return segments;
}
