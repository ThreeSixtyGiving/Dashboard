import hashlib
import os
import json
import io
import datetime
import dateutil.parser

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

import babel.numbers
import humanize
import requests_cache

from utils import get_registry_by_publisher, get_registry, pluralize, format_currency, message_box


# THREESIXTY_STATUS_JSON = 'https://storage.googleapis.com/datagetter-360giving-output/branch/master/status.json'
THREESIXTY_STATUS_JSON = 'https://storage.googleapis.com/datagetter-360giving-output/branch/11-coverage/coverage.json'
THREESIXTY_STATUS_LOCATION = 'data/status.json'
FILE_TYPES = {
    "xlsx": ("Excel", "Microsoft Excel"),
    "xls": ("Excel", "Microsoft Excel (pre 2007)"),
    "csv": ("CSV", "Comma Separated Values"),
    "json": ("JSON", "JSON is a structured file format"),
}

app = dash.Dash(__name__)
# app.config.suppress_callback_exceptions = True

app.css.append_css({
    "external_url": "https://unpkg.com/tachyons@4.10.0/css/tachyons.min.css"
})
app.css.append_css({
    "external_url": "https://fonts.googleapis.com/css?family=Source+Sans+Pro%3A400%2C400i%2C600%2C700&ver=4.9.8"
})

cache_expiry = 60*60 # one hour in seconds
requests_cache.install_cache(
    backend='sqlite',
    expire_after=cache_expiry,
    allowable_methods=('GET', 'HEAD',),
)

app.title = '360Giving Insights'

