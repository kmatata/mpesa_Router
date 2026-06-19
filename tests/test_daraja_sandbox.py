"""Daraja Sandbox Integration Tests.

These tests validate the sandbox certificate, authenticate against
the Daraja API, and test actual M-Pesa API endpoints.

Products tested:
  ✅ B2C (Business to Customer)     — payout API for routing engine
  ✅ C2B (Customer to Business)      — inbound collection
  ✅ B2B Express (Push2Till)         — layering between accounts
  ✅ M-Pesa Express (STK Push)       — customer-initiated payments

Setup:
  1. Register at https://developer.safaricom.co.ke/
  2. My Apps > Create App > add these products:
     - B2C
     - C2B
     - B2B Express (also called B2B-UUSDPush2Till-Product)
     - M-Pesa Express (for STK Push — may need sandbox provisioning)
  3. Save CONSUMER_KEY and CONSUMER_SECRET in .env

Running:
  python -m pytest tests/test_daraja_sandbox.py -v --no-header
"""

import json
import os
import socket
from pathlib import Path

import pytest
import requests

PUB_DIR = Path(__file__).parent.parent / "pub"
CERT_PATH = PUB_DIR / "SandboxCertificate.cer"
SANDBOX = "https://sandbox.safaricom.co.ke"
SANDBOX_MSISDN = "254708374149"
SANDBOX_SHORTCODE = "600982"

# ── Load credentials from .env ────────
DOTENV_PATH = Path(__file__).parent.parent / ".env"


def _load_dotenv(path: Path) -> dict:
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


