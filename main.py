#========================================= IMPORT LIBRARIES ============================================================
import plotly.express as px
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
#from tkinter import filedialog #REMEMBER this doesnt work with HEROKU deployment, must comment out before deploying this code
import base64
import plotly.graph_objs as go
from datetime import date
import gunicorn

#===================================== LOADING + TRANSFORMING THE DATA =================================================

#Load Core data
df = pd.read_csv(r'ActualsPlanTidy_Data.csv', encoding='ISO-8859-1', low_memory=False)

#Basic cleansing
df['Activity Count'].fillna(0, inplace=True)
df['Activity Count'].replace('-', 0)

#print(df.shape)
df = df[(df['POD'] !='DNA/Cancellation (Theatres Only)') & (df['POD'] !='Number of 1/2 Day Lists (Theatres Only)') & (df['POD'] !='Chemotherapy')]
#print(df.shape)

#Load Location data
location_df = pd.read_csv(r'Location_data.csv', encoding='ISO-8859-1', low_memory=False)

#Join Location onto the Core df
df = pd.merge(df,location_df,on='Independent Provider', how='left')
print(df.shape)
print(df)

#Convert Lat and Long to str for grouping
df['Lat'] = df['Lat'].astype(str)
df['Long'] = df['Long'].astype(str)


df_grouped = df.groupby(['Inner or Outer','Plan or Actuals','Activity Type', 'Independent Provider','STP','POD','Week Commencing Date','Lat','Long'], as_index=False)['Activity Count'].sum()
df_actuals = df_grouped[(df_grouped['Plan or Actuals'] =='Actuals')]
df_actuals.rename(columns={"Activity Count": "Actual Activity"}, inplace=True)
df_plan = df_grouped[(df_grouped['Plan or Actuals'] =='Plan')]
df_plan.rename(columns={"Activity Count": "Plan Activity"}, inplace=True)

print(df_actuals.shape)
print(df_plan.shape)


#Now we need to merge the datasets so we have 2 extra fact columns - plan and capacity values, this will be much easier to plot on tables/graphs
df_merged = df_actuals.merge(df_plan, on=['Activity Type','Independent Provider','STP','POD','Week Commencing Date'], how='left')
df_merged = df_merged.drop(['Inner or Outer_y','Plan or Actuals_y','Lat_y','Long_y','Plan or Actuals_x'], axis=1)
df_merged.rename(columns={'Inner or Outer_x':'Inner or Outer','Lat_x':'Lat','Long_x':'Long'}, inplace=True)

#Find the most recent date
df_merged['Week Commencing Date'] = pd.to_datetime(df_merged['Week Commencing Date'], dayfirst=True)
most_recent_date = df_merged['Week Commencing Date'].max()
oldest_date = df_merged['Week Commencing Date'].min()

#========================================= DASH LAYOUT =================================================================

