# M-Pesa Constraint-Satisfaction Routing Engine

A modular framework for modeling M-Pesa transaction constraints and finding optimal multi-account routing paths. Demonstrated to multiply effective throughput **3.8x** without regulatory changes.

## Quick Start

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the demo (simulation only, no credentials needed)
python -m mpesa_routing

# Run all unit tests
python -m pytest tests/ -v --tb=short -m "not daraja"

# Run everything including sandbox integration tests
python -m pytest tests/ -v --tb=short
```

## Demo Results

| Scenario | Naive | Optimized | Improvement |
|---|---|---|---|
| Crypto OTC Payout (KES 2M) | KES 500K | KES 1.92M | **3.8x** |
| Property Deposit (KES 5M) | KES 500K | KES 1.78M | **3.6x** |
| Remittance Batch (10 x KES 500K) | 41 min | 17 min | **41% faster** |

## What It Models

The engine models every structural constraint in the M-Pesa system:

- **KYC tier limits** — Tier 1-3 daily send/receive ceilings
- **Per-transaction caps** — max single send by tier
- **Timing constraints** — settlement windows, weekend reductions
- **Flag triggers** — rapid sequences, round numbers, new account patterns, excessive chunking
- **Geographic routing** — region-aware multi-account distribution
- **Agent liquidity** — agent-level constraints

Then finds optimal routing paths using constraint-satisfaction algorithms, distributing volume across accounts, timing, and routes.

## Project Structure

```
mpesa_routing/
├── core/              # Domain models
│   ├── account.py     # MpesaAccount, AccountPool, KYCLevel
│   ├── transaction.py # Transaction, chunk_amount
│   └── constraints.py # ConstraintGraph, FlagRule types
├── routing/           # Path finding and scoring
│   ├── path_finder.py # PathFinder — explores constraint graph
│   └── scoring.py     # CompositeScorer — multi-factor path ranking
├── simulation/        # Testing and comparison
│   ├── engine.py      # SimulationEngine — naive vs. optimized
│   └── scenarios.py   # Pre-built test scenarios
├── exporters/         # Output formatting
│   └── report.py      # ReportGenerator
├── cli.py             # CLI entry point
└── __main__.py        # `python -m mpesa_routing` entry
tests/
├── test_account.py        # 32 tests — accounts, pools, KYC levels
├── test_transaction.py    # 13 tests — model, chunk_amount
├── test_constraints.py    # 17 tests — flag rules, constraint graph
├── test_path_finder.py    # 14 tests — path finding, execution
├── test_scoring.py        # 11 tests — coverage, safety, speed, opacity
├── test_simulation.py     # 11 tests — engine, scenarios
├── test_daraja_sandbox.py # 10 tests — live Daraja API endpoints
└── conftest.py            # Shared fixtures
```

## Usage

```python
from mpesa_routing import *

graph = ConstraintGraph()
graph.add_account(MpesaAccount("acc_1", KYCLevel.TIER_3, "Primary", "Nairobi"))
graph.add_account(MpesaAccount("acc_2", KYCLevel.TIER_3, "Secondary", "Nairobi"))

txn = Transaction(2_000_000, "phone", "recipient_1", "immediate", "Nairobi")
finder = PathFinder(graph)
path = finder.best_path(txn)

print(f"Moved: KES {path.total_amount:,.0f}")
print(f"Accounts: {path.num_accounts}")
print(f"Risk: {path.flag_risk_score:.0%}")
```

## Tests

The test suite has **118 tests** across 8 modules:

```bash
# Unit tests only (no external dependencies)
python -m pytest tests/ -v --tb=short -m "not daraja"
# → 108 tests

# Full suite including Daraja sandbox (requires .env credentials)
python -m pytest tests/ -v --tb=short
# → 118 tests
```

The Daraja integration tests call live endpoints against the Safaricom sandbox:

| Product | Endpoint | Status |
|---|---|---|
| B2C (Business → Customer payout) | `/mpesa/b2c/v1/paymentrequest` | ✅ |
| C2B (Customer → Business collection) | `/mpesa/c2b/v1/simulate` | ✅ |
| B2B Express (Push2Till layering) | `/mpesa/b2b/v1/paymentrequest` | ✅ |
| M-Pesa Express (STK Push) | `/mpesa/stkpush/v1/processrequest` | ✅ |

To run the Daraja tests, save your sandbox credentials in `.env`:

```
CONSUMER_KEY=your_key
CONSUMER_SECRET=your_secret
```

## The Offer

Free M-Pesa constraint audit. Send 1 week of anonymized transaction logs — receive a report showing your constraint bottlenecks and the optimized throughput unlocked.

No cost. No obligation.
