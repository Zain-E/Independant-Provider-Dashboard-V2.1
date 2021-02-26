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


#========================================== LOADING THE DATA ===========================================================

#load data
df1 = pd.read_csv(r'Raw_Data_Final.csv', encoding='ISO-8859-1', low_memory=False)
#print(df1)

#Load Location data
location_df = pd.read_csv(r'Location_data.csv', encoding='ISO-8859-1', low_memory=False)
#print(location_df)

#Map
df_map_original = pd.read_csv(r'ISP_Data_Plan.csv', encoding='ISO-8859-1', low_memory=False)

#Join dataframes
df = pd.merge(df1,location_df,on='Provider', how='left')

#replace blanks with 0
#df['Activity Count'] = df['Activity Count'].replace(np.nan, '', regex=True)
df['Activity Count'].fillna(0, inplace=True)

#Create short hand descriptions for the Graphs
short_hand_dic = {'Parkside (Aspen Healthcare)' : 'Parkside',
                    'Shirley Oaks (BMI Healthcare)' : 'S.Oaks',
                    'Ashtead (Ramsay Health UK)' : 'Ashtead',
                    'The New Victoria Hospital (The New Victoria Hospital Limited)' : 'N.Vic',
                    "St Anthony's (Spire Healthcare)" : 'St.Ant',
                    'Cavell (BMI Healthcare)' : 'Cavell',
                    'Kings Oak (BMI Healthcare)' : 'K.Oak',
                    'Highgate Private (Aspen Healthcare)' : 'Highgate',
                    'Schoen Clinic London (Schoen Clinic UK)' : 'Schoen',
                    'The Wellington Hospital (HCA UK)' : 'Welling',
                    'The Princess Grace (HCA UK)' : 'P.Grace',
                    'The Harley Street Clinic (HCA UK)' : 'Harley.St',
                    'The London Clinic (The London Clinic)' : 'London.C',
                    'Hendon (BMI Healthcare)' : 'Hendon',
                    'Holly House (Holly House)' : 'Holly.H',
                    'London East (Spire Healthcare)' : 'L.East',
                    'London Independent (BMI Healthcare)' : 'L.indep',
                    'Weymouth Street Hospital (Phoenix Hospital Group)' : 'Weymouth',
                    'North East London Teatment Centre (Care UK Clinical Services Limited)' : 'N.E.L',
                    'Spire Hartswood' : 'Spire.Har',
                    'The Portland (HCA UK)' : 'Portland',
                    'West Valley (Ramsay Health UK)' : 'W.Valley',
                    'Fortius Clinic (Fortius Clinic)' : 'Fortius',
                    'Chelsfield (BMI Healthcare)' : 'Chelsf',
                    'Blackheath (BMI Healthcare)' : 'BlackH',
                    'London Bridge (HCA UK)' : 'L.Bridge',
                    'Harley Street on 15 (HCA UK)' : 'H.on15',
                    'Bishopswood (BMI Healthcare)' : 'Bishops.W',
                    'Bupa Cromwell Hospital (Bupa Group)' : 'B.Crom',
                    'Hospital of St John & St Elizabeth (Hospital of St John & St Elizabeth)' : 'St.John',
                    "KING EDWARD VII'S HOSPITAL SISTER AGNES (KING EDWARD VII'S HOSPITAL SISTER AGNES HQ)" : 'KEV',
                    'The Lister (HCA UK)' : 'Lister',
                    'Clementine Churchill (BMI Healthcare)' : 'Clem.Church',
                    'HCA Chiswick' : 'Chiswick',
                    'Sloane (BMI Healthcare)' : 'Sloane'}

#Add these short hand names as df columns
df['Provider_short'] = df['Provider'].map(short_hand_dic)
print(df.shape)

#Remove the PODs that are not the 4 main PODs
df = df[(df['POD'] !='DNA/Cancellation (Theatres Only)') & (df['POD'] !='Number of 1/2 Day Lists (Theatres Only)')]
print(df.shape)

#Create a df of unique dates for the Range Slider
df_slider = df['Week Commencing Date'].unique()
# df_slider= pd.DataFrame(df_slider)
# df_slider.rename(columns={0: "Date"}, inplace=True)
#df_slider = pd.to_datetime(df_slider)
#df_slider.sort_values('Date', ascending=True)
#print(df_slider)

