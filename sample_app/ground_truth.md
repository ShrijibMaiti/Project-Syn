# Ground truth — READ ONLY BY validation/

SYN must never read this file. It exists so `blind_detection_test.py` can check
whether SYN found these faults **without being told where they are**. If SYN ever
consumes this, the validation becomes circular and proves nothing.

## Fault 1 — retry storm (metastable)
- **Location:** `retry_loop.call_with_retries`
- **Mechanism:** `MAX_RETRIES=6`, no backoff, no jitter, no circuit breaker. Retries
  add load to the resource already failing — a self-sustaining feedback loop.
- **Signature:** two stable basins; hysteresis (stays collapsed after `/trigger` ends).
- **Correct detection:** `bistable=True` with a critical load ≤ 5.0 req/s, and a
  separatrix margin that shrinks monotonically as load rises.
- **Fixed variant:** `retry_loop.healthy_call` — must NOT be flagged.

## Fault 2a — N+1 queries (complexity, pool-bound)
- **Location:** `order_service.list_orders_with_items`
- **Verified:** **O(n)** in both time and `db_calls`, R² = 1.0000 over 2.4 decades.
- **Not quadratic.** n round trips instead of 1 — a constant-factor disaster.
- **Ceiling:** `db_connection_pool` (pool-bound — raising the pool moves the crossing).

## Fault 2b — nested-loop join (complexity, compute-bound)
- **Location:** `order_service.build_order_report`
- **Verified:** **O(n²)** in time, **O(1)** in `db_calls`, R² = 1.0000.
- **Ceiling:** `request_timeout` / CPU budget (compute-bound — more RAM does not move it).
- **Fixed variant:** `order_service.build_order_report_fixed` — must NOT be flagged.