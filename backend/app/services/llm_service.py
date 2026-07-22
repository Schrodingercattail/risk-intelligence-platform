"""
LLM Explanation Service (Optional Extension)

Abstracted service for generating AI-assisted investigation explanations.
This is an OPTIONAL enhancement — the platform operates fully without LLM integration.

When ANTHROPIC_API_KEY is configured: LLM generates natural language case summaries
When not configured: Returns structured explanations from model outputs

Supports Claude (default) with extensibility for other providers.
"""
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import os

from anthropic import Anthropic

from app.config import settings


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

    def __init__(self, api_key: str):
        """Initialize Claude client."""
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")
        self.client = Anthropic(api_key=api_key)

    async def generate_explanation(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate explanation using Claude API."""
        message = self.client.messages.create(
            model=settings.LLM_MODEL,
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
            Dict with summary, key_findings, and recommended_action
        """
        if not self.provider:
            return self._mock_explanation(risk_event, risk_factors)

        # Construct prompt
        prompt = self._construct_prompt(user_id, risk_event, risk_factors, graph_data)

        # Generate explanation
        try:
            explanation_text = await self.provider.generate_explanation(prompt)

            # Parse response into structured format
            return self._parse_explanation(explanation_text, risk_event)

        except Exception as e:
            # Fallback to structured response on error
            return self._structured_fallback(risk_event, risk_factors, str(e))

    def _construct_prompt(
        self,
        user_id: str,
        risk_event: Dict[str, Any],
        risk_factors: List[Dict[str, Any]],
        graph_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Construct the LLM prompt from structured data."""
        prompt_parts = [
            f"## Risk Analysis for User: {user_id}\n",
            f"### Overall Risk Assessment",
            f"- Risk Score: {risk_event.get('risk_score', 'N/A')}/100",
            f"- Risk Level: {risk_event.get('risk_level', 'N/A')}",
            f"- Primary Reason: {risk_event.get('primary_reason', 'N/A')}\n",
            f"### Component Scores",
            f"- ML Score: {risk_event.get('ml_score', 'N/A')}",
            f"- Rule Score: {risk_event.get('rule_score', 'N/A')}",
            f"- Graph Score: {risk_event.get('graph_score', 'N/A')}\n",
        ]

        if risk_factors:
            prompt_parts.append("### Key Risk Factors")
            for factor in risk_factors[:5]:  # Top 5 factors
                prompt_parts.append(
                    f"- {factor.get('factor_name')}: {factor.get('factor_description', '')}"
                )
            prompt_parts.append("")

        if graph_data and graph_data.get('nodes'):
            connected_count = len(graph_data['nodes']) - 1  # Exclude self
            if connected_count > 0:
                prompt_parts.append(
                    f"### Network Analysis\n"
                    f"- This user is connected to {connected_count} other accounts\n"
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

    def _mock_explanation(
        self,
        risk_event: Dict[str, Any],
        risk_factors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Return a mock explanation when no LLM provider is configured."""
        top_factors = [f.get('factor_name', 'Unknown') for f in risk_factors[:3]]

        return {
            "summary": (
                f"This account has a risk score of {risk_event.get('risk_score', 'NAVA')}/100, "
                f"indicating {risk_event.get('risk_level', 'UNKNOWN')} risk level. "
                f"Primary concern: {risk_event.get('primary_reason', 'Suspicious activity detected')}."
            ),
            "key_findings": [
                f"Elevated {factor} detected" for factor in top_factors
            ] or ["Suspicious activity patterns detected"],
            "recommended_action": risk_event.get("recommended_action", "Manual investigation required"),
        }

    def _structured_fallback(
        self,
        risk_event: Dict[str, Any],
        risk_factors: List[Dict[str, Any]],
        error: str
    ) -> Dict[str, Any]:
        """Return structured explanation when LLM call fails."""
        return {
            "summary": (
                f"Risk analysis completed with score {risk_event.get('risk_score', 'N/A')}/100. "
                f"Note: AI explanation generation encountered an error."
            ),
            "key_findings": [
                f.get('factor_description') or f.get('factor_name')
                for f in risk_factors[:3]
            ],
            "recommended_action": risk_event.get("recommended_action", "Manual review required"),
            "error": f"Explanation generation error: {error}",
        }
