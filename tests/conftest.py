"""Shared fixtures for M-Pesa routing engine tests."""

import pytest

from mpesa_routing.core.account import MpesaAccount, KYCLevel, AccountPool
from mpesa_routing.core.transaction import Transaction, DestinationType, Urgency
from mpesa_routing.core.constraints import ConstraintGraph


@pytest.fixture
def tier3_account() -> MpesaAccount:
    return MpesaAccount("acc_001", KYCLevel.TIER_3, "Primary", "Nairobi")


@pytest.fixture
def tier2_account() -> MpesaAccount:
    return MpesaAccount("acc_002", KYCLevel.TIER_2, "Backup", "Nairobi")


@pytest.fixture
def tier1_account() -> MpesaAccount:
    return MpesaAccount("acc_003", KYCLevel.TIER_1, "Limited", "Nairobi")


@pytest.fixture
def business_account() -> MpesaAccount:
    return MpesaAccount("acc_biz", KYCLevel.TIER_3, "Business", "Nairobi", is_business=True)


@pytest.fixture
def empty_pool() -> AccountPool:
    return AccountPool()


@pytest.fixture
def populated_pool(tier3_account, tier2_account, tier1_account, business_account) -> AccountPool:
    pool = AccountPool()
    pool.add(tier3_account)
    pool.add(tier2_account)
    pool.add(tier1_account)
    pool.add(business_account)
    return pool


@pytest.fixture
def empty_graph() -> ConstraintGraph:
    return ConstraintGraph()


@pytest.fixture
def populated_graph(populated_pool) -> ConstraintGraph:
    graph = ConstraintGraph()
    for acc in populated_pool:
        graph.add_account(acc)
    return graph


@pytest.fixture
def sample_transaction() -> Transaction:
    return Transaction(250_000, DestinationType.PHONE, "recip_1", Urgency.NORMAL, "Nairobi")
