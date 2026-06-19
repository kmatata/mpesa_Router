"""Tests for scoring strategies."""

import pytest
from pytest import approx

from mpesa_routing.routing.scoring import (
    CoverageScorer, SafetyScorer, SpeedScorer, OpacityScorer, CompositeScorer,
)
from mpesa_routing.routing.path_finder import RoutingPath, PathChunk
from mpesa_routing.core.transaction import Transaction, DestinationType, Urgency


def make_path(total_amount=500_000, flag_risk=0.3, minutes=10.0, opacity=0.5):
    chunks = []
    remaining = total_amount
    while remaining > 0:
        c = min(remaining, 250_000)
        chunks.append(PathChunk("a1", c))
        remaining -= c
    return RoutingPath(
        chunks=chunks,
        total_fee=total_amount * 0.015,
        flag_risk_score=flag_risk,
        estimated_minutes=minutes,
        opacity_score=opacity,
    )


class TestCoverageScorer:
    def test_full_coverage(self):
        path = make_path(total_amount=500_000)
        txn = Transaction(500_000, "phone", "r")
        score = CoverageScorer().score(path, txn)
        assert score == 1.0

    def test_half_coverage(self):
        path = make_path(total_amount=250_000)
        txn = Transaction(500_000, "phone", "r")
        score = CoverageScorer().score(path, txn)
        assert score == 0.5

    def test_zero_amount_txn(self):
        path = make_path(total_amount=100_000)
        txn = Transaction(0, "phone", "r")
        score = CoverageScorer().score(path, txn)
        assert score == 0.0

    def test_over_coverage_capped(self):
        path = make_path(total_amount=300_000)
        txn = Transaction(200_000, "phone", "r")
        score = CoverageScorer().score(path, txn)
        assert score == 1.0


class TestSafetyScorer:
    def test_no_risk(self):
        path = make_path(flag_risk=0.0)
        assert SafetyScorer().score(path, None) == 1.0

    def test_high_risk(self):
        path = make_path(flag_risk=0.8)
        assert SafetyScorer().score(path, None) == pytest.approx(0.2)

    def test_max_risk(self):
        path = make_path(flag_risk=1.0)
        assert SafetyScorer().score(path, None) == 0.0


class TestSpeedScorer:
    def test_immediate_urgency_fast(self):
        path = make_path(minutes=5)
        txn = Transaction(100_000, "phone", "r", Urgency.IMMEDIATE)
        score = SpeedScorer().score(path, txn)
        assert 0 < score <= 1.0

    def test_immediate_urgency_slow(self):
        path = make_path(minutes=60)
        txn = Transaction(100_000, "phone", "r", Urgency.IMMEDIATE)
        score = SpeedScorer().score(path, txn)
        assert score < 0.1

    def test_normal_urgency(self):
        path = make_path(minutes=60)
        txn = Transaction(100_000, "phone", "r", Urgency.NORMAL)
        score = SpeedScorer().score(path, txn)
        assert 0.5 <= score <= 1.0

    def test_low_urgency_slow(self):
        path = make_path(minutes=300)
        txn = Transaction(100_000, "phone", "r", Urgency.LOW)
        score = SpeedScorer().score(path, txn)
        assert 0 < score <= 1.0


class TestOpacityScorer:
    def test_returns_opacity_score(self):
        path = make_path(opacity=0.8)
        assert OpacityScorer().score(path, None) == 0.8


class TestCompositeScorer:
    def test_returns_composite_score(self):
        path = make_path(total_amount=500_000)
        txn = Transaction(500_000, "phone", "r", Urgency.NORMAL)
        scorer = CompositeScorer()
        score = scorer.score(path, txn)
        assert 0 < score <= 1.0

    def test_rank_paths_best_first(self):
        txn = Transaction(500_000, "phone", "r")
        path_good = make_path(total_amount=500_000, flag_risk=0.1)
        path_bad = make_path(total_amount=100_000, flag_risk=0.8)
        ranked = CompositeScorer().rank_paths([path_bad, path_good], txn)
        assert ranked[0] == path_good

    def test_rank_paths_empty(self):
        ranked = CompositeScorer().rank_paths([], Transaction(100, "phone", "r"))
        assert ranked == []
