# -*- coding: utf-8 -*-
import dash

THREESIXTY_STATUS_JSON = 'https://storage.googleapis.com/datagetter-360giving-output/branch/master/status.json'
THREESIXTY_STATUS_LOCATION = 'data/status.json'

app = dash.Dash(__name__)
app.config.suppress_callback_exceptions = True



## FETCHING STATUS FILE ##
import requests
import json
import dateutil.parser
import datetime


def fetch_status_file(url=THREESIXTY_STATUS_JSON, location=THREESIXTY_STATUS_LOCATION):
    """
    Download the json status file and save to disk
    """
    with open(location, 'w') as reg_file:
        reg = requests.get(url)
        json.dump(reg.json(), reg_file, indent=4)


def get_status_file(location=THREESIXTY_STATUS_LOCATION):
    """
    Open the status file from disk and turn into list

    Convert any datetime fields into datetime objects
    """
    with open(location, 'r') as reg_file:
        reg = json.load(reg_file)

        # convert date/datetime fields
        datetime_fields = [ 
            # format YYYY-MM-DDTHH:MM+00:00:
            ['modified'], 
            ['datagetter_metadata', 'datetime_downloaded'], 
            # format YYYY-MM-DD:
            ['issued'],
            ['datagetter_aggregates', 'max_award_date'],
            ['datagetter_aggregates', 'min_award_date'],
        ]
        for reg_entry in reg:
            for field in datetime_fields:
                if len(field) == 2:
                    val = reg_entry.get(field[0], {}).get(field[1])
                    if val:
                        reg_entry[field[0]][field[1]] = dateutil.parser.parse(
                            val, ignoretz=True)
                elif len(field) == 1:
                    val = reg_entry.get(field[0])
                    if val:
                        reg_entry[field[0]] = dateutil.parser.parse(
                            val, ignoretz=True)

        return reg


def get_registry_by(by='publisher', location=THREESIXTY_STATUS_LOCATION):
    """
    Turn registry list into a dictionary ordered by a particular key
    """
    reg = get_status_file(location)
    reg_ = {}
    reg_stats = {}
    for r in reg:
        if by == 'file':
            key = r.get('identifier')
        else:
            key = r.get('publisher', {}).get('name')
        if key not in reg_:
            reg_[key] = []
            reg_stats[key] = {
                "files": 0,
                "count": 0,
                "currencies": [],
                "distinct_funding_org_identifier": [],
                "recipient_org_identifier_prefixes": {},
                "max_award_date": None,
                "min_award_date": None,
                "license": {},
            }
        reg_[key].append(r)
    return reg_


def get_registry_currencies(reg):
    currencies = set()

    # by publisher (etc)
    if isinstance(reg, dict):
        for reg_pub in reg.values():
            for r in reg_pub:
                for currency in r.get('datagetter_aggregates', {}).get('currencies', {}):
                    currencies.add(currency)

    # raw list from status.json
    elif isinstance(reg, list):
        for r in reg:
            for currency in r.get('datagetter_aggregates', {}).get('currencies', {}):
                currencies.add(currency)

    return list(currencies)


def normalize_data(data):
    total = sum(data)
    return [d / float(total) for d in data]


def get_buttons(data, title=''):
    return [
        {
            'label': 'By {}'.format(d["name"]),
            'method': 'update',
            'args': [
                {'visible': [i == j for j in range(len(data))]},
                # {'title': '{} by {}'.format(title, d["name"])},
            ]
        }
        for i, d in enumerate(data)
    ]

def flatten_list(l):
    """
    From: https://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python
    """
    return [item for sublist in l for item in sublist]


## SERVER ##
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

app.css.append_css({
    "external_url": "https://unpkg.com/tachyons@4.10.0/css/tachyons.min.css"
})