def layout_wrapper(contents):
    return html.Div(children=[
        html.Div(className='pv2 ph4', children=[
            dcc.Location(id='url', refresh=False),
            html.Div(id="page-header", className='cf mv3 pv3', children=[
                html.H1(className='ostrich', children=[
                    dcc.Link(href='/', className='link threesixty-red', children=[
                        html.Img(className='mw4point5',
                                src='/assets/360logo-text.png')
                    ]),
                ]),
            ]),
            html.Div(id='page-content', className='cf', children=contents),
        ]),
        html.Footer(className='pa3 bg-threesixty-grey cf', children=[
            html.A(className='link fl', href='http://www.threesixtygiving.org/', children=[
                html.Img(className='mw4', src='/assets/360logo-white.png'),
            ]),
            html.Nav(className='fr', children=[
                html.Ul(className='list ttu b white f4 cf', children=[
                    html.Li(className='fl pl3', children=[
                        html.A(className='white link underline-hover',
                            href='http://www.threesixtygiving.org/contact/',
                            children='Contact'),
                    ]),
                    html.Li(className='fl pl3', children=[
                        html.A(className='white link underline-hover',
                            href='http://www.threesixtygiving.org/support/',
                            children='Support'),
                    ]),
                    html.Li(className='fl pl3', children=[
                        html.A(className='white link underline-hover',
                            href='http://www.threesixtygiving.org/news-2/',
                            children='News'),
                    ]),
                    html.Li(className='fl pl3', children=[
                        html.A(className='white link underline-hover',
                            href='http://www.threesixtygiving.org/support/standard/',
                            children='360Giving Standard'),
                    ]),
                ]),
                html.P(className='white f4 tr mt3', children=[
                    html.A(className='white link underline-hover b br b--white pr3 mr3',
                        href='tel:+442037525775',
                        children='020 3752 5775'),
                    html.A(className='white link underline-hover',
                        href='mailto:info@threesixtygiving.org',
                        children='info@threesixtygiving.org'),
                ])
            ]),
        ]),
        html.Footer(className='pa3 bg-threesixty-grey cf bt b--threesixty-dark-green', children=[
            html.Div(className='cf', children=[
                html.P(className='white fl ma0', children=[
                    '360Giving is a company limited by guarantee ',
                    html.A(className='white link underline pointer',
                        href='https://beta.companieshouse.gov.uk/company/09668396',
                        children='09668396'),
                    ' and a registered charity ',
                    html.A(className='white link underline pointer',
                        href='http://beta.charitycommission.gov.uk/charity-details/?regid=1164883&subid=0',
                        children='1164883'),
                ]),
                html.A(className='white ostrich ttu fr f4 link',
                    href='https://us10.campaign-archive.com/home/?u=216b8b926250184f90c7198e8&id=91870dde44',
                    children='Sign up to our newsletter'),
            ]),
            html.Nav(className='', children=[
                html.Ul(className='list threesixty-mid-grey cf mt3 pl0', children=[
                    html.Li(className='fl pr2 mr2 br b--threesixty-mid-grey', children=[
                        html.A(className='threesixty-mid-grey link underline-hover',
                            href='http://www.threesixtygiving.org/privacy/',
                            children='Privacy notice'),
                    ]),
                    html.Li(className='fl pr2 mr2 br b--threesixty-mid-grey', children=[
                        html.A(className='threesixty-mid-grey link underline-hover',
                            href='http://www.threesixtygiving.org/terms-conditions/',
                            children='Terms & Conditions'),
                    ]),
                    html.Li(className='fl pr2 mr2 br b--threesixty-mid-grey', children=[
                        html.A(className='threesixty-mid-grey link underline-hover',
                            href='http://www.threesixtygiving.org/cookie-policy/',
                            children='Cookie Policy'),
                    ]),
                    html.Li(className='fl pr2 mr2 br b--threesixty-mid-grey', children=[
                        html.A(className='threesixty-mid-grey link underline-hover',
                            href='http://www.threesixtygiving.org/take-down-policy/',
                            children='Take Down Policy'),
                    ]),
                    html.Li(className='fl pr2 mr2 br b--threesixty-mid-grey', children=[
                        html.A(className='threesixty-mid-grey link underline-hover',
                            href='https://creativecommons.org/licenses/by/4.0/',
                            children='License'),
                    ]),
                    html.Li(className='fl pr2 mr2 br b--threesixty-mid-grey', children=[
                        'Built by ',
                        html.A(className='threesixty-mid-grey link underline',
                            href='https://drkane.co.uk/',
                            children='David Kane'),
                        ' using ',
                        html.A(className='threesixty-mid-grey link underline',
                            href='https://dash.plot.ly/',
                            children='Dash by Plotly'),
                    ]),
                    html.Li(className='fl', children=[
                        html.A(className='threesixty-mid-grey link underline-hover',
                            href='https://github.com/ThreeSixtyGiving/explorer',
                            children='Github'),
                    ]),
                ])
            ]),
        ]),
    ])

app.layout = layout_wrapper(html.Div(id="status-container", className='', children=[
    html.Div(className="fl w-25-l w-100 pa2-l", children=[
        message_box(title="Filter data", contents=[
            html.Form(className='', children=[
                html.Div(className='cf mv3', children=[
                    html.Div(className='', children=[
                        dcc.Input(id='status-search', placeholder='Search',
                                  type='text', className='w-100 pa2'),
                        html.I(className='search icon'),
                    ]),
                ]),
                html.Div(className='cf mv3', children=[
                    html.Label('Licence'),
                    dcc.Dropdown(id='status-licence', multi=True, options=[]),
                ]),
                html.Div(className='cf mv3', children=[
                    html.Label('Currency'),
                    dcc.Dropdown(id='status-currency', multi=True, options=[]),
                ]),
                html.Div(className='cf mv3', children=[
                    html.Label('File type'),
                    dcc.Dropdown(id='status-file-type', multi=True, options=[]),
                ]),
                html.Div(className='cf mv3', children=[
                    html.Label('Last updated'),
                    dcc.Dropdown(id='status-last-modified', options=[
                        {'label': 'All publishers', 'value': '__all'},
                        {'label': 'In the last month', 'value': 'lastmonth'},
                        {'label': 'In the last 6 months', 'value': '6month'},
                        {'label': 'In the last year', 'value': '12month'},
                    ]),
                ]),
                html.Div(className='cf mv3', children=[
                    html.Label('Fields'),
                    dcc.Dropdown(id='status-fields', multi=True, options=[]),
                ]),
            ]),
        ]),
    ]),
    html.Div(className="fl w-75-l w-100 pa2-l", children=[
        html.Div(id='status-rows', children=[], className=''),
    ]),
]))

