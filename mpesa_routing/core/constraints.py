"""Constraint graph — the complete model of what limits value movement."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from .account import AccountPool, MpesaAccount


class FlagSeverity(Enum):
    LOW = 0.1
    MEDIUM = 0.3
    HIGH = 0.5
    CRITICAL = 0.8


@dataclass
class FlagRule:
    """Abstract base for a rule that detects flaggable transaction patterns."""

    name: str
    severity: FlagSeverity
    description: str

    def evaluate(self, account: MpesaAccount, amount: float, destination: str) -> float:
        raise NotImplementedError


@dataclass
class RapidSequenceRule(FlagRule):
    """Detects rapid consecutive sends within a time window."""

    threshold: int = 5
    window_minutes: int = 5

    def __init__(self):
        super().__init__(
            name="rapid_sequential_sends",
            severity=FlagSeverity.MEDIUM,
            description="Multiple sends in quick succession",
        )

    def evaluate(self, account: MpesaAccount, amount: float, destination: str) -> float:
        if account.transaction_count_last_5min >= self.threshold:
            return self.severity.value
        return 0.0


@dataclass
class NewAccountRule(FlagRule):
    """Detects high-value transactions from recently created accounts."""

    high_value_threshold: float = 200_000

    def __init__(self):
        super().__init__(
            name="new_account_high_value",
            severity=FlagSeverity.HIGH,
            description="High-value transaction from recently created account",
        )

    def evaluate(self, account: MpesaAccount, amount: float, destination: str) -> float:
        if account.is_newly_created and amount > self.high_value_threshold:
            return self.severity.value
        return 0.0


@dataclass
class RoundNumberRule(FlagRule):
    """Detects round-number transactions (structuring indicator)."""

    tolerance: float = 0.01

    def __init__(self):
        super().__init__(
            name="round_number_transaction",
            severity=FlagSeverity.LOW,
            description="Round-number transaction amount",
        )

    def evaluate(self, account: MpesaAccount, amount: float, destination: str) -> float:
        if amount > 100_000 and amount % 100_000 < self.tolerance * amount:
            return self.severity.value
        return 0.0


@dataclass
class ChunkCountRule(FlagRule):
    """Detects transactions split into many small chunks."""

    max_chunks: int = 8

    def __init__(self):
        super().__init__(
            name="excessive_chunking",
            severity=FlagSeverity.MEDIUM,
            description="Transaction split into many small chunks",
        )

    def evaluate(self, account: MpesaAccount, amount: float, destination: str) -> float:
        estimated_chunks = amount // account.max_chunk_size
        if estimated_chunks >= self.max_chunks:
            return self.severity.value
        return 0.0


class ConstraintGraph:
    """Complete constraint model of the M-Pesa environment.

    Combines account pool state with flag rules to evaluate
    the risk and capacity of any proposed routing path.
    """

    def __init__(self, flag_rules: Optional[List[FlagRule]] = None):
        self.accounts = AccountPool()
        self._flag_rules = flag_rules or [
            RapidSequenceRule(),
            NewAccountRule(),
            RoundNumberRule(),
            ChunkCountRule(),
        ]

    def evaluate_flag_risk(self, account: MpesaAccount, amount: float, destination: str) -> float:
        total = 0.0
        for rule in self._flag_rules:
            total += rule.evaluate(account, amount, destination)
        return min(total, 1.0)

    def evaluate_chunked_risk(self, account: MpesaAccount, chunks: List[float], destination: str) -> float:
        if not chunks:
            return 0.0
        base_risk = self.evaluate_flag_risk(account, sum(chunks), destination)
        chunk_penalty = 0.02 * len(chunks)
        return min(base_risk + chunk_penalty, 1.0)

    def add_account(self, account: MpesaAccount) -> None:
        self.accounts.add(account)

    def has_sufficient_capacity(self, amount: float, region: Optional[str] = None) -> bool:
        return self.accounts.total_send_capacity(region) >= amount

    def __repr__(self) -> str:
        return (
            f"ConstraintGraph({len(self.accounts)} accounts, "
            f"{self.accounts.total_send_capacity():,.0f} KES capacity)"
        )
