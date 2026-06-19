"""Tests for the account domain model."""

import time
import pytest

from mpesa_routing.core.account import KYCLevel, MpesaAccount, AccountPool, AccountStatus


class TestKYCLevel:
    def test_tier_1_limits(self):
        assert KYCLevel.TIER_1.daily_send_limit == 70_000
        assert KYCLevel.TIER_1.daily_receive_limit == 140_000
        assert KYCLevel.TIER_1.max_per_transaction == 70_000

    def test_tier_2_limits(self):
        assert KYCLevel.TIER_2.daily_send_limit == 140_000
        assert KYCLevel.TIER_2.daily_receive_limit == 280_000
        assert KYCLevel.TIER_2.max_per_transaction == 140_000

    def test_tier_3_limits(self):
        assert KYCLevel.TIER_3.daily_send_limit == 500_000
        assert KYCLevel.TIER_3.daily_receive_limit == 500_000
        assert KYCLevel.TIER_3.max_per_transaction == 250_000

    def test_display_name(self):
        assert KYCLevel.TIER_3.display_name == "Tier 3"


class TestMpesaAccount:
    def test_create_tier3_account(self):
        acc = MpesaAccount("a1", KYCLevel.TIER_3, "Test", "Nairobi")
        assert acc.account_id == "a1"
        assert acc.kyc_level == KYCLevel.TIER_3
        assert acc.remaining_send_capacity == 500_000

    def test_create_with_int_kyc(self):
        acc = MpesaAccount("a2", 3, "Test", "Nairobi")
        assert acc.kyc_level == KYCLevel.TIER_3

    def test_remaining_send_capacity_daily_limit(self, tier3_account):
        assert tier3_account.remaining_send_capacity == 500_000
        tier3_account.daily_sent = 300_000
        assert tier3_account.remaining_send_capacity == 200_000

    def test_remaining_send_capacity_does_not_go_negative(self, tier3_account):
        tier3_account.daily_sent = 600_000
        assert tier3_account.remaining_send_capacity == 0.0

    def test_business_account_unlimited(self, business_account):
        assert business_account.remaining_send_capacity == 9_999_999_999

    def test_record_send_updates_state(self):
        acc = MpesaAccount("a1", KYCLevel.TIER_3, "Test", "Nairobi")
        acc.record_send(250_000, "dest_1")
        assert acc.daily_sent == 250_000
        assert acc.remaining_send_capacity == 250_000
        assert "dest_1" in acc.destinations_used

    def test_record_send_multiple_chunks(self):
        acc = MpesaAccount("a1", KYCLevel.TIER_3, "Test", "Nairobi")
        acc.record_send(250_000, "dest_1")
        acc.record_send(250_000, "dest_1")
        assert acc.daily_sent == 500_000
        assert acc.remaining_send_capacity == 0

    def test_max_chunk_size_tier3(self, tier3_account):
        assert tier3_account.max_chunk_size == 250_000

    def test_max_chunk_size_business(self, business_account):
        assert business_account.max_chunk_size == 9_999_999_999

    def test_newly_created_account(self):
        import time
        acc = MpesaAccount("new", KYCLevel.TIER_3, "New", "Nairobi", created_at=time.time())
        assert acc.is_newly_created

    def test_old_account_not_newly_created(self, tier3_account):
        assert not tier3_account.is_newly_created

    def test_active_by_default(self, tier3_account):
        assert tier3_account.is_active
        assert tier3_account.status == AccountStatus.ACTIVE

    def test_frozen_account_not_active(self, tier3_account):
        tier3_account.status = AccountStatus.FROZEN
        assert not tier3_account.is_active

    def test_record_send_tracks_timing(self):
        acc = MpesaAccount("a1", KYCLevel.TIER_3, "Test", "Nairobi")
        assert acc.last_transaction_at is None
        acc.record_send(10_000, "d1")
        assert acc.last_transaction_at is not None

    def test_reset_daily_limits(self):
        acc = MpesaAccount("a1", KYCLevel.TIER_3, "Test", "Nairobi")
        acc.daily_sent = 500_000
        acc.transaction_count_last_5min = 10
        acc.reset_daily_limits()
        assert acc.daily_sent == 0
        assert acc.transaction_count_last_5min == 0

    def test_repr(self, tier3_account):
        r = repr(tier3_account)
        assert "acc_001" in r
        assert "Tier 3" in r


class TestAccountPool:
    def test_empty_pool(self, empty_pool):
        assert len(empty_pool) == 0
        assert empty_pool.total_send_capacity() == 0

    def test_add_account(self, empty_pool, tier3_account):
        empty_pool.add(tier3_account)
        assert len(empty_pool) == 1

    def test_get_account(self, populated_pool, tier3_account):
        assert populated_pool.get("acc_001") == tier3_account

    def test_get_nonexistent_raises(self, populated_pool):
        with pytest.raises(KeyError):
            populated_pool.get("nonexistent")

    def test_all_returns_all(self, populated_pool):
        assert len(populated_pool.all) == 4

    def test_by_region_filters(self, populated_pool):
        acc = MpesaAccount("coast", KYCLevel.TIER_3, "Coast", "Mombasa")
        populated_pool.add(acc)
        mombasa = populated_pool.by_region("Mombasa")
        assert len(mombasa) == 1
        assert mombasa[0].region == "Mombasa"

    def test_active_filters_frozen(self, populated_pool):
        populated_pool.get("acc_001").status = AccountStatus.FROZEN
        active = populated_pool.active()
        assert len(active) == 3

    def test_senders_ordered_by_capacity(self, populated_pool):
        """Business account should come first (unlimited capacity)."""
        senders = populated_pool.senders_ordered_by_capacity()
        assert senders[0].account_id == "acc_biz"

    def test_senders_ordered_by_capacity_with_region(self, populated_pool):
        populated_pool.add(MpesaAccount("coast", KYCLevel.TIER_2, "Coast", "Mombasa"))
        nairobi = populated_pool.senders_ordered_by_capacity("Nairobi")
        assert all(a.region == "Nairobi" for a in nairobi)

    def test_total_send_capacity(self, populated_pool):
        cap = populated_pool.total_send_capacity()
        assert cap > 0

    def test_iteration(self, populated_pool):
        ids = [a.account_id for a in populated_pool]
        assert len(ids) == 4

    def test_to_dict(self, populated_pool):
        d = populated_pool.to_dict()
        assert "acc_001" in d
        assert d["acc_001"]["kyc"] == 3