app.layout = html.Div(id='registry-container', className='avenir pa4', children=[
    html.H1(className='f1 lh-solid', children='Registry Dashboard'),
    html.Div(id='registry-filters', className='fl w-25 pa2', children=[
        'Test'
    ]),
    html.Div(id='registry-charts', className='fl w-75 pa2'),
    dcc.Graph(id='dummy-graph', style={'display': 'none'}),
])



@app.callback(Output('registry-charts', 'children'),
                [Input('registry-filters', 'children')])
def get_registry_charts(filters):
    reg = get_registry_by('publisher')
    reg_file = get_registry_by('file')
    currencies = get_registry_currencies(reg)

    return [
        html.Div([
            html.H2('Grants by publisher'),
            grants_treemap(reg)
        ], className='fl w-50'),
        
        html.Div([

            html.H2('Currencies used'),
            by_currency(reg, currencies),
        ], className='fl w-50'),

        html.Div([
            html.H2('Years covered'),
            by_year(reg),
            html.Div(html.Pre(id='years-covered-selected'))
        ], className='fl w-50'),

        html.Div([
            html.H2('Number of grants'),
            by_number_of_grants(reg),
        ], className='fl w-50'),

        html.Div([
            html.H2('Year issued'),
            by_date_issued(reg),
        ], className='fl w-50'),

    ]


### Charts ####

import squarify

CHART_CONFIG = {
                'scrollZoom': False,
                'modeBarButtonsToRemove': ['sendDataToCloud', 'zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d',
                                           'autoScale2d', 'resetScale2d', 'hoverClosestCartesian',
                                           'hoverCompareCartesian', 'toggleSpikelines', 'lasso2d']
            }


def grants_treemap(reg, sort_by='grants'):

    x = 0.
    y = 0.
    width = 100.
    height = 100.

    pub_sums = [{
        "publisher": pub, 
        "grants": sum([
            r.get('datagetter_aggregates', {}).get('count', 0.0000001) for r in pub_reg
        ]),
        "grant_amount_GBP": sum([
            r.get('datagetter_aggregates', {}).get('currencies', {}).get('GBP', {}).get('total_amount', 0.0000001) for r in pub_reg
        ])
    } for pub, pub_reg in reg.items()]

    shapes = {}
    annotations = {}
    hovertext = {}
    publishers = {}
    traces = []

    for f in ['grants', 'grant_amount_GBP']:
        values = sorted(pub_sums, key=lambda x: x.get(f, 0), reverse=True)
        publishers[f] = [p["publisher"] for p in values]
        values = [p[f] for p in values]
    
        normed = squarify.normalize_sizes(values, width, height)
        rects = squarify.squarify(normed, x, y, width, height)

        colours = ['rgb(166,206,227)', 'rgb(31,120,180)', 'rgb(178,223,138)',
                        'rgb(51,160,44)', 'rgb(251,154,153)', 'rgb(227,26,28)']
        shapes[f] = []
        annotations[f] = []
        hovertext[f] = []

        for counter, r in enumerate(rects):
            shapes[f].append(
                dict(
                    type='rect',
                    x0=r['x'],
                    y0=r['y'],
                    x1=r['x']+r['dx'],
                    y1=r['y']+r['dy'],
                    line=dict(width=2),
                    fillcolor=colours[counter % len(colours)]
                )
            )
            if counter < 4:
                annotations[f].append(
                    dict(
                        x=r['x']+(r['dx']/2),
                        y=r['y']+(r['dy']/2),
                        text=publishers[f][counter],
                        showarrow=False
                    )
                )

            hovertext[f].append(
                "{} ({:,.0f})".format(publishers[f][counter], values[counter])
            )

        # For hover text
        traces.append(dict(
            x=[r['x']+(r['dx']/2) for r in rects],
            y=[r['y']+(r['dy']/2) for r in rects],
            text=hovertext,
            mode='none',
            hoverinfo='text',
            type='scatter',
            # visible=(f == 'grants')
        ))

    layout = dict(
        height=700,
        width=700,
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        shapes=shapes[sort_by],
        annotations=annotations[sort_by],
        hovermode='closest',
        updatemenus=list([
            dict(buttons=[
                    {
                        'label': "by number of grants",
                        "method": 'update',
                        "args": [
                            {'visible': [True, False]},
                            {'shapes': shapes['grants'],
                            'annotations': annotations['grants']},
                        ]
                    },
                    {
                        'label': "by grant amount",
                        "method": 'update',
                        "args": [
                            {'visible': [False, True]},
                            {'shapes': shapes['grant_amount_GBP'],
                            'annotations': annotations['grant_amount_GBP']},
                        ]
                    }
                ],
                y = 1.0,
                yanchor = 'top',
            )
        ])
    )

    return dcc.Graph(id='grants-treemap',
                     figure={
                        'data': traces,
                        'layout': layout
                     },
                     config=CHART_CONFIG
                     )

