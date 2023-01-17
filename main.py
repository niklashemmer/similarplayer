import pandas as pd
from dash.dependencies import Input, Output, State
import dash
import copy
import math
from dash import html, dcc, dash_table
import numpy as np
import plotly_express as px
import plotly.graph_objects as go
from control import Metrics, all, all_pp, Templates, Templates1

# Read in the DataFrame
df = pd.read_csv("/Users/niklashemmer/PycharmProjects/DashApp/data/Similar Player_22-05-11.csv")
df_per = pd.read_csv("/Users/niklashemmer/PycharmProjects/DashApp/data/Similar Player Percentiles_22-05-11.csv")
df.rename(columns={"cluster_gmm_new":"Player Role"}, inplace=True)
df.rename(columns={"PA": "PA Entry"}, inplace=True)
df_per.rename(columns={"PA": "PA Entry"}, inplace=True)
df_per.rename(columns={"cluster_gmm_new":"Player Role"}, inplace=True)
df = df.round(1)
df_per = df_per.round(1)
df["Age"] = df["Age"].astype(int)
df_per["Age"] = df_per["Age"].astype(int)

################################# HELPER FUNCTIONS #################################

metrics_options=[{"label":str(Metrics[metric]),
                  "value":str(metric)}
                 for metric in Metrics]

template_options=[{"label":str(Templates[value]),
                  "value":str(value)}
                 for value in Templates]

metrics_opt = [
    dict(label=key, value=Metrics[key])
    for key in df.columns.tolist()
    if key in Metrics.keys()
]

# Create sub-dataframes for the templates
centre_back = df_per[["ID", "Press", "Fls", "Dribb Tkl", "Tkl", "Int", "AerWon", "AerWon%", "Clr", "Carries PrgDist", "Pass PrgDist", "1/3 Entry"]]
full_back = df_per[["ID", "Tkl", "Int", "Press", "1/3 Entry", "PA Entry", "Crs", "Pass Cmp%", "Dribb Succ", "Turnover", "AerWon", "Fls", "Dribb Tkl"]]
defensive_mid = df_per[["ID", "Pass Cmp%", "1/3 Entry", "PA Entry", "xA", "Dribb Succ", "Fld", "Turnover", "Press Succ", "Press", "Tkl", "Int"]]
attacking_mid = df_per[["ID", "npxG", "Sh", "Touches Att Pen", "Pass Cmp%", "Crs PA", "PA Entry","xA", "Fld", "Turnover", "Dribb Succ", "Press Succ"]]
striker = df_per[["ID", "npxG", "Sh", "Touches Att Pen", "Sh/Touch", "xA", "Press Succ", "Press", "AerWon", "Turnover", "Dribb Succ", "npxG/Sh"]]

# Compile all sub-dataframes in one list
bar_options = [centre_back, full_back, defensive_mid, attacking_mid, striker]


################################# CONDITIONAL FORMATTING ON SIMILARITY (not used) #################################
def discrete_background_color_bins(df, n_bins=10, columns="all"):
    import colorlover as cl
    bounds = [i * (100/n_bins) for i in range(n_bins+1)]
    if columns == "all":
        if "id" in df:
            df_numeric_columns = df.select_dtypes("number").drop(["id"], axis=1)
        else:
            # returns a subset of the DataFrame's columns based on the column dtypes
            df_numeric_columns = df.select_dtypes("number")
    else:
        df_numeric_columns = df[columns]
    # First, it takes the max of each column and then the max of the max of each column (only one number)
    df_max = df_numeric_columns.max().max()
    df_min = df_numeric_columns.min().min()
    ranges = [
        ((df_max - df_min) * i) + df_min
        for i in bounds
    ]

    styles = []
    #legend = []

    for i in range (1, len(bounds)):
        min_bound = ranges[i-1]
        max_bound = ranges[i]
        backgroundColor = cl.scales[str(n_bins)]['qual']['Set3'][i - 1]
        color = 'white' if i > len(bounds) / 2. else 'inherit'

        for column in df_numeric_columns:
            styles.append({
                'if': {
                    'filter_query': (
                        '{{{column}}} >= {min_bound}' +
                        (' && {{{column}}} < {max_bound}' if (i < len(bounds) - 1) else '')
                    ).format(column=column, min_bound=min_bound, max_bound=max_bound),
                    'column_id': column
                },
                'backgroundColor': backgroundColor,
                'color': color
            })
    return styles