app = dash.Dash(__name__, eager_loading=True, external_stylesheets=[dbc.themes.LUX])
server = app.server
image_filename = r'NHS 10mm - RGB Blue on white.png' # replace with your own image - must be png image type - use this website to convert :https://jpg2png.com/
encoded_image = base64.b64encode(open(image_filename, 'rb').read())
app.layout = html.Div([
                        dbc.Row([dbc.Col(html.H1('Independant Sector Weekly Activity Dashboard',className='dark'),style={'text-align': 'center','vertical-align':'middle'}),
                                dbc.Col(html.Img(src='data:image/png;base64,{}'.format(encoded_image.decode()), width=130, height=50, style={'vertical-align':'middle'}), width=1),
                                ]),

                        html.Hr(),

                        dbc.Row(dbc.Col(html.H5('Data can be filtered using the options below',className='dark'),style={'text-align': 'center','vertical-align':'middle'})),

                        dbc.Row([dbc.Col(dcc.Dropdown(id='POD_Dropdown',
                                     options=[
                                         {"label": "Elective", "value": "Elective"},
                                         {"label": "Daycase", "value": "Daycase"},
                                         {"label": "Diagnostics", "value": "Diagnostics"},
                                         {"label": "Outpatients", "value": "Outpatients"}
                                     ],
                                     multi=True,
                                     value=['Elective', 'Daycase'],
                                     style={'text-align': 'center'},
                                     clearable=False,
                                     placeholder='Please select point of delivery'
                                     ), width={'size':5, 'offset':1}),

                                    dbc.Col(dcc.Dropdown(id='STP_Dropdown',
                                                                                    options=[
                                                                                                {"label": "SWL STP", "value": "South West London STP"},
                                                                                                {"label": "SEL STP", "value": "South East London STP"},
                                                                                                {"label": "NWL STP", "value": "North West London STP"},
                                                                                                {"label": "NCL STP", "value": "North London STP"},
                                                                                                {"label": "NEL STP", "value": "East London STP"}
                                                                                    ],
                                                                                    multi=True,
                                                                                    value=['South West London STP','South East London STP',"North West London STP","North London STP","East London STP"],
                                                                                    style={'text-align': 'center'},
                                                                                    clearable=False,
                                                                                    placeholder='Please select your STP(s)'
                                                                                 ),width={'size':5, 'offset':-1})]),


                        html.Br(),

                        dbc.Row(dbc.Col(
                                        dcc.Checklist(id='Checklist',
                                                      options=[
                                                        {'label': 'Outer Providers', 'value': 'Outer'},
                                                        {'label': 'Inner Providers', 'value':'Inner'}
                                                      ],
                                                      value=['Outer'],
                                                      inputStyle={"margin-right": "10px","margin-left": "10px"},
                                                      #labelStyle={'display': 'inline-block'},
                        ),style={'text-align': 'center','vertical-align':'middle'})),

                       #html.Br(),

                       dbc.Row(dbc.Col(
                            dcc.Checklist(id='Checklist-eRS',
                                          options=[
                                              {'label': 'Acute', 'value': 'Normal'},
                                              {'label': 'eRS', 'value': 'eRS'}
                                          ],
                                          value=['Normal','eRS'],
                                          inputStyle={"margin-right": "10px","margin-left": "10px"},
                                          # labelStyle={'display': 'inline-block'},
                                          ), style={'text-align': 'center', 'vertical-align': 'middle','margin-left': '15px'})),

                       html.Br(),

                       html.Hr(),

                       dcc.Tabs(id="tabs", value='util-tab', children=[

                                # TAB 1 - THE TABLE
                                dcc.Tab(label='Utilisation Table', value='util-tab', children=[html.Div([

                                    html.Br(),
                                    dbc.Row(dbc.Col(dcc.DatePickerRange(
                                        id='date',
                                        min_date_allowed=date(1995, 8, 5),
                                        max_date_allowed=date(2023, 9, 1),
                                        initial_visible_month=date(2021, 1, 1),
                                        start_date=date(2021,1,1),
                                        end_date=date(2021,3,30),
                                        style={'position':'relative', 'zIndex':'999'}
                                    ), width={'offset': 1})),

                                    html.Div(id='Table'),

                                    html.Br(),

                                    # dbc.Row([dbc.Col(),
                                    #          dbc.Col(dbc.Card(dbc.CardBody([html.H2(id='Card Utilisation Table',style={'text-align': 'center'},className="card-text"),html.H3("%",className="card-title",style={'text-align': 'center'})]),color="rgb(188, 219, 245)",outline=True), width={'size': 5, 'offset': -1}),
                                    #          dbc.Col()]),
                                    #
                                    # html.Br()

                                ])]),


                                # TAB 2 - THE DASHBOARD
                                dcc.Tab(label='Utilisation Dashboard', value='dash-tab', children=[
                                    html.Div([
                                    html.Br(),

                                    dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.H3("Weekly Utilisation (%) ==> " + most_recent_date.strftime('%d/%m/%y'), className="card-title",style={'text-align': 'center'}),html.H2(id='Card Utilisation Week',style={'text-align': 'center'},className="card-text")]),color="rgb(188, 219, 245)",outline=True),width={'size': 5, 'offset': 1}),
                                             dbc.Col(dbc.Card(dbc.CardBody([html.H3("Total Utilisation (%)",className="card-title",style={'text-align': 'center'}),html.H2(id='Card Utilisation Total',style={'text-align': 'center'},className="card-text")]),color="rgb(188, 219, 245)",outline=True), width={'size': 5, 'offset': -1})
                                             ]),

                                    html.Br(),
                                    html.Hr(),

                                    dbc.Row([dbc.Col(dcc.Graph(id='Bar', figure={}), width={'size': 5, 'offset': 1}),
                                             dbc.Col(dcc.Graph(id='Line', figure={}), width={'size': 5, 'offset': -1})
                                             ]),

                                    html.Hr(),

                                ])]),

                                # TAB 3 - THE MAP
                                dcc.Tab(label='Map + Upload', value='map-tab',children=[

                                    html.Br(),

                                    dbc.Row([dbc.Col(dcc.Graph(id='Map_content', figure={}))]),

                                    html.Br(),
                                    html.Br(),
                                    html.Hr(),
                                    html.Br(),

                                    dbc.Col(dcc.Upload(id='upload-data',children=html.Div(['Drag and Drop or ',html.A('Select Files')]),multiple=True,style={'text-align': 'center'})),

                                    html.Br(),
                                    html.Hr(),

                                    html.Br(),


                                ])
                       ])

])

