"""Simulation engine — runs routing comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..core.account import KYCLevel, MpesaAccount
from ..core.transaction import Transaction, DestinationType, Urgency, chunk_amount
from ..core.constraints import ConstraintGraph
from ..routing.path_finder import PathFinder
from ..routing.scoring import CompositeScorer


@dataclass
class Scenario:
    """A test scenario for the routing engine comparison."""

    name: str
    description: str
    transaction_amount: float
    num_transactions: int = 1
    urgency: Urgency = Urgency.NORMAL
    region: str = "Nairobi"
    destination_type: DestinationType = DestinationType.PHONE


@dataclass
class SimulationResult:
    """Results of running a scenario against a routing strategy."""

    volume_moved: float = 0.0
    total_fees: float = 0.0
    total_time_minutes: float = 0.0
    flag_events: int = 0
    transactions_blocked: int = 0
    accounts_used: int = 0


class SimulationEngine:
    """Runs scenarios comparing naive vs. optimized routing."""

    def build_default_graph(self) -> ConstraintGraph:
        graph = ConstraintGraph()
        accounts = [
            MpesaAccount("acc_001", KYCLevel.TIER_3, "Primary", "Nairobi"),
            MpesaAccount("acc_002", KYCLevel.TIER_3, "Secondary", "Nairobi"),
            MpesaAccount("acc_003", KYCLevel.TIER_2, "Backup-1", "Nairobi"),
            MpesaAccount("acc_004", KYCLevel.TIER_3, "Regional", "Mombasa"),
            MpesaAccount("acc_005", KYCLevel.TIER_2, "Backup-2", "Mombasa"),
            MpesaAccount("acc_006", KYCLevel.TIER_1, "Limited-1", "Nairobi"),
            MpesaAccount("acc_007", KYCLevel.TIER_3, "Spouse", "Nairobi"),
            MpesaAccount("acc_008", KYCLevel.TIER_2, "Sibling", "Nairobi"),
            MpesaAccount("acc_009", KYCLevel.TIER_1, "Limited-2", "Nairobi"),
        ]
        for a in accounts:
            graph.add_account(a)
        return graph

    def _run_naive(self, graph: ConstraintGraph, scenario: Scenario) -> SimulationResult:
        result = SimulationResult()
        for i in range(scenario.num_transactions):
            txn = Transaction(
                scenario.transaction_amount,
                scenario.destination_type,
                f"recipient_{i}",
                scenario.urgency,
                scenario.region,
            )
            best = graph.accounts.senders_ordered_by_capacity(scenario.region)
            if not best or best[0].remaining_send_capacity <= 0:
                result.transactions_blocked += 1
                continue

            sender = best[0]
            can_send = min(txn.amount, sender.remaining_send_capacity)
            chunks = chunk_amount(can_send, sender.max_chunk_size)

            for c in chunks:
                sender.record_send(c, txn.destination_id)

            result.volume_moved += can_send
            result.total_fees += can_send * 0.015
            result.total_time_minutes += 2.0 + 0.3 * len(chunks)
            result.accounts_used = max(result.accounts_used, 1)

            if len(chunks) > 3:
                result.flag_events += 1
            if can_send < txn.amount:
                result.transactions_blocked += 1

        return result

    def _run_optimized(self, graph: ConstraintGraph, scenario: Scenario) -> SimulationResult:
        result = SimulationResult()
        finder = PathFinder(graph)
        scorer = CompositeScorer()

        for i in range(scenario.num_transactions):
            txn = Transaction(
                scenario.transaction_amount,
                scenario.destination_type,
                f"recipient_{i}",
                scenario.urgency,
                scenario.region,
            )
            paths = finder.find_paths(txn)
            if not paths:
                result.transactions_blocked += 1
                continue

            ranked = scorer.rank_paths(paths, txn)
            best = ranked[0]
            finder.execute_path(best, txn)

            result.volume_moved += best.total_amount
            result.total_fees += best.total_fee
            result.total_time_minutes += best.estimated_minutes
            result.accounts_used = max(result.accounts_used, best.num_accounts)

            if best.flag_risk_score > 0.5:
                result.flag_events += 1
            if best.total_amount < txn.amount:
                result.transactions_blocked += 1

        return result

    def compare(self, scenario: Scenario) -> Dict[str, SimulationResult]:
        return {
            "naive": self._run_naive(self.build_default_graph(), scenario),
            "optimized": self._run_optimized(self.build_default_graph(), scenario),
        }
