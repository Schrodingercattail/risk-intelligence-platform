"""
LLM Explanation Service (Optional Extension)

Abstracted service for generating AI-assisted investigation explanations.
This is an OPTIONAL enhancement — the platform operates fully without LLM integration.

When ANTHROPIC_API_KEY is configured: LLM generates natural language case summaries
When not configured: Returns structured explanations from model outputs

Supports Claude (default) with extensibility for other providers.
"""
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod
import os
import re
import asyncio
import logging
logger = logging.getLogger(__name__)

from anthropic import Anthropic

from app.config import settings


# Constants for sanitization
MAX_FACTOR_DESCRIPTION_LENGTH = 200
MAX_QUOTE_LENGTH = 400
ALLOWED_RISK_EVENT_KEYS = {
    'risk_score', 'risk_level', 'primary_reason',
    'ml_score', 'rule_score', 'graph_score', 'recommended_action'
}


def sanitize_text_for_llm(text: str, max_length: int = MAX_FACTOR_DESCRIPTION_LENGTH) -> str:
    """
    Sanitize text by masking sensitive patterns and truncating.

    Masks:
    - IP addresses -> [REDACTED_IP]
    - Email addresses -> [REDACTED_EMAIL]
    - Phone-like sequences -> [REDACTED_PHONE]
    - Long id-like numbers/hex strings (len>=10) -> [REDACTED_ID]

    Also truncates to max_length to reduce data leakage and cost.
    """
    if not text:
        return ""

    # Truncate first to reduce processing
    if len(text) > max_length:
        text = text[:max_length]

    # Mask IP addresses (IPv4 and IPv6 patterns)
    text = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '[REDACTED_IP]', text)
    text = re.sub(r'\b[0-9a-fA-F:]{2,}:[0-9a-fA-F:]{2,}\b', '[REDACTED_IP]', text)

    # Mask email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', text)

    # Mask phone-like sequences (7+ digits with optional separators)
    text = re.sub(r'\b[\d\-\(\)\+]{7,}\d\b', '[REDACTED_PHONE]', text)

    # Mask long id-like numbers or hex strings (10+ characters)
    # Matches sequences of hex characters or long numbers
    text = re.sub(r'\b[0-9a-fA-F]{10,}\b', '[REDACTED_ID]', text)
    text = re.sub(r'\b\d{10,}\b', '[REDACTED_ID]', text)

    return text


def sanitize_policy_quote(text: Optional[str], max_length: int = MAX_QUOTE_LENGTH) -> str:
    """
    Sanitize policy citation quotes by masking sensitive patterns and truncating.

    This function is designed specifically for redacting sensitive information from
    policy/SOP citations before they are displayed to users.

    Masks (in addition to patterns from sanitize_text_for_llm):
    - Money/threshold-like numeric patterns ($10,000, 10000, >= 5000) -> [REDACTED_THRESHOLD]
    - Percentage patterns (20%, 20 percent) -> [REDACTED_PERCENT]

    Truncates to max_length AFTER redaction to ensure consistent display.

    Args:
        text: The policy quote text to sanitize
        max_length: Maximum length after redaction (default: 400)

    Returns:
        Sanitized quote text with sensitive patterns redacted.
        Never raises exceptions; returns empty string for None/empty input.
    """
    if not text:
        return ""

    # Reuse existing redaction patterns for common sensitive data
    text = sanitize_text_for_llm(text, max_length=max_length * 2)  # Allow more space before truncation

    # Mask money/threshold-like patterns
    # Patterns like: $10,000, $10000, 10000 USD, >= 5000, >=$5,000
    text = re.sub(r'\$[\d,]+\.?\d*', '[REDACTED_THRESHOLD]', text)
    text = re.sub(r'[\d,]+\.?\d*\s*(?:USD|EUR|GBP|CNY)', '[REDACTED_THRESHOLD]', text)
    text = re.sub(r'>=?\s*\$?[\d,]+\.?\d*', '[REDACTED_THRESHOLD]', text)
    text = re.sub(r'>=?\s*[\d,]+\.?\d*\s*(?:USD|EUR|GBP|CNY)', '[REDACTED_THRESHOLD]', text)

    # Mask percentage patterns
    # Patterns like: 20%, 20 percent, 20.5%
    text = re.sub(r'\b\d+\.?\d*%\b', '[REDACTED_PERCENT]', text)
    text = re.sub(r'\b\d+\.?\d*\s+percent\b', '[REDACTED_PERCENT]', text)

    # Truncate to max length after redaction
    if len(text) > max_length:
        text = text[:max_length].strip()

    return text


