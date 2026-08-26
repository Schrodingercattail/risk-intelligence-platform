# Citation System Design

## Overview

The citation system provides policy-backed explanations for risk findings. It enforces domain constraints to ensure findings cite policies from relevant evidentiary domains only, preventing inappropriate cross-domain citations.

## Architecture

### Core Components

| Component | File | Responsibility |
|-----------|------|-----------------|
| Policy Router | `citation_policy_router.py` | Defines domain constraints and allowed/forbidden documents |
| Retrieval Service | `citation_retrieval_service.py` | Domain-enforced RAG retrieval with pre-filter validation |
| Coverage Service | `citation_coverage_service.py` | Citation generation and coverage validation |
| Mapper | `citation_mapper.py` | Finding classification and finding-to-policy mapping |
| Validator | `citation_validator.py` | Citation quality validation |
| Normalizer | `citation_normalizer.py` | Citation text normalization and deduplication |
| Registry | `citation_registry.py` | Citation deduplication and budget control |

### Citation Pipeline

```
Risk Findings → Classification → Domain Enforcement → RAG Retrieval → Validation → Output
                   (Mapper)        (Policy Router)      (Coverage Service)    (Validator)
```

## Domain Enforcement Design

### Constraint Principle

**Citations are validated BEFORE retrieval, not after.** The policy router enforces domain constraints at the retrieval layer, preventing irrelevant documents from being considered.

### Finding Type Classification

Each finding is classified into one of six types:

1. **ML_SIGNAL** — Model outputs, feature importance, pattern detection
2. **GRAPH_SIGNAL** — Network relationships, clusters, shared devices
3. **RULE_SIGNAL** — Rule engine hits, threshold triggers
4. **TRANSACTION_BEHAVIOR** — Velocity, volume, transaction patterns
5. **ACCOUNT_PROFILE** — Account age, verification status, onboarding
6. **ACTION_RECOMMENDATION** — Investigation steps, escalation guidance

### Domain Constraint Rules

| Finding Type | Allowed Documents | Forbidden Sections |
|--------------|------------------|-------------------|
| **ML_SIGNAL** | `Risk_Scoring_Explainability_Guide.md` | Transaction, Velocity, KYC, Network |
| **GRAPH_SIGNAL** | `AML_Suspicious_Indicators.md` (Section 5 only) | KYC, Transaction, Velocity |
| **ACCOUNT_PROFILE** | `KYC_CDD_Requirements.md` | Transaction, Network |
| **RULE_SIGNAL** | `AML_Suspicious_Indicators.md` (Sections 2-4) | KYC, Verification |
| **TRANSACTION_BEHAVIOR** | `AML_Suspicious_Indicators.md` (Sections 2-3) | KYC, Network |

### Section-Level Validation

For multi-domain documents like `AML_Suspicious_Indicators.md`, citations validate at the **section level**:

| Section Path | Domain | Allowed Finding Types |
|---------------|--------|----------------------|
| `Transaction Velocity & Burst Patterns` | TRANSACTION_BEHAVIOR | RULE_SIGNAL, TRANSACTION_BEHAVIOR |
| `Amount & Behavioral Anomalies` | TRANSACTION_BEHAVIOR | RULE_SIGNAL, TRANSACTION_BEHAVIOR |
| `Geolocation & Access Inconsistencies` | TRANSACTION_BEHAVIOR | RULE_SIGNAL, TRANSACTION_BEHAVIOR |
| `Network / Relationship Signals` | NETWORK_CLUSTER | GRAPH_SIGNAL, RULE_SIGNAL (network rules) |

## Validation Strategy

### Multi-Layer Validation

1. **Pre-Retrieval Validation** (Policy Router)
   - Document-level allowlist enforcement
   - Section-level forbidden checks
   - Finding type → domain validation

2. **Post-Retrieval Validation** (Coverage Service)
   - Citation relevance scoring
   - Duplicate detection and removal
   - Maximum citation count enforcement (default: 5)

3. **Quality Validation** (Validator)
   - Citation text normalization
   - Metadata chunk filtering
   - Reference format validation

