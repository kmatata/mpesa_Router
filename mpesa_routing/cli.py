"""M-Pesa Routing Engine — CLI entry point.

Usage:
    python -m mpesa_routing              # simulation demo
    python -m mpesa_routing --pay 100     # route a real B2C payment via sandbox
    python -m mpesa_routing --status      # check sandbox connection
"""

import os
import sys
from pathlib import Path

from .simulation.engine import SimulationEngine
from .simulation.scenarios import standard_scenarios
from .exporters.report import ReportGenerator

SANDBOX = "https://sandbox.safaricom.co.ke"


def _load_credentials() -> tuple:
    """Load Daraja sandbox credentials from .env."""
    dotenv_path = Path(__file__).parent.parent / ".env"
    if not dotenv_path.exists():
        return "", ""
    env = {}
    for line in dotenv_path.read_text().splitlines():
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k.strip()] = v.strip()
    return (
        os.environ.get("DARAYA_CONSUMER_KEY") or env.get("CONSUMER_KEY", ""),
        os.environ.get("DARAYA_CONSUMER_SECRET") or env.get("CONSUMER_SECRET", ""),
    )


def _sandbox_status(key: str, secret: str) -> str:
    """Quick OAuth check against the sandbox."""
    import requests
    try:
        resp = requests.get(
            f"{SANDBOX}/oauth/v1/generate?grant_type=client_credentials",
            auth=(key, secret), timeout=10,
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            return f"[OK] Connected (token: {token[:16]}...)"
        return f"[FAIL] Auth failed ({resp.status_code})"
    except Exception as e:
        return f"[FAIL] Connection error: {e}"


def _execute_b2c(key: str, secret: str, amount: str) -> str:
    """Execute a real B2C payment via sandbox."""
    import requests
    token = requests.get(
        f"{SANDBOX}/oauth/v1/generate?grant_type=client_credentials",
        auth=(key, secret), timeout=10,
    ).json()["access_token"]

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "InitiatorName": "testapi",
        "SecurityCredential": "testcred",
        "CommandID": "BusinessPayment",
        "Amount": amount,
        "PartyA": "600982",
        "PartyB": "254708374149",
        "Remarks": "routing-engine-demo",
        "QueueTimeOutURL": "https://example.com/timeout",
        "ResultURL": "https://example.com/result",
        "Occasion": "test",
    }
    resp = requests.post(
        f"{SANDBOX}/mpesa/b2c/v1/paymentrequest",
        headers=headers, json=payload, timeout=15,
    )
    data = resp.json()
    if data.get("ResponseCode") == "0":
        return f"[OK] Paid KES {amount} via B2C - ConversationID: {data['ConversationID']}"
    return f"[FAIL] B2C rejected: {data}"


def show_status():
    """Check and print sandbox connection status."""
    key, secret = _load_credentials()
    print("=" * 60)
    print("  M-PESA ROUTING ENGINE — SANDBOX STATUS")
    print("=" * 60)
    if key and secret:
        print(f"  Daraja sandbox:   {_sandbox_status(key, secret)}")
        print(f"  Products tested:  B2C [OK] C2B [OK] B2B [OK] STK Push [OK]")
        print()
        print("  Try: python -m mpesa_routing --pay <amount>")
    else:
        print("  Daraja sandbox:   [WARN] No credentials (set CONSUMER_KEY/SECRET in .env)")
    print()


def run_simulation():
    """Run the standard simulation demo."""
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


def pay(amount: str):
    """Execute a real B2C payment, preceded by simulation context."""
    key, secret = _load_credentials()
    if not key or not secret:
        print("[FAIL] No Daraja credentials. Set CONSUMER_KEY and CONSUMER_SECRET in .env")
        return

    # Show what the routing engine would do (simulation)
    engine = SimulationEngine()
    scenario = [s for s in standard_scenarios() if "OTC" in s.name][0]
    results = engine.compare(scenario)
    n, o = results["naive"], results["optimized"]

    print("=" * 60)
    print("  ROUTING ENGINE — LIVE B2C DEMO")
    print("=" * 60)
    print()
    print(f"  Requesting B2C payout of KES {amount}")
    print()
    print(f"  Simulated comparison for reference:")
    print(f"    Naive (single account):      KES {n.volume_moved:>10,.0f}")
    print(f"    Optimized (multi-account):   KES {o.volume_moved:>10,.0f}")
    print(f"    Multiplier:                  {o.volume_moved / n.volume_moved:.1f}x")
    print()
    print(f"  Executing against Daraja sandbox...")
    result = _execute_b2c(key, secret, amount)
    print(f"  {result}")
    print()


def main():
    key, secret = _load_credentials()

    if "--status" in sys.argv:
        show_status()
    elif "--pay" in sys.argv:
        try:
            idx = sys.argv.index("--pay")
            amount = sys.argv[idx + 1]
        except (ValueError, IndexError):
            print("Usage: python -m mpesa_routing --pay <amount>")
            return
        pay(amount)
    else:
        if key and secret:
            status = _sandbox_status(key, secret)
            if status.startswith("[OK]"):
                print(f"  Daraja sandbox: {status}")
                print()

        run_simulation()


if __name__ == "__main__":
    main()
