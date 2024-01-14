import os
import pathlib
from datetime import datetime as dt, timedelta
import time
import numpy as np
import pandas as pd

import dash
from dash import Dash, html, dcc, callback, Output, Input, clientside_callback
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import dash_daq as daq

import plotly.express as px

from data.api import API

api = API()
devices = api.getdevicelist()

INTERVAL = 2  # Dash update interval in seconds

# dbc styling for dcc components
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app_name = 'Device Energy Dashboard'
app = Dash(app_name,
           external_stylesheets=[dbc.themes.LUX,
                                 dbc_css, dbc.icons.FONT_AWESOME],
           meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
rt_markers = {
    0: '0',
    24: '24'
}

hist_periods = {
    'week': 'This Week',
    'month': 'This Month',
    'year': 'This Year',
    'all': 'All Time'
}


interval = dcc.Interval(
    id='update_interval',
    interval=INTERVAL*1000,  # in milliseconds
    n_intervals=0
)

datepicker_single = html.Div(
    [
        dbc.Stack([
            dbc.Label("Select a Date", html_for='date_picker_day'),
            dcc.DatePickerSingle(
                id='date_picker_day',
                placeholder='Date',
                max_date_allowed=dt.today(),
                className="mb-2")
        ])
    ]
)

datepicker_range = html.Div(
    [
        dbc.Stack([
            dbc.Label("Select Date Range", html_for='date_picker_range'),
            dcc.DatePickerRange(
                id='date_picker_range',
                max_date_allowed=dt.today(),
                end_date_placeholder_text='End Date',
                start_date_placeholder_text='Start Date',
                className="mb-2")
        ])
    ]
)

checklist_periods = html.Div(
    [
        dbc.Stack([
            dbc.Label("Select Period", html_for='date_picker_range'),
            dcc.Dropdown(
                id='dropdown_periods',
                options=hist_periods,
                className='mb-2'
            )
        ])
    ]
)

color_mode_switch = html.Span(
    [
        dbc.Label(className="fa fa-moon",
                  html_for="color-mode-switch"),
        daq.BooleanSwitch(id='my-boolean-switch',
                          on=False),
        dbc.Switch(id="color-mode-switch",
                   value=False, persistence=True,
                   className="d-inline-block ms-1"),
        dbc.Label(className="fa fa-sun",
                  html_for="color-mode-switch"),
    ],
    className='p-3 rounded-pill'
)

datepickers = dbc.Row(
    [
        dbc.Col(checklist_periods),
        dbc.Col(datepicker_range),
        dbc.Col(datepicker_single),
    ],
    justify='center'
)

rt_period_slider = dcc.Slider(
    id='rt_slider',
    min=0,
    max=24,
    step=1,
    value=3,
    marks=rt_markers,
    tooltip={"placement": "top", "always_visible": True},
)

rt_slider_view = html.Div(
    [
        dbc.Button(
            "Select range (Hours)",
            id="rt_slider-collapse-button",
            className="mb-3",
            n_clicks=0,
            outline=True
        ),
        html.Div(
            dbc.Collapse(
                rt_period_slider,
                id="rt_slider-collapse",
                is_open=False
            ),
        ),
    ]
)

rt_energy_text = html.Div(
    [
        html.H5(
            "kWh"
        ),
        html.Hr(),
        html.P(
            "0.0",
            id='rt_energy_wh',
        ),

    ]

)

rt_graph = dcc.Graph(
    id="rt_chart",
)

rt_layout = html.Div(
    [
        html.H5("A real time graph of consumed energy over the last hour."),
        rt_graph
    ]
)

devices = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4("Select Devices", className='card-title'),
                dbc.Checklist(
                    id="device_checklist",
                    options=devices,
                    value=devices)
            ]
        )
    ]
)


rt_stats = dbc.Card(
    [
        html.H4("Real-Time Stats", className="card-title"),
        rt_slider_view,
        rt_energy_text,
    ],
    body=True
)

sidebar = html.Div(
    [
        dbc.Stack(
            [
                devices,
                rt_stats
            ],
            gap=5
        ),
    ]
)

rt_tab = dcc.Tab(
    label="Real Time",
    children=[
        html.Div(rt_layout,
                 className="p-4 border")],
)

hist_tab = dcc.Tab(
    label="Historical",
    children=[
        html.Div(datepickers,
                 className="p-4 border")
    ]
)
tabs = html.Div(
    [
        dcc.Tabs(
            value="tab-1",
            children=[
                rt_tab,
                hist_tab
            ],
        ),
    ]
)

readings_layout = dbc.Row(
    [
        dbc.Col(sidebar,  width=3),
        dbc.Col(tabs, width=9),
    ]
)

header = html.Header(
    [
        html.H3('Device Energy Consumption Dashboard',
                className='bg-primary text-white p-2 text-center'),
    ],
    className='my-4 mx-3'
)

app.layout = html.Div(
    [
        dbc.Container([header, readings_layout, interval],
                      fluid=True, className="dbc")
    ])


@callback(Output('rt_chart', 'figure'),
          [
              Input('update_interval', 'n_intervals'),
              Input('device_checklist', 'value'),
              Input('rt_slider', 'value'),
])
def update_rt_graph(n, dev, period):

    df = api.getReadingsInPastHrs(period).query()

    trace = dict(
        type="scatter",
        y=df["watt_hours"],
        line={"color": "#42C4F7"},
        hoverinfo="skip",
        mode="lines",
    )

    layout = dict(
        # plot_bgcolor=app_color["graph_bg"],
        # paper_bgcolor=app_color["graph_bg"],
        font={"color": "#fff"},
        xaxis={
            # "range": [0, 200],
            "showline": True,
            # "fixedrange": True,
            # "tickvals": [0, 50, 100, 150, 200],
            # "ticktext": ["200", "150", "100", "50", "0"],
            "title": "Time Elapsed (sec)",
        },
        yaxis={
            # "range": [0, max(100, max(df["readings.watt_hours"]))],
            "showgrid": True,
            "showline": True,
            "fixedrange": True,
            # "gridcolor": app_color["graph_line"],
            # "nticks": max(6, round(df["Speed"].iloc[-1] / 10)),
        },
    )

    return dict(data=[trace], layout=layout)


@callback(Output('rt_energy_wh', 'children'),
          [
              Input('update_interval', 'n_intervals'),
              Input('device_checklist', 'value'),
              Input('rt_slider', 'value'),
])
def update_rt_stats(n, device, period):
    return api.getRealtimeKWh(period)


@app.callback(
    Output("rt_slider-collapse", "is_open"),
    [Input("rt_slider-collapse-button", "n_clicks")],
    [State("rt_slider-collapse", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


if __name__ == '__main__':
    app.run(debug=True)