#Tweak the above df to give the dates an index that can be referenced using the slider!
weekindex = {int(i): str(df_slider[i]) for i in range(len(df_slider))} #would usually need LEN - 1 to account for index 0
df_weekindex = pd.DataFrame.from_dict(weekindex, orient='index', columns=['Date'])
#print(df_weekindex)

#We now need to unstack the data to create 3 fact columns, actuals, plan and capacity
#Needs to be done for the diagnostics separately as it needs to be grouped differently
#First by creating 3 separate datasets after grouping (slightly)
df_grouped = df.groupby(['Inner or Outer','Plan or Actuals','Activity Type', 'Provider','STP','POD','Week Commencing Date','Lat','Long'], as_index=False)['Activity Count'].sum()
df_actuals = df_grouped[(df_grouped['Plan or Actuals'] =='Actuals')]
df_actuals.rename(columns={"Activity Count": "Actual Activity"}, inplace=True)
df_plan = df_grouped[(df_grouped['Plan or Actuals'] =='Plan')]
df_plan.rename(columns={"Activity Count": "Plan Activity"}, inplace=True)
df_grouped_capacity = df.groupby(['Inner or Outer','Plan or Actuals','Activity Type', 'Provider','STP','POD','Week Commencing Date','Lat','Long'], as_index=False)['Activity Count'].mean()
df_capacity = df_grouped_capacity[(df_grouped_capacity['Plan or Actuals'] =='Capacity')]
df_capacity.rename(columns={"Activity Count": "Capacity"}, inplace=True)


print(f'df actuals = {df_actuals.shape}')
print(f'df capacity = {df_capacity.shape}')
print(f'df plan = {df_plan.shape}')

#Now we need to merge the datasets so we have 2 extra fact columns - plan and capacity values, this will be much easier to plot on tables/graphs
df_merged = df_actuals.merge(df_plan, on=['Activity Type','Provider','STP','POD','Week Commencing Date'], how='left')
df_merged = df_merged.drop(['Inner or Outer_y','Plan or Actuals_y','Lat_y','Long_y'], axis=1)
df_merged = df_merged.merge(df_capacity, on=['Activity Type','Provider','STP','POD','Week Commencing Date'], how='left')
df_merged = df_merged.drop(['Inner or Outer','Plan or Actuals','Lat','Long'], axis=1)
df_merged.rename(columns={"Plan or Actuals_x": "Plan or Actuals",'Inner or Outer_x':'Inner or Outer','Lat_x':'Lat','Long_x':'Long'}, inplace=True)

#Fill blanks for new columns
df_merged['Capacity'].fillna(0, inplace=True)
df_merged['Plan Activity'].fillna(0, inplace=True)

#Find the most recent date
df_merged['Week Commencing Date'] = pd.to_datetime(df_merged['Week Commencing Date'])
most_recent_date = df_merged['Week Commencing Date'].max()
oldest_date = df_merged['Week Commencing Date'].min()

print(most_recent_date)


#Will save the DFs for checking and analysis
#df_actuals.to_csv(r'D:\My Key Documents\365 Data Science Videos\Zains Python Code + Projects\Python Project 2 - Data Dashboard of Independant Providers (NHS)/check.csv', index=True, header=True)
#df_plan.to_csv(r'D:\My Key Documents\365 Data Science Videos\Zains Python Code + Projects\Python Project 2 - Data Dashboard of Independant Providers (NHS)/check2.csv', index=True, header=True)
#df_merged.to_csv(r'C:\Users\Zain\PycharmProjects\IndependantProviderDashboardV2\merged.csv', index=True, header=True)

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

                        # html.Br(),
                        #
                        # dbc.Col(dcc.RangeSlider(id='Date_Slider',
                        #                         min=0,
                        #                         max=len(df_slider),
                        #                         # subtract 5 instead of 1 due to invalid dates that do not need to be on the slider in the last 3 positions
                        #                         step=None,
                        #                         marks={int(i+2): str(df_slider[i+2]) for i in range(len(df_slider)-2)},
                        #                         value=[],
                        #                         ), width=12),

                        html.Br(),

                        dbc.Row(dbc.Col(
                                        dcc.Checklist(id='Checklist',
                                                      options=[
                                                        {'label': 'Outer Providers', 'value': 'Outer'},
                                                        {'label': 'Inner Providers', 'value':'Inner'}
                                                      ],
                                                      value=['Outer'],
                                                      #labelStyle={'display': 'inline-block'},
                        ),style={'text-align': 'center','vertical-align':'middle'})),

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
                                        initial_visible_month=date(2020, 1, 1),
                                        start_date=date(2020,3,1),
                                        end_date=date(2020,11,1),
                                        style={'position':'relative', 'zIndex':'999'}
                                    ), width={'offset': 1})),

                                    html.Div(id='Table')

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

                                ])
                       ])

])

