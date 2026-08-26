# Citation Mapping Taxonomy

## Overview

This document defines the proper citation mapping taxonomy for risk findings to policy documents. It establishes domain constraints to ensure findings cite policies from relevant domains only.

## Executive Summary

The citation mapping system enforces domain constraints to prevent inappropriate policy citations. Each finding type has specific allowed and forbidden policy documents and sections.

### Key Design Principle

**Findings must cite policies from their evidentiary domain.** For example:
- ML signal findings should cite model explainability policies, not transaction monitoring policies
- Graph signal findings should cite network relationship policies, not KYC policies
- Account profile findings should cite customer onboarding policies, not transaction behavior policies

---

## Available Policy Documents

| Document | Sections | Primary Domain |
|----------|----------|----------------|
| `KYC_CDD_Requirements.md` | Principle, Risk-Based Review Tiers, Information Requests, Documentation | **KYC_CDD** |
| `AML_Suspicious_Indicators.md` | Transaction Velocity, Amount Anomalies, Geolocation, Network/Relationship Signals | **MULTI-DOMAIN** |
| `Risk_Scoring_Explainability_Guide.md` | Explanation Objectives, Evidence Types, Writing Style, Citation Requirement | **ML_ANOMALY** |
| `Investigation_and_Action_SOP.md` | Guiding Principles, Investigation Flow, Recommended Actions, Fallback | **INVESTIGATION_SOP** |

### Critical Note on AML_Suspicious_Indicators.md

This document is **multi-domain**:
- Sections 2-4: Transaction behavior (velocity, amount, geolocation)
- Section 5: Network/Relationship signals (clusters, shared devices)

**Citations must reference the specific section, not just the document.**

---

## Finding Type Taxonomy

### 1. ML_SIGNAL Finding Type

**What evidence does this finding represent?**
- ML model outputs (scores, predictions)
- Feature importance (factor contributions)
- Pattern detection anomalies
- LightGBM model signals

**Examples:**
- "ML Signal Score: 85.00"
- "Primary concern: ML Pattern Detection"
- "Elevated trading_frequency_24h (ML-derived factor)"
- "LightGBM model prediction"
- "ML anomaly detected"

**Policy Domain:** ML_ANOMALY

**Allowed documents:**
- `Risk_Scoring_Explainability_Guide.md` (PRIMARY)
  - Section: "Evidence Types → ML Factors"
  - Section: "Explanation Objectives"
- `Investigation_and_Action_SOP.md` (FALLBACK)
  - Section: "Guiding Principles"

**Forbidden documents:**
- `KYC_CDD_Requirements.md` — ML is not about customer verification
- `AML_Suspicious_Indicators.md` — ML output ≠ AML suspicious indicators (except Section 5 for network-specific findings)

---

### 2. RULE_SIGNAL Finding Type

**What evidence does this finding represent?**
- Rule engine hits (threshold-based triggers)
- Suspicious indicator matches
- Binary rule outcomes

**Examples:**
- "Rule Engine Signal Score: 72.50"
- "Hit rule: High Velocity Transfer Threshold"
- "Suspicious: Rapid Fund Movement"

**Policy Domain:** TRANSACTION_BEHAVIOR

**Allowed documents:**
- `AML_Suspicious_Indicators.md` (PRIMARY)
  - Section: "Transaction Velocity & Burst Patterns"
  - Section: "Amount & Behavioral Anomalies"
  - Section: "Geolocation & Access Inconsistencies"
  - Section: "Network / Relationship Signals" (if rule is network-related)
- `Investigation_and_Action_SOP.md` (FALLBACK)
  - Section: "Triage → Evidence Review"

**Forbidden documents:**
- `KYC_CDD_Requirements.md` — Rule hits ≠ customer due diligence
- `Risk_Scoring_Explainability_Guide.md` — Rules are not ML model outputs

---

### 3. GRAPH_SIGNAL Finding Type

**What evidence does this finding represent?**
- Network relationships
- Shared device/IP connections
- Cluster membership
- Account linkage

**Examples:**
- "Connected to 18 other accounts"
- "Elevated Linked Account Network"
- "Shared devices/IPs detected"
- "Graph Network Signal Score: 60.00"
- "Cluster membership detected"

**Policy Domain:** NETWORK_CLUSTER

**Allowed documents:**
- `AML_Suspicious_Indicators.md` (PRIMARY — Section 5 ONLY)
  - Section: "Network / Relationship Signals → Links to Known Risky Clusters"
- `Investigation_and_Action_SOP.md` (FALLBACK)
  - Section: "Evidence Review → network/cluster membership"

**Forbidden documents:**
- `KYC_CDD_Requirements.md` — Network signals ≠ customer onboarding
- `Risk_Scoring_Explainability_Guide.md` — Network is not ML explainability
- `AML_Suspicious_Indicators.md` — Sections 2-4 (transaction behavior only)

**Critical Constraint:** Network-related terms must have higher classification priority than generic "account" keyword to prevent misclassification as ACCOUNT_PROFILE.

---

### 4. ACCOUNT_PROFILE Finding Type

**What evidence does this finding represent?**
- Account age/tenure
- New account status
- Customer verification status
- Onboarding completion

**Examples:**
- "Elevated New Account Risk"
- "Elevated account_age_days"
- "New account detected (< 30 days)"
- "Customer verification pending"

**Policy Domain:** KYC_CDD

**Allowed documents:**
- `KYC_CDD_Requirements.md` (PRIMARY)
  - Section: "Principle"
  - Section: "Suggested Risk-Based Review Tiers → Enhanced Due Diligence"
  - Section: "Common Information Requests → Identity & Verification"
  - Section: "Account Context"
