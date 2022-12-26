import click
import requests
import json 
from os import environ

import jinja2
import pytz
from dateutil import parser
from typing import List

import avalanche
import s3records
from api import S3_STORE
from api import Recipient

import tqdm

TEMPLATE_FILE = environ.get('EMAIL_TEMPLATE', "mailtemplate.html")
A3_API = avalanche.AvalancheAPI()
RECIPIENTS_DB = s3records.S3Records(S3_STORE)

def get_recipients() -> List[Recipient]:
    return RECIPIENTS_DB.data

def update_recipients(data: List[Recipient]): 
    RECIPIENTS_DB.data = data
    RECIPIENTS_DB.save()

def render_forecast(template: jinja2.Template, forecast: dict) -> str:
    return template.render(forecast)

def transform_forecast(forecast: dict, center_meta: dict) -> dict:
    center_tz = pytz.timezone(center_meta['timezone'])

    for key in forecast.keys():
        if "_time" in key or "created" in key or "updated" in key:
            newdate = parser.parse(forecast[key]).astimezone(center_tz).strftime("%a %b %d %Y %-I:%M:%S %p %Z")
            forecast[key] = newdate

    return forecast

def send_forecast(r: Recipient, template: jinja2.Template): 
    forecast = A3_API.get_forecast(r['center_id'], r['zone_id'])
    center_meta = A3_API.get_center_meta(r['center_id'])

    forecast = transform_forecast(forecast, center_meta)
    rendered = render_forecast(template, forecast)

    with open(f"{r['email']}_sent.html", 'w') as f:
        f.write(rendered)


def get_template(file: str) -> jinja2.Template:
    with open(file) as _f:
        return jinja2.Environment().from_string(_f.read())



@click.command()
@click.option('--output', '-o', help="Output rendered email to specified file.")
@click.option('--noemail', is_flag=True)
def main(*args, **kwargs):
    template = get_template(TEMPLATE_FILE)
    recipients = get_recipients()
    for recipient in tqdm.tqdm(recipients):
        send_forecast(recipient, template)

    
if __name__ == "__main__": 
    main()