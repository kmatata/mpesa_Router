"""Daraja Sandbox Integration Tests.

These tests validate the sandbox certificate and attempt to verify
connectivity to the Safaricom Daraja API sandbox environment.

The sandbox certificate is used for SSL pinning when connecting to
the Daraja API endpoints. Full API integration requires a consumer
key and secret from the Safaricom Developer Portal.

Prerequisites:
    1. Register at https://developer.safaricom.co.ke/
    2. Create an app to get consumer_key and consumer_secret
    3. The sandbox certificate is at pub/SandboxCertificate.cer
"""

import ssl
import os
from pathlib import Path

import pytest

PUB_DIR = Path(__file__).parent.parent / "pub"
CERT_PATH = PUB_DIR / "SandboxCertificate.cer"
DARAYA_SANDBOX_URL = "https://sandbox.safaricom.co.ke"
DARAYA_AUTH_URL = f"{DARAYA_SANDBOX_URL}/oauth/v1/generate?grant_type=client_credentials"


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

    Set these environment variables to run:
        export DARAYA_CONSUMER_KEY=your_key
        export DARAYA_CONSUMER_SECRET=your_secret
    """

    CONSUMER_KEY = os.environ.get("DARAYA_CONSUMER_KEY", "")
    CONSUMER_SECRET = os.environ.get("DARAYA_CONSUMER_SECRET", "")

    def test_credentials_available(self):
        if not self.CONSUMER_KEY or not self.CONSUMER_SECRET:
            pytest.skip(
                "Set DARAYA_CONSUMER_KEY and DARAYA_CONSUMER_SECRET "
                "environment variables to run auth tests"
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
    print("  To enable Daraja integration tests, you need:")
    print()
    print("  1. Register at https://developer.safaricom.co.ke/")
    print("  2. Create a new app in the sandbox")
    print("  3. Note your Consumer Key and Consumer Secret")
    print("  4. Download the sandbox certificate if not present")
    print()
    print("  Then run tests with:")
    print("    DARAYA_CONSUMER_KEY=xxx DARAYA_CONSUMER_SECRET=xxx \\")
    print("      python -m pytest tests/test_daraja_sandbox.py -v --no-header")
    print()
    print("  Current certificate path:", CERT_PATH)
    print("  Certificate exists:", CERT_PATH.exists())
    print()
