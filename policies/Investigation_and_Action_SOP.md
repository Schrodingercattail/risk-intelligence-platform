# Investigation & Action SOP (Demo Template)

> Status: DEMO TEMPLATE (non-authoritative)
> Purpose: Provide citable actions and escalation steps for the demo platform.
> Replace with your organization's official SOP before production.

## 1. Guiding Principles
- Actions should be proportional to risk and evidence.
- Decisions should be explainable and auditable.
- Automated outputs (ML scores, rules) should support—not replace—human judgment.

## 2. Standard Investigation Flow

### 2.1 Triage
1. Review risk level and primary drivers (ML factors, rule hits, graph signals).
2. Validate whether key evidence is present (transaction burst, amount anomaly, location mismatch).
3. Identify missing information required to confirm or refute risk hypotheses.

### 2.2 Evidence Review
- Check top suspicious transactions (time, amount, counterparties).
- Compare recent behavior vs historical baselines.
- Review network/cluster membership and shared entities.

### 2.3 Decision & Documentation
- Record rationale and evidence references.
- Document what information was missing and whether it was requested.

## 3. Recommended Actions (Non-Automated)

### 3.1 Manual Review
Use when risk is high or evidence is ambiguous. Confirm whether anomalies are explained by legitimate activity.

### 3.2 Temporary Limits / Controls
Consider temporary outbound limits when:
- High velocity + large amount anomaly is observed
- There are signs of compromise (location/device mismatch)

### 3.3 Enhanced Due Diligence Request
Request additional information when:
- Risk factors indicate potential AML concern
- Source of funds context is missing

### 3.4 Escalation
Escalate to senior investigators or compliance when:
- Links to known risky clusters exist
- Patterns strongly indicate suspicious activity
- Repeated anomalies persist after prior interventions

## 4. Fallback & Safety
If narrative generation fails, the system should return structured evidence-based explanations (model/rule/graph) without blocking investigator workflows.