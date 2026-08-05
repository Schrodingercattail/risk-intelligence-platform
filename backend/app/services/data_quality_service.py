"""
Data quality and evidence completeness checks.

This service identifies missing investigation inputs.
It does NOT infer risk.
It does NOT use policy citations.
"""

from typing import List


class DataQualityService:
    """
    Check whether required evidence exists for investigation.
    """

    def generate_missing_info(
        self,
        user,
        trades_exist: bool,
        device_exists: bool,
        graph_device_evidence_exists: bool,
    ) -> List[str]:

        missing_info = []

        # Account age / onboarding
        if not getattr(user, "account_created_time", None):
            missing_info.append(
                "Account age and onboarding date"
            )

        # Transaction evidence
        if not trades_exist:
            missing_info.append(
                "Transaction history"
            )

        # Device / IP evidence
        if (
            not device_exists
            and not graph_device_evidence_exists
        ):
            missing_info.append(
                "Device fingerprint and IP history"
            )

        # KYC evidence
        if not getattr(user, "kyc_level", None):
            missing_info.append(
                "Customer KYC verification status"
            )

        return missing_info


def create_data_quality_service():
    return DataQualityService()
