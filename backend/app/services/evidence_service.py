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

    # Feature-level factor name -> the finding names it corresponds to.
    # RiskFactor rows are CONTEXTUAL / feature-level descriptive evidence (see
    # RiskScoringService._create_risk_factors) — they are NOT ML findings.
    # This mapping only records which unified finding a factor describes.
    # Note: opposite_trade_ratio is handled separately below due to threshold semantics.
    _FEATURE_FINDING_NAMES = {
        "shared_device_count": "Shared Device Relationships",
        "linked_account_count": "Linked Account Network",
        "trade_frequency_24h": "High Trading Frequency",
        "withdrawal_risk_score": "Abnormal Withdrawal Behavior",
    }

    # Threshold-based finding names (rule-triggered vs contextual)
    # These are handled separately because the finding name depends on threshold
    _THRESHOLD_FINDINGS = {
        "opposite_trade_ratio": {
            "threshold": 0.4,
            "rule_triggered_name": "Coordinated Trading Pattern",
            "contextual_name": "Opposite Trade Ratio",
        }
    }

    # Investigator-facing evidence text for feature findings with no persisted
    # RiskFactor description (stale/historical cases). Raw field names would
    # violate the narrative contract if this text reaches the narrative via
    # the completeness append.
    _FEATURE_FALLBACK_EVIDENCE = {
        "shared_device_count": "{value} linked account(s) through shared devices",
        "linked_account_count": "{value} connected account(s) detected",
        "trade_frequency_24h": "{value} trades were recorded in 24 hours",
        "withdrawal_risk_score": "abnormal withdrawal behavior was observed (elevated risk indicator)",
    }

    async def get_canonical_evidence(
        self,
        user_id: str,
        risk_event=None,
        risk_factors: Optional[List[Dict[str, Any]]] = None,
        graph_data: Optional[Dict[str, Any]] = None,
        has_graph_evidence: bool = False,
    ) -> Dict[str, Any]:
        """
        Build the CANONICAL structured evidence for a case.

        Two dimensions are kept strictly separate:
          1. findings[]       — WHAT the system observed (unified, deduplicated;
                                a finding may be supported by several sources)
          2. detection_sources — WHICH detection methods actually produced /
                                attributed that finding ("ML", "Rule", "Graph")

        RiskFactor rows are feature-level/contextual evidence and are NEVER
        auto-attributed to ML: "the ML model uses a feature" is not "ML
        independently detected this finding". Attribution is only added where
        the system has real evidence for it (a triggered rule => "Rule";
        an actual graph relationship => "Graph").

        Structure:
            {
              "ml":       {score, probability, primary_driver},
              "rules":    {score, triggered: [...], consistent},
              "graph":    {score, has_evidence, connected_accounts | note},
              "contextual": {account_age_days, account_age_note},
              "findings": [
                  {name, evidence, detection_sources, evidence_type,
                   observed_value?, threshold?, contribution?, description?,
                   supporting_feature?}
              ],
            }

        Read-only; reuses _derive_rule_evidence (aligned with the scorer).
        """
        from app.models.database import RiskEvent as RiskEventModel

        if risk_event is None:
            result = await self.db.execute(
                select(RiskEventModel)
                .where(RiskEventModel.user_id == user_id)
                .order_by(desc(RiskEventModel.detected_at))
                .limit(1)
            )
            risk_event = result.scalar_one_or_none()
        if risk_event is None:
            return {"ml": None, "rules": None, "graph": None, "contextual": None, "findings": []}

        feature_evidence = await self._get_feature_evidence(user_id)
        rule_evidence = await self._derive_rule_evidence(user_id, feature_evidence)

        # Graph evidence: only when graph detection actually found something.
        if has_graph_evidence and graph_data:
            connected = max(len(graph_data.get("nodes") or []) - 1, 0)
            graph_evidence = {
                "score": float(risk_event.graph_score) if risk_event.graph_score else 0.0,
                "has_evidence": True,
                "connected_accounts": connected,
            }
        else:
            connected = 0
            graph_evidence = {
                "score": float(risk_event.graph_score) if risk_event.graph_score else 0.0,
                "has_evidence": False,
                "note": "No detected graph signal (graph_score = 0 means no "
                        "network relationship was found — it says nothing about "
                        "the account being isolated, evasive, or operating alone).",
            }

        findings: List[Dict[str, Any]] = []
        index: Dict[str, Dict[str, Any]] = {}

        def upsert(name, sources, evidence_type, evidence, observed=None,
                   threshold=None, contribution=None, description=None,
                   supporting_feature=None):
            """One real finding appears once; multiple sources merge on it."""
            if name in index:
                existing = index[name]
                for s in sources:
                    if s not in existing["detection_sources"]:
                        existing["detection_sources"].append(s)
                return
            f = {
                "name": name,
                "evidence": evidence,
                "detection_sources": list(sources),
                "evidence_type": evidence_type,
            }
            if observed is not None:
                f["observed_value"] = observed
            if threshold is not None:
                f["threshold"] = threshold
            if contribution is not None:
                f["contribution"] = contribution
            if description is not None:
                f["description"] = description
            if supporting_feature is not None:
                f["supporting_feature"] = supporting_feature
            findings.append(f)
            index[name] = f

        # --- ML detector-level signal (expressed as data so it is always
        # present in the findings list; it is a detector signal, NOT an
        # attribution of any feature finding to ML) ---
        ml_score = float(risk_event.ml_score) if risk_event.ml_score else 0.0
        if ml_score >= 50:
            upsert(
                "ML Pattern Detection Signal",
                ["ML"],
                "detector_signal",
                f"ML pattern detection score {ml_score}/100 — system signal, "
                "not a calibrated probability of fraud",
                observed={"ml_score": ml_score},
                supporting_feature="ml_score",
            )

        # --- Rule findings (authoritative, from _derive_rule_evidence) ---
        for rule in rule_evidence:
            name = rule["rule_name"]
            sources = ["Rule"]
            # A rule on trading frequency / withdrawal behavior is about the
            # same behavior the ML model scores, but ML attribution is only
            # claimed when ML actually flagged this case AND the finding maps
            # to an ML feature — modelUSES feature is not model DETECTED it.
            observed = dict(rule.get("trigger") or {})
            upsert(
                name,
                sources,
                "rule",
                rule.get("description", ""),
                observed=observed or None,
                threshold=rule.get("threshold"),
                contribution=rule.get("contribution"),
                description=rule.get("description"),
            )

        # --- Graph findings (only when graph detection found relationships) ---
        if graph_evidence["has_evidence"]:
            shared = (feature_evidence or {}).get("shared_device_count") or 0
            if shared > 0:
                upsert(
                    "Shared Device Relationships",
                    ["Graph"],
                    "graph",
                    f"{shared} linked account(s) through shared devices",
                    observed={"shared_device_count": shared},
                    supporting_feature="shared_device_count",
                )
            upsert(
                "Linked Account Network",
                ["Graph"],
                "graph",
                f"{connected} connected account(s) detected by network analysis",
                observed={"connected_accounts": connected},
                supporting_feature="linked_account_count",
            )

        # --- Feature-level findings (contextual/behavioral observations) ---
        # RiskFactor rows describe observed behavior; they get a unified
        # finding WITHOUT ML attribution (no per-feature ML attribution is
        # persisted by the pipeline). If the same finding already exists
        # (rule/graph above), only merge sources — no duplicates.
        if feature_evidence:
            for feat_key, finding_name in self._FEATURE_FINDING_NAMES.items():
                value = feature_evidence.get(feat_key)
                if value is None or value == 0:
                    continue
                factor = next(
                    (f for f in (risk_factors or [])
                     if (f.get("factor_name") if isinstance(f, dict) else getattr(f, "factor_name", None)) == finding_name),
                    None,
                )
                desc = (factor.get("factor_description") if isinstance(factor, dict)
                        else getattr(factor, "factor_description", None)) if factor else None
                # Fallback text must be investigator-facing (no raw field
                # names): this string can surface in the user-facing narrative
                # via the narrative-contract completeness append.
                fallback_desc = self._FEATURE_FALLBACK_EVIDENCE.get(feat_key)
                upsert(
                    finding_name,
                    ["Feature"],
                    "feature",
                    desc or (fallback_desc.format(value=value) if fallback_desc
                             else f"{finding_name}: observed value {value}"),
                    observed={feat_key: value},
                    supporting_feature=feat_key,
                )

            # --- Threshold-based findings (opposite_trade_ratio) ---
            # Handle separately to provide semantic clarity:
            # - "Opposite Trade Ratio": contextual observation (below threshold)
            # - "Coordinated Trading Pattern": rule-triggered (above threshold)
            # This uses CURRENT semantic rules on the source FeatureTable value,
            # NOT the historical RiskFactor label (which may not exist for old cases).
            opp_ratio = feature_evidence.get("opposite_trade_ratio")
            if opp_ratio is not None and opp_ratio > 0:
                threshold_config = self._THRESHOLD_FINDINGS.get("opposite_trade_ratio", {})
                rule_threshold = threshold_config.get("threshold", 0.4)
                rule_triggered = opp_ratio > rule_threshold

                # Use CURRENT semantic naming based on threshold
                factor_name = (
                    threshold_config.get("rule_triggered_name") if rule_triggered
                    else threshold_config.get("contextual_name")
                )

                # Generate description using CURRENT semantic rules. The
                # narrative MUST distinguish the below-threshold OBSERVATION
                # from the threshold-triggered RULE — these strings feed the
                # LLM prompt (as evidence) and the completeness fallback text.
                percentage = opp_ratio * 100
                threshold_percent = rule_threshold * 100
                if rule_triggered:
                    desc = (
                        f"An opposite-trade ratio of {percentage:.2f}% exceeded the "
                        f"{threshold_percent:.0f}% threshold, triggering the "
                        f"coordinated trading rule."
                    )
                else:
                    desc = (
                        f"An opposite-trade ratio of {percentage:.2f}% was observed, "
                        f"which is below the {threshold_percent:.0f}% threshold for "
                        f"the coordinated trading rule."
                    )

                upsert(
                    factor_name,
                    ["Feature"],
                    "feature",
                    desc,
                    observed={"opposite_trade_ratio": opp_ratio},
                    supporting_feature="opposite_trade_ratio",
                )

        # --- Contextual account age (never a rule by itself) ---
        contextual = {}
        if feature_evidence:
            age = feature_evidence.get("account_age_days")
            if age is not None:
                contextual["account_age_days"] = age
                contextual["account_age_note"] = (
                    "Contextual evidence only. The ONLY account-age rule is "
                    "'New account with high activity' (account_age_days < 7 AND "
                    "trade_frequency_24h > 50)."
                )

        rule_score = float(risk_event.rule_score) if risk_event.rule_score else 0.0
        return {
            "ml": {
                "score": float(risk_event.ml_score) if risk_event.ml_score else 0.0,
                "probability": float(risk_event.risk_probability) if risk_event.risk_probability else None,
                "primary_driver": risk_event.primary_reason,
            },
            "rules": {
                "score": rule_score,
                "triggered": rule_evidence,
                "note": "Rule score = sum of triggered rule contributions (capped at 100).",
                "consistent": (
                    None if not feature_evidence
                    else (sum(r["contribution"] for r in rule_evidence) == int(rule_score))
                ),
            },
            "graph": graph_evidence,
            "contextual": contextual,
            "findings": findings,
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
            "first_withdrawal_flag": bool(feature.first_withdrawal_flag) if feature.first_withdrawal_flag is not None else None,
        }

    async def _derive_rule_evidence(self, user_id: str, feature_evidence: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Derive rule evidence from feature values.

        Since rules are hardcoded in RiskScoringService, we derive
        which rules would have triggered based on feature values.

        This is a READ-ONLY derivation - no new rule evaluation. The rules
        below MUST stay aligned with RiskScoringService._calculate_rule_score
        (same trigger conditions, same contributions), so the evidence shown
        to the LLM/citations/UI matches what actually produced rule_score.

        Each triggered rule carries its observed value(s), the threshold, and
        the score contribution, so consumers never have to guess what a
        rule_score number means.
        """
        if not feature_evidence:
            return []

        triggered_rules = []

        # Rule: New account with high activity
        account_age = feature_evidence.get("account_age_days")
        trade_freq = feature_evidence.get("trade_frequency_24h")
        if account_age is not None and trade_freq is not None and account_age < 7 and trade_freq > 50:
            triggered_rules.append({
                "rule_name": "New account with high activity",
                "severity": "HIGH",
                "description": f"Account is {account_age} days old with {trade_freq} trades in 24h",
                "trigger": {
                    "account_age_days": account_age,
                    "trade_frequency_24h": trade_freq,
                },
                "threshold": "account_age_days < 7 AND trade_frequency_24h > 50",
                "contribution": 40,
            })

        # Rule: High opposite trade ratio (frequent alternating buy/sell behavior)
        # Rule name matches the factor name for proper evidence merging
        opp_ratio = feature_evidence.get("opposite_trade_ratio")
        if opp_ratio and opp_ratio > 0.4:
            triggered_rules.append({
                "rule_name": "Coordinated Trading Pattern",  # Matches factor name for merging
                "severity": "HIGH",
                # Threshold-explicit business wording (the narrative must state
                # the rule fired because the ratio exceeded the 40% threshold);
                # mirrors the threshold-finding description above.
                "description": (
                    f"An opposite-trade ratio of {opp_ratio:.2%} exceeded the 40% "
                    f"threshold, triggering the coordinated trading rule."
                ),
                "trigger": {"opposite_trade_ratio": round(float(opp_ratio), 4)},
                "threshold": "opposite_trade_ratio > 0.4",
                "contribution": 35,
            })

        # Rule: Multiple shared devices
        shared_devices = feature_evidence.get("shared_device_count")
        if shared_devices and shared_devices > 3:
            triggered_rules.append({
                "rule_name": "Multiple shared devices",
                "severity": "HIGH",
                "description": f"User shares {shared_devices} devices with other accounts",
                "trigger": {"shared_device_count": shared_devices},
                "threshold": "shared_device_count > 3",
                "contribution": 30,
            })

        # Rule: High withdrawal frequency
        withdrawal_freq = feature_evidence.get("withdrawal_frequency_24h")
        if withdrawal_freq and withdrawal_freq > 5:
            triggered_rules.append({
                "rule_name": "High withdrawal frequency",
                "severity": "MEDIUM",
                "description": f"{withdrawal_freq} withdrawals in 24h exceeds the normal pattern",
                "trigger": {"withdrawal_frequency_24h": withdrawal_freq},
                "threshold": "withdrawal_frequency_24h > 5",
                "contribution": 25,
            })

        # Rule: First withdrawal (to a new address, with activity present)
        first_withdrawal = feature_evidence.get("first_withdrawal_flag")
        if first_withdrawal and withdrawal_freq is not None:
            triggered_rules.append({
                "rule_name": "First withdrawal to new address",
                "severity": "MEDIUM",
                "description": (
                    "First withdrawal to a new address flagged while withdrawal "
                    f"activity is present ({withdrawal_freq} in 24h)"
                ),
                "trigger": {
                    "first_withdrawal_flag": bool(first_withdrawal),
                    "withdrawal_frequency_24h": withdrawal_freq,
                },
                "threshold": "first_withdrawal_flag = true AND withdrawal_frequency_24h present",
                "contribution": 20,
            })

        return triggered_rules
