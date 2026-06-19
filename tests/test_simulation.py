"""Tests for the simulation engine and scenarios."""

import pytest

from mpesa_routing.simulation.engine import SimulationEngine, SimulationResult, Scenario
from mpesa_routing.simulation.scenarios import standard_scenarios
from mpesa_routing.core.transaction import DestinationType, Urgency


class TestSimulationResult:
    def test_defaults(self):
        r = SimulationResult()
        assert r.volume_moved == 0.0
        assert r.transactions_blocked == 0

    def test_with_values(self):
        r = SimulationResult(volume_moved=500_000, total_fees=7_500, total_time_minutes=5.0)
        assert r.volume_moved == 500_000
        assert r.total_fees == 7_500


class TestScenario:
    def test_defaults(self):
        s = Scenario("Test", "test", 100_000)
        assert s.urgency == Urgency.NORMAL
        assert s.destination_type == DestinationType.PHONE
        assert s.region == "Nairobi"

    def test_custom(self):
        s = Scenario("Test", "test", 2_000_000, 5, Urgency.IMMEDIATE, "Mombasa", DestinationType.TILL)
        assert s.num_transactions == 5
        assert s.region == "Mombasa"


class TestSimulationEngine:
    def test_build_default_graph(self):
        engine = SimulationEngine()
        graph = engine.build_default_graph()
        assert len(graph.accounts) == 9
        assert graph.accounts.total_send_capacity() == 2_560_000

    def test_crypto_otc_comparison(self):
        engine = SimulationEngine()
        scenario = Scenario("OTC", "Test", 2_000_000, 1)
        results = engine.compare(scenario)
        naive = results["naive"]
        optimized = results["optimized"]
        assert naive.volume_moved > 0
        assert optimized.volume_moved > naive.volume_moved

    def test_small_transaction_no_difference(self):
        engine = SimulationEngine()
        scenario = Scenario("Small", "Test", 10_000, 1)
        results = engine.compare(scenario)
        assert results["naive"].volume_moved == 10_000
        assert results["optimized"].volume_moved == 10_000

    def test_large_transaction_shows_multiple_accounts(self):
        engine = SimulationEngine()
        scenario = Scenario("Large", "Test", 2_000_000, 1)
        results = engine.compare(scenario)
        assert results["optimized"].accounts_used > 1

    def test_naive_blocks_when_capacity_exceeded(self):
        engine = SimulationEngine()
        scenario = Scenario("Exceed", "Test", 5_000_000, 1)
        results = engine.compare(scenario)
        assert results["naive"].volume_moved < 5_000_000

    def test_naive_and_optimized_both_runnable(self):
        engine = SimulationEngine()
        for scenario in standard_scenarios():
            results = engine.compare(scenario)
            assert "naive" in results
            assert "optimized" in results

    def test_volume_multiplier_for_large_txns(self):
        engine = SimulationEngine()
        scenario = Scenario("Mult", "Test", 2_000_000, 1)
        results = engine.compare(scenario)
        n = results["naive"].volume_moved
        o = results["optimized"].volume_moved
        assert o >= n

    def test_remittance_batch_processes_all(self):
        engine = SimulationEngine()
        scenario = Scenario("Batch", "Test", 500_000, 10)
        results = engine.compare(scenario)
        assert results["naive"].volume_moved > 0

    def test_many_small_txns_same_region(self):
        engine = SimulationEngine()
        scenario = Scenario("Many", "Test", 50_000, 20, urgency=Urgency.NORMAL)
        results = engine.compare(scenario)
        assert results["naive"].volume_moved > 0
        assert results["optimized"].volume_moved > 0
