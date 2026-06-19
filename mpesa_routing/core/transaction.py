"""Transaction model — what the router moves and how."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class DestinationType(Enum):
    TILL = "till"
    PHONE = "phone"
    AGENT = "agent"
    PAYBILL = "paybill"


class Urgency(Enum):
    IMMEDIATE = "immediate"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class Transaction:
    """A transaction request to route through the M-Pesa constraint graph."""

    amount: float
    destination_type: DestinationType
    destination_id: str
    urgency: Urgency = Urgency.NORMAL
    sender_region: str = "Nairobi"

    def __post_init__(self):
        if isinstance(self.destination_type, str):
            self.destination_type = DestinationType(self.destination_type)
        if isinstance(self.urgency, str):
            self.urgency = Urgency(self.urgency)

    def __repr__(self) -> str:
        return (
            f"Transaction({self.amount:,.0f} KES → {self.destination_type.value}, "
            f"urgency={self.urgency.value})"
        )


def chunk_amount(amount: float, max_chunk: float, min_chunk: float = 50.0) -> List[float]:
    """Split `amount` into individual transaction chunks each ≤ `max_chunk`."""
    if amount <= 0:
        return []
    if amount <= max_chunk:
        return [amount]

    chunks: List[float] = []
    remaining = amount
    while remaining > max_chunk:
        chunks.append(max_chunk)
        remaining -= max_chunk

    if remaining >= min_chunk:
        chunks.append(round(remaining, 2))
    elif chunks:
        chunks[-1] = round(chunks[-1] + remaining, 2)
    else:
        chunks.append(round(remaining, 2))

    return chunks