def by_currency(reg, currencies):

    def publisher_uses_currency(publisher, currency):
        for r in publisher:
            if currency in r.get('datagetter_aggregates', {}).get('currencies', {}).keys():
                return True
        return False

    data = [
        {
            'x': currencies,
            'y': [
                sum([1 if publisher_uses_currency(pub, currency)
                     else 0 for pub in reg.values()])
                for currency in currencies
            ],
            'type': 'bar',
            'name': 'Publishers',
            'visible': True,
        },
        {
            'x': currencies,
            'y': [
                sum([
                    sum([1 if currency in r.get('datagetter_aggregates', {}).get(
                        'currencies', {}).keys() else 0 for r in pub])
                    for pub in reg.values()])
                for currency in currencies
            ],
            'type': 'bar',
            'name': 'Files',
            'visible': False,
        },
        {
            'x': currencies,
            'y': [
                sum([
                    sum([r.get('datagetter_aggregates', {}).get(
                        'currencies', {}).get(currency, {}).get('count', 0) for r in pub])
                    for pub in reg.values()])
                for currency in currencies
            ],
            'type': 'bar',
            'name': 'Grants',
            'visible': False,
        }
    ]

    return dcc.Graph(id='currencies-used',
        figure={
            'data': data,
            'layout': {
                'title': 'Currency used',
                'updatemenus': [
                    {   
                        'active': 0,
                        'buttons': get_buttons(data),
                        'y': 1.0,
                        'yanchor': 'top',
                    }
                ]
            },
        },
        config=CHART_CONFIG
    )


def by_date_issued(reg):
    issued = flatten_list([[r.get('issued') for r in reg_pub if r.get('issued')] for reg_pub in reg.values()])
    issued_count = flatten_list([[
        r.get('datagetter_aggregates', {}).get('count', 0)
        for r in reg_pub if r.get('issued')] for reg_pub in reg.values()])
    issued_amount = flatten_list([[
        r.get('datagetter_aggregates', {}).get('currencies', {}).get('GBP', {}).get('total_amount', 0)
        for r in reg_pub if r.get('issued')] for reg_pub in reg.values()])
    issued_pub = [min([r.get('issued') for r in reg_pub if r.get('issued')]) for reg_pub in reg.values()]
    min_issued = min(issued)
    max_issued = max(issued)

    data = [
        {
            'x': issued_pub,
            'type': 'histogram',
            'name': 'Publishers',
            'visible': True,
        },
        {
            'x': issued,
            'type': 'histogram',
            'name': 'Files',
            'visible': False,
        },
        {
            'x': issued,
            'y': issued_count,
            'histfunc': 'sum',
            'type': 'histogram',
            'name': 'Grant count',
            'visible': False,
        },
        {
            'x': issued,
            'y': issued_amount,
            'histfunc': 'sum',
            'type': 'histogram',
            'name': 'Grant amount',
            'visible': False,
        },
    ]

    return dcc.Graph(id='files-issued',
                     figure={
                         'data': data,
                         'layout': {
                             'title': 'By date published',
                             'updatemenus': [
                                 {
                                     'active': 0,
                                     'buttons': get_buttons(data)
                                 }
                             ]
                         }
                     },
                     config=CHART_CONFIG
                     )

