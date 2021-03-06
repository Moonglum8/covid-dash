import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

import pandas as pd
import io
import os

from flask_caching import Cache

from typing import Iterable, Dict, Union, List
from json import dumps
from requests import get
from http import HTTPStatus


StructureType = Dict[str, Union[dict, str]]
FiltersType = Iterable[str]
APIResponseType = Union[List[StructureType], str]


def get_paginated_dataset(filters: FiltersType, structure: StructureType,
                          as_csv: bool = False) -> APIResponseType:
    """
    Extracts paginated data by requesting all of the pages
    and combining the results.

    Parameters
    ----------
    filters: Iterable[str]
        API filters. See the API documentations for additional
        information.

    structure: Dict[str, Union[dict, str]]
        Structure parameter. See the API documentations for
        additional information.

    as_csv: bool
        Return the data as CSV. [default: ``False``]

    Returns
    -------
    Union[List[StructureType], str]
        Comprehensive list of dictionaries containing all the data for
        the given ``filters`` and ``structure``.
    """
    endpoint = "https://api.coronavirus.data.gov.uk/v1/data"

    api_params = {
        "filters": str.join(";", filters),
        "structure": dumps(structure, separators=(",", ":")),
        "format": "json" if not as_csv else "csv"
    }

    data = list()

    page_number = 1

    while True:
        # Adding page number to query params
        api_params["page"] = page_number

        response = get(endpoint, params=api_params, timeout=100)
        print(response.status_code)
        if response.status_code >= HTTPStatus.BAD_REQUEST:
            raise RuntimeError(f'Request failed: {response.text}')
        elif response.status_code == HTTPStatus.NO_CONTENT:
            break

        if as_csv:
            csv_content = response.content.decode()

            # Removing CSV header (column names) where page
            # number is greater than 1.
            if page_number > 1:
                data_lines = csv_content.split("\n")[1:]
                csv_content = str.join("\n", data_lines)

            data.append(csv_content.strip())
            page_number += 1
            continue

        current_data = response.json()
        page_data: List[StructureType] = current_data['data']

        data.extend(page_data)

        # The "next" attribute in "pagination" will be `None`
        # when we reach the end.
        if current_data["pagination"]["next"] is None:
            break

        page_number += 1

    if not as_csv:
        return data

    # Concatenating CSV pages
    return str.join("\n", data)



query_filters = [
    f"areaType=region"
]

query_structure_cases = {
    "date": "date",
    "name": "areaName",
    "code": "areaCode",
    "daily": "newCasesBySpecimenDate",
    "cumulative": "cumCasesBySpecimenDate"
}

query_structure_deaths = {
    "date": "date",
    "name": "areaName",
    "code": "areaCode",
    "daily": "newDeaths28DaysByDeathDate",
    "cumulative": "cumDeaths28DaysByDeathDate"
}


CACHE_CONFIG = {
    # 'CACHE_TYPE': 'redis',
    # 'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_THRESHOLD': 5
}

def get_cases():
    csv_data = get_paginated_dataset(query_filters, query_structure_cases, as_csv=True)
    df = pd.read_csv(io.StringIO(csv_data), index_col='date', parse_dates=True)
    print(df)
    return df

def get_deaths():
    csv_data = get_paginated_dataset(query_filters, query_structure_deaths, as_csv=True)
    df = pd.read_csv(io.StringIO(csv_data), index_col='date', parse_dates=True)
    print(df)
    return df

def set_cache():
    cases = get_cases()
    deaths = get_deaths()
    cache.set('cases', cases)
    cache.set('deaths', deaths)
    return cases, deaths

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