styles = discrete_background_color_bins(df, columns=["Similarity"])

################################# CHART PREP #################################

layout = dict(
    plot_bgcolor="#FFFFFF",
    #paper_bgcolor="#F2F2F2",
    xaxis=dict(
        showline=True,
        showgrid=True,
        gridcolor="rgb(235,235,235)",
        showticklabels=True,
        linecolor="black",
        ticks="outside",
        title="Percentile Rank",
        range=[0,100],
        dtick=25
    ),
    yaxis=dict(
        showgrid=True,
    ),
)

################################# LAYOUT #################################

app = dash.Dash(__name__)

server = app.server
app.layout = html.Div(
    [
        html.Div(
            id="banner",
            className="banner",
            children=[
                html.Div(
                    id="banner-text",
                    className="inner",
                    style={"display":"inline block"},
                    #
                    children=[
                        html.H4("SIMILAR PLAYER TOOL", style={"fontWeight":"bold"}),
                        html.P("This tool displays a player's percentile ranks in various statistics. It also identifies similar players based on their statistical profile throughout the Big 5 Leagues.")
                    ],
                ),
                html.Div(
                    id="banner-logo",
                    className="inner2",
                    children=[
                        html.A(
                            html.Button("Read more", style={"backgroundColor":"white"}),
                            href="https://xandfootball.substack.com/p/similarplayer",
                        ),
                    ],
                ),
            ],
        ),

        html.Br(),
        html.Div(
            [
                html.Div(
                    [
                        html.H6("PLAYER SELECTION", style={"fontWeight":"bold"}),
                        html.Br(),
                        html.B("1. Which player do you want to look for?", className="control_label"
                        ),
                        dcc.Dropdown(id="player",
                                     options=[{"label": i, "value": i} for i in df["ID"]],
                                     placeholder="Select a player",
                                     value=df["ID"][0],
                                     multi=False
                        ),
                        html.Hr(),
                        html.B("2. Do you want to use templates or customize?", className="control_label"
                        ),
                        dcc.RadioItems(id="metrics_selector",
                                        options=[
                                            {"label": "Template", "value": "template"},
                                            {"label": "Customize", "value": "custom"}
                                        ],
                                        value="template",
                                        labelStyle={"display":"inline-block"},
                                        className="dcc_control"
                        ),

                        #html.Hr()
                        dcc.Dropdown(id="metrics",
                                        value=[],
                                        className="dcc_control"
                        ),
                        html.Div(
                            [
                                html.Button(id="submit_button", n_clicks=0, children="submit"),
                                #html.Button(id="reset_button", n_clicks=0, children="reset"),
                            ],
                        className="row"
                        ),
                        html.Hr(),
                        html.Div(id="display_selected_values"),

                        html.B("3. Which player do you want to compare him to?", className="control_label"
                               ),
                        dcc.Dropdown(id="player2",
                                     options=[{"label": i, "value": i} for i in df["ID"]],
                                     placeholder="Select a player",
                                     multi=False,
                                     #value=df["ID"][1],
                                     #value="None",
                                     className="dcc_control"
                        ),
                        html.Br(),
                        html.A(
                            html.I("Go to fbref for explanations of each metric", style={"fontSize":12}),
                            href="https://fbref.com/en/",
                        ),
                        #html.Button(id="submit_button2", n_clicks=0, children="submit"),
                        #html.Div(id="display_selected_values"),
                    ],
                    className="pretty_container five columns"
                ),
                # New section for the bar chart
                html.Div(
                    [
                        html.Div(
                            [
                                html.B(id="chart_title"),
                                #html.Hr(),
                                dcc.Graph(id="percentile_chart", config={"displayModeBar":False},
                                className="pretty_container",
                                ),
                            ],
                            id="percentileContainer",
                        )
                    ],
                    id="rightCol",
                    className="eight columns"
                )
            ],
            className="row"
        ),

        # Data Table
        html.Div(
            [
                html.Hr(),
                html.Div(
                    [
                        html.Div(
                            [
                                html.B("Age"),
                                dcc.RangeSlider(id="age_selector",
                                                min=df["Age"].min(),
                                                max=40,
                                                step=1,
                                                value=[df["Age"].min(), 40],
                                                marks={i: str(i) for i in range(0, 40, 2)},
                                                className="dcc_control"
                                                ),
                            ],
                            className="four columns pretty_container"
                        ),
                        html.Div(
                            [
                                html.B("Season"),
                                dcc.Checklist(id="season_selector",
                                              options=[
                                                  {"label": i, "value": i} for i in df["Season"].unique()
                                              ],
                                              inline=True,
                                              value=df["Season"].unique()[0:5],
                                              className="dcc_control"
                                              ),
                            ],
                            className="four columns pretty_container"
                        ),

                        html.Div(
                            [
                                html.B("League"),
                                dcc.Checklist(id="league_selector",
                                              options=[
                                                  {"label": "EPL", "value": "Premier League"},
                                                  {"label": "Ligue 1", "value": "Ligue 1"},
                                                  {"label":"Bundesliga", "value":"Bundesliga"},
                                                  {"label": "Serie A", "value": "Serie A"},
                                                  {"label": "La Liga", "value": "La Liga"}
                                              ],
                                              inline=True,
                                              value=df["Comp"].unique()[0:5],
                                              className="dcc_control"
                                              ),
                            ],
                            className="four columns pretty_container"
                        ),
                    ],
                    className="row",
                ),

        html.Div(
            [
                dcc.Checklist(
                    id="percentile",
                    options=[
                        {"label": "Toggle Percentiles", "value": "toggle"}
                    ],
                    value=[],
                    style={"paddingLeft": "0%",
                           "paddingTop": "3%",
                           "fontSize": 18,
                           "fontWeight": "bold"},
                    className="dcc_control"
                ),
            ],
            className="dcc_control"
        ),

        html.Div(
            [
                dash_table.DataTable(
                    id="player_data",
                    columns=[{"name": i, "id": i}
                             if i == "ID" or i == "Similarity" or i == "Age" or i == "Comp" or i == "90s" or i == "Player Role"
                             else {"name": i, "id": i, "hideable": True}
                             for i in df[all].columns],
                    row_selectable=None,
                    row_deletable=True,
                    page_action="custom",
                    page_current=0,
                    page_size=20,
                    export_format="csv",
                    style_cell={"font-family":"Helvetica",
                                "font-size":13,
                                "paddingLeft":"5px",
                                "paddingRight":"5px"},
                    style_data={#"whiteSpace":"normal", # this would make it more lines
                                "height":"auto",
                                "lineHeight":"15px",
                                'width': '{}%'.format(len(df.columns)),
                                "textOverflow":"ellipsis",
                                "overflow":"hidden",
                                "textAlign":"center"
                    },
                    style_table={'overflowX': 'auto'},
                    fixed_columns={'headers': True, 'data': 1},
                    style_header={
                        "background-color":"rgb(14,83,235)",
                        "color":"white",
                        "fontSize": 14,
                        "fontWeight": "bold",
                        "textAlign":"left",
                    },
                    style_header_conditional=[
                        {"if": {"column_id": ["ID", "Comp", "Player Role"]}, "textAlign": "left"}
                    ]
                ),
            ],
            id="datatableContainer",
            className="table"
        ),

        html.Br(),
        html.Div(
            id="banner2",
            className="banner2",
            children=[
                html.Div(
                    className="inner",
                    children=[
                        html.P("All data from Fbref via Statsbomb")
                    ],
                ),
                html.Div(
                    className="inner",
                    children=[
                        html.A(
                            html.P("The code is available in this Github repository", style={"fontSize": 12}),
                            href="https://github.com/niklashemmer/similarplayer_tool",
                        ),
                    ],
                ),
                html.Div(
                    className="inner2",
                    children=[
                        html.Img(
                            src=app.get_asset_url("fbrefcom-logos-idxc7lyqtc.png"),
                            style={"height":"20px"},
                            id="fbref",
                        ),
                        html.Img(
                            src=app.get_asset_url("SB - Core Wordmark - Colour positive.png"),
                            style={"height":"20px"},
                            id="statsbomb",
                        ),
                    ],
                ),
            ],
        ),
    ],
),

])