def sanitize_for_llm(
    user_id: str,
    risk_event: Dict[str, Any],
    risk_factors: List[Dict[str, Any]],
    graph_data: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Sanitize inputs before sending to LLM to prevent sensitive data leakage.

    Applies minimize + mask + block rules:
    A) user_id: Redacted unless SHOW_USER_ID_IN_LLM_PROMPT is true
    B) risk_event: Whitelist only safe keys (scores, level, reason, action)
    C) risk_factors: Sanitize descriptions to mask IPs, emails, phones, IDs
    D) graph_data: Only include connected_count, not raw node/edge data

    Returns:
        Tuple of (sanitized_user_id, sanitized_risk_event, sanitized_risk_factors, sanitized_graph_data)
    """
    # A) Handle user_id
    if settings.SHOW_USER_ID_IN_LLM_PROMPT:
        sanitized_user_id = user_id
    else:
        sanitized_user_id = "User [REDACTED_ID]"

    # B) Whitelist safe risk_event keys only
    sanitized_risk_event = {
        key: risk_event[key]
        for key in ALLOWED_RISK_EVENT_KEYS
        if key in risk_event
    }

    # C) Sanitize risk_factors: only keep factor_name and sanitized factor_description
    sanitized_risk_factors = []
    for factor in risk_factors[:5]:  # Still limit to top 5
        sanitized_factor = {
            'factor_name': factor.get('factor_name', 'Unknown Factor'),
        }

        # Sanitize description if present
        description = factor.get('factor_description', '')
        if description:
            sanitized_factor['factor_description'] = sanitize_text_for_llm(str(description))

        sanitized_risk_factors.append(sanitized_factor)

    # D) Sanitize graph_data: only include connected_count
    sanitized_graph_data = None
    if graph_data and graph_data.get('nodes'):
        connected_count = len(graph_data['nodes']) - 1  # Exclude self
        if connected_count > 0:
            sanitized_graph_data = {'connected_count': connected_count}

    return sanitized_user_id, sanitized_risk_event, sanitized_risk_factors, sanitized_graph_data


def _self_check_sanitizer() -> Dict[str, Any]:
    """
    Internal self-check function to verify sanitizer actually redacts sensitive patterns.

    This can be used for testing or debugging to ensure the sanitizer works correctly.
    """
    test_cases = {
        'ip_address': 'User connected from IP 192.168.1.1',
        'email': 'Contact at john.doe@example.com for verification',
        'phone': 'Call +1-555-123-4567 for support',
        'long_id': 'Transaction ID: a1b2c3d4e5f6',
        'mixed': 'User user_12345 connected from 10.0.0.5, email test@test.com'
    }

    results = {}
    for case_name, test_input in test_cases.items():
        results[case_name] = {
            'input': test_input,
            'output': sanitize_text_for_llm(test_input),
            'redacted': bool(re.search(r'\[REDACTED_', sanitize_text_for_llm(test_input)))
        }

    return results


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_explanation(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate explanation from prompt."""
        pass


