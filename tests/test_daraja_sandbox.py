"""Daraja Sandbox Integration Tests.

These tests validate the sandbox certificate and attempt to verify
connectivity to the Safaricom Daraja API sandbox environment.

Safaricom Developer Portal Products
====================================

For the routing engine's use case (inbound capital through M-Pesa),
the relevant API products are:

1. B2C (Business to Customer) — PRIMARY
   Used to send money from a business to M-Pesa users.
   This is the payout API for OTC desks, remittance disbursement,
   and bulk agent payouts. The routing engine optimizes which
   accounts/channels these payouts flow through.

2. M-Pesa Express (STK Push / Lipa na M-Pesa Online) — PRIMARY
   Used to initiate a payment request from an M-Pesa user.
   This is how inbound capital would be collected from diaspora
   or foreign sources into Kenyan mobile money.

3. C2B (Customer to Business) — SECONDARY
   Used to receive payments via till number or paybill.
   Relevant for merchant collection of inbound funds.

4. B2B (Business to Business) — SECONDARY
   Used to transfer between business accounts.
   Relevant for layering/structuring across multiple accounts.

When creating a sandbox app in the developer portal, add ALL of
the above products to test the complete inbound capital flow.

Setup Steps:
   1. Register at https://developer.safaricom.co.ke/
   2. Go to: My Apps > Create App
   3. Add these API products: B2C, M-Pesa Express, C2B, B2B
   4. Note your Consumer Key and Consumer Secret
   5. Download the sandbox certificate from the app dashboard
      (or use the one at pub/SandboxCertificate.cer)

Running Daraja Tests:
   Option 1 (.env file — recommended):
     echo "CONSUMER_KEY=xxx" > .env
     echo "CONSUMER_SECRET=xxx" >> .env
     python -m pytest tests/test_daraja_sandbox.py -v --no-header -k "daraja"

   Option 2 (environment variables):
     DARAYA_CONSUMER_KEY=xxx DARAYA_CONSUMER_SECRET=xxx \\
       python -m pytest tests/test_daraja_sandbox.py -v --no-header -k "daraja"
"""

import ssl
import os
from pathlib import Path

import pytest

PUB_DIR = Path(__file__).parent.parent / "pub"
CERT_PATH = PUB_DIR / "SandboxCertificate.cer"
DARAYA_SANDBOX_URL = "https://sandbox.safaricom.co.ke"
DARAYA_AUTH_URL = f"{DARAYA_SANDBOX_URL}/oauth/v1/generate?grant_type=client_credentials"

# ── Load credentials from .env ──────────────────────────────────────
DOTENV_PATH = Path(__file__).parent.parent / ".env"


def _load_dotenv(path: Path) -> dict:
    """Simple .env parser — reads KEY=VALUE pairs, no external deps."""
    if not path.exists():
        return {}
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


_dotenv = _load_dotenv(DOTENV_PATH)



@pytest.mark.daraja
class TestSandboxCertificate:
    """Validate that the Daraja sandbox certificate is present and loadable."""

    def test_certificate_exists(self):
        assert CERT_PATH.exists(), (
            f"Sandbox certificate not found at {CERT_PATH}. "
            "Download it from the Safaricom Developer Portal."
        )

    def test_certificate_is_readable(self):
        data = CERT_PATH.read_bytes()
        assert len(data) > 0
        assert b"BEGIN CERTIFICATE" in data

    def test_certificate_has_pem_format(self):
        text = CERT_PATH.read_text()
        assert text.startswith("-----BEGIN CERTIFICATE-----")
        assert "-----END CERTIFICATE-----" in text


@pytest.mark.daraja
class TestDarajaConnectivity:
    """Test basic connectivity to Daraja sandbox endpoints."""

    def test_sandbox_resolves(self):
        import socket
        host = "sandbox.safaricom.co.ke"
        try:
            addr = socket.getaddrinfo(host, 443)
            assert len(addr) > 0
        except socket.gaierror:
            pytest.skip(f"Cannot resolve {host} — check internet connection")

    def test_sandbox_port_open(self):
        import socket
        host = "sandbox.safaricom.co.ke"
        try:
            sock = socket.create_connection((host, 443), timeout=5)
            sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError):
            pytest.skip(f"Cannot connect to {host}:443")


@pytest.mark.daraja
class TestDarajaAuth:
    """Requires consumer_key and consumer_secret from Safaricom Dev Portal.

    Credentials are loaded from .env (CONSUMER_KEY and CONSUMER_SECRET)
    or from DARAYA_CONSUMER_KEY / DARAYA_CONSUMER_SECRET env vars.
    """

    CONSUMER_KEY = (
        os.environ.get("DARAYA_CONSUMER_KEY")
        or _dotenv.get("CONSUMER_KEY")
        or ""
    )
    CONSUMER_SECRET = (
        os.environ.get("DARAYA_CONSUMER_SECRET")
        or _dotenv.get("CONSUMER_SECRET")
        or ""
    )

    def test_credentials_available(self):
        if not self.CONSUMER_KEY or not self.CONSUMER_SECRET:
            pytest.skip(
                "Set CONSUMER_KEY and CONSUMER_SECRET in .env "
                "or DARAYA_CONSUMER_KEY / DARAYA_CONSUMER_SECRET env vars"
            )

    def test_oauth_token_generation(self):
        if not self.CONSUMER_KEY or not self.CONSUMER_SECRET:
            pytest.skip("Credentials not configured")

        import requests
        if not CERT_PATH.exists():
            pytest.skip("Sandbox certificate not found")

        try:
            resp = requests.get(
                DARAYA_AUTH_URL,
                auth=(self.CONSUMER_KEY, self.CONSUMER_SECRET),
                timeout=15,
            )
            assert resp.status_code == 200, (
                f"Auth failed: {resp.status_code} — {resp.text}"
            )
            data = resp.json()
            assert "access_token" in data, f"No access_token in response: {data}"
            print(f"Access token obtained: {data['access_token'][:20]}...")

        except requests.exceptions.ConnectionError as e:
            pytest.skip(f"Connection failed: {e}")
        except requests.exceptions.Timeout:
            pytest.skip("Auth request timed out")


def print_setup_instructions():
    """Print instructions for setting up Daraja API access."""
    print()
    print("=" * 60)
    print("  DARAJA API SETUP INSTRUCTIONS")
    print("=" * 60)
    print()
    print("  Products to activate (all 4 for routing engine):")
    print("    1. B2C (Business to Customer)      — PRIMARY (payouts)")
    print("    2. M-Pesa Express (STK Push)       — PRIMARY (collections)")
    print("    3. C2B (Customer to Business)      — Secondary (receiving)")
    print("    4. B2B (Business to Business)      — Secondary (layering)")
    print()
    print("  Steps:")
    print("    1. Go to https://developer.safaricom.co.ke/")
    print("    2. My Apps > Create App")
    print("    3. Add the 4 products above")
    print("    4. Copy Consumer Key and Consumer Secret")
    print("    5. Download sandbox certificate (or use existing)")
    print()
    print("  Set credentials in .env (recommended):")
    print('    echo "CONSUMER_KEY=xxx" > .env')
    print('    echo "CONSUMER_SECRET=xxx" >> .env')
    print()
    print("  Or use environment variables:")
    print("    DARAYA_CONSUMER_KEY=xxx DARAYA_CONSUMER_SECRET=xxx \\")
    print("      python -m pytest tests/test_daraja_sandbox.py -v --no-header")
    print()
    print("  Certificate path:", CERT_PATH)
    print("  Certificate exists:", CERT_PATH.exists())
    print()