################################# CALLBACKS #################################

# CALLBACK TO UPDATE CUSTOMIZE OR TEMPLATE DROPDOWN
@app.callback(
    [Output("metrics", "options"),
     Output("metrics", "multi"),
     Output("metrics", "value"),
     Output("submit_button", "n_clicks")],
    [Input("metrics_selector", "value"),
     Input("player", "value")],
    [State("metrics", "value")],
     #Input("reset_button", "n_clicks")
     #]
)

def update_metrics_dropdown(selector, player_selected, current_metrics):
    if selector == "custom":
        options_return = metrics_opt
        multi = True
        pos = (df_per["cluster_gmm"])[(df_per["ID"] == player_selected)]
        # if (pos == "FB").bool():
        #     value = ["Tkl", "Int", "Press", "1/3 Entry", "PA", "Crs", "Pass Cmp%", "Dribb Succ", "Turnover", "AerWon", "Fls", "Dribb Tkl"]
        # elif (pos == "CB").bool():
        #     value= ["Press", "Fls", "Dribb Tkl", "Tkl", "Int", "AerWon", "AerWon%", "Clr", "Carries PrgDist", "Pass PrgDist", "1/3 Entry"]
        # elif (pos == "DM").bool():
        #     value = ["Pass Cmp%", "1/3 Entry", "PA", "xA", "Dribb Succ", "Fld", "Turnover", "Press Succ", "Press", "Tkl", "Int"]
        # elif (pos == "AM").bool():
        #     value = ["npxG", "Sh", "Touches Att Pen", "Pass Cmp%", "Crs PA", "PA","xA", "Fld", "Turnover", "Dribb Succ", "Press Succ"]
        # else:
        #     value = ["npxG", "Sh", "Touches Att Pen", "Sh/Touch", "xA", "Press Succ", "Press", "AerWon", "Turnover", "Dribb Succ", "npxG/Sh"]
        value=current_metrics
        n_clicks=1

    else:
        options_return = Templates1
        multi = False
        # aktuell noch unnötig, vielleicht langfristig aber sinnvoll
        pos = (df["cluster_gmm"])[(df["ID"] == player_selected)]
        if (pos == "FB").bool():
            value = 1
        elif (pos == "CB").bool():
            value= 0
        elif (pos == "DM").bool():
            value = 2
        elif (pos == "ST").bool():
            value = 4
        else:
            value = 3
        n_clicks=1
    return (options_return, multi, value, n_clicks)

