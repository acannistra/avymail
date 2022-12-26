import click
import requests
import json 
from os import environ

import jinja2
import pytz
from dateutil import parser

import avalanche

TEMPLATE_FILE = environ.get('EMAIL_TEMPLATE', "mailtemplate.html")
A3_API = avalanche.AvalancheAPI()

TEST = {
    "center_id": "NWAC",
    "zone_id": 1136
}

def render_forecast(template: jinja2.Template, forecast: dict) -> str:
    return template.render(forecast)

def transform_forecast(forecast: dict, center_meta: dict) -> dict:
    center_tz = pytz.timezone(center_meta['timezone'])

    for key in forecast.keys():
        if "_time" in key or "created" in key or "updated" in key:
            newdate = parser.parse(forecast[key]).astimezone(center_tz).strftime("%a %b %d %Y %-I:%M:%S %p %Z")
            forecast[key] = newdate

    return forecast

def get_template(file: str) -> jinja2.Template:
    with open(file) as _f:
        return jinja2.Environment().from_string(_f.read())

@click.command()
@click.option('--output', '-o', help="Output rendered email to specified file.")
@click.option('--noemail', is_flag=True)
def main(*args, **kwargs):
    
    forecast = A3_API.get_forecast(TEST['center_id'], TEST['zone_id'])
    center_meta = A3_API.get_center_meta(TEST['center_id'])

    forecast = transform_forecast(forecast, center_meta)
    template = get_template(TEMPLATE_FILE)

    rendered = render_forecast(template, forecast)

    with open('rendered.html', 'w') as f:
        f.write(rendered)

    
if __name__ == "__main__": 
    main()