@app.callback([Output('status-licence', 'options'),
               Output('status-fields', 'options'),
               Output('status-currency', 'options'),
               Output('status-file-type', 'options')],
              [Input('status-container', 'children')])
def get_options(_):
    reg = get_registry(THREESIXTY_STATUS_JSON)
    return_options = []

    # get licences
    licenses = {}
    for r in reg:
        if r.get('license') and r.get('license') in licenses:
            continue
        licenses[r.get('license')] = r.get('license_name')
    return_options.append([{
        "label": v,
        "value": k
    } for k, v in licenses.items()])

    # get fields
    fields = set()
    for r in reg:
        for f, field in r.get("datagetter_coverage", {}).items():
            if field.get("standard"):
                fields.add(f)
    return_options.append([{
        "label": f,
        "value": f
    } for f in sorted(list(fields))])

    # get currencies
    currencies = set()
    for r in reg:
        for c in r.get("datagetter_aggregates", {}).get('currencies', {}).keys():
            currencies.add(c)
    return_options.append([{
        "label": "{} [{}]".format(babel.numbers.get_currency_name(c), c),
        "value": c
    } for c in currencies])

    # get filetypes
    filetypes = {}
    for r in reg:
        filetype = r.get('datagetter_metadata', {}).get("file_type")
        filetypes[filetype] = FILE_TYPES.get(filetype, (filetype, "Unknown"))
    return_options.append([{
        "label": "{} ({})".format(v[0], v[1]),
        "value": k
    } for k, v in filetypes.items()])

    return return_options


@app.callback(Output('status-rows', 'children'),
              [Input('status-search', 'value'),
               Input('status-licence', 'value'),
               Input('status-last-modified', 'value'),
               Input('status-currency', 'value'),
               Input('status-file-type', 'value'),
               Input('status-fields', 'value')])
def update_status_container(search, licence, last_modified, currency, filetype, fields):
    reg = get_registry_by_publisher(filters={
        "search": search,
        "licence": licence,
        "last_modified": last_modified,
        "currency": currency,
        "filetype": filetype,
        "fields": fields
    }, reg_url=THREESIXTY_STATUS_JSON)

    file_count = sum([len(pub_reg) for pub, pub_reg in reg.items()])
    rows = [
        html.Div(className='w-100 f3', children=[
            html.Span(className="", children=[
                html.Strong(len(reg)),
                ' ' + pluralize("publisher", len(reg))
            ]),
            html.Span(className='mh2', children='·'),
            html.Span(className="", children=[
                html.Strong(file_count),
                ' ' + pluralize("file", file_count)
            ]),
        ])
    ]
    for pub, pub_reg in reg.items():
        rows.append(
            html.Div(className='br2 ba dark-gray b--black-10 mv4 w-100 center mb4', children=[
                html.Div(className='w-100 cf pa3', children=[
                    html.A(className='f3 link black b',
                           href=pub_reg[0].get("publisher", {}).get("website"),
                           target='_blank', children=[
                               pub_reg[0].get("publisher", {}).get("name")
                           ]),
                    html.Img(className='fr mw5', src=pub_reg[0].get(
                        "publisher", {}).get("logo"), style={'max-height': '8rem'}),
                ]),
                html.Div(className='content', children=[
                    html.Div(className='flex ph3', children=([
                        to_statistic(len(pub_reg), pluralize("file", len(pub_reg)))
                    ] + get_publisher_stats(pub_reg, separator=html.Span('·')) if len(pub_reg)>1 else [])
                    ),
                    html.Div(className='description', children=[
                        file_row(v, len(pub_reg)) for v in pub_reg
                    ])
                ])
            ])
        )
    return rows

