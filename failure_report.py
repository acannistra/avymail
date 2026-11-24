"""Send a failure report email for a send run.

This module uses only the standard library and boto3, so that cron_send.py can
use it when send-avymail.py cannot start.
"""

import datetime
from os import environ

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# send-avymail.py exits with this code when it sent its own failure report.
# cron_send.py then does not send a second report.
REPORTED_EXIT_CODE = 3


def send_failure_email(num_failures: int, body: str) -> bool:
    """Send a report to the FAILURE_EMAIL address from the FROM_EMAIL address.

    Returns True if SES accepted the email. Returns False if a variable is not
    set or the send fails. The function prints the reason in both cases.
    """
    to_email = environ.get("FAILURE_EMAIL")
    from_email = environ.get("FROM_EMAIL")
    if not to_email or not from_email:
        print("Failure report not sent: FAILURE_EMAIL or FROM_EMAIL is not set.")
        return False

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    subject = f"avymail_send: {num_failures} failures ({timestamp})"

    try:
        ses_client = boto3.client("sesv2", region_name="us-east-1")
        ses_client.send_email(
            FromEmailAddress=from_email,
            Destination={"ToAddresses": [to_email]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": f"{subject}\n\n{body}"}},
                }
            },
        )
    except (BotoCoreError, ClientError) as e:
        print(f"Failure report not sent: {e}")
        return False

    print("Failure report sent.")
    return True


if __name__ == "__main__":
    # Send a test report: python3 failure_report.py
    import sys

    sent = send_failure_email(0, "Test report. No action is needed.")
    sys.exit(0 if sent else 1)