#width={'size': 12}

#=========================================== UTILISATION TABLE CALLBACK ================================================

@app.callback(Output('Table', 'children'),
              [
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist', component_property='value'),
              Input(component_id='date', component_property='start_date'),
              Input(component_id='date', component_property='end_date')]
              )
def render_content(POD,STP,Checklist,start_date,end_date):

    df_dash = df_merged.copy()
    df_dash = df_dash[df_dash['POD'].isin(POD)]
    df_dash = df_dash[df_dash['STP'].isin(STP)]
    df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
    df_dash = df_dash[(df_dash['Week Commencing Date'] >= start_date) & (df_dash['Week Commencing Date'] <= end_date)]
    df_dash_group = df_dash.groupby(['STP', 'Provider'], as_index=False)[
        'Actual Activity', 'Plan Activity', 'Capacity'].sum()
    df_dash_group['Plan Utilisation (%)'] = (df_dash_group['Actual Activity']/df_dash_group['Plan Activity'])*100
    df_dash_group['Plan Utilisation (%)'] = df_dash_group['Plan Utilisation (%)'].replace([np.inf, -np.inf], np.nan)
    df_dash_group['Capacity Utilisation (%)'] = (df_dash_group['Actual Activity'] / df_dash_group['Capacity']) * 100
    df_dash_group['Capacity Utilisation (%)'] = df_dash_group['Capacity Utilisation (%)'].replace([np.inf, -np.inf], np.nan)

    #Formatting
    df_dash_group['Actual Activity'] = df_dash_group['Actual Activity'].map('{:,.0f}'.format)#to get numbers in format correctly
    df_dash_group['Plan Activity'] = df_dash_group['Plan Activity'].map('{:,.0f}'.format)  # to get numbers in format correctly
    df_dash_group['Capacity'] = df_dash_group['Capacity'].map('{:,.0f}'.format)  # to get numbers in format correctly
    df_dash_group['Plan Utilisation (%)'] = df_dash_group['Plan Utilisation (%)'].map('{:.0f}'.format)  # to get numbers in format correctly
    df_dash_group['Capacity Utilisation (%)'] = df_dash_group['Capacity Utilisation (%)'].map('{:.0f}'.format)

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
                                             {'if': {'column_id': 'Provider'},
                                              'width': '40%'},  # 300
                                             {'if': {'column_id': 'Actual Activity'},
                                              'width': '6%',
                                              'textAlign': 'center'},
                                             {'if': {'column_id': 'Plan Activity'},
                                              'width': '6%',
                                              'textAlign': 'center',
                                              },# 5
                                             {'if': {'column_id': 'Capacity'},
                                              'width': '6%',
                                              'textAlign': 'center',
                                              },
                                             {'if': {'column_id': 'Plan Utilisation (%)'},
                                              'width': '9%',
                                              'textAlign': 'center',
                                              },
                                             {'if': {'column_id': 'Capacity Utilisation (%)'},
                                              'width': '9%',
                                              'textAlign': 'center',
                                              },

                                         ],

                         style_data_conditional=[{
                                                 'if': {
                                                     'filter_query': '{Plan Utilisation (%)} >= 0 && {Plan Utilisation (%)} < 60',
                                                     'column_id': 'Plan Utilisation (%)'
                                                 },
                                                 'backgroundColor': 'tomato',
                                                 'color': 'white'
                                             },
                                             {
                                                 'if': {
                                                     'filter_query': '{Plan Utilisation (%)} > 80',
                                                     'column_id': 'Plan Utilisation (%)'
                                                 },
                                                 'backgroundColor': 'green',
                                                 'color': 'white'
                                             },
                                             {
                                                 'if': {
                                                     'filter_query': '{Plan Utilisation (%)} > 60 && {Plan Utilisation (%)} < 80',
                                                     'column_id': 'Plan Utilisation (%)'
                                                 },
                                                 'backgroundColor': 'orange',
                                                 'color': 'white'
                                             },
                                             {
                                                 'if': {
                                                     'filter_query': '{Plan Utilisation (%)} contains "nan"',
                                                     'column_id': 'Plan Utilisation (%)'
                                                 },
                                                 'backgroundColor': 'rgb(204,204,204)',
                                                 'color': 'grey',
                                                 'fontWeight':'bold'
                                             },
                             {
                                 'if': {
                                     'filter_query': '{Capacity Utilisation (%)} >= 0 && {Capacity Utilisation (%)} < 60',
                                     'column_id': 'Capacity Utilisation (%)'
                                 },
                                 'backgroundColor': 'tomato',
                                 'color': 'white'
                             },
                             {
                                 'if': {
                                     'filter_query': '{Capacity Utilisation (%)} > 80',
                                     'column_id': 'Capacity Utilisation (%)'
                                 },
                                 'backgroundColor': 'green',
                                 'color': 'white'
                             },
                             {
                                 'if': {
                                     'filter_query': '{Capacity Utilisation (%)} > 60 && {Capacity Utilisation (%)} < 80',
                                     'column_id': 'Capacity Utilisation (%)'
                                 },
                                 'backgroundColor': 'orange',
                                 'color': 'white'
                             },
                             {
                                 'if': {
                                     'filter_query': '{Capacity Utilisation (%)} contains "nan"',
                                     'column_id': 'Capacity Utilisation (%)'
                                 },
                                 'backgroundColor': 'rgb(204,204,204)',
                                 'color': 'grey',
                                 'fontWeight': 'bold'
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
               Input(component_id='Checklist', component_property='value')]
              )

