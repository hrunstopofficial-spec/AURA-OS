"""Phase 12.5 Steps 3 & 4: Dedicated Quota Manager & Token Bucket Rate Limiter Test Suite.
Verifies Concurrency Slots, Two-Phase Budget Reservations (Reserve -> Commit/Rollback),
Storage Limits, Token Bucket Refill, Retry-After Calculations, and Tenant Isolation.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import threading
import time
import pytest

from app.core.contracts.governance import (
    BudgetExhaustedError,
    BudgetPeriod,
    QuotaDimension,
    QuotaExceededError,
    RateLimitAlgorithm,
    RateLimitExceededError,
    RateLimitPolicyContract,
    ReservationStatus,
    StorageLimitExceededError,
    TenantQuotaContract,
    UnauthorizedGovernanceError,
)
from app.core.governance.quota_manager import InMemoryTenantQuotaManager
from app.core.governance.rate_limiter import InMemoryTokenBucketRateLimiter


# ═════════════════════════════════════════════════════════════════════════════
# 1. TENANT CONCURRENCY QUOTA MANAGEMENT (Tests 1 - 4)
# ═════════════════════════════════════════════════════════════════════════════

def test_p12_5_s3_01_concurrency_slot_acquisition_succeeds():
    """S3-01: Tenant acquires concurrency slots within quota limits."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_concurrent_tasks=3))

    assert qm.acquire_concurrency_slot("tenant_A", "task_1") is True
    assert qm.acquire_concurrency_slot("tenant_A", "task_2") is True
    assert qm.get_active_concurrency_count("tenant_A") == 2


def test_p12_5_s3_02_concurrency_overflow_raises_429():
    """S3-02: Tenant exceeding max_concurrent_tasks raises QuotaExceededError (429)."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_concurrent_tasks=2))

    qm.acquire_concurrency_slot("tenant_A", "task_1")
    qm.acquire_concurrency_slot("tenant_A", "task_2")

    with pytest.raises(QuotaExceededError) as exc_info:
        qm.acquire_concurrency_slot("tenant_A", "task_3")
    assert exc_info.value.status_code == 429
    assert "exceeded max concurrent tasks" in exc_info.value.detail


def test_p12_5_s3_03_release_concurrency_slot_allows_next_task():
    """S3-03: Releasing a concurrency slot frees capacity for subsequent tasks."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_concurrent_tasks=1))

    qm.acquire_concurrency_slot("tenant_A", "task_1")
    assert qm.release_concurrency_slot("tenant_A", "task_1") is True

    # Now task_2 can acquire cleanly
    assert qm.acquire_concurrency_slot("tenant_A", "task_2") is True


def test_p12_5_s3_04_idempotent_concurrency_acquisition():
    """S3-04: Same task_id re-acquiring concurrency slot is an idempotent no-op."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_concurrent_tasks=1))

    assert qm.acquire_concurrency_slot("tenant_A", "task_1") is True
    assert qm.acquire_concurrency_slot("tenant_A", "task_1") is True  # Idempotent
    assert qm.get_active_concurrency_count("tenant_A") == 1


# ═════════════════════════════════════════════════════════════════════════════
# 2. TWO-PHASE BUDGET RESERVATION & SETTLEMENT (Tests 5 - 9)
# ═════════════════════════════════════════════════════════════════════════════

def test_p12_5_s3_05_two_phase_budget_reservation_pending():
    """S3-05: Budget reservation deducts from available token balance in PENDING state."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_tokens_per_period=10_000))

    res = qm.reserve_budget("tenant_A", "task_1", QuotaDimension.TOKEN_BUDGET, amount=4000.0)
    assert res.status == ReservationStatus.PENDING

    usage = qm.get_current_usage("tenant_A")
    assert usage["tokens_reserved"] == 4000.0
    assert usage["tokens_used"] == 0.0