def file_row(v, files=1):
    style = {"border-top": '0'} if files > 1 else {}

    validity = {
        'valid': {'class': '', 'icon': None, 'messages': {
            'positive': 'Valid data', 'negative': 'Data invalid'
        }, 'message': 'Validity unknown'},
        'downloads': {'class': '', 'icon': None, 'messages': {
            'positive': 'Download link working', 'negative': 'Download link broken'
        }, 'message': 'Download link not checked'},
        'acceptable_license': {'class': '', 'icon': None, 'messages': {
            'positive': 'Licensed for reuse', 'negative': 'Licence doesn\'t allow reuse'
        }, 'message': 'Unknown licence'},
    }
    for i in validity:
        if v.get('datagetter_metadata', {}).get(i)==True:
            validity[i]['class'] = 'positive'
            validity[i]['icon'] = html.Span(className='green mr1', children='✓')
            validity[i]['message'] = validity[i]['messages']['positive']
            validity[i]['color'] = 'green'
        elif v.get('datagetter_metadata', {}).get(i)==False:
            validity[i]['class'] = 'positive'
            validity[i]['icon'] = html.Span(className='red mr1', children='✕')
            validity[i]['message'] = validity[i]['messages']['negative']
            validity[i]['color'] = 'red'

    file_type = v.get("datagetter_metadata", {}).get("file_type", "")
    file_type = FILE_TYPES.get(file_type.lower(), (file_type, "Unknown"))

    return html.Div(className='bt pa3 b--black-10', children=[
        html.Div(className='content', children=[
            html.A(
                children=get_license_badge(v.get('license'), v.get("license_name")),
                href=v.get('license'), 
                target='_blank',
                className='fr',
            ),
            html.A(
                v.get("title"),
                href=v.get('distribution', [{}])[0].get('accessURL'),
                target="_blank",
                className='f4 link black b'
            ),
            html.Div(className='gray', children=[
                html.Span(get_date_range(v)),
                html.Span(className='mh1', children='·'),
                html.Span(', '.join(
                    [babel.numbers.get_currency_name(k) for k in v.get("datagetter_aggregates", {}).get("currencies", {})]
                )),
                html.Span(className='mh1', children='·'),
                html.Span([
                    'Last modified ',
                    html.Time(dateTime=v.get("modified"), children=[
                    humanize.naturaldelta(
                        datetime.datetime.now() - dateutil.parser.parse(v.get("modified"), ignoretz=True)
                    )]),
                    ' ago'
                ]),
            ]),
            html.Div(className='mt3', children=[
                html.Div(className='flex', children=get_file_stats(v, as_statistic=True),)
            ]),
        ]),
        html.Div(className='pb3', children=[
            html.Span(
                [
                    validity[i]['icon'],
                    validity[i]['message']
                ],
                className=validity[i]['class'] + ' mr3',
                style={
                    "color": validity[i].get('color')
                }
            )
            for i in validity
        ]),
        html.Div(className='mv3', children=[
            html.A(
                'Download from publisher (in {} format)'.format(file_type[0]),
                href=v.get('distribution', [{}])[0].get('downloadURL'),
                className='link white dim bg-threesixty-red pa2',
                title=file_type[1],
            ),
        ]),
        html.Div(className='mv3 f7 gray', children=[html.Strong("Fields used")] + [
            html.Span(f, className="ml2") for f, field in v.get("datagetter_coverage", {}).items()
        ])
    ])

def to_statistic(val, label):
    return html.Div([
        html.Strong(val, className='f3 b', style={}),
        html.Div(label, className=''),
    ], className='pa3 tc', style={})