#width={'size': 12}

#=========================================== UTILISATION TABLE CALLBACK ================================================

@app.callback(Output('Table', 'children'),
               #Output('Card Utilisation Table', 'children')],
              [
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist', component_property='value'),
               Input(component_id='Checklist-eRS', component_property='value'),
               Input(component_id='date', component_property='start_date'),
               Input(component_id='date', component_property='end_date')]
              )
def render_content(POD,STP,Checklist,Checklist_eRS,start_date,end_date):

    df_dash = df_merged.copy()
    df_dash = df_dash[df_dash['POD'].isin(POD)]
    df_dash = df_dash[df_dash['STP'].isin(STP)]
    df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
    df_dash = df_dash[df_dash['Activity Type'].isin(Checklist_eRS)]
    df_dash = df_dash[(df_dash['Week Commencing Date'] >= start_date) & (df_dash['Week Commencing Date'] <= end_date)]
    df_dash_group = df_dash.groupby(['STP', 'Independent Provider'], as_index=False)[
        'Actual Activity', 'Plan Activity'].sum()
    df_dash_group['Utilisation (%)'] = (df_dash_group['Actual Activity']/df_dash_group['Plan Activity'])*100
    df_dash_group['Utilisation (%)'] = df_dash_group['Utilisation (%)'].replace([np.inf, -np.inf], np.nan)
    card = df_dash_group['Utilisation (%)'].mean()
    card = card.round(2)


    #Formatting
    df_dash_group['Actual Activity'] = df_dash_group['Actual Activity'].map('{:,.0f}'.format)#to get numbers in format correctly
    df_dash_group['Plan Activity'] = df_dash_group['Plan Activity'].map('{:,.0f}'.format)  # to get numbers in format correctly
    df_dash_group['Utilisation (%)'] = df_dash_group['Utilisation (%)'].map('{:.0f}'.format)  # to get numbers in format correctly

    return html.Div([

            html. Br(),

            dbc.Row(dbc.Col(dt.DataTable(data=df_dash_group.to_dict('rows'),
                         columns=[{"name": i, "id": i} for i in df_dash_group.columns],
                         sort_action='native',
                         page_size=100,
                         fixed_rows={'headers': True},
                         style_table={'height': 800},
                         style_cell_conditional=[
                                             {'if': {'column_id': 'STP'},
                                              'width': '14%'},  # 40
                                             {'if': {'column_id': 'Independent Provider'},
                                              'width': '35%'},  # 300
                                             {'if': {'column_id': 'Actual Activity'},
                                              'width': '12%',
                                              'textAlign': 'center'},
                                             {'if': {'column_id': 'Plan Activity'},
                                              'width': '12%',
                                              'textAlign': 'center',
                                              },# 5
                                             {'if': {'column_id': 'Utilisation (%)'},
                                              'width': '9%',
                                              'textAlign': 'center',
                                              },

                                         ],

                         style_data_conditional=[{
                                                 'if': {
                                                     'filter_query': '{Utilisation (%)} >= 0 && {Utilisation (%)} < 60',
                                                     'column_id': 'Utilisation (%)'
                                                 },
                                                 'backgroundColor': 'tomato',
                                                 'color': 'white'
                                             },
                                             {
                                                 'if': {
                                                     'filter_query': '{Utilisation (%)} >= 80',
                                                     'column_id': 'Utilisation (%)'
                                                 },
                                                 'backgroundColor': 'green',
                                                 'color': 'white'
                                             },
                                             {
                                                 'if': {
                                                     'filter_query': '{Utilisation (%)} >= 60 && {Utilisation (%)} < 80',
                                                     'column_id': 'Utilisation (%)'
                                                 },
                                                 'backgroundColor': 'orange',
                                                 'color': 'white'
                                             },
                                             {
                                                 'if': {
                                                     'filter_query': '{Utilisation (%)} contains "nan"',
                                                     'column_id': 'Utilisation (%)'
                                                 },
                                                 'backgroundColor': 'rgb(204,204,204)',
                                                 'color': 'grey',
                                                 'fontWeight':'bold'
                                             }
                         ],
                         style_header={
                                             'backgroundColor': 'rgb(188, 219, 245)',
                                             'fontWeight': 'bold',
                                             'textAlign': 'center',
                                             'color': 'black',
                                             'border': '1px solid black'
                                         },
                         style_cell={'font_family': 'Nunito Sans',
                                                    'border': '1px solid grey',
                                                    'minWidth': 95, 'maxWidth': 95, 'width': 95,
                                                    'whiteSpace': 'normal'
                                                    },
                                         ),width={'size':10,'offset':1}))
        ])

