# Security & Privacy Documentation

## Overview

This document outlines the security and privacy considerations for the Risk Intelligence Platform. The platform is designed as a machine learning-driven risk detection, monitoring, and investigation system.

## LLM Integration (Optional Enhancement)

The LLM explanation feature is an **optional enhancement** - the core platform operates fully without it.

- **Configuration**: Controlled by `ENABLE_LLM_EXPLANATION` setting (default: `false`)
- **Fallback Behavior**: When LLM is disabled or unavailable, the platform returns model-based explanations from risk analysis outputs
- **Error Handling**: On LLM API failure, the system automatically falls back to model-based explanations without breaking the investigation workflow
- **User Impact**: Investigators see consistent explanation content regardless of LLM availability; only the source indicator changes

### LLM Privacy Protections

When LLM is enabled, the platform applies strict data minimization and redaction:

- **User ID Redaction**: Controlled by `SHOW_USER_ID_IN_LLM_PROMPT` (default: `false`). User IDs are replaced with "User [REDACTED_ID]"
- **Input Whitelisting**: Only specific risk_event keys are sent to LLM (risk_score, risk_level, primary_reason, ml_score, rule_score, graph_score, recommended_action)
- **Text Sanitization**: Factor descriptions are sanitized to mask:
  - IP addresses → `[REDACTED_IP]`
  - Email addresses → `[REDACTED_EMAIL]`
  - Phone-like sequences → `[REDACTED_PHONE]`
  - Long ID-like numbers/hex strings → `[REDACTED_ID]`
- **Graph Data Minimization**: Only connection counts are included; raw node/edge data is never sent

## Structured Logging Privacy

The `/api/risk/explain` endpoint emits structured JSON logs for monitoring and debugging. Logging redaction is **separate from LLM prompt redaction** and provides independent control over log verbosity.

### Logging Redaction Control

| Setting | Default | Description |
|---------|---------|-------------|
| `LOG_REDACT_USER_ID` | `true` | Control whether user_id is redacted in structured logs |

### Log Redaction Behavior

**When `LOG_REDACT_USER_ID=true` (default):**
- All structured logs include `user_id: "[REDACTED]"`
- Privacy-safe for production logging
- Suitable for log aggregation and monitoring systems

**When `LOG_REDACT_USER_ID=false` (debug mode):**
- Structured logs include actual `user_id` values
- Useful for debugging and investigation tracing
- Use with caution in production environments

### Log Entry Example

```json
{
  "event": "risk_explain",
  "status_code": 200,
  "latency_ms": 125.5,
  "cache_hit": true,
  "rate_limited": false,
  "fallback_used": false,
  "explanation_source": "LLM",
  "citations_count": 3,
  "audience": "investigator",
  "user_id": "[REDACTED]"
}
```

### Independence from LLM Redaction

Logging redaction is **independent** from LLM prompt redaction:

- `SHOW_USER_ID_IN_LLM_PROMPT`: Controls what data is sent to external LLM API
- `LOG_REDACT_USER_ID`: Controls what appears in internal structured logs

**Example configuration:**
```python
# Send redacted user_id to LLM (privacy-safe)
SHOW_USER_ID_IN_LLM_PROMPT = False

# Log actual user_id for debugging (internal use only)
LOG_REDACT_USER_ID = False
```

## Read-Only Evidence APIs

All explanation and evidence endpoints are **READ-ONLY**:

- **No Score Modification**: These endpoints do not modify risk scores, ML predictions, or thresholds
- **No New Detection**: These endpoints do not perform new detection or risk assessment
- **Investigation Support**: The endpoints are designed to support investigator workflow with explainable evidence

## Policy Citation Redaction

Policy citations returned by the `/api/risk/explain` endpoint are redacted to protect sensitive internal information:

### Quote Sanitization

Policy citation quotes are sanitized before being returned to clients:

