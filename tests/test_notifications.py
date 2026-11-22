import logging
import smtplib
import ssl

import pytest

import notifications
import observations
import escalations


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def starttls(self, context):
        self.context = context

    def login(self, sender, password):
        self.login_values = sender, password

    def send_message(self, message, from_addr, to_addrs):
        self.message = message
        self.from_addr = from_addr
        self.to_addrs = to_addrs


def enable_email(monkeypatch, recipients="test-one@example.com,test-two@example.org"):
    monkeypatch.setenv("CARESIGHT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("GMAIL_ADDRESS", "caresight.demo@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "configured-app-password")
    monkeypatch.setenv("ESCALATION_RECIPIENTS", recipients)


def sample_escalation():
    return {
        "id": "abc12345",
        "patient_id": "P-SYNTHETIC-01",
        "total_score": 6,
        "risk_level": "Medium",
        "parameters_scoring_three": ["consciousness"],
        "clinical_response": "Urgent clinical assessment",
        "created_at": "2026-11-22T13:00:00",
    }


def test_email_is_disabled_by_default_and_never_connects(monkeypatch):
    monkeypatch.delenv("CARESIGHT_EMAIL_ENABLED", raising=False)
    monkeypatch.setattr(
        notifications.smtplib,
        "SMTP",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("SMTP connected")),
    )

    notifications.send_escalation_notification({"id": "test"})


def test_enabled_email_sends_verified_tls_message_to_all_recipients(monkeypatch):
    FakeSMTP.instances = []
    enable_email(monkeypatch)
    monkeypatch.setattr(notifications.smtplib, "SMTP", FakeSMTP)
    notifications.send_escalation_notification(sample_escalation())

    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port) == ("smtp.gmail.com", 587)
    assert smtp.timeout > 0
    assert smtp.context.check_hostname is True
    assert smtp.context.verify_mode == ssl.CERT_REQUIRED
    assert smtp.login_values == ("caresight.demo@gmail.com", "configured-app-password")
    assert smtp.from_addr == "caresight.demo@gmail.com"
    assert smtp.to_addrs == ["test-one@example.com", "test-two@example.org"]
    assert smtp.message["Subject"] == "[CareSight DEMO] Escalation alert"
    assert smtp.message["To"] == "test-one@example.com, test-two@example.org"
    body = smtp.message.get_content()
    for text in (
        "Escalation ID: abc12345",
        "Synthetic patient ID: P-SYNTHETIC-01",
        "NEWS2 total: 6",
        "Risk level: Medium",
        "Parameters scoring 3: consciousness",
        "Required response: Urgent clinical assessment",
        "Creation timestamp: 2026-11-22T13:00:00",
        "Sign in to CareSight to review this escalation.",
        "educational simulation, not a clinical alert",
    ):
        assert text in body
    assert "patient name" not in body.lower()
    assert "configured-app-password" not in body


@pytest.mark.parametrize(
    "overrides",
    [
        {"GMAIL_ADDRESS": ""},
        {"GMAIL_APP_PASSWORD": ""},
        {"ESCALATION_RECIPIENTS": ""},
        {"ESCALATION_RECIPIENTS": "not-an-address"},
        {"GMAIL_ADDRESS": "sender@example.com\nBcc: other@example.com"},
        {"ESCALATION_RECIPIENTS": "valid@example.com\nBcc: other@example.com"},
        {"GMAIL_APP_PASSWORD": "password\nInjected: value"},
    ],
)
def test_invalid_email_configuration_does_not_connect(monkeypatch, overrides):
    enable_email(monkeypatch)
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        notifications.smtplib,
        "SMTP",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("SMTP connected")),
    )

    notifications.send_escalation_notification({"id": "test"})


def test_smtp_authentication_failure_is_sanitized(monkeypatch, caplog):
    enable_email(monkeypatch)

    class AuthenticationFailure(FakeSMTP):
        def login(self, sender, password):
            raise smtplib.SMTPAuthenticationError(535, b"private-app-password")

    monkeypatch.setattr(notifications.smtplib, "SMTP", AuthenticationFailure)
    with caplog.at_level(logging.WARNING, logger="notifications"):
        notifications.send_escalation_notification(sample_escalation())

    assert "delivery failed" in caplog.text
    assert "private-app-password" not in caplog.text
    assert "configured-app-password" not in caplog.text


def test_connection_timeout_is_sanitized(monkeypatch, caplog):
    enable_email(monkeypatch)
    monkeypatch.setattr(
        notifications.smtplib,
        "SMTP",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("private-app-password")),
    )
    with caplog.at_level(logging.WARNING, logger="notifications"):
        notifications.send_escalation_notification(sample_escalation())

    assert "delivery failed" in caplog.text
    assert "private-app-password" not in caplog.text


def _nurse_headers(client):
    response = client.post(
        "/api/login",
        json={"username": "nurse", "password": "password123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_only_new_qualifying_observations_schedule_one_delivery(
    client,
    valid_request,
    monkeypatch,
):
    scheduled = []
    monkeypatch.setattr(
        notifications,
        "send_escalation_notification",
        lambda escalation: scheduled.append(escalation["id"]),
    )
    headers = _nurse_headers(client)
    valid_request["consciousness"] = "C"

    response = client.post("/api/observations", json=valid_request, headers=headers)
    assert response.status_code == 200
    escalation_id = response.json()["escalation"]["id"]
    assert scheduled == [escalation_id]

    assert client.get(
        "/api/patients/P-001/observations",
        headers=headers,
    ).status_code == 200
    clinician = client.post(
        "/api/login",
        json={"username": "clinician", "password": "password123"},
    ).json()["access_token"]
    assert client.get(
        "/api/escalations",
        headers={"Authorization": f"Bearer {clinician}"},
    ).status_code == 200
    assert scheduled == [escalation_id]


def test_nonqualifying_observation_schedules_no_delivery(
    client,
    valid_request,
    monkeypatch,
):
    scheduled = []
    monkeypatch.setattr(
        notifications,
        "send_escalation_notification",
        lambda escalation: scheduled.append(escalation["id"]),
    )

    response = client.post(
        "/api/observations",
        json=valid_request,
        headers=_nurse_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["escalation"] is None
    assert scheduled == []


def test_email_failure_does_not_fail_or_undo_observation(
    client,
    valid_request,
    monkeypatch,
    caplog,
):
    enable_email(monkeypatch, "test@example.com")

    class AuthenticationFailure(FakeSMTP):
        def login(self, sender, password):
            raise smtplib.SMTPAuthenticationError(535, b"secret-auth-response")

    monkeypatch.setattr(notifications.smtplib, "SMTP", AuthenticationFailure)
    valid_request["consciousness"] = "C"
    with caplog.at_level(logging.WARNING, logger="notifications"):
        response = client.post(
            "/api/observations",
            json=valid_request,
            headers=_nurse_headers(client),
        )

    assert response.status_code == 200
    assert "configured-app-password" not in response.text
    assert "secret-auth-response" not in response.text
    assert "configured-app-password" not in caplog.text
    assert "secret-auth-response" not in caplog.text
    assert len(observations.load_observations()) == 1
    assert len(escalations.load_escalations()) == 1
