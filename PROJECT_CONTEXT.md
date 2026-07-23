# Project Context - Risk Intelligence Platform

**Version:** 1.0
**Last Updated:** 2026-07-22
**Purpose:** Repository context for AI coding assistants and contributors

---

## Repository Purpose

This repository contains an **industry-agnostic Risk Intelligence Platform prototype** that demonstrates machine learning–driven risk detection, monitoring, and investigation workflows.

The platform showcases:
- Complete ML risk detection pipeline
- Multi-signal fusion architecture (ML + Rules + Graph)
- Model monitoring and drift detection (PSI)
- Investigation workflow support
- Explainable risk decisions

**Primary Use Case:** Demonstration of production-ready ML system architecture patterns applicable across risk-sensitive industries.

---

## Project Identity

**Name:** Risk Intelligence Platform

**Short Description:** Machine Learning–Driven Detection, Monitoring & Investigation

**One-Liner:** A machine learning-driven risk detection and monitoring platform designed to identify suspicious behaviors, combine multiple risk signals, and support investigation workflows across risk-sensitive industries.

---

## Business Background

### Domain Inspiration

This project was inspired by risk management scenarios from:

1. **Consumer Finance**
   - Credit risk assessment patterns
   - Fraud detection workflows
   - Behavioral risk scoring
   - Model monitoring and governance

2. **Online Activity Platforms**
   - Abnormal activity pattern detection
   - Coordinated account behavior analysis
   - Network relationship analysis
   - Activity risk assessment

### Industry-Agnostic Design

The architecture is designed to be transferable to multiple domains:

- **Fintech** - Banks, payments, lending, wealth management
- **Fraud Prevention** - Payment fraud, account takeover, application fraud
- **Marketplace Integrity** - E-commerce fraud, fake reviews, seller verification
- **Account Security** - Login anomalies, credential stuffing, account sharing
- **Online Activity Platforms** - Activity risk, behavioral patterns, coordinated manipulation

**Important:** This is NOT a domain-specific product. The patterns demonstrated apply broadly to risk-sensitive industries.

---

## Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  DATASET INGESTION LAYER                     │
├─────────────────────────────────────────────────────────────┤
│  CSV Upload → Data Validation → Quality Checks             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               FEATURE ENGINEERING PIPELINE                    │
├─────────────────────────────────────────────────────────────┤
│  13 Risk Features: Device Patterns, Behavioral Activity,    │
│  Account Attributes, Activity Patterns                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              RISK DETECTION ENGINE                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ ML Model     │  │ Rule Engine  │  │ Graph Detect │    │
│  │ (LightGBM)   │  │              │  │ (NetworkX)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                     Signal Fusion                              │
│                  (0.5 + 0.3 + 0.2)                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              RISK EVENT GENERATION                           │
├─────────────────────────────────────────────────────────────┤
│  Risk Score + Risk Level + Signal Attribution + Evidence      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              MONITORING & EXPLAINABILITY                      │
├─────────────────────────────────────────────────────────────┤
│  PSI Monitoring + Model Explainability + Investigation       │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:** Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy
**Frontend:** React, TypeScript, Tailwind CSS
**Machine Learning:** LightGBM, scikit-learn, pandas
**Graph:** NetworkX
**Monitoring:** PSI (Population Stability Index)

---

## Implemented Capabilities

### Risk Detection

- **ML Risk Scoring** - LightGBM gradient boosting (AUC: 0.85, KS: 0.43)
- **Rule Engine** - Expert-defined risk signals for known patterns
- **Graph Detection** - Network analysis for coordinated behavior
- **Multi-Signal Fusion** - Weighted combination (0.5 ML + 0.3 Rule + 0.2 Graph)

### Risk Monitoring

- **PSI Drift Detection** - Population Stability Index for model drift
- **Model Performance Tracking** - AUC, KS, feature distribution monitoring
- **Baseline Validation** - Automated comparison against training distributions

### Investigation Support

- **Risk Event Lifecycle** - Complete audit trail with pipeline traceability
- **Signal Attribution** - Which detection methods contributed
- **Evidence Factors** - Detailed feature-level explanations
- **Investigation Queue** - Filterable workflow for analyst review

---

## ML vs LLM Boundary

### Current Implementation: Machine Learning

**Core Risk Intelligence (Always Active):**
- LightGBM risk scoring model
- Feature engineering pipeline (13 features)
- Rule-based expert system
- Graph-based network analysis
- Multi-signal risk fusion
- PSI drift monitoring
- Model-based explainability

**Model Explainability (Current):**
- Risk score breakdown (ML + Rule + Graph contributions)
- Signal attribution (which methods triggered)
- Evidence factors (feature-level details)
- Investigation guidance (risk-level based actions)

**Implementation:** Generated from model outputs, signal attribution, and evidence factors. NOT LLM-generated.

### Optional Enhancement: LLM Integration

**LLM-Assisted Investigation (Optional):**
- Natural language case summaries
- Analyst-friendly narrative explanations
- Investigation workflow assistance

**Configuration Control:**
```bash
ENABLE_LLM_EXPLANATION=false  # Default: disabled
# ANTHROPIC_API_KEY=           # Only required when enabling LLM
```

**Behavior:**
- When disabled (default): Model-based explanations from risk outputs
- When enabled + API key: LLM generates natural language summaries
- On LLM failure: Falls back to model-based explanations

**Key Point:** Platform operates **fully without LLM integration**. LLM is purely additive for narrative explanations.

---

## Future AI Extension Opportunities

### NOT Currently Implemented

The platform is architected to support future enhancements:

**Possible LLM-Based Extensions:**
- Natural language case summaries (optional, partially implemented)
- Analyst copilot for investigation workflow
- Historical case retrieval for context
- Automated investigation assistance

**Future Infrastructure:**
- Real-time alerting and notifications
- Automated retraining based on PSI thresholds
- Advanced graph analytics with temporal patterns

**Important:** These are architectural opportunities, not current implementation. The platform demonstrates current ML capability with architecture ready for AI enhancement.

---

## Important Terminology Rules

### Preferred Language

✅ **Use:**
- "Machine Learning–Driven Risk Intelligence Platform"
- "ML-based risk scoring"
- "Model explainability"
- "LLM-assisted investigation enhancement"
- "Multi-signal risk fusion"
- "Risk investigation workflow"
- "Model monitoring and drift detection"

### Avoid Language

❌ **Do NOT Use:**
- "AI-powered detection" (implies LLM when current implementation is ML)
- "LLM-based risk decision system"
- Domain-specific positioning like "industry-specific risk system" or "domain-specific platform" as primary identity
- Positioning as any domain-specific system as primary identity
- "Automated AI decision making"
- Any language that positions the project as domain-specific rather than industry-agnostic

### Context-Specific Language

✅ **Acceptable When Contextualized:**
- "Inspired by online activity scenarios"
- "Applicable to risk-sensitive domains including fintech, fraud prevention, online platforms, marketplace integrity, and account security"
- "Consumer finance risk patterns"

❌ **Avoid:**
- Positioning the entire project as domain-specific
- Describing as "industry-specific risk system" without broader context

---

## Architecture Principles

### Core Principles

1. **Industry-Agnostic Design**
   - Patterns transfer across risk-sensitive domains
   - Not tied to specific industry or use case

2. **Multi-Signal Fusion**
   - No single detection method catches all cases
   - ML finds patterns, rules encode knowledge, graph finds relationships
   - Weighted combination provides comprehensive coverage

3. **Investigation Support, Not Auto-Ban**
   - Platform provides evidence and recommendations
   - Human analysts make enforcement decisions
   - Aligns with real-world risk operations

4. **Model Reliability**
   - Model-based explainability always available
   - LLM is optional enhancement, not dependency
   - System works fully without external AI services

5. **Production ML Concerns**
   - PSI drift detection for model monitoring
   - Pipeline traceability for audit trails
   - Feature engineering as primary value driver

### Design Decisions

**LightGBM Choice:**
- Interpretability and performance balance
- Handles tabular data effectively
- Feature importance extraction built-in

**Multi-Signal Architecture:**
- Real-world risk requires multiple perspectives
- ML + Rules + Graph provides complementary coverage
- Weighted fusion allows business tuning

**PSI Monitoring:**
- Production ML models degrade over time
- Data distribution shifts affect performance
- Automated drift detection enables retraining decisions

---

## Data Disclaimer

**All datasets in this repository are synthetic.**

This project uses demonstration datasets for validation and testing:

- ✅ All user accounts, devices, transactions, and activity data are synthetically generated
- ✅ No real customer data is included
- ✅ No proprietary company information is included
- ✅ No actual production platform data is used

**Data Scenarios:**

The synthetic datasets demonstrate common risk management patterns:
- Abnormal behavioral patterns (high-frequency activity, unusual timing)
- Coordinated account activity (shared devices, network clusters)
- Risk signal distribution (low, medium, high, critical cases)
- Model drift scenarios (for PSI monitoring validation)

---

## Development Context

### AI-Assisted Development

This project demonstrates effective use of AI coding assistants for:
- Rapid prototyping and architecture design
- Code implementation across full stack
- Documentation generation
- Test creation and validation

### Architecture Patterns

The project demonstrates production-ready patterns:
- Feature engineering pipelines
- Multi-signal fusion architecture
- Model monitoring and drift detection
- Investigation workflow support
- Explainable risk decisions

### System Design

Capability demonstrated:
- End-to-end system architecture
- API design and data modeling
- Frontend/backend integration
- System reliability and monitoring
- Security and privacy considerations

---

## Repository Usage Guidelines

### For AI Coding Assistants

When working with this repository:

1. **Positioning:** Refer to "Risk Intelligence Platform" or "ML-driven risk detection"
2. **Scope:** Focus on technical architecture and system design
3. **LLM:** Describe LLM as "optional enhancement" not core functionality
4. **Domains:** Mention multiple applicable industries, not single domains
5. **Context:** This is an industry-agnostic prototype demonstrating ML system patterns

### For Contributors

When extending this project:

1. Maintain industry-agnostic design principles
2. Keep LLM integration optional (platform works without it)
3. Preserve model-based explainability as default
4. Follow existing architecture patterns
5. Document production considerations

### Architecture Extension

When adding new capabilities:

1. Consider cross-industry applicability
2. Maintain separation between core ML and optional LLM features
3. Preserve investigation workflow support
4. Ensure monitoring and observability
5. Keep failure safety mechanisms

---

## Contact & Documentation Reference

For additional context:
- README.md - Product overview and capabilities
- CLAUDE.md - Architecture and development guidance
- docs/architecture/llm-optional-design.md - LLM optional architecture details
- docs/archive/FINAL_RELEASE_SUMMARY.md - Release preparation summary

---

## Repository Standards

### Code Quality

- Clear separation of concerns (API, services, models, ML)
- Comprehensive documentation for architectural decisions
- Configuration control for optional features
- Failure safety and graceful degradation

### Documentation Standards

- Industry-agnostic language
- Clear ML vs LLM boundary
- Accurate capability descriptions
- No overstatement of features

### Architecture Documentation

- System design rationale
- Technology choice justification
- Production ML considerations
- Future extension pathways
