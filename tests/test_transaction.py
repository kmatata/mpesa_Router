"""Tests for the transaction model."""

import pytest

from mpesa_routing.core.transaction import Transaction, DestinationType, Urgency, chunk_amount


class TestTransaction:
    def test_create_phone_default(self):
        txn = Transaction(100_000, DestinationType.PHONE, "recip_1")
        assert txn.amount == 100_000
        assert txn.destination_type == DestinationType.PHONE
        assert txn.urgency == Urgency.NORMAL
        assert txn.sender_region == "Nairobi"

    def test_create_with_strings(self):
        txn = Transaction(500_000, "till", "123456", "immediate", "Mombasa")
        assert txn.destination_type == DestinationType.TILL
        assert txn.urgency == Urgency.IMMEDIATE
        assert txn.sender_region == "Mombasa"

    def test_repr(self):
        txn = Transaction(250_000, "phone", "r")
        r = repr(txn)
        assert "250,000" in r
        assert "normal" in r

    def test_all_destination_types(self):
        for dt in DestinationType:
            txn = Transaction(100, dt, "d")
            assert txn.destination_type == dt


class TestChunkAmount:
    def test_zero_amount(self):
        assert chunk_amount(0, 250_000) == []

    def test_negative_amount(self):
        assert chunk_amount(-100, 250_000) == []

    def test_amount_under_max_chunk(self):
        assert chunk_amount(100_000, 250_000) == [100_000.0]

    def test_amount_equals_max_chunk(self):
        assert chunk_amount(250_000, 250_000) == [250_000.0]

    def test_two_chunks(self):
        result = chunk_amount(300_000, 250_000)
        assert result == [250_000.0, 50_000.0]
        assert sum(result) == 300_000

    def test_three_chunks(self):
        result = chunk_amount(600_000, 250_000)
        assert len(result) == 3
        assert sum(result) == 600_000

    def test_exact_multiple(self):
        result = chunk_amount(500_000, 250_000)
        assert result == [250_000.0, 250_000.0]
        assert sum(result) == 500_000

    def test_large_amount(self):
        result = chunk_amount(2_000_000, 250_000)
        assert len(result) == 8
        assert sum(result) == 2_000_000

    def test_very_small_min_chunk(self):
        result = chunk_amount(100, 250_000, min_chunk=10)
        assert result == [100.0]

    def test_custom_min_chunk(self):
        result = chunk_amount(500_050, 250_000, min_chunk=100)
        assert sum(result) == 500_050
