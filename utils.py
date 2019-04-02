import datetime

import requests
import inflect
import humanize
import babel.numbers
import dateutil.parser

import dash_core_components as dcc
import dash_html_components as html

# fetch the 360Giving registry
def get_registry(reg_url):
    r = requests.get(reg_url)
    return r.json()

def get_registry_by_publisher(filters={}, **kwargs):
    reg = get_registry(**kwargs)

    reg_ = {}
    for r in reg:
        
        p = r.get("publisher", {}).get("name")

        # filter
        if filters.get("licence"):
            if r.get("license", "") not in filters["licence"]:
                continue

        if filters.get("search"):
            if filters.get("search", "").lower() not in p.lower():
                continue

        if filters.get("last_modified"):
            last_modified_poss = {
                "lastmonth": datetime.datetime.now() - datetime.timedelta(days=30),
                "6month": datetime.datetime.now() - datetime.timedelta(days=30*6),
                "12month": datetime.datetime.now() - datetime.timedelta(days=365),
            }
            if last_modified_poss.get(filters.get("last_modified")):
                last_modified = dateutil.parser.parse(r.get("modified"), ignoretz=True)
                if last_modified < last_modified_poss.get(filters.get("last_modified")):
                    continue

        if filters.get("currency"):
            choose_this = False
            for c in filters.get("currency", []):
                if c in r.get("datagetter_aggregates", {}).get("currencies", {}).keys():
                    choose_this = True
            if not choose_this:
                continue

        if filters.get("filetype"):
            if r.get('datagetter_metadata', {}).get("file_type") not in filters["filetype"]:
                continue

        if filters.get("fields"):
            this_fields = list(r.get("datagetter_coverage", {}).keys())
            choose_this = False
            for f in filters.get("fields", []):
                if f in this_fields:
                    choose_this = True
            if not choose_this:
                continue


        if p not in reg_:
            reg_[p] = []

        reg_[p].append(r)

    return reg_

def message_box(title, contents, error=False):
    border = 'b--red' if error else 'b--black'
    background = 'bg-red' if error else 'bg-black'
    if isinstance(contents, str):
        contents_div = dcc.Markdown(
            className='f6 f5-ns lh-copy mv0', children=contents)
    else:
        contents_div = html.P(
            className='f6 f5-ns lh-copy mv0', children=contents),

    return html.Div(className='center hidden ba mb4 {}'.format(border), children=[
        html.H1(className='f4 white mv0 pv2 ph3 ostrich {}'.format(background),
                children=title),
        html.Div(className='pa3', children=contents_div),
    ])


def pluralize(string, count):
    p = inflect.engine()
    return p.plural(string, count)

def format_currency(amount, currency='GBP', humanize_=True, int_format="{:,.0f}"):
    if humanize_:
        amount_str = humanize.intword(amount).split(" ")
        if len(amount_str) == 2:
            return (
                babel.numbers.format_currency(
                    float(amount_str[0]),
                    currency,
                    format="¤#,##0.0",
                    currency_digits=False,
                    locale='en_UK'
                ), 
                amount_str[1]
            )

    return (
        babel.numbers.format_currency(
            amount,
            currency,
            format="¤#,##0",
            currency_digits=False,
            locale='en_UK'
        ), 
        ""
    )