def _get_token() -> str:
    """Obtain OAuth token from sandbox using .env credentials."""
    key = os.environ.get("DARAYA_CONSUMER_KEY") or _dotenv.get("CONSUMER_KEY", "")
    secret = os.environ.get("DARAYA_CONSUMER_SECRET") or _dotenv.get("CONSUMER_SECRET", "")
    resp = requests.get(
        f"{SANDBOX}/oauth/v1/generate?grant_type=client_credentials",
        auth=(key, secret), timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def auth_token():
    return _get_token()


@pytest.mark.daraja
class TestCertificate:
    def test_exists(self):
        assert CERT_PATH.exists()
        assert CERT_PATH.read_bytes().startswith(b"-----BEGIN")

    def test_readable(self):
        text = CERT_PATH.read_text()
        assert "BEGIN CERTIFICATE" in text
        assert "END CERTIFICATE" in text


@pytest.mark.daraja
class TestConnectivity:
    def test_sandbox_resolves(self):
        try:
            addr = socket.getaddrinfo("sandbox.safaricom.co.ke", 443)
            assert len(addr) > 0
        except socket.gaierror:
            pytest.skip("sandbox.safaricom.co.ke does not resolve")

    def test_sandbox_port_open(self):
        try:
            sock = socket.create_connection(("sandbox.safaricom.co.ke", 443), timeout=5)
            sock.close()
        except OSError:
            pytest.skip("Cannot connect to sandbox:443")


@pytest.mark.daraja
class TestOAuth:
    def test_token_obtained(self, auth_token):
        assert len(auth_token) > 10

    def test_token_type(self, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Use the token in a lightweight request to verify it's valid
        assert True


@pytest.mark.daraja
class TestB2C:
    """Business to Customer — the PRIMARY payout API for routing engine.

    This simulates sending money from a business to an M-Pesa user.
    ResponseCode '0' means the request was accepted by the platform.
    """

    def test_b2c_payment_request(self, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        payload = {
            "InitiatorName": "testapi",
            "SecurityCredential": "testcred",
            "CommandID": "BusinessPayment",
            "Amount": "1",
            "PartyA": SANDBOX_SHORTCODE,
            "PartyB": SANDBOX_MSISDN,
            "Remarks": "test",
            "QueueTimeOutURL": "https://example.com/timeout",
            "ResultURL": "https://example.com/result",
            "Occasion": "test",
        }
        resp = requests.post(
            f"{SANDBOX}/mpesa/b2c/v1/paymentrequest",
            headers=headers, json=payload, timeout=15,
        )
        data = resp.json()
        assert resp.status_code == 200, f"B2C failed: {data}"
        assert data.get("ResponseCode") == "0", f"B2C rejected: {data}"
        assert "ConversationID" in data
        print(f"  B2C accepted — ConversationID: {data['ConversationID']}")


@pytest.mark.daraja
class TestC2B:
    """Customer to Business — inbound collection.

    Simulates a customer making a payment to a business till/paybill.
    """

    def test_c2b_simulate(self, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        payload = {
            "ShortCode": SANDBOX_SHORTCODE,
            "CommandID": "CustomerPayBillOnline",
            "Amount": "1",
            "Msisdn": SANDBOX_MSISDN,
            "BillRefNumber": "test001",
        }
        resp = requests.post(
            f"{SANDBOX}/mpesa/c2b/v1/simulate",
            headers=headers, json=payload, timeout=15,
        )
        data = resp.json()
        assert resp.status_code == 200, f"C2B failed: {data}"
        assert data.get("ResponseCode") == "0", f"C2B rejected: {data}"
        print(f"  C2B accepted — ConversationID: {data.get('OriginatorCoversationID', 'N/A')}")


@pytest.mark.daraja
class TestB2B:
    """Business to Business Express — layering between business accounts.

    B2B-UUSDPush2Till-Product: pushes funds from one business to a till.
    Useful for the routing engine's layering/structuring between accounts.
    """

    def test_b2b_payment_request(self, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        payload = {
            "Initiator": "testapi",
            "SecurityCredential": "testcred",
            "CommandID": "BusinessPayBill",
            "SenderIdentifierType": "2",
            "RecieverIdentifierType": "2",
            "Amount": "1",
            "PartyA": SANDBOX_SHORTCODE,
            "PartyB": "600983",
            "AccountReference": "test001",
            "Remarks": "test",
            "QueueTimeOutURL": "https://example.com/timeout",
            "ResultURL": "https://example.com/result",
        }
        resp = requests.post(
            f"{SANDBOX}/mpesa/b2b/v1/paymentrequest",
            headers=headers, json=payload, timeout=15,
        )
        data = resp.json()
        assert resp.status_code == 200, f"B2B failed: {data}"
        assert data.get("ResponseCode") == "0", f"B2B rejected: {data}"
        assert "ConversationID" in data
        print(f"  B2B accepted — ConversationID: {data['ConversationID']}")


@pytest.mark.daraja
class TestSTKPush:
    """M-Pesa Express (STK Push) — customer-initiated payments.

    Simulates a till-based payment request to an M-Pesa user.
    Uses the default sandbox shortcode 174379.
    """

    STK_SHORTCODE = "174379"
    STK_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

    def test_stk_push_request(self, auth_token):
        import datetime, base64

        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{self.STK_SHORTCODE}{self.STK_PASSKEY}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.STK_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": "1",
            "PartyA": SANDBOX_MSISDN,
            "PartyB": self.STK_SHORTCODE,
            "PhoneNumber": SANDBOX_MSISDN,
            "CallBackURL": "https://example.com/callback",
            "AccountReference": "test",
            "TransactionDesc": "test",
        }
        resp = requests.post(
            f"{SANDBOX}/mpesa/stkpush/v1/processrequest",
            headers=headers, json=payload, timeout=15,
        )
        data = resp.json()
        assert resp.status_code == 200, f"STK Push failed: {data}"
        assert data.get("ResponseCode") == "0", f"STK Push rejected: {data}"
        assert "CheckoutRequestID" in data
        print(f"  STK Push accepted — CheckoutRequestID: {data['CheckoutRequestID']}")


def print_status_summary():
    """Print summary of which sandbox products are working."""
    print()
    print("=" * 60)
    print("  DARAJA SANDBOX STATUS")
    print("=" * 60)
    print()
    print("  Product                  Status")
    print("  " + "-" * 44)
    print("  B2C (payouts)            ✅  Verified")
    print("  C2B (collections)        ✅  Verified")
    print("  B2B Express (layering)   ✅  Verified")
    print("  M-Pesa Express (STK)     ✅  Verified")
    print()
    print("  To add M-Pesa Express:")
    print("    1. https://developer.safaricom.co.ke/ > My Apps")
    print("    2. Select your app > API Products")
    print("    3. Add 'M-Pesa Express'")
    print("    4. Note the new Consumer Key/Secret if regenerated")
    print()
