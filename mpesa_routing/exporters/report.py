"""Report generation for simulation comparisons."""

from ..simulation.engine import SimulationResult, Scenario


class ReportGenerator:
    """Generates formatted comparison reports."""

    SEPARATOR = "-" * 55

    def generate_text(self, scenario: Scenario, results: dict) -> str:
        native = results.get("naive")
        optimized = results.get("optimized")

        if not native or not optimized:
            return "Simulation incomplete."

        lines = []
        lines.append("=" * 60)
        lines.append(f"  SIMULATION: {scenario.name}")
        lines.append(f"  {scenario.description}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"{'':25} {'NAIVE':>15} {'OPTIMIZED':>15}")
        lines.append(self.SEPARATOR)
        lines.append(self._row("Volume (KES)", native.volume_moved, optimized.volume_moved))
        lines.append(self._row("Time (min)", native.total_time_minutes, optimized.total_time_minutes))
        lines.append(self._row("Fees (KES)", native.total_fees, optimized.total_fees))
        lines.append(self._row("Flag Events", native.flag_events, optimized.flag_events))
        lines.append(self._row("Blocked", native.transactions_blocked, optimized.transactions_blocked))
        lines.append(self._row("Accounts Used", native.accounts_used, optimized.accounts_used))
        lines.append(self.SEPARATOR)
        lines.append("")

        vol_mult = optimized.volume_moved / native.volume_moved if native.volume_moved else 0
        fee_diff = ((optimized.total_fees - native.total_fees) / native.total_fees * 100) if native.total_fees else 0
        time_diff = ((native.total_time_minutes - optimized.total_time_minutes) / native.total_time_minutes * 100) if native.total_time_minutes else 0

        lines.append("  KEY TAKEAWAYS")
        lines.append(f"  * Volume multiplier: {vol_mult:.1f}x")
        lines.append(f"  * Fee impact:        {fee_diff:+.1f}%")
        lines.append(f"  * Time impact:       {time_diff:+.1f}%")
        lines.append(f"  * Flag reduction:    {native.flag_events - optimized.flag_events} events")

        return "\n".join(lines)

    def _row(self, label: str, naive_val, opt_val) -> str:
        if isinstance(naive_val, float):
            n = f"{naive_val:>15.1f}"
            o = f"{opt_val:>15.1f}"
        else:
            n = f"{naive_val:>15}"
            o = f"{opt_val:>15}"
        return f"{label:25} {n} {o}"

    def generate_all(self, comparisons: list) -> str:
        lines = []
        for scenario, results in comparisons:
            lines.append(self.generate_text(scenario, results))
            lines.append("")
        return "\n".join(lines)
