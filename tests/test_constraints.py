"""Tests for the constraint graph and flag rules."""

import time
import pytest

from mpesa_routing.core.constraints import (
    ConstraintGraph,
    RapidSequenceRule,
    NewAccountRule,
    RoundNumberRule,
    ChunkCountRule,
    FlagSeverity,
)
from mpesa_routing.core.account import KYCLevel, MpesaAccount


class TestRapidSequenceRule:
    def test_no_risk_when_below_threshold(self, tier3_account):
        rule = RapidSequenceRule()
        risk = rule.evaluate(tier3_account, 10_000, "d")
        assert risk == 0.0

    def test_risk_when_above_threshold(self, tier3_account):
        tier3_account.transaction_count_last_5min = 5
        rule = RapidSequenceRule()
        risk = rule.evaluate(tier3_account, 10_000, "d")
        assert risk == FlagSeverity.MEDIUM.value


class TestNewAccountRule:
    def test_risk_for_new_account_high_value(self):
        import time
        acc = MpesaAccount("new", KYCLevel.TIER_3, "New", "Nairobi", created_at=time.time())
        rule = NewAccountRule()
        risk = rule.evaluate(acc, 300_000, "d")
        assert risk == FlagSeverity.HIGH.value

    def test_no_risk_for_new_account_low_value(self):
        acc = MpesaAccount("new", KYCLevel.TIER_3, "New", "Nairobi")
        rule = NewAccountRule()
        risk = rule.evaluate(acc, 50_000, "d")
        assert risk == 0.0

    def test_no_risk_for_established_account(self, tier3_account):
        rule = NewAccountRule()
        risk = rule.evaluate(tier3_account, 300_000, "d")
        assert risk == 0.0


class TestRoundNumberRule:
    def test_risk_for_round_number(self, tier3_account):
        rule = RoundNumberRule()
        risk = rule.evaluate(tier3_account, 500_000, "d")
        assert risk > 0.0

    def test_no_risk_for_non_round(self, tier3_account):
        rule = RoundNumberRule()
        risk = rule.evaluate(tier3_account, 123_456, "d")
        assert risk == 0.0


class TestChunkCountRule:
    def test_risk_for_many_chunks(self, tier3_account):
        rule = ChunkCountRule()
        risk = rule.evaluate(tier3_account, 2_500_000, "d")
        assert risk > 0.0

    def test_no_risk_for_few_chunks(self, tier3_account):
        rule = ChunkCountRule()
        risk = rule.evaluate(tier3_account, 100_000, "d")
        assert risk == 0.0


class TestConstraintGraph:
    def test_empty_graph(self, empty_graph):
        assert len(empty_graph.accounts) == 0
        assert empty_graph.accounts.total_send_capacity() == 0

    def test_add_account(self, empty_graph, tier3_account):
        empty_graph.add_account(tier3_account)
        assert len(empty_graph.accounts) == 1

    def test_has_sufficient_capacity_true(self, populated_graph):
        assert populated_graph.has_sufficient_capacity(500_000) is True

    def test_has_sufficient_capacity_false(self, populated_graph):
        assert populated_graph.has_sufficient_capacity(99_999_999_999) is False

    def test_has_sufficient_capacity_with_region(self, populated_graph):
        assert populated_graph.has_sufficient_capacity(500_000, "Nairobi") is True

    def test_evaluate_flag_risk(self, populated_graph, tier3_account):
        risk = populated_graph.evaluate_flag_risk(tier3_account, 10_000, "d")
        assert 0.0 <= risk <= 1.0

    def test_evaluate_chunked_risk(self, populated_graph, tier3_account):
        risk = populated_graph.evaluate_chunked_risk(tier3_account, [250_000, 250_000], "d")
        assert risk > 0.0
        assert risk <= 1.0

    def test_repr(self, populated_graph):
        r = repr(populated_graph)
        assert "accounts" in r
        assert "capacity" in r

    def test_capacity_after_partial_usage(self, populated_graph):
        acc = populated_graph.accounts.senders_ordered_by_capacity()[0]
        orig_cap = acc.remaining_send_capacity
        acc.record_send(200_000, "d")
        assert acc.remaining_send_capacity == orig_cap - 200_000
