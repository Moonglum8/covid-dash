import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

import pandas as pd
import requests
import io
import os

from flask_caching import Cache

CACHE_CONFIG = {
    # 'CACHE_TYPE': 'redis',
    # 'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_THRESHOLD': 5
}

def get_cases():
    datastr_cases = requests.get('https://coronavirus.data.gov.uk/downloads/csv/coronavirus-cases_latest.csv',allow_redirects=True).text
    data_file_cases = io.StringIO(datastr_cases)
    return pd.read_csv(data_file_cases, index_col='Specimen date', parse_dates=True)

def get_deaths():
    datastr_deaths = requests.get('https://coronavirus.data.gov.uk/downloads/csv/coronavirus-deaths_latest.csv',allow_redirects=True).text
    data_file_deaths = io.StringIO(datastr_deaths)
    return pd.read_csv(data_file_deaths, index_col='Reporting date', parse_dates=True)

def set_cache():
    cases = get_cases()
    deaths = get_deaths()
    cache.set('cases', cases)
    cache.set('deaths', deaths)
    return cases, deaths

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

def plotly_cases(area_name):
    cases = cache.get('cases')
    last_date_cases = cases.index.max().strftime("%d %B %Y")
    total_cases = cases[cases['Area name'] == area_name]['Daily lab-confirmed cases'].resample('d').sum()
    total_cases_rolling = total_cases.rolling(window=7).mean()
    peak_cases = total_cases_rolling.idxmax().strftime("%d %B %Y")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=total_cases.index, y=total_cases,
                        name='daily cases',
                        marker_color='blue'))
    fig.add_trace(go.Scatter(x=total_cases_rolling.index, y=total_cases_rolling,
                        mode='lines',
                        name='7 day average',
                        line=dict(dash='dash', color='black')))
    fig.update_layout(title_text='Cases @ ' + last_date_cases + ' [Peak: ' + peak_cases + ']: ' + area_name,
                     template='plotly_white')

    return fig

def plotly_deaths(area_name):
    deaths = cache.get('deaths')
    last_date_deaths = deaths.index.max().strftime("%d %B %Y")
    total_deaths = deaths[deaths['Area name'] == area_name]['Daily change in deaths'].resample('d').sum()
    total_deaths_rolling = total_deaths.rolling(window=7).mean()
    peak_deaths = total_deaths_rolling.idxmax().strftime("%d %B %Y")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=total_deaths.index, y=total_deaths,
                        name='daily deaths',
                        marker_color='red'))
    fig.add_trace(go.Scatter(x=total_deaths_rolling.index, y=total_deaths_rolling,
                        mode='lines',
                        name='7 day average',
                        line=dict(dash='dash', color='black')))
    fig.update_layout(title_text='Deaths @ ' + last_date_deaths + ' [Peak: ' + peak_deaths + ']: '+area_name,
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
            value='England'
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
            value='England'
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
    return [{'label': area, 'value': area} for area in cases['Area name'].drop_duplicates()], [{'label': area, 'value': area} for area in deaths['Area name'].drop_duplicates()], n

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