def by_year(reg):

    default_year = datetime.datetime.now()

    max_year = max([
        max([r.get('datagetter_aggregates', {}).get('max_award_date', default_year).year for r in reg_pub]) 
        for reg_pub in reg.values()])
    min_year = min([
        min([r.get('datagetter_aggregates', {}).get('min_award_date', default_year).year for r in reg_pub]) 
        for reg_pub in reg.values()])
    years = list(range(min_year, max_year))

    def year_in_file(year, max_award_date, min_award_date):
        return max_award_date is not None and min_award_date is not None and \
            year <= max_award_date.year and year >= min_award_date.year

    def year_in_publisher(pub, year):
        for r in pub:
            if year_in_file(year, 
                            r.get('datagetter_aggregates', {}).get('max_award_date'), 
                            r.get('datagetter_aggregates', {}).get('min_award_date')):
                return True

    data = [
        {
            'x': years,
            'y': [
                sum([1 if year_in_publisher(pub, year)
                     else 0 for pub in reg.values()])
                for year in years
            ],
            'type': 'line',
            'name': 'Publishers',
            'visible': True,
        },
        {
            'x': years,
            'y': [
                sum([
                    sum([1 if year_in_file(year,
                                           r.get('datagetter_aggregates', {}).get('max_award_date'),
                                           r.get('datagetter_aggregates', {}).get('min_award_date')) else 0 for r in pub])
                    for pub in reg.values()])
                for year in years
            ],
            'type': 'line',
            'name': 'Files',
            'visible': False,
        },
        {
            'x': years,
            'y': [
                sum([
                    sum([r.get('datagetter_aggregates', {}).get('count', 0) if year_in_file(year,
                                           r.get('datagetter_aggregates', {}).get(
                                               'max_award_date'),
                                           r.get('datagetter_aggregates', {}).get('min_award_date')) else 0 for r in pub])
                    for pub in reg.values()])
                for year in years
            ],
            'type': 'line',
            'name': 'Grants',
            'visible': False,
        }
    ]

    return dcc.Graph(id='years-covered',
        figure={
            'data': data,
            'layout': {
                'title': 'Years covered',
                'xaxis': {
                    'fixedrange': True
                },
                'yaxis': {
                    'fixedrange': True
                },
                'updatemenus': [
                    {   
                        'active': 0,
                        'buttons': get_buttons(data)
                    }
                ]
            },
        },
        config=CHART_CONFIG
    )

@app.callback(Output('years-covered-selected', 'children'),
              [Input('years-covered', 'selectedData')])
def get_selected_years(points):
    if points:
        print(points)
        years = [x.get('x') for x in points.get('points', [])]
        return json.dumps(years, indent=4)

def by_number_of_grants(reg):

    data = [
        {
            'x': [
                sum([
                    r.get('datagetter_aggregates', {}).get('count') for r in pub 
                    if r.get('datagetter_aggregates', {}).get('count')
                ]) for pub in reg.values()
            ],
            'type': 'histogram',
            'name': 'Publishers',
            'visible': True,
        },
        {
            'x': flatten_list([
                [
                    r.get('datagetter_aggregates', {}).get('count') for r in pub
                    if r.get('datagetter_aggregates', {}).get('count')
                ] for pub in reg.values()
            ]),
            'type': 'histogram',
            'name': 'Files',
            'visible': False,
        },
    ]

    return dcc.Graph(id='number-of-grants',
                     figure={
                         'data': data,
                         'layout': {
                             'title': 'Number of grants',
                             'updatemenus': [
                                 {
                                     'active': 0,
                                     'buttons': get_buttons(data)
                                 }
                             ]
                         }
                     },
                     config=CHART_CONFIG
                     )


if __name__ == '__main__':
    app.run_server(debug=True)
