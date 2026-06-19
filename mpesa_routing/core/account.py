"""Core domain models — accounts and their state."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class KYCLevel(Enum):
    """M-Pesa KYC tier levels with their associated limits."""

    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3

    @property
    def daily_send_limit(self) -> float:
        return {1: 70_000, 2: 140_000, 3: 500_000}[self.value]

    @property
    def daily_receive_limit(self) -> float:
        return {1: 140_000, 2: 280_000, 3: 500_000}[self.value]

    @property
    def max_per_transaction(self) -> float:
        return {1: 70_000, 2: 140_000, 3: 250_000}[self.value]

    @property
    def display_name(self) -> str:
        return f"Tier {self.value}"


class AccountStatus(Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    SUSPENDED = "suspended"
    COOLDOWN = "cooldown"


@dataclass
class MpesaAccount:
    """A single M-Pesa account with its configuration and runtime state."""

    account_id: str
    kyc_level: KYCLevel
    label: str
    region: str
    is_business: bool = False
    status: AccountStatus = AccountStatus.ACTIVE
    created_at: float = field(default_factory=lambda: time.time() - 90 * 86400)

    daily_sent: float = 0.0
    daily_received: float = 0.0
    last_transaction_at: Optional[float] = None
    transaction_count_last_5min: int = 0
    destinations_used: set = field(default_factory=set)

    def __post_init__(self):
        if isinstance(self.kyc_level, int):
            self.kyc_level = KYCLevel(self.kyc_level)

    @property
    def remaining_send_capacity(self) -> float:
        limit = 9_999_999_999 if self.is_business else self.kyc_level.daily_send_limit
        return max(0.0, limit - self.daily_sent)

    @property
    def remaining_receive_capacity(self) -> float:
        limit = 9_999_999_999 if self.is_business else self.kyc_level.daily_receive_limit
        return max(0.0, limit - self.daily_received)

    @property
    def max_chunk_size(self) -> float:
        return 9_999_999_999 if self.is_business else self.kyc_level.max_per_transaction

    @property
    def is_newly_created(self) -> bool:
        return (time.time() - self.created_at) < 7 * 86400

    @property
    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE

    def record_send(self, amount: float, destination: str) -> None:
        self.daily_sent += amount
        self._record_timing()
        self.destinations_used.add(destination)

    def record_receive(self, amount: float, source: str) -> None:
        self.daily_received += amount
        self._record_timing()
        self.destinations_used.add(source)

    def _record_timing(self) -> None:
        now = time.time()
        if self.last_transaction_at and (now - self.last_transaction_at) < 300:
            self.transaction_count_last_5min += 1
        else:
            self.transaction_count_last_5min = 1
        self.last_transaction_at = now

    def reset_daily_limits(self) -> None:
        self.daily_sent = 0.0
        self.daily_received = 0.0
        self.transaction_count_last_5min = 0

    def __repr__(self) -> str:
        return (
            f"MpesaAccount({self.account_id}, {self.kyc_level.display_name}, "
            f"{self.label}, {self.region})"
        )


class AccountPool:
    """Manages a collection of MpesaAccounts with query methods."""

    def __init__(self):
        self._accounts: Dict[str, MpesaAccount] = {}

    def add(self, account: MpesaAccount) -> None:
        self._accounts[account.account_id] = account

    def get(self, account_id: str) -> MpesaAccount:
        return self._accounts[account_id]

    @property
    def all(self) -> List[MpesaAccount]:
        return list(self._accounts.values())

    def by_region(self, region: str) -> List[MpesaAccount]:
        return [a for a in self._accounts.values() if a.region == region]

    def active(self) -> List[MpesaAccount]:
        return [a for a in self._accounts.values() if a.is_active]

    def senders_ordered_by_capacity(self, region: Optional[str] = None) -> List[MpesaAccount]:
        candidates = self.active()
        if region:
            candidates = [a for a in candidates if a.region == region]
        return sorted(candidates, key=lambda a: a.remaining_send_capacity, reverse=True)

    def total_send_capacity(self, region: Optional[str] = None) -> float:
        return sum(a.remaining_send_capacity for a in self.senders_ordered_by_capacity(region))

    def __iter__(self):
        return iter(self._accounts.values())

    def __len__(self):
        return len(self._accounts)

    def to_dict(self) -> dict:
        return {
            aid: {
                "id": aid,
                "kyc": acc.kyc_level.value,
                "label": acc.label,
                "region": acc.region,
                "is_business": acc.is_business,
                "daily_sent": acc.daily_sent,
                "remaining_send": acc.remaining_send_capacity,
                "status": acc.status.value,
            }
            for aid, acc in self._accounts.items()
        }
