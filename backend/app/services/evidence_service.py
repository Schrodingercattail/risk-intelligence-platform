"""
Risk Evidence Explainability Service

Provides read-only evidence aggregation for investigation workflow.
This service does NOT modify risk scores or perform new detection.
It only aggregates existing evidence from database tables.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from decimal import Decimal
from datetime import datetime, timezone


class EvidenceService:
    """
    Risk Evidence Explainability Service

    READ-ONLY service that aggregates evidence from existing database tables.
    Does not modify risk scoring, ML predictions, or perform new detection.

    Evidence sources:
    - Transaction data (trades table)
    - Withdrawal data (withdrawals table)
    - Network/cluster data (account_clusters, cluster_members)
    - Risk factors (risk_factors table)
    - Feature data (feature_table)
    """

    def __init__(self, db: AsyncSession):
        """Initialize evidence service with database session."""
        self.db = db

    async def get_case_evidence(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete evidence package for a user's risk case.

        Args:
            user_id: User to get evidence for

        Returns:
            Evidence dict with all available evidence types
        """
        # Get latest risk event for summary
        risk_summary = await self._get_risk_summary(user_id)

        # Gather evidence from all sources
        transaction_evidence = await self._get_transaction_evidence(user_id)
        withdrawal_evidence = await self._get_withdrawal_evidence(user_id)
        network_evidence = await self._get_network_evidence(user_id)
        risk_factor_evidence = await self._get_risk_factor_evidence(user_id)
        feature_evidence = await self._get_feature_evidence(user_id)
        rule_evidence = await self._derive_rule_evidence(user_id, feature_evidence)

        return {
            "user_id": user_id,
            "risk_summary": risk_summary,
            "transaction_evidence": transaction_evidence,
            "withdrawal_evidence": withdrawal_evidence,
            "network_evidence": network_evidence,
            "risk_factor_evidence": risk_factor_evidence,
            "feature_evidence": feature_evidence,
            "rule_evidence": rule_evidence,
        }

    async def _get_risk_summary(self, user_id: str) -> Dict[str, Any]:
        """Get risk summary from latest risk event."""
        from app.models.database import RiskEvent

        result = await self.db.execute(
            select(RiskEvent)
            .where(RiskEvent.user_id == user_id)
            .order_by(desc(RiskEvent.detected_at))
            .limit(1)
        )
        event = result.scalar_one_or_none()

        if not event:
            return {
                "risk_level": "UNKNOWN",
                "risk_score": 0,
                "primary_reason": None,
                "recommended_action": None,
                "detection_methods": [],
                "detected_at": None,
            }

        # Determine detection methods from scores
        detection_methods = self._get_detection_methods(
            event.ml_score, event.rule_score, event.graph_score
        )

        return {
            "risk_level": event.risk_level,
            "risk_score": float(event.risk_score),
            "primary_reason": event.primary_reason,
            "recommended_action": event.recommended_action,
            "detection_methods": detection_methods,
            "detected_at": event.detected_at.isoformat() if event.detected_at else None,
            "ml_score": float(event.ml_score) if event.ml_score else None,
            "rule_score": float(event.rule_score) if event.rule_score else None,
            "graph_score": float(event.graph_score) if event.graph_score else None,
        }

    def _get_detection_methods(
        self,
        ml_score: Optional[float],
        rule_score: Optional[float],
        graph_score: Optional[float]
    ) -> List[str]:
        """
        Get detection methods that contributed meaningful risk signals.

        Uses same thresholds as detection attribution in risk routes.
        """
        from app.config import settings

        methods = []
        if ml_score is not None and ml_score >= settings.DETECTION_ML_THRESHOLD:
            methods.append("LightGBM")
        if rule_score is not None and rule_score >= settings.DETECTION_RULE_THRESHOLD:
            methods.append("Rule Engine")
        if graph_score is not None and graph_score >= settings.DETECTION_GRAPH_THRESHOLD:
            methods.append("Graph Network")
        return methods

    async def _get_transaction_evidence(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get suspicious transaction evidence.

        Returns top transactions by value (price * quantity).
        These are transactions that may warrant investigation.
        """
        from app.models.database import Trade

        # Get top trades by calculated value
        result = await self.db.execute(
            select(Trade)
            .where(Trade.user_id == user_id)
            .order_by(desc(Trade.price * Trade.quantity))
            .limit(limit)
        )

        transactions = []
        for trade in result.scalars().all():
            value = float(trade.price) * float(trade.quantity)
            transactions.append({
                "transaction_id": trade.trade_id,
                "symbol": trade.symbol,
                "side": trade.side,
                "price": float(trade.price),
                "quantity": float(trade.quantity),
                "value": value,
                "timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
                "risk_reason": self._classify_transaction_risk(trade, value),
            })

        return transactions

    def _classify_transaction_risk(self, trade, value: float) -> str:
        """Classify transaction risk level for explainability."""
        # Simple heuristic for transaction risk explanation
        if value > 100000:
            return "Large transaction amount"
        elif trade.side == "SELL" and value > 50000:
            return "Large sell transaction"
        elif value > 20000:
            return "Above average transaction value"
        else:
            return "Recent trading activity"

    async def _get_withdrawal_evidence(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get withdrawal evidence.

        Returns top withdrawals by amount.
        Highlights withdrawals to new addresses which may indicate risk.
        """
        from app.models.database import Withdrawal

        result = await self.db.execute(
            select(Withdrawal)
            .where(Withdrawal.user_id == user_id)
            .order_by(desc(Withdrawal.amount))
            .limit(limit)
        )

        withdrawals = []
        for w in result.scalars().all():
            withdrawals.append({
                "withdrawal_id": w.withdraw_id,
                "asset": w.asset,
                "amount": float(w.amount),
                "address": w.address,
                "is_new_address": w.is_new_address,
                "timestamp": w.timestamp.isoformat() if w.timestamp else None,
                "risk_reason": self._classify_withdrawal_risk(w),
            })

        return withdrawals

    def _classify_withdrawal_risk(self, withdrawal) -> str:
        """Classify withdrawal risk level for explainability."""
        if withdrawal.is_new_address:
            return "Withdrawal to new address"
        elif float(withdrawal.amount) > 10:
            return "Large withdrawal amount"
        elif float(withdrawal.amount) > 5:
            return "Above average withdrawal"
        else:
            return "Recent withdrawal activity"

    async def _get_network_evidence(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get network/graph evidence from cluster membership.

        Shows if user is part of a suspicious cluster.
        """
        from app.models.database import ClusterMember, AccountCluster, Device

        # Get cluster membership
        result = await self.db.execute(
            select(ClusterMember, AccountCluster)
            .join(AccountCluster, ClusterMember.cluster_id == AccountCluster.cluster_id)
            .where(ClusterMember.user_id == user_id)
            .limit(1)
        )

        cluster_row = result.first()
        if not cluster_row:
            return None

        member, cluster = cluster_row

        # Get related accounts (same cluster)
        related_result = await self.db.execute(
            select(ClusterMember.user_id)
            .where(ClusterMember.cluster_id == cluster.cluster_id)
            .where(ClusterMember.user_id != user_id)
            .limit(10)
        )
        related_accounts = [row[0] for row in related_result]

        # Get shared devices
        device_result = await self.db.execute(
            select(Device.device_id)
            .join(ClusterMember, ClusterMember.user_id == Device.user_id)
            .where(ClusterMember.cluster_id == cluster.cluster_id)
            .where(Device.device_id.isnot(None))
            .distinct()
            .limit(5)
        )
        shared_devices = [row[0] for row in device_result]

        return {
            "cluster_id": cluster.cluster_id,
            "cluster_name": cluster.cluster_name,
            "detection_type": cluster.detection_type,
            "member_count": cluster.member_count,
            "cluster_risk_score": float(cluster.risk_score),
            "role_in_cluster": member.role_in_cluster,
            "related_accounts_count": len(related_accounts),
            "related_accounts": related_accounts[:5],  # Return top 5
            "shared_devices": shared_devices,
        }

    async def get_network_signals(self, user_id: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """
        Get detailed network signals showing entity-level relationships.

        This provides actionable investigation evidence by showing:
        - Which specific accounts are connected
        - What relationship type connects them (shared device, shared IP)
        - The evidence entities (device IDs, IP addresses)
        - Each related account's risk level and score

        Args:
            user_id: User to get network signals for
            limit: Maximum number of connected accounts to return

        Returns:
            Network signals dict with connected accounts details, or None if no relationships
        """
        from app.models.database import ClusterMember, AccountCluster, Device, RiskEvent, User

        # Get cluster membership for the user
        cluster_result = await self.db.execute(
            select(ClusterMember, AccountCluster)
            .join(AccountCluster, ClusterMember.cluster_id == AccountCluster.cluster_id)
            .where(ClusterMember.user_id == user_id)
            .limit(1)
        )

        cluster_row = cluster_result.first()
        if not cluster_row:
            # No network relationships found
            return None

        user_member, cluster = cluster_row

        # Get all related accounts in the same cluster (excluding self)
        members_result = await self.db.execute(
            select(ClusterMember)
            .where(ClusterMember.cluster_id == cluster.cluster_id)
            .where(ClusterMember.user_id != user_id)
        )
        related_members = members_result.scalars().all()

        if not related_members:
            return {
                "connected_account_count": 0,
                "connected_accounts": []
            }

        # Get detailed relationship evidence for each related account
        connected_accounts = []
        for related_member in related_members[:limit]:
            related_user_id = related_member.user_id

            # Determine relationship types and evidence entities
            relationship_types = []
            device_fingerprints = []
            shared_ips = []

            # Check for shared device relationship
            if cluster.detection_type == "device_sharing":
                # Get devices shared between the two users
                user_devices_result = await self.db.execute(
                    select(Device.device_id)
                    .where(Device.user_id == user_id)
                    .where(Device.device_id.isnot(None))
                )
                user_devices = {row[0] for row in user_devices_result}

                related_devices_result = await self.db.execute(
                    select(Device.device_id)
                    .where(Device.user_id == related_user_id)
                    .where(Device.device_id.isnot(None))
                )
                related_devices = {row[0] for row in related_devices_result}

                shared = user_devices & related_devices
                if shared:
                    relationship_types.append("shared_device")
                    device_fingerprints = list(shared)[:3]  # Top 3 shared devices

            # Check for shared IP relationship
            user_ips_result = await self.db.execute(
                select(Device.ip_address)
                .where(Device.user_id == user_id)
                .where(Device.ip_address.isnot(None))
            )
            user_ips = {row[0] for row in user_ips_result}

            related_ips_result = await self.db.execute(
                select(Device.ip_address)
                .where(Device.user_id == related_user_id)
                .where(Device.ip_address.isnot(None))
            )
            related_ips = {row[0] for row in related_ips_result}

            shared_ip_set = user_ips & related_ips
            if shared_ip_set:
                relationship_types.append("shared_ip")
                shared_ips = [ip for ip in list(shared_ip_set)[:3]]  # Top 3 shared IPs

            # Get related account's risk level and score
            risk_result = await self.db.execute(
                select(RiskEvent.risk_level, RiskEvent.risk_score)
                .join(User, RiskEvent.user_id == User.user_id)
                .where(RiskEvent.user_id == related_user_id)
                .order_by(RiskEvent.detected_at.desc())
                .limit(1)
            )
            risk_row = risk_result.first()

            risk_level = risk_row[0] if risk_row else "UNKNOWN"
            risk_score = float(risk_row[1]) if risk_row and risk_row[1] else 0

            connected_accounts.append({
                "user_id": related_user_id,
                "relationship_type": relationship_types,
                "device_fingerprints": device_fingerprints,
                "shared_ips": shared_ips,
                "risk_level": risk_level,
                "risk_score": risk_score
            })

        # Sort by risk score (highest first) for investigation priority
        connected_accounts.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "connected_account_count": len(related_members),
            "connected_accounts": connected_accounts
        }

    async def _get_risk_factor_evidence(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get risk factor evidence from latest risk event.

        These are the detailed factors that contributed to the risk score.
        """
        from app.models.database import RiskEvent, RiskFactor

        # Get latest risk event
        event_result = await self.db.execute(
            select(RiskEvent)
            .where(RiskEvent.user_id == user_id)
            .order_by(desc(RiskEvent.detected_at))
            .limit(1)
        )
        event = event_result.scalar_one_or_none()

        if not event:
            return []

        # Get risk factors for this event
        factors_result = await self.db.execute(
            select(RiskFactor)
            .where(RiskFactor.risk_event_id == event.id)
            .limit(10)
        )

        factors = []
        for factor in factors_result.scalars().all():
            # Determine severity based on factor value
            severity = self._classify_factor_severity(factor)

            factors.append({
                "factor_id": factor.id,
                "factor_name": factor.factor_name,
                "factor_value": float(factor.factor_value) if factor.factor_value else None,
                "factor_description": factor.factor_description,
                "severity": severity,
            })

        return factors

    def _classify_factor_severity(self, factor) -> str:
        """Classify risk factor severity."""
        if factor.factor_value is None:
            return "low"

        value = float(factor.factor_value)

        # Severity heuristics based on factor type
        if "cluster" in factor.factor_name.lower() or "network" in factor.factor_name.lower():
            if value > 10:
                return "critical"
            elif value > 5:
                return "high"
        elif "device" in factor.factor_name.lower():
            if value > 3:
                return "high"
            elif value > 1:
                return "medium"
        elif "new account" in factor.factor_name.lower():
            if value < 30:
                return "high"
            elif value < 90:
                return "medium"

        return "medium"

    async def _get_feature_evidence(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get feature evidence from feature table.

        Returns key feature values that contributed to the risk score.
        """
        from app.models.database import FeatureTable

        result = await self.db.execute(
            select(FeatureTable).where(FeatureTable.user_id == user_id)
        )
        feature = result.scalar_one_or_none()

        if not feature:
            return None

        # Extract key features for explainability
        return {
            "shared_device_count": feature.shared_device_count,
            "linked_account_count": feature.linked_account_count,
            "unique_ip_count": feature.unique_ip_count,
            "trade_frequency_24h": feature.trade_frequency_24h,
            "trade_frequency_7d": feature.trade_frequency_7d,
            "opposite_trade_ratio": float(feature.opposite_trade_ratio) if feature.opposite_trade_ratio else None,
            "avg_trade_size": float(feature.avg_trade_size) if feature.avg_trade_size else None,
            "trade_volume_24h": float(feature.trade_volume_24h) if feature.trade_volume_24h else None,
            "account_age_days": feature.account_age_days,
            "active_days_count": feature.active_days_count,
            "withdrawal_risk_score": float(feature.withdrawal_risk_score) if feature.withdrawal_risk_score else None,
            "withdrawal_frequency_24h": feature.withdrawal_frequency_24h,
            "withdrawal_volume_24h": float(feature.withdrawal_volume_24h) if feature.withdrawal_volume_24h else None,
        }

    async def _derive_rule_evidence(self, user_id: str, feature_evidence: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Derive rule evidence from feature values.

        Since rules are hardcoded in RiskScoringService, we derive
        which rules would have triggered based on feature values.

        This is a READ-ONLY derivation - no new rule evaluation.
        """
        if not feature_evidence:
            return []

        triggered_rules = []

        # Rule: New account with high activity
        account_age = feature_evidence.get("account_age_days")
        trade_freq = feature_evidence.get("trade_frequency_24h")
        if account_age and trade_freq and account_age < 7 and trade_freq > 50:
            triggered_rules.append({
                "rule_name": "New account with high activity",
                "severity": "HIGH",
                "description": f"Account is {account_age} days old with {trade_freq} trades in 24h",
            })

        # Rule: High opposite trade ratio (frequent alternating buy/sell behavior)
        opp_ratio = feature_evidence.get("opposite_trade_ratio")
        if opp_ratio and opp_ratio > 0.4:
            triggered_rules.append({
                "rule_name": "High opposite trade ratio",
                "severity": "HIGH",
                "description": f"Opposite trade ratio of {opp_ratio:.1%} indicates frequent alternating buy/sell behavior and possible wash trading pattern",
            })

        # Rule: Multiple shared devices
        shared_devices = feature_evidence.get("shared_device_count")
        if shared_devices and shared_devices > 3:
            triggered_rules.append({
                "rule_name": "Multiple shared devices",
                "severity": "HIGH",
                "description": f"User shares {shared_devices} devices with other accounts",
            })

        # Rule: High withdrawal frequency
        withdrawal_freq = feature_evidence.get("withdrawal_frequency_24h")
        if withdrawal_freq and withdrawal_freq > 5:
            triggered_rules.append({
                "rule_name": "High withdrawal frequency",
                "severity": "MEDIUM",
                "description": f"{withdrawal_freq} withdrawals in 24h exceeds normal pattern",
            })

        # Rule: Linked account network
        linked_accounts = feature_evidence.get("linked_account_count")
        if linked_accounts and linked_accounts > 5:
            triggered_rules.append({
                "rule_name": "Large linked account network",
                "severity": "MEDIUM",
                "description": f"User connected to {linked_accounts} other accounts",
            })

        return triggered_rules
