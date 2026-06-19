"""Tests for the path finder and routing path data structures."""

import pytest

from mpesa_routing.routing.path_finder import PathFinder, RoutingPath, PathChunk
from mpesa_routing.core.transaction import Transaction, DestinationType, Urgency


class TestPathChunk:
    def test_create(self):
        c = PathChunk("acc_001", 250_000)
        assert c.account_id == "acc_001"
        assert c.amount == 250_000


class TestRoutingPath:
    def test_empty_path(self):
        p = RoutingPath(chunks=[])
        assert p.total_amount == 0
        assert p.num_chunks == 0
        assert p.num_accounts == 0

    def test_single_chunk(self):
        p = RoutingPath(chunks=[PathChunk("a1", 250_000)])
        assert p.total_amount == 250_000
        assert p.num_chunks == 1
        assert p.num_accounts == 1
        assert p.unique_accounts == ["a1"]

    def test_multi_chunk_same_account(self):
        p = RoutingPath(chunks=[
            PathChunk("a1", 250_000),
            PathChunk("a1", 250_000),
        ])
        assert p.total_amount == 500_000
        assert p.num_chunks == 2
        assert p.num_accounts == 1

    def test_multi_account_path(self):
        p = RoutingPath(chunks=[
            PathChunk("a1", 250_000),
            PathChunk("a2", 250_000),
        ])
        assert p.num_accounts == 2

    def test_repr(self):
        p = RoutingPath(chunks=[PathChunk("a1", 100_000)])
        r = repr(p)
        assert "100,000" in r


class TestPathFinder:
    def test_find_paths_single_account(self, populated_graph, sample_transaction):
        finder = PathFinder(populated_graph)
        paths = finder.find_paths(sample_transaction)
        assert len(paths) >= 1

    def test_best_path_returns_highest_scored(self, populated_graph, sample_transaction):
        finder = PathFinder(populated_graph)
        path = finder.best_path(sample_transaction)
        assert path is not None
        assert path.total_amount > 0

    def test_best_path_large_transaction(self, populated_graph):
        txn = Transaction(2_000_000, DestinationType.PHONE, "big_recip", Urgency.IMMEDIATE)
        finder = PathFinder(populated_graph)
        path = finder.best_path(txn)
        assert path is not None
        assert path.total_amount > 0

    def test_best_path_small_transaction(self, populated_graph):
        txn = Transaction(10_000, DestinationType.PHONE, "small_recip")
        finder = PathFinder(populated_graph)
        path = finder.best_path(txn)
        assert path is not None
        assert path.total_amount == 10_000

    def test_find_paths_empty_graph(self, empty_graph, sample_transaction):
        finder = PathFinder(empty_graph)
        paths = finder.find_paths(sample_transaction)
        assert len(paths) == 0

    def test_execute_path_updates_accounts(self, populated_graph, sample_transaction):
        finder = PathFinder(populated_graph)
        path = finder.best_path(sample_transaction)
        assert path is not None
        orig_capacity = finder.graph.accounts.total_send_capacity()
        finder.execute_path(path, sample_transaction)
        assert finder.graph.accounts.total_send_capacity() < orig_capacity

    def test_split_path_uses_multiple_accounts(self, populated_graph):
        txn = Transaction(2_000_000, DestinationType.PHONE, "big", Urgency.IMMEDIATE)
        finder = PathFinder(populated_graph)
        path = finder.best_path(txn)
        assert path is not None
        assert path.num_accounts >= 1

    def test_path_has_fee(self, populated_graph, sample_transaction):
        finder = PathFinder(populated_graph)
        path = finder.best_path(sample_transaction)
        assert path.total_fee > 0

    def test_path_has_flag_risk(self, populated_graph, sample_transaction):
        finder = PathFinder(populated_graph)
        path = finder.best_path(sample_transaction)
        assert 0.0 <= path.flag_risk_score <= 1.0

    def test_path_has_estimated_time(self, populated_graph, sample_transaction):
        finder = PathFinder(populated_graph)
        path = finder.best_path(sample_transaction)
        assert path.estimated_minutes > 0