# CALLBACK TO CREATE PERCENTILE CHART
@app.callback(
    Output("percentile_chart", "figure"),
    [Input("metrics_selector", "value"),
     Input("player", "value"),
     Input("player2", "value"),
     Input("submit_button", "n_clicks"),
     ],
    [State("metrics", "value"),
     State("percentile_chart", "figure")],
)

def update_graph(metrics_selector, player_selected, player_selected2, n_clicks, metrics, fig): #n_clicks2

    #layout_bar = copy.deepcopy(layout)
    if metrics_selector == "custom":
        df_bar = df_per.copy()
        df_player = df_bar[df_bar["ID"] == player_selected]
        # # The default value is a string. But when I add another option, Python directly converts it into a list. That's where it crashes
        # # We cannot compare a list with a string(because the ID column is a string)
        if type(player_selected)!=str:
             val = player_selected[0]
             player = df[df["ID"] == player]
        df_player = df_player[metrics]
        df_player_t = df_player.T
        # ## Reset index (just adds an index basically)
        df_player_t = df_player_t.reset_index(drop=False)
        # Rename columns
        df_player_t.columns = ["Metric", "PR"]
        metric = df_player_t["Metric"]
        pr = df_player_t["PR"]

        trace = (go.Bar(
            x=pr[0:],
            y=metric[0:],
            #text=pr2[0:],
            orientation="h",
            name=player_selected,
            marker=dict(
                color="rgb(14,83,235)",
                line=dict(color="#000000", width=1)
            )
        ))

    else:
        df_bar = bar_options[metrics]
        df_player = df_bar[df_bar["ID"] == player_selected]
        # The default value is a string. But when I add another option, Python directly converts it into a list. That's where it crashes
        # We cannot compare a list with a string(because the ID column is a string)
        if type(player_selected)!=str:
            val = player_selected[0]
            player = df[df["ID"] == player]
        df_player_t = df_player.T
        ## Reset index (just adds an index basically)
        df_player_t = df_player_t.reset_index(drop=False)
        # Rename columns
        df_player_t.columns = ["Metric", "PR"]
        metric = df_player_t["Metric"]
        pr = df_player_t["PR"]

        trace = (go.Bar(
            x=pr[1:],
            #text=pr2[1:],
            y=metric[1:],
            orientation="h",
            name=player_selected,
            marker=dict(
                color="rgb(14,83,235)",
                line=dict(color="#000000", width=1)
            )
        ))

    layout_bar = copy.deepcopy(layout)
    layout_bar["title"] = f"{player_selected} <br><sup><I> Percentiles calculated against players in the same position in respective season (>900 min)"

    fig = go.Figure(trace, layout=layout_bar)
    fig.update_layout(legend=dict(
        orientation="h",
        x=0,
        y=-0.2,
    ),
    height=580
    )

    if player_selected2 is not None:
        if metrics_selector == "custom":
            df_bar2 = df_per.copy()
            df_player2 = df_bar2[df_bar2["ID"] == player_selected2] #| df_bar["ID"] == player2]
            # # The default value is a string. But when I add another option, Python directly converts it into a list. That's where it crashes
            # # We cannot compare a list with a string(because the ID column is a string)
            if type(player_selected2)!=str:
                 val2 = player_selected2[0]
                 player2 = df[df["ID"] == player2]
            #player1 = create_barchart(player_selected)
            df_player2 = df_player2[metrics]
            df_player2_t = df_player2.T
            # ## Reset index (just adds an index basically)
            df_player2_t = df_player2_t.reset_index(drop=False)
            # ## Rename columns
            df_player2_t.columns = ["Metric", "PR"]
            metric2 = df_player2_t["Metric"]
            pr2 = df_player2_t["PR"]
            trace2 = (go.Bar(
                x=pr2[0:],
                y=metric2[0:],
                orientation="h",
                name=player_selected2,
                marker=dict(
                    color="rgb(189,233,254)",
                    line=dict(color="#000000", width=1)
                )
            ))

        else:
            df_bar2 = bar_options[metrics]
            df_player2 = df_bar2[df_bar2["ID"] == player_selected2]
            # The default value is a string. But when I add another option, Python directly converts it into a list. That's where it crashes
            # We cannot compare a list with a string(because the ID column is a string)
            if type(player_selected2)!=str:
                val2 = player_selected2[0]
                player2 = df[df["ID"] == player2]
            df_player2_t = df_player2.T
            ## Reset index (just adds an index basically)
            df_player2_t = df_player2_t.reset_index(drop=False)
            ## Rename columns
            df_player2_t.columns = ["Metric", "PR"]
            metric2 = df_player2_t["Metric"]
            pr2 = df_player2_t["PR"]
            trace2 = (go.Bar(
                x=pr2[1:],
                y=metric2[1:],
                orientation="h",
                name=player_selected2,
                marker=dict(
                    color="rgb(189,233,254)",
                    line=dict(color="#000000", width=1)
                )
            ))

        layout_bar = copy.deepcopy(layout)
        layout_bar["title"] = f"{player_selected} vs {player_selected2} <br><sup><I> Percentiles calculated against players in the same position in respective season (>900 min)"
        fig.add_trace(trace2)
        fig.update_layout(layout_bar)

    else:
        pass

    return fig

