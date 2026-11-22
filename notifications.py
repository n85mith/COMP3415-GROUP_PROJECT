import logging
import os
import re
import smtplib
import ssl
from email.message import EmailMessage


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 10
logger = logging.getLogger(__name__)
_ADDRESS_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}$"
)


def _is_valid_address(address):
    if not address or "\r" in address or "\n" in address:
        return False
    if address.count("@") != 1 or not _ADDRESS_PATTERN.fullmatch(address):
        return False
    local, domain = address.split("@")
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if ".." in domain or any(
        not label or label.startswith("-") or label.endswith("-")
        for label in domain.split(".")
    ):
        return False
    return True


def _configuration():
    enabled = os.environ.get("CARESIGHT_EMAIL_ENABLED", "false").strip().lower()
    if enabled in {"false", "0", "no", "off", ""}:
        return None
    if enabled not in {"true", "1", "yes", "on"}:
        logger.warning("Escalation email skipped: invalid enable setting.")
        return None

    sender = os.environ.get("GMAIL_ADDRESS", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipients_value = os.environ.get("ESCALATION_RECIPIENTS", "")
    if any("\r" in value or "\n" in value for value in (sender, password, recipients_value)):
        logger.warning("Escalation email skipped: invalid email configuration.")
        return None

    recipients = [value.strip() for value in recipients_value.split(",")]
    if (
        not _is_valid_address(sender.strip())
        or not password.strip()
        or not recipients
        or any(not _is_valid_address(address) for address in recipients)
    ):
        logger.warning("Escalation email skipped: incomplete or invalid email configuration.")
        return None

    return sender.strip(), password, recipients


def _message(escalation, sender, recipients):
    message = EmailMessage()
    message["Subject"] = "[CareSight DEMO] Escalation alert"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    parameters = escalation.get("parameters_scoring_three") or []
    message.set_content(
        "\n".join(
            [
                f"Escalation ID: {escalation['id']}",
                f"Synthetic patient ID: {escalation['patient_id']}",
                f"NEWS2 total: {escalation['total_score']}",
                f"Risk level: {escalation['risk_level']}",
                "Parameters scoring 3: " + (", ".join(parameters) or "None"),
                f"Required response: {escalation['clinical_response']}",
                f"Creation timestamp: {escalation['created_at']}",
                "",
                "Sign in to CareSight to review this escalation.",
                "This is an educational simulation, not a clinical alert.",
            ]
        )
    )
    return message


def send_escalation_notification(escalation):
    configuration = _configuration()
    if configuration is None:
        return

    sender, password, recipients = configuration
    try:
        message = _message(escalation, sender, recipients)
        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=SMTP_TIMEOUT_SECONDS,
        ) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(sender, password)
            smtp.send_message(message, from_addr=sender, to_addrs=recipients)
    except (smtplib.SMTPException, OSError, ssl.SSLError, ValueError):
        logger.warning("Escalation email delivery failed.")