#============================================ CARD UTILISATION TOTAL CALLBACK ==========================================

@app.callback(Output('Card Utilisation Total', 'children'),
              [
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist', component_property='value'),
               Input(component_id='Checklist-eRS', component_property='value')]
              )

def render_content(POD,STP,Checklist,Checklist_eRS):


        df_dash = df_merged.copy()
        df_dash = df_dash[df_dash['POD'].isin(POD)]
        df_dash = df_dash[df_dash['STP'].isin(STP)]
        df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
        df_dash = df_dash[df_dash['Activity Type'].isin(Checklist_eRS)]
        df_dash_group = df_dash.groupby(['STP', 'POD'], as_index=False)[
            'Actual Activity', 'Plan Activity'].sum()
        df_dash_group['Plan Utilisation (%)'] = (df_dash_group['Actual Activity']/df_dash_group['Plan Activity'])*100
        df_dash_group['Plan Utilisation (%)'] = df_dash_group['Plan Utilisation (%)'].replace([np.inf, -np.inf], np.nan)
        df_card = df_dash_group['Plan Utilisation (%)'].mean()
        df_card = df_card.round(2)
        #df_card.map('{:.0f}'.format)

        return df_card

#============================================ CARD UTILISATION WEEKLY CALLBACK =========================================

@app.callback(Output('Card Utilisation Week', 'children'),
              [
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist', component_property='value'),
               Input(component_id='Checklist-eRS', component_property='value')]
              )

def render_content(POD,STP,Checklist,Checklist_eRS):


        df_dash = df_merged.copy()
        df_dash = df_dash[df_dash['POD'].isin(POD)]
        df_dash = df_dash[df_dash['STP'].isin(STP)]
        df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
        df_dash = df_dash[df_dash['Activity Type'].isin(Checklist_eRS)]
        df_dash = df_dash[df_dash['Week Commencing Date']==most_recent_date]
        df_dash_group = df_dash.groupby(['STP', 'POD'], as_index=False)[
            'Actual Activity', 'Plan Activity'].sum()
        df_dash_group['Plan Utilisation (%)'] = (df_dash_group['Actual Activity']/df_dash_group['Plan Activity'])*100
        df_dash_group['Plan Utilisation (%)'] = df_dash_group['Plan Utilisation (%)'].replace([np.inf, -np.inf], np.nan)
        df_card = df_dash_group['Plan Utilisation (%)'].mean()
        #df_card.map('{:.0f}'.format)
        df_card = df_card.round(2)

        return df_card

#============================================ LINE GRAPH CALLBACK ======================================================

@app.callback(Output('Line', 'figure'),
              [
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist', component_property='value'),
               Input(component_id='Checklist-eRS', component_property='value')]
              )

def render_content(POD,STP,Checklist,Checklist_eRS):


        df_dash = df_merged.copy()
        df_dash = df_dash[df_dash['POD'].isin(POD)]
        df_dash = df_dash[df_dash['STP'].isin(STP)]
        df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
        df_dash = df_dash[df_dash['Activity Type'].isin(Checklist_eRS)]
        # df_dash = df_dash[df_dash['Week Commencing Date']==oldest_date]
        df_dash_group = df_dash.groupby(['Week Commencing Date'], as_index=False)[
            'Actual Activity', 'Plan Activity'].sum()

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=df_dash_group["Week Commencing Date"], y=df_dash_group["Actual Activity"], name='Actuals',
                                 line=dict(color='royalblue', width=4)))

        fig.add_trace(go.Scatter(x=df_dash_group["Week Commencing Date"], y=df_dash_group["Plan Activity"], name='Plan',
                                 line=dict(color='firebrick', width=4, dash='dot')))

        fig.update_xaxes(showgrid=True, ticklabelmode="period", dtick="M1", tickformat="%b\n%Y", title='')

        fig.update_xaxes(
            rangeslider_visible=False,
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )


        return fig

#============================================ BAR GRAPH CALLBACK ======================================================