- **Personal Information**: IP addresses, emails, phone numbers are masked
- **Financial Thresholds**: Money/threshold patterns ($10,000, 10000, >= 5000) → `[REDACTED_THRESHOLD]`
- **Percentages**: Percentage patterns (20%, 20 percent) → `[REDACTED_PERCENT]`
- **Length Limits**: Quotes are truncated to 400 characters after redaction

## Audience-Based Output Mode

The `/api/risk/explain` endpoint supports an optional `audience` query parameter for output granularity control:

- **investigator** (default): Full citations with redacted quotes, detailed key_findings
- **business**: Redacted quotes (`[REDACTED]`), reduced sensitive phrasing in key_findings

### Business Mode Transformations

In business mode, the following transformations are applied to key_findings:

- "shared devices" → "shared access signals"
- "shared IPs" → "shared access signals"
- "connected to X other accounts" → "connected to multiple related accounts"

### Important Notes

⚠️ **This is a demo audience-based output mode only** - it demonstrates output-granularity control without implementing full authentication/authorization.

**Production deployments should enforce RBAC via API gateway/SSO** rather than relying on client-provided audience parameters.

## Investigation UI Design Principles

The Investigation Workspace is designed as an **investigator workflow**, not a data dump:

- **Information Hygiene**: The UI avoids overwhelming reviewers with excessive raw data
- **Actionable Focus**: Content is structured to support investigation decisions rather than displaying all available information
- **Progressive Disclosure**: Sensitive or detailed information is revealed progressively as needed

## Configuration Reference

### Privacy-Related Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_LLM_EXPLANATION` | `false` | Control whether LLM is used for explanation generation |
| `ANTHROPIC_API_KEY` | `""` | API key for Claude LLM provider |
| `SHOW_USER_ID_IN_LLM_PROMPT` | `false` | Control whether user_id is sent to LLM (redacted by default) |
| `LOG_REDACT_USER_ID` | `true` | Control whether user_id is redacted in structured logs (redacted by default) |

### API Endpoints

| Endpoint | Privacy Considerations |
|----------|----------------------|
| `POST /api/risk/explain` | Returns redacted policy citations; supports audience mode |
| `GET /api/risk/cases/{user_id}/evidence` | READ-ONLY; returns aggregated evidence from database records |
| `GET /api/risk/cases/{user_id}/network-signals` | READ-ONLY; returns network relationship evidence |

## Data Flow

### Explanation Generation Flow

```
User Request → /api/risk/explain
    ↓
1. Fetch risk event from database (READ-ONLY)
2. Fetch risk factors (READ-ONLY)
3. Fetch graph data (READ-ONLY, minimized)
4. Search policy documents via local RAG
5. Sanitize citation quotes (redaction applied)
6. Generate explanation:
   - If LLM enabled: Send sanitized data to LLM → Parse response
   - If LLM disabled/unavailable: Use model-based explanation
7. Apply audience-based output shaping (if business mode)
8. Return unified response with explanation_source indicator
```

### Data Minimization Principles

- **LLM Prompt**: Only essential, sanitized data is sent to external LLM services
- **Policy Citations**: Quotes are redacted to remove sensitive thresholds and percentages
- **Network Evidence**: Only connection counts and anonymized relationship types are exposed

## Security Best Practices

### For Production Deployments

1. **API Gateway**: Implement authentication/authorization at the API gateway level
2. **SSO Integration**: Use Single Sign-On for investigator identity management
3. **Audit Logging**: Log all explanation requests with user identity and timestamps
4. **Data Retention**: Implement appropriate data retention policies for investigation records
5. **Rate Limiting**: Protect explanation endpoints from abuse

### For Development

1. **Environment Variables**: Never commit API keys or secrets to version control
2. **Local Testing**: Test privacy features with realistic sensitive data patterns
3. **Redaction Verification**: Regularly test that redaction patterns are effective

## References

- CLAUDE.md - Project architecture and service boundaries
- backend/app/config.py - Privacy-related configuration settings
- backend/app/services/llm_service.py - LLM privacy implementation
- backend/app/api/routes/risk.py - API endpoint privacy controls
