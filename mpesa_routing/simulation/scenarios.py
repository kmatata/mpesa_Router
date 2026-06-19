"""Pre-built demonstration scenarios."""

from .engine import Scenario
from ..core.transaction import DestinationType, Urgency


def crypto_otc_payout() -> Scenario:
    """2M KES to a single counterparty — tests max daily throughput."""
    return Scenario(
        name="Crypto OTC Payout",
        description="2M KES to a single counterparty",
        transaction_amount=2_000_000,
        num_transactions=1,
        urgency=Urgency.IMMEDIATE,
        destination_type=DestinationType.PHONE,
    )


def diaspora_remittance_batch() -> Scenario:
    """10 x 500K KES payouts to different recipients."""
    return Scenario(
        name="Diaspora Remittance Batch",
        description="10 x 500K KES payouts to different recipients",
        transaction_amount=500_000,
        num_transactions=10,
        urgency=Urgency.NORMAL,
        destination_type=DestinationType.PHONE,
    )


def property_deposit() -> Scenario:
    """5M KES one-time payment for property purchase."""
    return Scenario(
        name="Property Deposit",
        description="5M KES one-time payment for property purchase",
        transaction_amount=5_000_000,
        num_transactions=1,
        urgency=Urgency.IMMEDIATE,
        destination_type=DestinationType.PAYBILL,
    )


def bulk_agent_disbursement() -> Scenario:
    """20 x 50K KES to different agents."""
    return Scenario(
        name="Agent Disbursement",
        description="20 x 50K KES to different agents",
        transaction_amount=50_000,
        num_transactions=20,
        urgency=Urgency.NORMAL,
        destination_type=DestinationType.AGENT,
    )


def standard_scenarios() -> list:
    return [
        crypto_otc_payout(),
        diaspora_remittance_batch(),
        property_deposit(),
        bulk_agent_disbursement(),
    ]