def get_file_stats(v, separator=None, as_statistic=True):
    stats = []
    agg = v.get("datagetter_aggregates")
    if agg is None:
        return stats

    count = agg.get("count", 0)
    stats.append(to_statistic(
        humanize.intcomma(count), 
        pluralize("grant", count)
    ))

    recip = agg.get("distinct_recipient_org_identifier_count", 0)
    if recip > 0:
        stats.append(to_statistic(
            humanize.intcomma(recip),
            pluralize("recipient", recip),
        ))

    funders = agg.get("distinct_funding_org_identifier_count", 0)
    if funders > 1:
        stats.append(to_statistic(
            humanize.intcomma(funders),
            pluralize("funder", funders),
        ))
        

    if len(agg.get("currencies", {}))==1:
        for c in agg["currencies"]:
            cur = format_currency(agg["currencies"][c].get("total_amount", 0), c)
            stats.append(to_statistic(cur[0], cur[1]))
            

    if separator:
        result = [separator] * (len(stats) * 2 - 1)
        result[0::2] = stats
        return result
    
    return stats


def get_publisher_stats(pub_reg, **kwargs):
    data = {
        "count": 0,
        "currencies": {}
    }

    for r in pub_reg:
        data["count"] += r.get("datagetter_aggregates", {}).get("count", 0)
        for c, cagg in r.get("datagetter_aggregates", {}).get("currencies", {}).items():
            if c not in data["currencies"]:
                data["currencies"][c] = {"total_amount": 0}
            data["currencies"][c]["total_amount"] += cagg.get("total_amount", 0)

    return get_file_stats({"datagetter_aggregates": data}, **kwargs)

def get_date_range(v):
    agg = v.get("datagetter_aggregates")
    if agg is None:
        return None

    max_award_date = datetime.datetime.strptime(agg.get("max_award_date", None), "%Y-%m-%d")
    min_award_date = datetime.datetime.strptime(agg.get("min_award_date", None), "%Y-%m-%d")
    if max_award_date and min_award_date:
        min_award_ym = min_award_date.strftime("%b %Y")
        max_award_ym = max_award_date.strftime("%b %Y")
        if min_award_ym == max_award_ym:
            return max_award_ym
        else:
            return (min_award_ym + " to " + max_award_ym)

def get_license_badge(url, name):
    if "creativecommons.org/licenses" in url:
        components = ['cc'] + url.split("/")[-3].split("-")
        return [
            html.Img(src="https://mirrors.creativecommons.org/presskit/icons/{}.png".format(c.lower()), 
                title=name, style={'max-height': '24px', 'margin-right': '2px'})
            for c in components
        ]

    if "creativecommons.org/publicdomain" in url:
        components = ['publicdomain'] + url.split("/")[-3].split("-")
        return [
            html.Img(src="https://mirrors.creativecommons.org/presskit/icons/{}.png".format(c.lower()), 
                title=name, style={'max-height': '24px', 'margin-right': '2px'})
            for c in components
        ]

    if "creativecommons.org" in url:
        badge_url = url.replace("creativecommons.org/licenses", "i.creativecommons.org/l")
        badge_url = badge_url.replace("creativecommons.org/publicdomain", "i.creativecommons.org/p")
        badge_url = badge_url + "88x31.png"
        return [html.Img(src=badge_url, title=name, style={'max-height': '24px'})]

    if "open-government-licence" in url:
        badge_url = "http://www.nationalarchives.gov.uk/images/infoman/ogl-symbol-41px-retina-black.png"
        return [html.Img(src=badge_url, title=name, style={'max-height': '24px'})]

    if "http://www.opendefinition.org/licenses/odc-pddl" == url:
        return [html.Div('ODC PDDL', title=name, className='')]
    
    return name


if __name__ == '__main__':
    app.run_server(debug=True)