class ClaudeProvider(LLMProvider):
    """Claude API implementation."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key (or gateway API key).
            base_url: Optional API endpoint override. If provided (or if
                settings.ANTHROPIC_BASE_URL is set), requests are routed to that
                Anthropic-compatible gateway (e.g. the Zhipu GLM gateway).
                If empty/None, the official Anthropic endpoint is used.
        """
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")
        # Resolve base_url: explicit arg -> settings -> None (official default)
        resolved_base_url = base_url or settings.ANTHROPIC_BASE_URL or None
        if resolved_base_url:
            self.client = Anthropic(api_key=api_key, base_url=resolved_base_url)
        else:
            self.client = Anthropic(api_key=api_key)

    async def generate_explanation(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate explanation using Claude API (or Anthropic-compatible gateway).

        The response content is a list of blocks that may include non-text
        blocks (e.g. type='thinking' blocks returned by some gateways/models,
        whose .text is None), so the first text block is located by type rather
        than assumed to be content[0].
        """
        message = self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            system=system_prompt or self._default_system_prompt(),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        for block in message.content:
            if getattr(block, "type", None) == "text":
                return block.text

        raise ValueError(
            "LLM response contained no text content block "
            f"(block types: {[getattr(b, 'type', type(b).__name__) for b in message.content]}); "
            "cannot extract explanation text"
        )

    def _default_system_prompt(self) -> str:
        """Default system prompt for risk analyst role, including the grounding contract."""
        return """You are an expert risk analyst for a risk intelligence platform. Your role is to:

1. Analyze risk data and explain findings clearly
2. Identify the most critical risk factors
3. Provide actionable recommendations
4. Maintain a professional, objective tone

When explaining risk, always:
- Start with a clear summary
- List specific findings with evidence
- End with a recommended action
- Keep explanations concise but thorough

GROUNDING CONTRACT (must follow):
1. Evidence boundary: State ONLY risk factors that are explicitly present in the supplied
   evidence. Do not invent additional risk factors, behavioral mechanisms, or fraud typologies.
2. Account age: Treat account age as CONTEXTUAL EVIDENCE unless an explicit rule trigger is
   supplied. Do not infer "new account risk", "sleeper account", deliberate aging, or similar
   narratives from account age alone, and do not invent age thresholds. The only account-age
   rule is "New account with high activity" (requires BOTH young age AND high activity); unless
   that rule is stated as triggered in the evidence, account age is just context.
3. Risk score semantics: Treat ML/Rule/Graph values as SYSTEM SCORES / SIGNALS, not calibrated
   probabilities. Do not describe an ML score as a probability of fraud unless the supplied
   evidence explicitly says it is a probability. Never present a high score as proof or
   certainty of malicious intent.
4. Graph score semantics: Graph Score = 0 means NO detected graph signal. Do not infer "lone
   wolf", "isolated/hidden infrastructure", VPN/OpSec/evasion, or similar from a zero graph
   score unless explicit supporting evidence is supplied.
5. Fraud typology calibration: Do not introduce money laundering, botnet, sleeper account,
   synthetic identity, bonus abuse, wash trading, layering, or other specific typologies
   unless they are explicitly supported by the supplied evidence. Use calibrated language
   ("indicates", "is consistent with", "may suggest", "requires investigation") instead of
   presenting hypotheses as confirmed facts.
6. Investigation boundary: This platform is an INVESTIGATION SUPPORT system, not an automatic
   enforcement system. Prioritize review/validation steps in recommendations, and never
   present an unverified fraud hypothesis as established fact."""


class OpenAIProvider(LLMProvider):
    """OpenAI API implementation (placeholder for future extension)."""

    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        self.api_key = api_key
        # Client would be initialized here: openai.OpenAI(api_key=api_key)

    async def generate_explanation(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate explanation using OpenAI API."""
        # Placeholder - would use actual OpenAI API call
        return "OpenAI provider not yet implemented."


class LLMExplanationService:
    """
    LLM Explanation Service (Optional Extension)

    This service provides AI-assisted natural language explanations for risk cases.
    It is designed as an OPTIONAL enhancement — the core platform operates fully without it.

    Input: risk_event + factors + graph_data
    Output: structured_explanation (with or without LLM)

    Service boundary: Abstracts LLM provider, handles prompt construction,
    manages response parsing, provides structured fallback when LLM unavailable.

    Behavior:
    - With ANTHROPIC_API_KEY: Uses Claude for natural language generation
    - Without API key: Returns structured explanations from model outputs
    - On error: Falls back to structured response with error information
    """

    # Coordinated-trading rule threshold (opposite_trade_ratio > 0.4 triggers
    # the rule; 0 < ratio <= 0.4 is an observed metric below threshold).
    # Mirrors EvidenceService._THRESHOLD_FINDINGS and the scorer's rule —
    # presentation only, never a scoring decision.
    OPPOSITE_TRADE_RULE_THRESHOLD = 0.4

    def __init__(self, provider: Optional[LLMProvider] = None):
        """Initialize service with LLM provider."""
        if provider:
            self.provider = provider
        elif settings.ANTHROPIC_API_KEY:
            self.provider = ClaudeProvider(settings.ANTHROPIC_API_KEY)
        else:
            self.provider = None  # Will return mock responses

    async def generate_explanation(
        self,
        user_id: str,
        risk_event: Dict[str, Any],
        risk_factors: List[Dict[str, Any]],
        graph_data: Optional[Dict[str, Any]] = None,
        canonical_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate AI-powered investigation explanation.

        Args:
            user_id: User being analyzed
            risk_event: Risk event data with scores
            risk_factors: List of risk factor details
            graph_data: Optional relationship graph data
            canonical_evidence: Optional canonical structured evidence from
                EvidenceService.get_canonical_evidence() — the authoritative
                ml/rules/graph/contextual evidence. When supplied, the LLM is
                asked to organize THIS evidence rather than infer meaning from
                the component scores alone.

        Returns:
            Dict with summary, key_findings, recommended_action, explanation_source, and llm_error
        """
        if not self.provider:
            # LLM unavailable - return model-based explanation with MODEL_FALLBACK source
            return self._model_based_explanation(
                risk_event, risk_factors, explanation_source="MODEL_FALLBACK", llm_error=None
            )

        # Construct prompt
        prompt = self._construct_prompt(
            user_id, risk_event, risk_factors, graph_data,
            canonical_evidence=canonical_evidence,
        )

        # Generate explanation with timeout protection
        try:
            # Wrap LLM call in timeout to ensure fast fallback
            explanation_text = await asyncio.wait_for(
                self.provider.generate_explanation(prompt),
                timeout=settings.EXPLAIN_LLM_TIMEOUT_SECONDS
            )

            # Parse response into structured format with LLM source
            parsed = self._parse_explanation(explanation_text, risk_event)
            parsed["explanation_source"] = "LLM"
            parsed["llm_error"] = None
            return parsed

        except asyncio.TimeoutError:
            # Handle timeout specifically
            logging.getLogger(__name__).warning(
                f"LLM provider timeout after {settings.EXPLAIN_LLM_TIMEOUT_SECONDS}s for user {user_id}"
            )
            return self._model_based_explanation(
                risk_event, risk_factors, explanation_source="MODEL_FALLBACK", llm_error="LLM provider timeout"
            )

        except Exception as e:
            # Log detailed error server-side
            logging.getLogger(__name__).error(f"LLM explanation generation failed: {e}", exc_info=True)

            # Return model-based explanation with MODEL_FALLBACK source and short error
            short_error = "LLM generation failed" if "timeout" in str(e).lower() else "LLM provider error"
            logger.exception("LLM provider call failed")   # 会打印完整 traceback
            return self._model_based_explanation(
                risk_event, risk_factors, explanation_source="MODEL_FALLBACK", llm_error=short_error
            )

    # Natural-language renderings for raw feature field names (presentation
    # layer only — Canonical Evidence keeps the raw values for audit).
    _FIELD_LANGUAGE = {
        "account_age_days": "the account is {value} days old",
        "trade_frequency_24h": "{value} trades were recorded in 24 hours",
        "withdrawal_frequency_24h": "{value} withdrawals were recorded in 24 hours",
        "first_withdrawal_flag": "a first withdrawal to a new address was detected",
        # Threshold-aware renderings; {threshold} is the coordinated-trading
        # rule threshold in percent. The wording must always distinguish the
        # below-threshold OBSERVATION from the threshold-triggered RULE.
        "opposite_trade_ratio_below": (
            "an opposite-trade ratio of {pct}% was observed, which is below "
            "the {threshold}% threshold for the coordinated trading rule"
        ),
        "opposite_trade_ratio_above": (
            "an opposite-trade ratio of {pct}% exceeded the {threshold}% "
            "threshold, triggering the coordinated trading rule"
        ),
        "shared_device_count": "{value} linked account(s) through shared devices",
        "connected_accounts": "{value} connected accounts were detected",
        "ml_score": "ML signal of {value}/100",
        # withdrawal_risk_score is the fraction of withdrawals sent to newly
        # encountered addresses (0..1) — never rendered as an internal sub-score.
        "withdrawal_risk_score": "{pct}% of withdrawals were sent to newly encountered addresses",
    }

    def _humanize_observed(self, finding_name: str, observed: Dict[str, Any]) -> str:
        """
        Render observed values as investigator-facing natural language.

        Hides raw field names / implementation detail ("account_age_days = 6")
        in favor of business language ("the account is 6 days old"). Values
        are preserved exactly; only the presentation changes.
        """
        if not isinstance(observed, dict) or not observed:
            return str(observed) if observed else ""

        parts = []
        for key, value in observed.items():
            # opposite_trade_ratio resolves to a threshold-aware template
            # (below/above the coordinated-trading rule threshold); all other
            # fields use their fixed template.
            if key == "opposite_trade_ratio":
                try:
                    ratio = float(value)
                    pct = f"{ratio * 100:.2f}"
                    threshold_pct = int(self.OPPOSITE_TRADE_RULE_THRESHOLD * 100)
                    template = (
                        self._FIELD_LANGUAGE["opposite_trade_ratio_below"]
                        if 0 < ratio <= self.OPPOSITE_TRADE_RULE_THRESHOLD
                        else self._FIELD_LANGUAGE["opposite_trade_ratio_above"]
                    )
                    parts.append(template.format(pct=pct, threshold=threshold_pct))
                except (TypeError, ValueError):
                    parts.append(f"{key} = {value}")
                continue
            template = self._FIELD_LANGUAGE.get(key)
            if template is None:
                parts.append(f"{key} = {value}")
                continue
            if key == "first_withdrawal_flag":
                if value:
                    parts.append(template)
            elif key == "withdrawal_risk_score":
                # 0..1 ratio renders as a business percentage, never a raw sub-score
                try:
                    parts.append(template.format(pct=f"{float(value) * 100:.2f}"))
                except (TypeError, ValueError):
                    parts.append(f"{key} = {value}")
            else:
                try:
                    parts.append(template.format(value=value))
                except (TypeError, ValueError):
                    parts.append(f"{key} = {value}")
        return "; ".join(parts)

    def _construct_prompt(
        self,
        user_id: str,
        risk_event: Dict[str, Any],
        risk_factors: List[Dict[str, Any]],
        graph_data: Optional[Dict[str, Any]] = None,
        canonical_evidence: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Construct the LLM prompt from structured data with privacy sanitization."""
        # Sanitize all inputs before prompt construction
        (sanitized_user_id, sanitized_risk_event, sanitized_risk_factors,
         sanitized_graph_data) = sanitize_for_llm(user_id, risk_event, risk_factors, graph_data)

        prompt_parts = [
            f"## Risk Analysis for User: {sanitized_user_id}\n",
            f"### Overall Risk Assessment",
            f"- Risk Score: {sanitized_risk_event.get('risk_score', 'N/A')}/100",
            f"- Risk Level: {sanitized_risk_event.get('risk_level', 'N/A')}",
            f"- Primary Reason: {sanitized_risk_event.get('primary_reason', 'N/A')}\n",
            f"### Component Scores",
            f"- ML Score: {sanitized_risk_event.get('ml_score', 'N/A')}",
            f"- Rule Score: {sanitized_risk_event.get('rule_score', 'N/A')}",
            f"- Graph Score: {sanitized_risk_event.get('graph_score', 'N/A')}\n",
        ]

        # Canonical structured evidence — the authoritative explanation input.
        # When present, the LLM organizes THIS evidence instead of guessing what
        # the component scores mean.
        if canonical_evidence:
            prompt_parts.append("### Canonical Evidence (authoritative — organize this, do not invent beyond it)")

            ml = canonical_evidence.get("ml")
            if ml:
                prompt_parts.append(
                    f"- ML pattern detection score: {ml.get('score')}/100 "
                    f"(system signal, not a calibrated probability; primary driver: "
                    f"{ml.get('primary_driver')})"
                )

            rules = canonical_evidence.get("rules")
            if rules:
                prompt_parts.append(
                    f"- Rule engine: score {rules.get('score')} (deterministic rules triggered below)"
                )
                for r in (rules.get("triggered") or []):
                    prompt_parts.append(
                        f"  - Triggered rule \"{r.get('rule_name')}\": "
                        f"{self._humanize_observed(r.get('rule_name', ''), r.get('trigger') or {})}"
                    )

            graph = canonical_evidence.get("graph")
            if graph:
                if graph.get("has_evidence"):
                    prompt_parts.append(
                        f"- Graph detection: score {graph.get('score')}, connected accounts: {graph.get('connected_accounts')}"
                    )
                else:
                    prompt_parts.append(
                        f"- Graph detection: score 0 — {graph.get('note')}"
                    )

            ctx = canonical_evidence.get("contextual")
            if ctx and ctx.get("account_age_days") is not None:
                prompt_parts.append(
                    f"- Contextual: the account is {ctx.get('account_age_days')} days old "
                    "(contextual evidence only; the system's only new-account rule requires "
                    "both a very young account AND high trading activity)"
                )

            findings = canonical_evidence.get("findings") or []
            if findings:
                prompt_parts.append("- Key Risk Findings (investigation-oriented, user-facing):")
                for f in findings:
                    # Presentation layer: investigators see natural language.
                    # Raw field names, threshold expressions and score
                    # contributions stay in Canonical Evidence (audit/debug).
                    # EVERY canonical finding is supplied: canonical evidence
                    # is authoritative for which findings exist — the LLM
                    # explains them all; the narrative contract aligns wording
                    # and the completeness append is only a safety net.
                    name = f.get("name", "")
                    observed = f.get("observed_value") or {}
                    prompt_parts.append(f"  - {name} (evidence: {self._humanize_observed(name, observed)})")
            prompt_parts.append("")

        if sanitized_risk_factors:
            prompt_parts.append("### Key Risk Factors")
            for factor in sanitized_risk_factors:
                prompt_parts.append(
                    f"- {factor.get('factor_name')}: {factor.get('factor_description', '')}"
                )
            prompt_parts.append("")

        if sanitized_graph_data and sanitized_graph_data.get('connected_count', 0) > 0:
            connected_count = sanitized_graph_data['connected_count']
            prompt_parts.append(
                f"### Network Analysis\n"
                f"- This user is connected to {connected_count} other account(s)\n"
            )

        prompt_parts.extend([
            "### Request",
            "Please provide:",
            "1. A clear summary of why this account is risky",
            "2. Key findings with specific evidence",
            "3. A recommended action for the investigation team",
            "",
            "Format your response clearly with sections for Summary, Key Findings, and Recommended Action.",
            "",
            "Finding organization rules:",
            "- Present ONE unified list of \"Key Risk Findings\" (not separate",
            "  ML/Rule/Graph sections). Each numbered finding = a short title line,",
            "  then one natural-language sentence of what was observed and why it",
            "  matters, in calibrated investigation wording.",
            "- Write findings in INVESTIGATOR language, never scoring-console language:",
            "  * NEVER state score contributions of any kind.",
            "  * NEVER print raw threshold expressions, comparisons or snake_case",
            "    field names — express each rule's meaning in plain words using the",
            "    observed values given in the evidence lines (e.g. \"The account is",
            "    6 days old and recorded 54 trades in 24 hours, satisfying the",
            "    system's new-account/high-activity rule.\" or \"7 withdrawals were",
            "    recorded in 24 hours, exceeding the system's threshold for",
            "    elevated withdrawal frequency.\")",
            "  * NEVER show \"withdrawal risk score = N\" or any raw sub-score for",
            "    withdrawal behavior; describe behavior in business terms.",
            "  * OPPOSITE-TRADE RATIO — threshold semantics are part of the",
            "    business contract; the narrative MUST state which side of the",
            "    40% coordinated-trading threshold the observed ratio falls on:",
            "    - Below threshold (finding \"Opposite Trade Ratio\"): phrase as",
            "      e.g. \"An opposite-trade ratio of 34.38% was observed, which is",
            "      below the 40% threshold for the coordinated trading rule.\"",
            "      NEVER write \"potentially coordinated trading behavior\",",
            "      \"coordinated trading pattern detected\", \"may warrant further",
            "      review for coordinated trading\", or ANY wording implying the",
            "      coordinated-trading rule was triggered.",
            "    - Above threshold (finding \"Coordinated Trading Pattern\"):",
            "      phrase as e.g. \"An opposite-trade ratio of 41.00% exceeded the",
            "      40% threshold, triggering the coordinated trading rule.\"",
            "    In both cases the ratio is a single aggregate statistic: it does",
            "    NOT show that the account offset another party's positions, nor",
            "    confirm coordination/manipulation by itself.",
            "- NEVER mention HOW a finding was produced. Do not write any",
            "  detection-source label (no ML/Rule/Graph/Feature provenance wording).",
            "  Detection provenance is internal; investigators see findings, not pipelines.",
            "- The ML detector is expressed ONLY as a detector-level signal statement",
            "  (e.g. \"ML Pattern Detection — 99.41/100; a system signal, not a",
            "  calibrated probability\") as the first finding; NEVER claim",
            "  \"ML detected <feature finding>\".",
            "- Do NOT add citation markers like [1] yourself — the system attaches",
            "  policy citations afterwards. Do not delete or omit a finding.",
            "- NEVER write \"policy requires/defines...\" for findings — policy",
            "  grounding is attached by the system only where it exists.",
            "- A finding supported by multiple sources appears ONCE.",
            "- When canonical evidence lists graph detection with no signal, state only",
            "  that no graph signal was detected — draw no conclusions from it.",
            "- List each finding as its own line starting with \"- \" (hyphen).",
            "  Put supporting sentences for the same finding on the following",
            "  indented line(s). NEVER number findings or actions yourself and",
            "  never use bold list markers — the backend adds all numbering.",
            "  Action steps: one per line, each starting with \"- \".",
            "- Cover ALL supplied canonical findings: you may merge duplicates",
            "  and rephrase, but never drop a Rule finding, never mention a",
            "  finding in the Summary without including it in Key Risk Findings.",
            "  If evidence states no graph signal was detected, mention it at",
            "  most briefly in the Summary — it is not a risk finding.",
        ])

        return "\n".join(prompt_parts)

    def _parse_explanation(self, text: str, risk_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the LLM response into summary / key_findings / recommended_action.

        Structure-preserving parsing (no dependence on exact wording):
        - section boundaries detected by heading words (Summary / Findings /
          Recommended Action)
        - findings accept BOTH bulleted lines ("- x", "* x") and numbered lines
          ("1. x", "2. x"); continuation (unmarked) lines within the findings
          section become supporting lines of the previous finding
        - numbered action steps are preserved as separate lines with their
          numbering (newlines kept) instead of being collapsed into one
          paragraph
        """
        lines = text.split('\n')

        summary_lines = []
        findings: List[str] = []
        action_lines: List[str] = []

        current_section = None
        for line in lines:
            stripped = line.strip()

            # Section headers (structural markers, not exact wording).
            # Headers are short heading-like lines containing the keyword.
            # A bulleted ("- x") or numbered ("1. x") line is CONTENT even if
            # it contains the keyword ("- finding one"), and '#' lines are
            # headings even though they start with a marker.
            def _is_header(candidate: str, keyword: str) -> bool:
                if not candidate or len(candidate) > 60:
                    return False
                if keyword not in candidate.lower():
                    return False
                if candidate.startswith("#"):
                    return True
                if candidate.startswith(("-", "•", "*")) or re.match(r'^\d+[\.\)]\s', candidate):
                    return False
                return True

            if current_section is None and _is_header(stripped, "summary") \
                    and not findings and not action_lines:
                current_section = "summary"
                continue
            if current_section == "summary" and _is_header(stripped, "finding"):
                current_section = "findings"
                continue
            if current_section in ("summary", "findings") and _is_header(stripped, "recommend"):
                current_section = "action"
                continue

            if current_section == "summary":
                if stripped:
                    summary_lines.append(stripped)
            elif current_section == "findings":
                if not stripped:
                    continue
                if stripped.startswith(("-", "•", "*")) or re.match(r'^\*{0,2}\d+[\.\)]\s+', stripped):
                    # marked finding line (bullet or number) — marker stripped
                    # later by the narrative contract; backend owns numbering
                    findings.append(stripped.rstrip())
                elif findings:
                    # unmarked line after a finding: continuation (supporting
                    # sentence of the same finding), e.g. "Evidence: ..."
                    findings[-1] = findings[-1].rstrip() + "\n" + stripped
                else:
                    # unmarked line before any finding: prose intro, skip
                    continue
            elif current_section == "action":
                if stripped:
                    action_lines.append(stripped)

        summary = " ".join(summary_lines).strip()
        recommended_action = "\n".join(action_lines).strip()

        return {
            "summary": summary or text[:200].strip(),  # Fallback to first 200 chars
            "key_findings": findings or [risk_event.get("primary_reason", "Risk detected")],
            "recommended_action": recommended_action or risk_event.get("recommended_action", "Further review needed"),
        }

    def _model_based_explanation(
        self,
        risk_event: Dict[str, Any],
        risk_factors: List[Dict[str, Any]],
        explanation_source: str = "MODEL_FALLBACK",
        llm_error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate consistent model-based explanation used for both unavailable LLM and fallback.

        This ensures investigators see the same core explanation content regardless of
        why LLM isn't being used (unavailable vs failed).

        Args:
            risk_event: Risk event data with scores
            risk_factors: List of risk factor details
            explanation_source: Either "MODEL_FALLBACK" or "LLM"
            llm_error: Optional short error message for LLM failures

        Returns:
            Dict with summary, key_findings, recommended_action, explanation_source, llm_error
        """
        risk_score = risk_event.get('risk_score', 0)
        risk_level = risk_event.get('risk_level', 'UNKNOWN')
        primary_reason = risk_event.get('primary_reason', 'Suspicious activity detected')
        ml_score = risk_event.get('ml_score', 0)
        rule_score = risk_event.get('rule_score', 0)
        graph_score = risk_event.get('graph_score', 0)

        # Build consistent summary
        summary = (
            f"This account received a {risk_level.lower()} risk score ({risk_score:.2f}/100). "
            f"Primary concern: {primary_reason}."
        )

        # Build consistent key_findings from signal scores and factors
        key_findings = []

        if ml_score > 0:
            key_findings.append(f"ML Signal Score: {ml_score:.2f}")

        if rule_score > 0:
            key_findings.append(f"Rule Engine Signal Score: {rule_score:.2f}")

        if graph_score > 0:
            key_findings.append(f"Graph Network Signal Score: {graph_score:.2f}")

        # Add specific risk factors if available
        for factor in risk_factors[:3]:
            factor_name = factor.get('factor_name', 'Unknown factor')
            key_findings.append(f"Elevated {factor_name}")

        if not key_findings:
            key_findings.append("Risk signals detected through analysis")

        # Use recommended_action from risk_event
        recommended_action = risk_event.get('recommended_action', 'Manual review required')

        return {
            "summary": summary,
            "key_findings": key_findings,
            "recommended_action": recommended_action,
            "explanation_source": explanation_source,
            "llm_error": llm_error,
        }
