"""Simulation — running scenarios through naive vs. optimized comparison."""

from .engine import SimulationEngine, SimulationResult, Scenario
from .scenarios import standard_scenarios

__all__ = [
    "SimulationEngine", "SimulationResult", "Scenario",
    "standard_scenarios",
]