### Classification Priority

To prevent misclassification (e.g., "Elevated Linked Account Network" misclassified as ACCOUNT_PROFILE due to "account" keyword), classification uses priority-based matching:

1. Direct signal score mentions (highest)
2. Network/cluster-specific terms
3. Factor-based classification
4. Evidence-based classification
5. Score-based classification
6. Generic keyword matching (lowest)

## Implementation Decisions

### 1. Pre-Retrieval vs Post-Retrieval Filtering

**Decision:** Enforce domain constraints BEFORE RAG retrieval.

**Rationale:** Prevents irrelevant documents from being considered, reduces noise, and ensures citation quality at the source rather than filtering after irrelevant content is retrieved.

### 2. Section-Level Validation

**Decision:** Validate citations at section path level, not document level.

**Rationale:** Multi-domain documents (e.g., AML_Suspicious_Indicators.md) contain sections for different domains. Section-level validation prevents cross-section mismatches.

### 3. Citation Budget Control

**Decision:** Maximum 5 citations per explanation, with deduplication.

**Rationale:** Prevents citation overload, ensures explanations remain concise, and avoids redundant policy references.

### 4. Finding Classification Priority

**Decision:** Network/cluster terms have higher priority than generic "account" keyword.

**Rationale:** Prevents network findings from being misclassified as account profile findings, which would cause inappropriate KYC citations.

### 5. Metadata Chunk Filtering

**Decision:** Filter out metadata-only chunks (e.g., "### Analysis Date:", "### Status:") from citation results.

**Rationale:** Metadata chunks are not policy content and should not appear as citations.

## API Integration

### Explain Endpoint

The `/api/risk/explain` endpoint uses the citation retrieval service:

```python
citation_service = create_citation_retrieval_service()
retrieval_result = citation_service.retrieve_citations(
    key_findings=key_findings,
    ml_score=ml_score,
    rule_score=rule_score,
    graph_score=graph_score,
    has_graph_evidence=has_graph_evidence,
    audience=audience,
    target_citation_count=5
)
citations = retrieval_result.citations
```

### Citation Output Format

Each citation contains:
- `id`: Sequential citation number [1], [2], [3], etc.
- `doc`: Policy document name
- `section`: Section path within document
- `text`: Relevant policy text excerpt
- `relevance`: Relevance score (0-1)

### Finding-to-Citation Mapping

The system tracks which findings cite which policies:

```python
finding_to_citation = {
    "ML Signal Score: 96.24": ["risk_scoring_explainability_guide.md"],
    "Elevated Linked Account Network": ["aml_suspicious_indicators.md"],
    "Elevated New Account Risk": ["kyc_cdd_requirements.md"]
}
```

## Example Output

**Input Findings:**
- ML Signal Score: 96.24
- Elevated Linked Account Network
- Elevated New Account Risk

**Output Citations:**

```
[1] Risk_Scoring_Explainability_Guide.md
    Section: Risk Scoring Explainability Guide / 1. Explanation Objectives
    → ML Signal Score: 96.24

[2] AML_Suspicious_Indicators.md
    Section: Network / Relationship Signals / 5.1 Links to Known Risky Clusters
    → Elevated Linked Account Network

[3] KYC_CDD_Requirements.md
    Section: KYC / CDD Requirements / 1. Principle
    → Elevated New Account Risk
```

## Test Coverage

The citation system has comprehensive test coverage:

- Domain enforcement validation (26+ tests)
- Section-level constraint validation
- Finding type classification
- Citation generation and filtering
- Metadata chunk removal
- Deduplication and budget control

Key test cases:
- ML findings cannot retrieve AML transaction citations
- Graph findings cannot retrieve KYC citations
- Account findings retrieve KYC citations
- Rule findings retrieve AML transaction policies
- No citation contains metadata text

## Related Documentation

- [Citation Taxonomy](citation-taxonomy.md) — Finding type to policy mapping definitions
- [LLM Explanation Design](llm-explanation-design.md) — LLM explanation subsystem design
