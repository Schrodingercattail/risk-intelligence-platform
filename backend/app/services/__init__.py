"""
Services Package

All business logic services are defined here.
This layer is separate from the API layer and contains the core business logic.
"""

from typing import Protocol, runtime_checkable
from abc import ABC, abstractmethod


@runtime_checkable
class FeatureEngineeringService(Protocol):
    """
    Feature Engineering Service Interface

    Input: Raw data (users, devices, trades, withdrawals)
    Output: feature_table records
    """

    @abstractmethod
    async def generate_features(
        self,
        users_df,
        devices_df,
        trades_df,
        withdrawals_df
    ):
        """Generate features from raw data."""
        pass


@runtime_checkable
class RiskScoringService(Protocol):
    """
    Risk Scoring Service Interface

    Orchestrates ML + Rules + Graph for combined risk scoring.
    Input: feature_table
    Output: risk_events with ml_score, rule_score, graph_score, final_score
    """

    @abstractmethod
    async def score_user(self, user_id: str, feature_dict: dict) -> dict:
        """Calculate risk scores for a user."""
        pass


@runtime_checkable
class GraphAnalysisService(Protocol):
    """
    Graph Analysis Service Interface

    Input: device relationships, trading patterns
    Output: clusters, linked accounts, graph structure
    """

    @abstractmethod
    async def detect_clusters(self, devices_df, trades_df) -> list:
        """Detect suspicious account clusters."""
        pass

    @abstractmethod
    async def get_user_graph(self, user_id: str) -> dict:
        """Get relationship graph for a user."""
        pass


@runtime_checkable
class LLMExplanationService(Protocol):
    """
    LLM Explanation Service Interface

    Input: risk_event + factors + graph_data
    Output: structured_explanation
    """

    @abstractmethod
    async def generate_explanation(
        self,
        user_id: str,
        risk_event: dict,
        risk_factors: list,
        graph_data: dict
    ) -> dict:
        """Generate AI-powered investigation explanation."""
        pass