def render_content(POD,STP,Checklist):


        df_dash = df_merged.copy()
        df_dash = df_dash[df_dash['POD'].isin(POD)]
        df_dash = df_dash[df_dash['STP'].isin(STP)]
        df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
        df_dash_group = df_dash.groupby(['STP', 'POD'], as_index=False)[
            'Actual Activity', 'Plan Activity', 'Capacity'].sum()
        df_dash_group['Plan Utilisation (%)'] = (df_dash_group['Actual Activity']/df_dash_group['Plan Activity'])*100
        df_dash_group['Plan Utilisation (%)'] = df_dash_group['Plan Utilisation (%)'].replace([np.inf, -np.inf], np.nan)
        df_dash_group['Capacity Utilisation (%)'] = (df_dash_group['Actual Activity'] / df_dash_group['Capacity']) * 100
        df_dash_group['Capacity Utilisation (%)'] = df_dash_group['Capacity Utilisation (%)'].replace([np.inf, -np.inf], np.nan)
        df_card = df_dash_group['Capacity Utilisation (%)'].mean()
        df_card = df_card.round(2)
        #df_card.map('{:.0f}'.format)

        return df_card

#============================================ CARD UTILISATION WEEKLY CALLBACK =========================================

@app.callback(Output('Card Utilisation Week', 'children'),
              [
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist', component_property='value')]
              )

def render_content(POD,STP,Checklist):


        df_dash = df_merged.copy()
        df_dash = df_dash[df_dash['POD'].isin(POD)]
        df_dash = df_dash[df_dash['STP'].isin(STP)]
        df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
        df_dash = df_dash[df_dash['Week Commencing Date']==oldest_date]
        df_dash_group = df_dash.groupby(['STP', 'POD'], as_index=False)[
            'Actual Activity', 'Plan Activity', 'Capacity'].sum()
        df_dash_group['Plan Utilisation (%)'] = (df_dash_group['Actual Activity']/df_dash_group['Plan Activity'])*100
        df_dash_group['Plan Utilisation (%)'] = df_dash_group['Plan Utilisation (%)'].replace([np.inf, -np.inf], np.nan)
        df_dash_group['Capacity Utilisation (%)'] = (df_dash_group['Actual Activity'] / df_dash_group['Capacity']) * 100
        df_dash_group['Capacity Utilisation (%)'] = df_dash_group['Capacity Utilisation (%)'].replace([np.inf, -np.inf], np.nan)
        df_card = df_dash_group['Capacity Utilisation (%)'].mean()
        #df_card.map('{:.0f}'.format)
        df_card = df_card.round(2)

        return df_card

#============================================ LINE GRAPH CALLBACK ======================================================

@app.callback(Output('Line', 'figure'),
              [
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value'),
               Input(component_id='Checklist', component_property='value')]
              )

def render_content(POD,STP,Checklist):


        df_dash = df_merged.copy()
        df_dash = df_dash[df_dash['POD'].isin(POD)]
        df_dash = df_dash[df_dash['STP'].isin(STP)]
        df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
        # df_dash = df_dash[df_dash['Week Commencing Date']==oldest_date]
        df_dash_group = df_dash.groupby(['Week Commencing Date'], as_index=False)[
            'Actual Activity', 'Capacity'].sum()

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=df_dash_group["Week Commencing Date"], y=df_dash_group["Actual Activity"], name='Actuals',
                                 line=dict(color='royalblue', width=4)))

        fig.add_trace(go.Scatter(x=df_dash_group["Week Commencing Date"], y=df_dash_group["Capacity"], name='Capacity',
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
               Input(component_id='Checklist', component_property='value')]
              )

