"""M-Pesa Routing Engine — CLI entry point.

Usage:
    python -m mpesa_routing        — run all standard scenarios
    python -m mpesa_routing.cli    — same
"""

import sys

from .simulation.engine import SimulationEngine
from .simulation.scenarios import standard_scenarios
from .exporters.report import ReportGenerator


def main():
    engine = SimulationEngine()
    scenarios = standard_scenarios()
    reporter = ReportGenerator()
    comparisons = []

    for scenario in scenarios:
        results = engine.compare(scenario)
        comparisons.append((scenario, results))

    print(reporter.generate_all(comparisons))

    graph = engine.build_default_graph()
    print("=" * 60)
    print("  SYSTEM CAPACITY ANALYSIS")
    print("=" * 60)
    print(f"  Total accounts:    {len(graph.accounts)}")
    print(f"  Daily capacity:    KES {graph.accounts.total_send_capacity():,.0f}")
    print(f"  Nairobi accounts:  {len(graph.accounts.by_region('Nairobi'))}")
    print(f"  Mombasa accounts:  {len(graph.accounts.by_region('Mombasa'))}")


if __name__ == "__main__":
    main()
