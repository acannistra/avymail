import click
import requests
import json
import datetime
from os import environ
from subprocess import check_output, CalledProcessError
from typing import Optional
import copy

import jinja2
import pytz
from dateutil import parser
from typing import List

import avalanche
import s3records
from api import S3_STORE
from api import Recipient
import urllib.parse
from retrying import retry
from pprint import pprint

import tqdm
from smtplib import SMTP, SMTPException
from email.message import EmailMessage
import boto3
from botocore.exceptions import BotoCoreError, ClientError

SES_CLIENT = boto3.client("sesv2", region_name="us-east-1")
AVYMAIL_API = environ.get("AVYMAIL_API", "https://avymail.fly.dev")
TEMPLATE_FILE = environ.get("EMAIL_TEMPLATE", "mailtemplate.html")
A3_API = avalanche.AvalancheAPI()
RECIPIENTS_DB = s3records.S3Records(S3_STORE)
CODE_VERSION_HASH = ""
try:
    CODE_VERSION_HASH = (
        check_output(["git", "rev-parse", "--short", "HEAD"]).decode("ascii").strip()
    )
except CalledProcessError:
    CODE_VERSION_HASH = environ.get("SHORT_SHA", "")


def load_email_config() -> dict:
    config = {"from_email": environ.get("FROM_EMAIL")}
    if not all(config.values()):
        raise Exception(
            "Missing one of FROM_EMAIL, SMTP_USERNAME, SMTP_PASSWORD env variables."
        )

    return config


def get_recipients() -> List[Recipient]:
    return RECIPIENTS_DB.data


def update_recipients(data: List[Recipient]):
    RECIPIENTS_DB.data = data
    RECIPIENTS_DB.save()


def render_forecast(template: jinja2.Template, forecast: dict) -> str:
    return template.render(forecast)


def transform_forecast(forecast: dict, center_meta: dict, zone_id: str) -> dict:
    forecast = copy.deepcopy(forecast)

    center_tz = pytz.timezone(center_meta["timezone"])

    # localize timezones
    utc_times = {}
    for key in forecast.keys():
        if ("_time" in key or "created" in key or "updated" in key) and forecast[key]:
            try:
                utc_times[f"{key}_utc"] = forecast[key]
                newdate = (
                    parser.parse(forecast[key])
                    .astimezone(center_tz)
                    .strftime("%a %b %d %Y %-I:%M:%S %p %Z")
                )
                forecast[key] = newdate
            except TypeError as e:
                print("Error parsing times: Forecast: ", forecast)
                raise e

    forecast.update(utc_times)

    # remove references to zones that aren't wanted.
    for zone in forecast["forecast_zone"]:
        if str(zone["id"]) == str(zone_id):
            forecast["forecast_zone"] = [zone]

    if len(forecast.get("forecast_zone", [])) != 1:
        raise ValueError(
            f"number of zones isn't 1! ({len(forecast.get('forecast_zone', []))})"
        )

    # replace "None" danger ratings with No Rating icon
    for danger in forecast["danger"]:
        for k, v in danger.items():
            if v is None:
                danger[k] = 0

    forecast["code_version"] = CODE_VERSION_HASH

    return forecast


def get_template(file: str) -> jinja2.Template:
    with open(file) as _f:
        return jinja2.Environment().from_string(_f.read())


def is_forecast_updated(r: Recipient, forecast: dict) -> bool:
    try:
        return parser.parse(forecast["published_time_utc"]) > parser.parse(
            r["data_last_updated_time"]
        )
    except TypeError:
        # if fail to parse date, consider forecast updated
        return True


def create_message(source, recipient, subject, content):
    m = EmailMessage()
    m.set_content(content, subtype="html")
    m["Subject"] = subject
    m["From"] = source
    m["To"] = recipient
    return m


def update_db_record(db_idx, forecast):
    RECIPIENTS_DB.data[db_idx]["data_last_updated_time"] = forecast[
        "published_time_utc"
    ]


def obfuscate_email(email):
    split = email.split("@")
    return split[0][:3] + "..." + "@" + split[1][:3]