def plotly_cases(area_name):
    cases = cache.get('cases')
    last_date_cases = cases.index.max()
    total_cases = cases[cases['name'] == area_name]['daily'].resample('d').sum()
    total_cases_rolling = total_cases.rolling(window=7).mean()
    peak_cases = total_cases_rolling.idxmax()
    peak_cases_from_today = last_date_cases - peak_cases
    peak = str(peak_cases_from_today.days)
    last_date_cases = last_date_cases.strftime("%d %B %Y")
    peak_cases = peak_cases.strftime("%d %B %Y")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=total_cases.index, y=total_cases,
                        name='daily cases',
                        marker_color='blue'))
    fig.add_trace(go.Scatter(x=total_cases_rolling.index, y=total_cases_rolling,
                        mode='lines',
                        name='7 day average',
                        line=dict(dash='dash', color='black')))
    fig.update_layout(title_text='Number of days since peak (on ' + peak_cases + ' from ' + last_date_cases +'): ' + peak + ' [' + area_name + ']',
                     template='plotly_white')

    return fig

def plotly_deaths(area_name):
    deaths = cache.get('deaths')
    last_date_deaths = deaths.index.max()
    total_deaths = deaths[deaths['name'] == area_name]['daily'].resample('d').sum()
    total_deaths_rolling = total_deaths.rolling(window=7).mean()
    peak_deaths = total_deaths_rolling.idxmax()
    peak_deaths_from_today = last_date_deaths - peak_deaths
    peak = str(peak_deaths_from_today.days)
    last_date_deaths = last_date_deaths.strftime("%d %B %Y")
    peak_deaths = peak_deaths.strftime("%d %B %Y")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=total_deaths.index, y=total_deaths,
                        name='daily deaths',
                        marker_color='red'))
    fig.add_trace(go.Scatter(x=total_deaths_rolling.index, y=total_deaths_rolling,
                        mode='lines',
                        name='7 day average',
                        line=dict(dash='dash', color='black')))
    fig.update_layout(title_text='Number of days since peak (on ' + peak_deaths + ' from ' + last_date_deaths +'): ' + peak + ' [' + area_name + ']',
                     template='plotly_white')

    return fig

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

cache = Cache()
cache.init_app(app.server, config=CACHE_CONFIG)
set_cache()

server = app.server
app.title = 'Covid Trends'


app.layout = html.Div(children=[
    dcc.Interval(
        id='interval-component',
        interval=60*1000, # in milliseconds
        n_intervals=0
    ),
    html.Div(id='test', children=['hello world'], style={'display':'none'}),
    html.H1(children='COVID-19 Trends'),
    html.A('Code can be found on Github', href='https://github.com/Moonglum8/covid-dash'),
    html.Div(children='''
        A basic dashboard displaying covid-19 trends by area for daily cases and deaths.
    '''),
    dcc.Loading(id='cases_loading', children=[
        dcc.Dropdown(
            id='cases-dropdown',
            options=[],
            value='London'
        ),
        dcc.Graph(
            style={'height': 300},
            id='cases-plot'
        ),
    ], type='circle'),
    dcc.Loading(id='deaths-loading', children=[
        dcc.Dropdown(
            id='deaths-dropdown',
            options=[],
            value='London'
        ),
        dcc.Graph(
            style={'height': 300},
            id='deaths-plot'
        ),
    ], type='circle')

])

@app.callback([Output('cases-dropdown', 'options'),
                Output('deaths-dropdown', 'options'),
                Output('test', 'children')],
              [Input('interval-component', 'n_intervals')])
def update_data(n):
    cases, deaths = set_cache()
    return [{'label': area, 'value': area} for area in cases['name'].drop_duplicates()], [{'label': area, 'value': area} for area in deaths['name'].drop_duplicates()], n

@app.callback(
    Output('cases-plot', 'figure'),
    [Input('cases-dropdown', 'value')])
def update_figure_cases(selected_area):
    return plotly_cases(selected_area)

@app.callback(
    Output('deaths-plot', 'figure'),
    [Input('deaths-dropdown', 'value')])
def update_figure_deaths(selected_area):
    return plotly_deaths(selected_area)

if __name__ == '__main__':
    app.run_server(debug=True)
