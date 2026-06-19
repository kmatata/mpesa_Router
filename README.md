# M-Pesa Constraint-Satisfaction Routing Engine

## What This Is

A modular, extensible framework for modeling the M-Pesa transaction constraint space and finding optimal multi-account routing paths through Kenya's mobile money system.

The engine models every structural constraint:
- **KYC tier limits** (Tier 1-3 daily send/receive ceilings)
- **Per-transaction caps** (max single send by tier)
- **Timing constraints** (settlement windows, weekend reductions)
- **Flag triggers** (rapid sequences, round numbers, new account patterns, excessive chunking)
- **Agent liquidity constraints**
- **Geographic routing**

Then finds optimal routing paths using constraint-satisfaction algorithms — distributing volume across accounts, timing, and routes to multiply effective throughput 3-5x while staying within existing regulatory frameworks.

## Results

| Scenario | Naive | Optimized | Improvement |
|---|---|---|---|
| Crypto OTC Payout (KES 2M) | KES 500K | KES 1.92M | **3.8x** |
| Property Deposit (KES 5M) | KES 500K | KES 1.78M | **3.6x** |
| Remittance Batch (10 x KES 500K) | 41 min | 17 min | **41% faster** |

## Architecture

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
└── exporters/         # Output formatting
    └── report.py      # ReportGenerator
```

## Usage

```python
from mpesa_routing import *

# Build constraint graph
graph = ConstraintGraph()
graph.add_account(MpesaAccount("acc_1", KYCLevel.TIER_3, "Primary", "Nairobi"))
graph.add_account(MpesaAccount("acc_2", KYCLevel.TIER_3, "Secondary", "Nairobi"))

# Route a transaction
txn = Transaction(2_000_000, "phone", "recipient_1", "immediate", "Nairobi")
finder = PathFinder(graph)
path = finder.best_path(txn)

print(f"Moved: KES {path.total_amount:,.0f}")
print(f"Accounts: {path.num_accounts}")
print(f"Risk: {path.flag_risk_score:.0%}")
```

## Quick Demo

```bash
python -m mpesa_routing.cli
```

## The Offer

I'm offering a **free M-Pesa constraint audit** to companies moving meaningful volume through M-Pesa. 

You provide 1 week of anonymized transaction logs. I run them through my routing engine. You receive a report showing:
- Your current effective throughput and constraint bottlenecks
- The optimized routing that would multiply your volume
- The exact KES impact of unblocking those constraints

No cost. No obligation. Just data.