def render_content(POD,STP,Checklist):


        df_dash = df_merged.copy()
        df_dash = df_dash[df_dash['POD'].isin(POD)]
        df_dash = df_dash[df_dash['STP'].isin(STP)]
        df_dash = df_dash[df_dash['Inner or Outer'].isin(Checklist)]
        df_dash_group = df_dash.groupby(['POD', 'Week Commencing Date'], as_index=False)[
            'Actual Activity', 'Plan Activity', 'Capacity'].sum()
        df_dash_group['Capacity Utilisation (%)'] = (df_dash_group['Actual Activity'] / df_dash_group['Capacity']) * 100
        df_dash_group['Capacity Utilisation (%)'] = df_dash_group['Capacity Utilisation (%)'].replace([np.inf, -np.inf],np.nan)

        fig = px.histogram(df_dash_group, x="Week Commencing Date", y="Capacity Utilisation (%)", histfunc="avg")
        fig.update_layout(bargap=0.1)
        fig.update_xaxes(showgrid=True, ticklabelmode="period", dtick="M1", tickformat="%b\n%Y", title='')
        fig.add_trace(go.Scatter(mode="markers", x=df_dash_group["Week Commencing Date"], y=df_dash_group["Capacity Utilisation (%)"], name="weekly values"))
        #fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(yaxis_title="Capacity Utilisation (%)",)
        fig

        return fig


#============================================ MAP TAB CALLBACK =========================================================
access_token = 'pk.eyJ1IjoiemFpbmVpc2EiLCJhIjoiY2tlZWg0MXJvMGcwZzJyb3k1OXh0Ym55aiJ9.0SJ_VBRVxyWd6SmbdUwmKQ'

@app.callback(Output('Map_content', 'figure'),
              [#Input('tabs', 'value'),
               Input(component_id='POD_Dropdown', component_property='value'),
               Input(component_id='STP_Dropdown', component_property='value')
               ])


def render_content(POD,STP):

        dfmap = df_merged
        #dfmap = dfmap.drop(dfmap[(dfmap['Plan Or Actual'] == 'Actuals')].index)
        dfmap = dfmap[dfmap['POD'].isin(POD)]
        dfmap = dfmap[dfmap['STP'].isin(STP)]
        #dfmap = dfmap[(dfmap['Week Index'] >= Date[0]) & (dfmap['Week Index'] <= Date[1])]
        # REMEMBER the as_index function turns the aggregate output from a Series into a Dataframe - important as some graphs/figures need Dfs
        dfmap_group = dfmap.groupby(['STP', 'Provider', 'Lat', 'Long'], as_index=False)['Actual Activity'].sum()
        dfmap_group['Actual Activity for label'] = dfmap_group['Actual Activity'].map('{:,.0f}'.format)
        dfmap_group['Label'] = dfmap_group['Actual Activity for label'].astype(str) + ' activities at ' + dfmap_group['Provider'] + ' within ' + dfmap_group['STP']

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