@app.callback(Output('Bar', 'figure'),
              [
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist', component_property='value'),
               Input(component_id='Checklist-eRS', component_property='value')]
              )

def render_content(POD,STP,Checklist,Checklist_eRS):


        df_dash = df_merged.copy()
        df_dash = df_dash[df_dash['POD'].isin(POD)]
        df_dash = df_dash[df_dash['STP'].isin(STP)]
        df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
        df_dash = df_dash[df_dash['Activity Type'].isin(Checklist_eRS)]
        df_dash_group = df_dash.groupby(['POD', 'Week Commencing Date'], as_index=False)[
            'Actual Activity', 'Plan Activity'].sum()
        df_dash_group['Plan Utilisation (%)'] = (df_dash_group['Actual Activity'] / df_dash_group['Plan Activity']) * 100
        df_dash_group['Plan Utilisation (%)'] = df_dash_group['Plan Utilisation (%)'].replace([np.inf, -np.inf],np.nan)

        fig = px.histogram(df_dash_group, x="Week Commencing Date", y="Plan Utilisation (%)", histfunc="avg")
        fig.update_layout(bargap=0.1)
        fig.update_xaxes(showgrid=True, ticklabelmode="period", dtick="M1", tickformat="%b\n%Y", title='')
        fig.add_trace(go.Scatter(mode="markers", x=df_dash_group["Week Commencing Date"], y=df_dash_group["Plan Utilisation (%)"], name="weekly values"))
        #fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(yaxis_title="Plan Utilisation (%)",)
        fig

        return fig


#============================================ MAP TAB CALLBACK =========================================================
access_token = 'pk.eyJ1IjoiemFpbmVpc2EiLCJhIjoiY2tlZWg0MXJvMGcwZzJyb3k1OXh0Ym55aiJ9.0SJ_VBRVxyWd6SmbdUwmKQ'

@app.callback(Output('Map_content', 'figure'),
              [#Input('tabs', 'value'),
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist-eRS', component_property='value')
               ])


def render_content(POD,STP,Checklist_eRS):

        dfmap = df_merged
        #dfmap = dfmap.drop(dfmap[(dfmap['Plan Or Actual'] == 'Actuals')].index)
        dfmap = dfmap[dfmap['POD'].isin(POD)]
        dfmap = dfmap[dfmap['STP'].isin(STP)]
        dfmap = dfmap[dfmap['Activity Type'].isin(Checklist_eRS)]
        #dfmap = dfmap[(dfmap['Week Index'] >= Date[0]) & (dfmap['Week Index'] <= Date[1])]
        # REMEMBER the as_index function turns the aggregate output from a Series into a Dataframe - important as some graphs/figures need Dfs
        dfmap_group = dfmap.groupby(['STP', 'Independent Provider', 'Lat', 'Long'], as_index=False)['Actual Activity'].sum()
        dfmap_group['Actual Activity for label'] = dfmap_group['Actual Activity'].map('{:,.0f}'.format)
        dfmap_group['Label'] = dfmap_group['Actual Activity for label'].astype(str) + ' activities at ' + dfmap_group['Independent Provider'] + ' within ' + dfmap_group['STP']

        locations = [go.Scattermapbox(
            lon=dfmap_group['Long'],
            lat=dfmap_group['Lat'],
            mode='markers',
            unselected={'marker': {'opacity': 0.5}},
            selected={'marker': {'opacity': 1, 'size': 50}},
            hoverinfo='text',
            hovertext=dfmap_group['Label'],
            marker=dict(
                size=dfmap_group['Actual Activity'] / 2.5,
                color='blue',
                sizemode='area'
            )
        )]

        return {
                    'data': locations,
                    'layout': go.Layout(
                        uirevision='foo',  # preserves state of figure/map after callback activated
                        clickmode='event+select',
                        margin=dict(l=0, r=0, t=0, b=0),
                        hovermode='closest',
                        hoverdistance=2,
                        # title=dict(text="COVID CASES MAPPED", font = dict(size=35)), #irrelevant with the margins given
                        mapbox=dict(
                            accesstoken=access_token,
                            bearing=25,
                            # style='dark', # Can enter to style the graph
                            center=dict(
                                lat=51.505958,
                                # 51.50853, # is technically the centre of London, but the other co-ordinates fit better
                                lon=-0.126770
                                # -0.12574 # is technically the centre of London, but the other co-ordinates fit better
                            ),
                            pitch=20,
                            zoom=9.5
                        ),
                    )
                }



#=======================================================================================================================
if __name__ == '__main__':
    app.run_server(debug=True)
