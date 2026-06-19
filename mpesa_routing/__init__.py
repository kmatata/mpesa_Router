"""M-Pesa Constraint-Satisfaction Routing Framework.

A modular framework for modeling M-Pesa transaction constraints
and finding optimal multi-account routing paths.

Quick demo:
    python -m mpesa_routing
"""

__version__ = "0.1.0"

from .core.account import KYCLevel, AccountStatus, MpesaAccount, AccountPool
from .core.transaction import Transaction, DestinationType, Urgency, chunk_amount
from .core.constraints import ConstraintGraph, FlagRule, RapidSequenceRule, NewAccountRule
from .routing.path_finder import PathFinder, RoutingPath, PathChunk, UnroutableError
from .routing.scoring import CompositeScorer

from .simulation.engine import SimulationEngine, Scenario

__all__ = [
    "KYCLevel", "AccountStatus", "MpesaAccount", "AccountPool",
    "Transaction", "DestinationType", "Urgency", "chunk_amount",
    "ConstraintGraph", "FlagRule", "RapidSequenceRule", "NewAccountRule",
    "PathFinder", "RoutingPath", "PathChunk", "UnroutableError",
    "CompositeScorer",
    "SimulationEngine", "Scenario",
]
