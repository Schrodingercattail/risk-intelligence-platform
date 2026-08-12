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
        """Generate explanation using Claude API."""
        message = self.client.messages.create(
            model=settings.ANTHROPIC_MODEL or settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            system=system_prompt or self._default_system_prompt(),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text

    def _default_system_prompt(self) -> str:
        """Default system prompt for risk analyst role."""
        return """You are an expert risk analyst for a risk intelligence platform. Your role is to:

1. Analyze risk data and explain findings clearly
2. Identify the most critical risk factors
3. Provide actionable recommendations
4. Maintain a professional, objective tone

When explaining risk, always:
- Start with a clear summary
- List specific findings with evidence
- End with a recommended action
- Keep explanations concise but thorough"""


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
    ) -> Dict[str, Any]:
        """
        Generate AI-powered investigation explanation.

        Args:
            user_id: User being analyzed
            risk_event: Risk event data with scores
            risk_factors: List of risk factor details
            graph_data: Optional relationship graph data

        Returns:
            Dict with summary, key_findings, recommended_action, explanation_source, and llm_error
        """
        if not self.provider:
            # LLM unavailable - return model-based explanation with MODEL_FALLBACK source
            return self._model_based_explanation(
                risk_event, risk_factors, explanation_source="MODEL_FALLBACK", llm_error=None
            )

        # Construct prompt
        prompt = self._construct_prompt(user_id, risk_event, risk_factors, graph_data)

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

    def _construct_prompt(
        self,
        user_id: str,
        risk_event: Dict[str, Any],
        risk_factors: List[Dict[str, Any]],
        graph_data: Optional[Dict[str, Any]] = None,
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
        ])

        return "\n".join(prompt_parts)

    def _parse_explanation(self, text: str, risk_event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        # Simple parsing - in production would use more sophisticated parsing
        lines = text.split('\n')

        summary = ""
        key_findings = []
        recommended_action = ""

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers
            if "summary" in line.lower():
                current_section = "summary"
                continue
            elif "finding" in line.lower():
                current_section = "findings"
                continue
            elif "recommend" in line.lower():
                current_section = "action"
                continue

            # Accumulate content
            if current_section == "summary":
                summary += line + " "
            elif current_section == "findings" and line.startswith(("-", "•", "*")):
                key_findings.append(line.lstrip("-•* "))
            elif current_section == "action":
                recommended_action += line + " "

        return {
            "summary": summary.strip() or text[:200],  # Fallback to first 200 chars
            "key_findings": key_findings or [risk_event.get("primary_reason", "Risk detected")],
            "recommended_action": recommended_action.strip() or risk_event.get("recommended_action", "Further review needed"),
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
