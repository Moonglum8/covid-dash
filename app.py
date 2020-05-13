import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

import pandas as pd
import requests
import io

datastr_cases = requests.get('https://coronavirus.data.gov.uk/downloads/csv/coronavirus-cases_latest.csv',allow_redirects=True).text
data_file_cases = io.StringIO(datastr_cases)
cases = pd.read_csv(data_file_cases, index_col='Specimen date', parse_dates=True)

datastr_deaths = requests.get('https://coronavirus.data.gov.uk/downloads/csv/coronavirus-deaths_latest.csv',allow_redirects=True).text
data_file_deaths = io.StringIO(datastr_deaths)
deaths = pd.read_csv(data_file_deaths, index_col='Reporting date', parse_dates=True)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# print(cases.info())
# print(deaths.info())

# cases = pd.read_csv('data/coronavirus-cases_latest.csv', index_col='Specimen date', parse_dates=True)
# deaths = pd.read_csv('data/coronavirus-deaths_latest.csv', index_col='Reporting date', parse_dates=True)

last_date_cases = cases.index.max().strftime("%d %B %Y")
last_date_deaths = deaths.index.max().strftime("%d %B %Y")

areas_cases = [{'label': area, 'value': area} for area in cases['Area name'].drop_duplicates()]
areas_deaths = [{'label': area, 'value': area} for area in deaths['Area name'].drop_duplicates()]

def plotly_cases(area_name):
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
server = app.server
app.title = 'Covid Trends'


app.layout = html.Div(children=[
    html.H1(children='COVID-19 Trends'),
    html.A('Code can be found on Github', href='https://github.com/Moonglum8/covid-dash'),
    html.Div(children='''
        A basic dashboard displaying covid-19 trends by area for daily cases and deaths.
    '''),
    dcc.Dropdown(
        id='cases-dropdown',
        options=areas_cases,
        value='England'
    ),
    dcc.Graph(
        style={'height': 300},
        id='cases-plot'
    ),
    dcc.Dropdown(
        id='deaths-dropdown',
        options=areas_deaths,
        value='England'
    ),
    dcc.Graph(
        style={'height': 300},
        id='deaths-plot'
    )
])

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
