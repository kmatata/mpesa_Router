"""Routing path data structures and path finding logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..core.account import MpesaAccount
from ..core.transaction import Transaction, chunk_amount
from ..core.constraints import ConstraintGraph


@dataclass
class PathChunk:
    """A single executable transaction chunk within a routing path."""

    account_id: str
    amount: float


@dataclass
class RoutingPath:
    """A complete route through the constraint graph."""

    chunks: List[PathChunk]
    total_fee: float = 0.0
    flag_risk_score: float = 0.0
    estimated_minutes: float = 0.0
    remaining_capacity_after: float = 0.0
    opacity_score: float = 0.0

    @property
    def total_amount(self) -> float:
        return sum(c.amount for c in self.chunks)

    @property
    def unique_accounts(self) -> List[str]:
        seen: List[str] = []
        for c in self.chunks:
            if c.account_id not in seen:
                seen.append(c.account_id)
        return seen

    @property
    def num_chunks(self) -> int:
        return len(self.chunks)

    @property
    def num_accounts(self) -> int:
        return len(self.unique_accounts)

    def __repr__(self) -> str:
        return (
            f"RoutingPath({self.total_amount:,.0f} KES across "
            f"{self.num_accounts} account(s), {self.num_chunks} chunk(s))"
        )


class UnroutableError(Exception):
    """Raised when no valid path exists for a transaction."""


class PathFinder:
    """Explores the constraint graph to find optimal routing paths."""

    FEE_RATE = 0.015

    def __init__(self, graph: ConstraintGraph):
        self.graph = graph

    def find_paths(self, transaction: Transaction) -> List[RoutingPath]:
        paths: List[RoutingPath] = []

        single = self._try_single_path(transaction)
        if single:
            paths.append(single)

        splits = self._try_split_paths(transaction)
        paths.extend(splits)

        return paths

    def best_path(self, transaction: Transaction) -> Optional[RoutingPath]:
        paths = self.find_paths(transaction)
        return paths[0] if paths else None

    def _try_single_path(self, transaction: Transaction) -> Optional[RoutingPath]:
        accounts = self.graph.accounts.senders_ordered_by_capacity(transaction.sender_region)
        if not accounts:
            return None

        best = accounts[0]
        if best.remaining_send_capacity <= 0:
            return None

        amount = min(transaction.amount, best.remaining_send_capacity)
        chunks = chunk_amount(amount, best.max_chunk_size)

        chunks_out = [PathChunk(best.account_id, amt) for amt in chunks]
        fee = amount * self.FEE_RATE
        flag_risk = self.graph.evaluate_chunked_risk(best, chunks, transaction.destination_id)

        return RoutingPath(
            chunks=chunks_out,
            total_fee=round(fee, 2),
            flag_risk_score=flag_risk,
            estimated_minutes=2.0 + 0.3 * len(chunks),
            remaining_capacity_after=best.remaining_send_capacity - amount,
            opacity_score=0.2,
        )

    def _try_split_paths(self, transaction: Transaction) -> List[RoutingPath]:
        accounts = self.graph.accounts.senders_ordered_by_capacity(transaction.sender_region)
        if len(accounts) < 2:
            return []

        paths: List[RoutingPath] = []
        counts = [2, 3, 5, len(accounts)]
        seen_signatures = set()

        for n in counts:
            if n > len(accounts):
                continue
            path = self._build_split_path(accounts[:n], transaction)
            if path is None:
                continue
            sig = tuple(sorted(c.account_id for c in path.chunks))
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            paths.append(path)

        return paths

    def _build_split_path(self, senders: List[MpesaAccount], transaction: Transaction) -> Optional[RoutingPath]:
        remaining = transaction.amount
        chunks: List[PathChunk] = []

        for sender in senders:
            if remaining <= 0:
                break
            can_take = min(remaining, sender.remaining_send_capacity)
            if can_take < 100:
                continue

            account_chunks = chunk_amount(can_take, sender.max_chunk_size)
            for c in account_chunks:
                chunks.append(PathChunk(sender.account_id, c))
            remaining -= can_take

        total_moved = transaction.amount - remaining
        if total_moved <= 0:
            return None

        fee = total_moved * self.FEE_RATE
        n_accounts = len(set(c.account_id for c in chunks))
        n_chunks = len(chunks)

        total_risk = 0.0
        for chunk in chunks:
            acc = self.graph.accounts.get(chunk.account_id)
            total_risk += self.graph.evaluate_flag_risk(acc, chunk.amount, transaction.destination_id)
        flag_risk = min(total_risk / max(n_accounts, 1) + 0.03 * n_chunks, 1.0)

        used_ids = set(c.account_id for c in chunks)
        total_capacity = sum(
            self.graph.accounts.get(aid).remaining_send_capacity for aid in used_ids
        )

        return RoutingPath(
            chunks=chunks,
            total_fee=round(fee, 2),
            flag_risk_score=round(flag_risk, 3),
            estimated_minutes=2.0 + 0.2 * n_chunks,
            remaining_capacity_after=total_capacity - total_moved,
            opacity_score=min(0.3 + 0.15 * n_accounts, 0.95),
        )

    def execute_path(self, path: RoutingPath, transaction: Transaction) -> None:
        for chunk in path.chunks:
            account = self.graph.accounts.get(chunk.account_id)
            account.record_send(chunk.amount, transaction.destination_id)
