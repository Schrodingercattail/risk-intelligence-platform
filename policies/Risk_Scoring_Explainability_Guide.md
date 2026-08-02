# Risk Scoring Explainability Guide (Demo Template)

> Status: DEMO TEMPLATE (non-authoritative)
> Purpose: Standardize how the system explains risk drivers using evidence and citations.

## 1. Explanation Objectives
An explanation should be:
- Accurate: grounded in available evidence
- Readable: clear to non-technical business users
- Actionable: suggests next steps and missing information
- Safe: avoids exposing sensitive identifiers or raw PII

## 2. Evidence Types (Conceptual)

### 2.1 ML Factors
ML drivers should be described as evidence-backed signals (e.g., velocity factor corresponds to short-window transfer counts).

### 2.2 Rule Hits
Rules should be explained as threshold-based triggers with the observed values when safe (e.g., "20 transfers in 1 hour").

### 2.3 Graph / Network Signals
Graph signals should be described as relationship indicators (cluster membership, shared device patterns) without exposing raw identifiers.

## 3. Writing Style
- Prefer bullets and numbered reasons.
- Include a short summary, then reasons, then actions.
- Clearly label missing information needed for confirmation.

## 4. Citation Requirement
When policy snippets are provided, explanations should attach citations like `[1] [2]` next to statements that rely on policy/SOP guidance.
If a statement is a hypothesis or inference not covered by policy text, label it as such (e.g., "Possible account takeover (inference)").