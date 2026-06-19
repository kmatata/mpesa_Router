"""Path scoring and ranking strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from .path_finder import RoutingPath
from ..core.transaction import Transaction, Urgency


class ScoringStrategy(ABC):
    """Interface for scoring a routing path on a single dimension."""

    @abstractmethod
    def score(self, path: RoutingPath, transaction: Transaction) -> float:
        ...


class CoverageScorer(ScoringStrategy):
    """How much of the requested amount was routed."""

    def score(self, path: RoutingPath, transaction: Transaction) -> float:
        if transaction.amount <= 0:
            return 0.0
        return min(path.total_amount / transaction.amount, 1.0)


class SafetyScorer(ScoringStrategy):
    """How low the flag risk is (inverse of flag_risk_score)."""

    def score(self, path: RoutingPath, transaction: Transaction) -> float:
        return 1.0 - path.flag_risk_score


class SpeedScorer(ScoringStrategy):
    """How fast the path executes relative to urgency tolerance."""

    def score(self, path: RoutingPath, transaction: Transaction) -> float:
        tolerance = {
            Urgency.IMMEDIATE: 30.0,
            Urgency.NORMAL: 120.0,
            Urgency.LOW: 360.0,
        }.get(transaction.urgency, 120.0)
        return max(0.0, 1.0 - path.estimated_minutes / tolerance)


class OpacityScorer(ScoringStrategy):
    """How opaque the path is (harder to trace)."""

    def score(self, path: RoutingPath, transaction: Transaction) -> float:
        return path.opacity_score


class CompositeScorer:
    """Weighted combination of multiple scoring strategies.

    Default weights prioritize coverage (getting the money moved) over
    speed and safety.
    """

    def __init__(self):
        self.strategies: List[tuple[ScoringStrategy, float]] = [
            (CoverageScorer(), 0.45),
            (SpeedScorer(), 0.15),
            (SafetyScorer(), 0.20),
            (OpacityScorer(), 0.20),
        ]

    def score(self, path: RoutingPath, transaction: Transaction) -> float:
        composite = 0.0
        for strategy, weight in self.strategies:
            composite += weight * strategy.score(path, transaction)
        return round(composite, 4)

    def rank_paths(self, paths: List[RoutingPath], transaction: Transaction) -> List[RoutingPath]:
        scored = [(self.score(p, transaction), p) for p in paths]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]