def test_p12_5_s3_06_budget_overrun_raises_402():
    """S3-06: Reserving budget beyond max_tokens_per_period raises BudgetExhaustedError (402)."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_tokens_per_period=5000))

    with pytest.raises(BudgetExhaustedError) as exc_info:
        qm.reserve_budget("tenant_A", "task_1", QuotaDimension.TOKEN_BUDGET, amount=6000.0)
    assert exc_info.value.status_code == 402


def test_p12_5_s3_07_commit_consumption_settles_actual_usage():
    """S3-07: Committing reservation settles exact tokens used and frees unused reserved quota."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_tokens_per_period=10_000))

    res = qm.reserve_budget("tenant_A", "task_1", QuotaDimension.TOKEN_BUDGET, amount=5000.0)

    # Actual consumption was only 3200 tokens
    rec = qm.commit_consumption(res.reservation_id, "tenant_A", "task_1", actual_amount=3200.0)
    assert rec.amount_consumed == 3200.0

    usage = qm.get_current_usage("tenant_A")
    assert usage["tokens_used"] == 3200.0
    assert usage["tokens_reserved"] == 0.0


def test_p12_5_s3_08_rollback_reservation_restores_capacity():
    """S3-08: Rolling back failed task's reservation immediately restores full capacity."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_tokens_per_period=10_000))

    res = qm.reserve_budget("tenant_A", "task_1", QuotaDimension.TOKEN_BUDGET, amount=8000.0)
    assert qm.rollback_reservation(res.reservation_id, "tenant_A") is True

    usage = qm.get_current_usage("tenant_A")
    assert usage["tokens_reserved"] == 0.0
    assert usage["tokens_used"] == 0.0


def test_p12_5_s3_09_expired_reservation_auto_swept():
    """S3-09: Expired pending reservation is automatically swept and quota restored."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_tokens_per_period=10_000))

    res = qm.reserve_budget("tenant_A", "task_1", QuotaDimension.TOKEN_BUDGET, amount=5000.0, ttl_seconds=1)
    # Backdate expiry maintaining expires_at > granted_at
    past = datetime.now(timezone.utc) - timedelta(seconds=5)
    res.granted_at = past - timedelta(seconds=10)
    res.expires_at = past

    usage = qm.get_current_usage("tenant_A")
    assert usage["tokens_reserved"] == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# 3. STORAGE & CROSS-TENANT SECURITY (Tests 10 - 12)
# ═════════════════════════════════════════════════════════════════════════════

def test_p12_5_s3_10_storage_limit_exceeded_raises_413():
    """S3-10: Exceeding max_storage_bytes raises StorageLimitExceededError (413)."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_storage_bytes=1024 * 1024)) # 1MB

    with pytest.raises(StorageLimitExceededError) as exc_info:
        qm.reserve_budget("tenant_A", "task_1", QuotaDimension.STORAGE_BYTES, amount=2 * 1024 * 1024)
    assert exc_info.value.status_code == 413


def test_p12_5_s3_11_cross_tenant_reservation_commit_rejected():
    """S3-11: Tenant B attempting to commit Tenant A's reservation raises 403."""
    qm = InMemoryTenantQuotaManager()
    res = qm.reserve_budget("tenant_A", "task_1", QuotaDimension.TOKEN_BUDGET, amount=1000.0)

    with pytest.raises(UnauthorizedGovernanceError) as exc_info:
        qm.commit_consumption(res.reservation_id, "tenant_B", "task_1", actual_amount=1000.0)
    assert exc_info.value.status_code == 403


def test_p12_5_s3_12_soft_limit_threshold_warning():
    """S3-12: Crossing 80% soft limit threshold flags is_soft_limit_exceeded in usage telemetry."""
    qm = InMemoryTenantQuotaManager()
    qm.set_tenant_quota(TenantQuotaContract(tenant_id="tenant_A", max_tokens_per_period=10_000, soft_limit_threshold_percent=80.0))

    res = qm.reserve_budget("tenant_A", "task_1", QuotaDimension.TOKEN_BUDGET, amount=8500.0)
    usage = qm.get_current_usage("tenant_A")
    assert usage["is_soft_limit_exceeded"] is True


