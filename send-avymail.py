import click
import requests
import json 
from os import environ
from subprocess import check_output
from typing import Optional

import jinja2
import pytz
from dateutil import parser
from typing import List

import avalanche
import s3records
from api import S3_STORE
from api import Recipient
from api import find_record
import urllib.parse 

import tqdm
from smtplib import SMTP
from email.message import EmailMessage

AVYMAIL_API = "https://avymail.fly.dev"
TEMPLATE_FILE = environ.get('EMAIL_TEMPLATE', "mailtemplate.html")
A3_API = avalanche.AvalancheAPI()
RECIPIENTS_DB = s3records.S3Records(S3_STORE)
CODE_VERSION_HASH = check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()

def load_email_config() -> dict:
    config = {
        "from_email": environ.get('FROM_EMAIL'),
        "username": environ.get('SMTP_USERNAME'),
        "password": environ.get('SMTP_PASSWORD'),
        "server": environ.get("SMTP_SERVER")
    }
    if not all(config.values()):
        raise Exception("Missing one of FROM_EMAIL, SMTP_USERNAME, SMTP_PASSWORD env variables.")

    config['SMTP'] = SMTP(config['server'], 587)
    config['SMTP'].starttls()
    config['SMTP'].login(config['username'], config['password'])
    return config

def get_recipients() -> List[Recipient]:
    return RECIPIENTS_DB.data

def update_recipients(data: List[Recipient]): 
    RECIPIENTS_DB.data = data
    RECIPIENTS_DB.save()

def render_forecast(template: jinja2.Template, forecast: dict) -> str:
    return template.render(forecast)

def transform_forecast(forecast: dict, center_meta: dict, zone_id: str) -> dict:
    center_tz = pytz.timezone(center_meta['timezone'])

    # localize timezones
    utc_times = {}
    for key in forecast.keys():
        if "_time" in key or "created" in key or "updated" in key:
            utc_times[f"{key}_utc"] = forecast[key]
            newdate = parser.parse(forecast[key]).astimezone(center_tz).strftime("%a %b %d %Y %-I:%M:%S %p %Z")
            forecast[key] = newdate

    forecast.update(utc_times)

    # remove references to zones that aren't wanted.
    for zone in forecast['forecast_zone']: 
        if str(zone['id']) == str(zone_id):
            forecast['forecast_zone'] = [zone]

    print(forecast['forecast_zone'])

    forecast['code_version'] = CODE_VERSION_HASH

    return forecast

def get_template(file: str) -> jinja2.Template:
    with open(file) as _f:
        return jinja2.Environment().from_string(_f.read())

def is_forecast_updated(r: Recipient, forecast: dict) -> bool:
    try: 
        return parser.parse(forecast['updated_at_utc']) > parser.parse(r['data_last_updated_time'])
    except TypeError:
        # if fail to parse date, consider forecast updated
        return True

def create_message(source, recipient, subject, content):
    m = EmailMessage()
    m.set_content(content, subtype='html')
    m['Subject'] = subject
    m['From'] = source
    m['To'] = recipient
    return m

def update_db_record(db_idx, forecast):
    RECIPIENTS_DB.data[db_idx]['data_last_updated_time'] = forecast['updated_at_utc']

def send_forecast(r: Recipient, template: jinja2.Template, email_config: Optional[dict], output: bool): 
    forecast = A3_API.get_forecast(r['center_id'], r['zone_id'])
    center_meta = A3_API.get_center_meta(r['center_id'])

    forecast = transform_forecast(forecast, center_meta, r['zone_id'])

    if not is_forecast_updated(r, forecast):
        return None

    forecast['unsub_url'] = AVYMAIL_API + f"/remove?email={urllib.parse.quote(r['email'])}&center_id={r['center_id']}&zone_id={r['zone_id']}"

    rendered = render_forecast(template, forecast)


    if output:
        with open(f"{r['email']}_{r['center_id']}_{r['zone_id']}_sent.html", 'w') as f:
            f.write(rendered)
    
    if email_config:
        subj_datestamp = forecast['published_at']
        subject = f"Avalanche Forecast for {forecast['forecast_zone'][0]['name']} ({subj_datestamp})"
        message = create_message(email_config['from_email'], r['email'], subject, rendered)
        email_config['SMTP'].send_message(message)

    return forecast
    



@click.command()
@click.option('--output', '-o', is_flag=True, help="Output rendered email to local file.")
@click.option('--noemail', is_flag=True)
def main(*args, **kwargs):
    template = get_template(TEMPLATE_FILE)
    recipients = get_recipients()
    email_config = None

    if not kwargs['noemail']: 
        email_config = load_email_config()
        print(email_config)

    for db_idx, recipient in tqdm.tqdm(list(enumerate(recipients))):
        forecast = send_forecast(recipient, template, email_config, output=kwargs['output'])
        if forecast:
            update_db_record(db_idx, forecast)
    
    RECIPIENTS_DB.save()

    
if __name__ == "__main__": 
    main()