@retry(
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000,
    stop_max_attempt_number=7,
    retry_on_exception=lambda x: isinstance(x, SMTPException),
)
def send_forecast(
    r: Recipient,
    template: jinja2.Template,
    email_config: Optional[dict],
    output: bool,
    send_anyway: bool = False,
):
    forecast = A3_API.get_forecast(r["center_id"], r["zone_id"])
    center_meta = A3_API.get_center_meta(r["center_id"])

    forecast = transform_forecast(forecast, center_meta, r["zone_id"])

    if not send_anyway and not is_forecast_updated(r, forecast):
        return None

    forecast["unsub_url"] = "https://avy.email/unsubscribe.html"

    try:
        rendered = render_forecast(template, forecast)
    except Exception as e:
        print(forecast)
        raise e

    if output:
        with open(f"{r['email']}_{r['center_id']}_{r['zone_id']}_sent.html", "w") as f:
            f.write(rendered)

    if email_config:

        subj_datestamp = forecast["published_time"]
        subject = f"Avalanche Forecast for {forecast['forecast_zone'][0]['name']} ({subj_datestamp})"
        try:
            msg = create_message(
                email_config["from_email"],
                r["email"],
                subject,
                rendered,
            )
            msg["List-Unsubscribe"] = (
                AVYMAIL_API
                + f"/remove?email={urllib.parse.quote(r['email'])}&center_id={r['center_id']}&zone_id={r['zone_id']}"
            )
            response = SES_CLIENT.send_email(
                FromEmailAddress=email_config["from_email"],
                Destination={
                    "ToAddresses": [r["email"]],
                },
                Content={
                    "Raw": {
                        "Data": msg.as_bytes(),
                    }
                },
            )
            print(
                f"sent: {r['zone_id']}-{r['center_id']} to {obfuscate_email(r['email'])} ({len(rendered)} chars)"
            )
        except (BotoCoreError, ClientError) as e:
            print(f"Failed to send email to {r['email']}: {e}")
            raise e

    return forecast


def post_email_metric(n: int):
    requests.post(AVYMAIL_API + "/emails_sent", params={"n": n})


@click.command()
@click.option(
    "--output", "-o", is_flag=True, help="Output rendered email to local file."
)
@click.option("--noemail", is_flag=True)
@click.option("--ignoretimes", is_flag=True)
@click.option("--nosave", is_flag=True)
@click.option("--test", is_flag=True)
def main(*args, **kwargs):
    template = get_template(TEMPLATE_FILE)
    if not kwargs["test"]:
        recipients = get_recipients()
    else:
        recipients = [
            dict(
                email="tony.cannistra+avymailtest@gmail.com",
                center_id="NWAC",
                zone_id="1653",
                data_last_updated_time=datetime.datetime.now()
                - datetime.timedelta(days=1),
            )
        ]
    email_config = None
    sent_emails = 0

    if not kwargs["noemail"]:
        email_config = load_email_config()

    failures = []
    try:
        for db_idx, recipient in enumerate(recipients):
            forecast = None
            try:
                forecast = send_forecast(
                    recipient,
                    template,
                    email_config,
                    output=kwargs["output"],
                    send_anyway=kwargs["ignoretimes"],
                )
            except Exception as e:
                failures.append((recipient, e))
            if forecast:
                sent_emails += 1
                update_db_record(db_idx, forecast)
    finally:
        if not kwargs["nosave"]:
            RECIPIENTS_DB.save()
        else:
            pprint(RECIPIENTS_DB.data)

    if len(failures) > 0:
        import traceback

        print("Failures:")
        for f in failures:
            pprint(
                {
                    "email": obfuscate_email(f[0]["email"]),
                    "center_id": f[0]["center_id"],
                    "zone_id": f[0]["zone_id"],
                    "last_updated": f[0]["data_last_updated_time"],
                }
            )
            pprint(traceback.format_exception(f[1]))
        raise RuntimeError("Some emails failed to send!!!")

    post_email_metric(sent_emails)


if __name__ == "__main__":
    main()


def lambda_handler(event, context):
    main()
    return {"statusCode": 200, "body": "ok"}