# ═════════════════════════════════════════════════════════════════════════════
# 4. TOKEN BUCKET RATE LIMITER ENGINE (Tests 13 - 18)
# ═════════════════════════════════════════════════════════════════════════════

def test_p12_5_s4_13_rate_limiter_consume_success():
    """S4-13: Initial token consumption succeeds within burst capacity."""
    limiter = InMemoryTokenBucketRateLimiter()
    limiter.set_policy(RateLimitPolicyContract(policy_id="p1", tenant_id="tenant_A", requests_per_minute=60, burst_capacity=5))

    assert limiter.consume("tenant_A", tokens_required=5) is True


def test_p12_5_s4_14_exhausted_rate_limit_raises_429_with_retry_after():
    """S4-14: Consuming beyond capacity raises RateLimitExceededError (429) with retry_after."""
    limiter = InMemoryTokenBucketRateLimiter()
    limiter.set_policy(RateLimitPolicyContract(policy_id="p2", tenant_id="tenant_A", requests_per_minute=60, burst_capacity=0))

    # Drain bucket (60 tokens)
    limiter.consume("tenant_A", tokens_required=60)

    with pytest.raises(RateLimitExceededError) as exc_info:
        limiter.consume("tenant_A", tokens_required=1)
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after_seconds > 0.0


def test_p12_5_s4_15_continuous_replenishment_after_delay():
    """S4-15: Token replenishment restores capacity over elapsed time."""
    limiter = InMemoryTokenBucketRateLimiter()
    # 600 req/min = 10 req/sec
    limiter.set_policy(RateLimitPolicyContract(policy_id="p3", tenant_id="tenant_A", requests_per_minute=600, burst_capacity=0))

    # Drain all tokens
    limiter.consume("tenant_A", tokens_required=600)
    assert limiter.get_token_balance("tenant_A") == pytest.approx(0.0, abs=0.05)

    # Wait 0.25s -> should replenish approx 2.5 tokens
    time.sleep(0.25)
    assert limiter.consume("tenant_A", tokens_required=1) is True


def test_p12_5_s4_16_cross_tenant_rate_limit_isolation():
    """S4-16: Tenant A exhausting rate limit has zero impact on Tenant B."""
    limiter = InMemoryTokenBucketRateLimiter()
    limiter.set_policy(RateLimitPolicyContract(policy_id="pA", tenant_id="tenant_A", requests_per_minute=10, burst_capacity=0))
    limiter.set_policy(RateLimitPolicyContract(policy_id="pB", tenant_id="tenant_B", requests_per_minute=10, burst_capacity=0))

    # Drain Tenant A
    limiter.consume("tenant_A", tokens_required=10)
    with pytest.raises(RateLimitExceededError):
        limiter.consume("tenant_A", tokens_required=1)

    # Tenant B is fully unaffected
    assert limiter.consume("tenant_B", tokens_required=10) is True


def test_p12_5_s4_17_custom_policy_update():
    """S4-17: Updating tenant rate limit policy adjusts max capacity immediately."""
    limiter = InMemoryTokenBucketRateLimiter()
    limiter.set_policy(RateLimitPolicyContract(policy_id="p1", tenant_id="tenant_A", requests_per_minute=100, burst_capacity=20))
    assert limiter.get_token_balance("tenant_A") == 120.0


def test_p12_5_s4_18_concurrent_rate_limiting_mutex_safety():
    """S4-18: 20 concurrent threads draining tokens evaluated atomically without race over-allocation."""
    limiter = InMemoryTokenBucketRateLimiter()
    limiter.set_policy(RateLimitPolicyContract(policy_id="p_con", tenant_id="tenant_A", requests_per_minute=10, burst_capacity=0))

    successes, failures = [], []
    barrier = threading.Barrier(20)

    def task(w_idx: int):
        barrier.wait()
        try:
            limiter.consume("tenant_A", tokens_required=1)
            successes.append(w_idx)
        except RateLimitExceededError as ex:
            failures.append((w_idx, ex))

    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(task, range(20)))

    # Exactly 10 successes and 10 rate-limit rejections
    assert len(successes) == 10
    assert len(failures) == 10