- `Investigation_and_Action_SOP.md` (FALLBACK)
  - Section: "Enhanced Due Diligence Request"

**Forbidden documents:**
- `AML_Suspicious_Indicators.md` (Sections 2-4) — Account age ≠ transaction behavior
- `Risk_Scoring_Explainability_Guide.md` — Account profile is not model output

---

### 5. ACTION_RECOMMENDATION Finding Type

**What evidence does this finding represent?**
- Recommended investigation steps
- Escalation guidance
- Control suggestions
- Workflow procedures

**Examples:**
- "Manual Review Recommended"
- "Request Enhanced Due Diligence"
- "Consider temporary limits"
- "Escalate to senior investigator"

**Policy Domain:** INVESTIGATION_SOP

**Allowed documents:**
- `Investigation_and_Action_SOP.md` (PRIMARY)
  - Section: "Standard Investigation Flow"
  - Section: "Recommended Actions"

**Forbidden documents:**
- All other documents — Actions are procedures, not evidence domains

---

### 6. TRANSACTION_BEHAVIOR Finding Type

**What evidence does this finding represent?**
- Trading frequency/velocity
- Transfer patterns
- Volume anomalies
- Transaction bursts

**Examples:**
- "High Trading Frequency"
- "Elevated withdrawal_frequency_24h"
- "Velocity anomaly detected"
- "Rapid fund movement"

**Policy Domain:** TRANSACTION_BEHAVIOR

**Allowed documents:**
- `AML_Suspicious_Indicators.md` (PRIMARY)
  - Section: "Transaction Velocity & Burst Patterns"
  - Section: "Amount & Behavioral Anomalies"
- `Investigation_and_Action_SOP.md` (FALLBACK)
  - Section: "Evidence Review → suspicious transactions"

**Forbidden documents:**
- `KYC_CDD_Requirements.md` — Transaction behavior ≠ onboarding
- `Risk_Scoring_Explainability_Guide.md` — Transaction patterns ≠ ML methodology

---

## Section-Level Validation Requirements

Since `AML_Suspicious_Indicators.md` is multi-domain, citations must validate the **section path**, not just the document.

### Section Path → Domain Mapping

| Section Path | Domain | Allowed Finding Types |
|---------------|--------|----------------------|
| `Transaction Velocity & Burst Patterns` | TRANSACTION_BEHAVIOR | RULE_SIGNAL, TRANSACTION_BEHAVIOR |
| `Amount & Behavioral Anomalies` | TRANSACTION_BEHAVIOR | RULE_SIGNAL, TRANSACTION_BEHAVIOR |
| `Geolocation & Access Inconsistencies` | TRANSACTION_BEHAVIOR | RULE_SIGNAL, TRANSACTION_BEHAVIOR |
| `Network / Relationship Signals` | NETWORK_CLUSTER | GRAPH_SIGNAL, RULE_SIGNAL (if network rule) |

---

## Implementation Constraints

### Finding Type → Document Mapping

```python
ALLOWED_POLICY_TYPES = {
    FindingType.ACCOUNT_PROFILE: [
        "KYC_CDD_Requirements.md",
        "Customer_Identification_Policy.md",
    ],
    FindingType.GRAPH_SIGNAL: [
        "AML_Suspicious_Indicators.md",  # Section 5 only
        "Network_Relationship_Policy.md",
    ],
    FindingType.RULE_SIGNAL: [
        "AML_Suspicious_Indicators.md",  # Sections 2-4
        "Transaction_Monitoring_Policy.md",
    ],
    FindingType.ML_SIGNAL: [
        "Risk_Scoring_Explainability_Guide.md",
    ],
    FindingType.TRANSACTION_BEHAVIOR: [
        "AML_Suspicious_Indicators.md",  # Sections 2-3
        "Transaction_Monitoring_Policy.md",
    ],
    FindingType.ACTION_RECOMMENDATION: [
        "Investigation_and_Action_SOP.md",
    ],
}
```

### Classification Priority

To prevent misclassification (e.g., "Elevated Linked Account Network" → ACCOUNT_PROFILE due to "account" keyword), classification priority must be:

1. Direct signal score mentions
2. Network/cluster-specific terms (highest priority for generic keywords)
3. Factor-based classification
4. Evidence-based classification
5. Score-based classification
6. Text-based keyword matching (lowest priority)

---

## Summary Table

| Finding Type | Primary Policy | Fallback Policy | Forbidden Policies |
|--------------|----------------|-----------------|-------------------|
| ML_SIGNAL | Risk_Scoring_Explainability_Guide.md | Investigation_and_Action_SOP.md | KYC_CDD_Requirements.md, AML_Suspicious_Indicators.md (sections 2-4) |
| RULE_SIGNAL | AML_Suspicious_Indicators.md (sections 2-4) | Investigation_and_Action_SOP.md | KYC_CDD_Requirements.md |
| GRAPH_SIGNAL | AML_Suspicious_Indicators.md (section 5) | Investigation_and_Action_SOP.md | KYC_CDD_Requirements.md |
| ACCOUNT_PROFILE | KYC_CDD_Requirements.md | Investigation_and_Action_SOP.md | AML_Suspicious_Indicators.md (sections 2-4) |
| TRANSACTION_BEHAVIOR | AML_Suspicious_Indicators.md (sections 2-3) | Investigation_and_Action_SOP.md | KYC_CDD_Requirements.md |
| ACTION_RECOMMENDATION | Investigation_and_Action_SOP.md | None | All evidence policies |

---

## Related Documentation

- [Citation System Design](citation-system-design.md) — Implementation architecture and validation strategy
- [LLM Explanation Design](llm-explanation-design.md) — LLM explanation subsystem design