# CALLBACK TO CREATE THE DATATABLE
@app.callback(
    Output("player_data", "data"),
    Output("player_data", "style_data_conditional"),
    #Output("player_data", "style_header_conditional"),
    [Input("age_selector", "value"),
     Input("season_selector", "value"),
     Input("league_selector", "value"),
     Input("player", "value"),
     Input("player_data", "page_current"),
     Input("player_data", "page_size"),
     Input("percentile", "value")
     ]
)
def update_table(age_selector, season_selector, league_selector, player_selected, page_current, page_size, percentile):

    #Calculate the distances per PCA
    position = (df["cluster_gmm"])[(df["ID"] == player_selected)]
    if (position == "FB").bool():

        dist_pca1 = float(df["PCA1"][(df["ID"] == player_selected)]),
        dist_pca2 = float(df["PCA2"][(df["ID"] == player_selected)]),
        dist_pca3 = float(df["PCA3"][(df["ID"] == player_selected)]),
        dist_pca4 = float(df["PCA4"][(df["ID"] == player_selected)]),
        dist_pca5 = float(df["PCA5"][(df["ID"] == player_selected)]),
        dist_pca6 = float(df["PCA6"][(df["ID"] == player_selected)]),
        dist_pca7 = float(df["PCA7"][(df["ID"] == player_selected)])

        #Calculate the overall distance
        df["Dist"] = np.sqrt( (dist_pca1 - df['PCA1'])**2 + (dist_pca2 - df['PCA2'])**2
                            + (dist_pca3 - df['PCA3'])**2 + (dist_pca4 - df['PCA4'])**2
                            + (dist_pca5 - df['PCA5'])**2 + (dist_pca6 - df['PCA6'])**2
                            + (dist_pca7 - df['PCA7'])**2)


    elif (position == "CB").bool():
        dist_pca1A = float(df["PCA1A"][(df["ID"] == player_selected)]),
        dist_pca2A = float(df["PCA2A"][(df["ID"] == player_selected)]),
        dist_pca3A = float(df["PCA3A"][(df["ID"] == player_selected)]),
        dist_pca4A = float(df["PCA4A"][(df["ID"] == player_selected)]),
        dist_pca5A = float(df["PCA5A"][(df["ID"] == player_selected)]),
        dist_pca6A = float(df["PCA6A"][(df["ID"] == player_selected)]),
        dist_pca7A = float(df["PCA7A"][(df["ID"] == player_selected)])
        dist_pca8A = float(df["PCA8A"][(df["ID"] == player_selected)])

        #Calculate the overall distance
        df["Dist"] = np.sqrt( (dist_pca1A - df['PCA1A'])**2 + (dist_pca2A - df['PCA2A'])**2
                            + (dist_pca3A - df['PCA3A'])**2 + (dist_pca4A - df['PCA4A'])**2
                            + (dist_pca5A - df['PCA5A'])**2 + (dist_pca6A - df['PCA6A'])**2
                            + (dist_pca7A - df['PCA7A'])**2 + (dist_pca8A - df['PCA8A'])**2)

    elif (position == "DM").bool():
        dist_pca1B = float(df["PCA1B"][(df["ID"] == player_selected)]),
        dist_pca2B = float(df["PCA2B"][(df["ID"] == player_selected)]),
        dist_pca3B = float(df["PCA3B"][(df["ID"] == player_selected)]),
        dist_pca4B = float(df["PCA4B"][(df["ID"] == player_selected)]),
        dist_pca5B = float(df["PCA5B"][(df["ID"] == player_selected)]),
        dist_pca6B = float(df["PCA6B"][(df["ID"] == player_selected)]),
        dist_pca7B = float(df["PCA7B"][(df["ID"] == player_selected)])

        #Calculate the overall distance
        df["Dist"] = np.sqrt( (dist_pca1B - df['PCA1B'])**2 + (dist_pca2B - df['PCA2B'])**2
                            + (dist_pca3B - df['PCA3B'])**2 + (dist_pca4B - df['PCA4B'])**2
                            + (dist_pca5B - df['PCA5B'])**2 + (dist_pca6B - df['PCA6B'])**2
                            + (dist_pca7B - df['PCA7B'])**2)# + (dist_pca8B - df['PCA8B'])**2).round(1)

    else:
        dist_pca1E = float(df["PCA1E"][(df["ID"] == player_selected)]),
        dist_pca2E = float(df["PCA2E"][(df["ID"] == player_selected)]),
        dist_pca3E = float(df["PCA3E"][(df["ID"] == player_selected)]),
        dist_pca4E = float(df["PCA4E"][(df["ID"] == player_selected)]),
        dist_pca5E = float(df["PCA5E"][(df["ID"] == player_selected)]),
        dist_pca6E = float(df["PCA6E"][(df["ID"] == player_selected)]),
        #dist_pca7C = float(df["PCA7C"][(df["ID"] == player_selected)]),
        #dist_pca7B = float(df["PCA7B"][(df["ID"] == player_selected)])

        #Calculate the overall distance
        df["Dist"] = np.sqrt( (dist_pca1E - df['PCA1E'])**2 + (dist_pca2E - df['PCA2E'])**2
                            + (dist_pca3E - df['PCA3E'])**2 + (dist_pca4E - df['PCA4E'])**2
                            + (dist_pca5E - df['PCA5E'])**2 + (dist_pca6E - df['PCA6E'])**2)
                            #+ (dist_pca7C - df['PCA7C'])**2)
                            #+ (dist_pca7B - df['PCA7B'])**2 + (dist_pca8B - df['PCA8B'])**2).round(1)

    df["Similarity"] = (((1 - df["Dist"] / np.max(df["Dist"]))*100).round(2))

    dff = df[(df["Age"] >= int(age_selector[0]))
            & (df["Age"] <= int(age_selector[1]))
            & (df["Season"].isin(season_selector))
            & (df["Comp"].isin(league_selector))]

    if "toggle" in percentile:
        dff_per = df_per[all_pp]
        #((dff_per.iloc[:,5:])*100)
        dff = pd.merge(dff, dff_per, how="left", on=["ID"], suffixes=("XX", None))
        dff = dff[all].sort_values(by="Similarity", ascending=False)

    else:
        dff = dff[all].sort_values(by="Similarity", ascending=False)

    #style_data_conditional=styles
    style_data_conditional = [
        {"if": {"row_index": "odd"}, "backgroundColor": "rgb(244, 247, 249)"},
        {"if": {"column_id": ["ID", "Comp", "Player Role"]}, "textAlign": "left"},
        {"if": {"column_type": "numeric"}, "textAlign": "center"},
                ]

    return (dff.iloc[page_current*page_size:(page_current+ 1)*page_size].to_dict("records"), style_data_conditional)

# Call main function
if __name__ == "__main__":
     app.run_server(debug=True)
