"""
NCAA Baseball School Finder - Python/Dash Version
Interactive dashboard for exploring NCAA baseball programs with academic and athletic filters
"""

import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import json
import requests
import os
from dotenv import load_dotenv
import time

# Firebase imports
from auth_components import (
    create_login_modal, create_user_menu, create_saved_schools_modal,
    create_analytics_modal, create_session_stores
)
from auth_callbacks import register_auth_callbacks

# Load environment variables
load_dotenv()

# College Scorecard API configuration
COLLEGE_SCORECARD_API_KEY = os.getenv('COLLEGE_SCORECARD_API_KEY')
COLLEGE_SCORECARD_API_URL = 'https://api.data.gov/ed/collegescorecard/v1/schools'

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes"}
    ]
)

# Expose Flask server for Gunicorn
server = app.server

# ============================================================================
# DATA LOADING
# ============================================================================

print("Loading data files...")

# Load main data
input_data = pd.read_csv('input_filtered.csv')
climate_data = pd.read_csv('climate_data_processed.csv')
climate_monthly = pd.read_csv('climate_data_monthly_long.csv')
roster_data = pd.read_csv('combined_ncaa_rosters_filtered.csv')
roster_data_full = pd.read_csv('combined_ncaa_rosters.csv')  # Full roster with positions
team_history = pd.read_csv('ncaa_team_history_updated.csv')
coach_metrics = pd.read_csv('team_coach_metrics.csv')

# Merge climate data
merged_data = input_data.merge(climate_data, on='unitid', how='left')

# Filter out rows without location data
merged_data = merged_data.dropna(subset=['latitude', 'longitude'])

# Calculate derived fields
merged_data['win_pct'] = np.where(
    (merged_data['wins'] + merged_data['losses']) > 0,
    (merged_data['wins'] / (merged_data['wins'] + merged_data['losses']) * 100).round(1),
    0
)
merged_data['accept_rate_pct'] = (merged_data['adm_rate'] * 100).round(1)
merged_data['sat_score'] = merged_data['sat_avg'].fillna(0)

# ============================================================================
# ROSTER METRICS HELPER FUNCTIONS
# ============================================================================

def calculate_team_trajectory(school_data, merged_data_full):
    """Get 10-year win% history for plotting"""
    try:
        # Use prev_team_id to match with team_history
        prev_team_id = school_data['prev_team_id'] if 'prev_team_id' in school_data else school_data.get('prev_team_id')
        
        if pd.isna(prev_team_id):
            print(f"No prev_team_id for school")
            return None
        
        # Convert to numeric for matching
        prev_team_id = int(float(prev_team_id))
        
        print(f"Looking for trajectory data for prev_team_id: {prev_team_id}")
        
        # Get historical data for this school using prev_team_id
        school_history = team_history[team_history['prev_team_id'] == prev_team_id].copy()
        
        if school_history.empty:
            print(f"No historical data found for prev_team_id: {prev_team_id}")
            return None
        
        print(f"Found {len(school_history)} years of data")
        
        # Convert Year from "2025-26" format to numeric (use ending year: 2026)
        # This way "2024-25" becomes 2025, representing when the season ends
        # Works for any century: "1898-99" -> 1899, "1999-00" -> 2000, "2024-25" -> 2025
        school_history['Year'] = school_history['Year'].astype(str).str.split('-').str[0].astype(int) + 1
        
        # Convert WL_pct from ".596" to 0.596
        school_history['WL_pct'] = pd.to_numeric(school_history['WL_pct'].astype(str).str.replace('.', '', regex=False), errors='coerce') / 1000
        
        # Filter out only invalid data (NaN), but keep 0 wins (winless seasons)
        school_history = school_history[school_history['WL_pct'].notna()]
        
        # Get last 10 years of complete data (up to most recent complete season)
        current_year = 2025  # Current date is Dec 2025, so 2024-25 season (labeled 2025) just ended
        school_history = school_history[
            (school_history['Year'] >= current_year - 9) & 
            (school_history['Year'] <= current_year)
        ].sort_values('Year')
        
        if len(school_history) < 2:
            return None
        
        # Calculate trend
        years = school_history['Year'].values
        win_pcts = school_history['WL_pct'].values
        
        # Simple linear regression
        if len(years) > 1:
            slope = np.polyfit(years, win_pcts, 1)[0]
            if slope > 0.01:
                trend = 'improving'
                indicator = '↑'
                color = '#28a745'
            elif slope < -0.01:
                trend = 'declining'
                indicator = '↓'
                color = '#dc3545'
            else:
                trend = 'stable'
                indicator = '→'
                color = '#888888'
        else:
            trend = 'stable'
            indicator = '→'
            color = '#888888'
        
        return {
            'trend': trend,
            'indicator': indicator,
            'color': color,
            'years': years.tolist(),
            'win_pcts': (win_pcts * 100).tolist(),  # Convert to percentage
            'current_pct': win_pcts[-1] * 100 if len(win_pcts) > 0 else 0
        }
    except Exception as e:
        print(f"Error calculating team trajectory: {e}")
        return None

def get_state_distribution_charts(school_data):
    """Create pie charts showing geographic distribution of players"""
    try:
        prev_team_id = school_data['prev_team_id'] if 'prev_team_id' in school_data else school_data.get('prev_team_id')
        
        if pd.isna(prev_team_id):
            return None, None
        
        prev_team_id = int(float(prev_team_id))
        
        # Get roster data for this team
        team_rosters = roster_data[roster_data['prev_team_id'] == prev_team_id].copy()
        
        if team_rosters.empty:
            return None, None
        
        # Most recent season (2025)
        recent_roster = team_rosters[team_rosters['year'] == 2025]
        if not recent_roster.empty:
            recent_states = recent_roster[recent_roster['State'].notna() & (recent_roster['State'] != '')]['State'].value_counts()
            # Keep top 8 states, group rest as "Other"
            if len(recent_states) > 8:
                top_states = recent_states.head(8)
                other_count = recent_states[8:].sum()
                recent_states = pd.concat([top_states, pd.Series({'Other': other_count})])
            
            fig_recent = go.Figure(data=[go.Pie(
                labels=recent_states.index,
                values=recent_states.values,
                hole=0.3,
                textinfo='label+percent',
                hovertemplate='%{label}: %{value} players<extra></extra>'
            )])
            fig_recent.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=30, b=20),
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
            )
        else:
            fig_recent = None
        
        # 2022-2025 aggregated
        multi_year = team_rosters[team_rosters['year'].between(2022, 2025)]
        if not multi_year.empty:
            multi_states = multi_year[multi_year['State'].notna() & (multi_year['State'] != '')]['State'].value_counts()
            # Keep top 8 states, group rest as "Other"
            if len(multi_states) > 8:
                top_states = multi_states.head(8)
                other_count = multi_states[8:].sum()
                multi_states = pd.concat([top_states, pd.Series({'Other': other_count})])
            
            fig_multi = go.Figure(data=[go.Pie(
                labels=multi_states.index,
                values=multi_states.values,
                hole=0.3,
                textinfo='label+percent',
                hovertemplate='%{label}: %{value} players<extra></extra>'
            )])
            fig_multi.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=30, b=20),
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
            )
        else:
            fig_multi = None
        
        return fig_recent, fig_multi
        
    except Exception as e:
        print(f"Error creating state distribution charts: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def calculate_freshman_retention(school_data):
    """Calculate freshman retention rate - percentage of freshmen who return the following year"""
    prev_team_id = school_data.get('prev_team_id')
    
    if pd.isna(prev_team_id):
        return None
    
    try:
        prev_team_id_int = int(float(prev_team_id))
        
        # Get all roster data for this team
        team_roster = roster_data[roster_data['prev_team_id'] == prev_team_id_int].copy()
        
        if team_roster.empty:
            return None
        
        # Get unique years and sort
        unique_years = sorted(team_roster['year'].unique())
        
        retention_rates = []
        
        # Loop through consecutive year pairs
        for i in range(len(unique_years) - 1):
            current_yr = unique_years[i]
            next_yr = unique_years[i + 1]
            
            # Find freshmen in current year
            freshmen = team_roster[
                (team_roster['year'] == current_yr) & 
                (team_roster['class'].str.strip() == 'Fr.')
            ]['player_name'].unique()
            
            if len(freshmen) > 0:
                # Check how many returned in next year
                returning = team_roster[
                    (team_roster['year'] == next_yr) & 
                    (team_roster['player_name'].isin(freshmen))
                ]['player_name'].unique()
                
                rate = len(returning) / len(freshmen)
                retention_rates.append(rate)
        
        # Calculate average retention rate
        if retention_rates:
            avg_retention = sum(retention_rates) / len(retention_rates) * 100
            return round(avg_retention, 1)
        else:
            return None
            
    except Exception as e:
        print(f"Error calculating freshman retention: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_instate_recruiting(school_data, roster_data_full):
    """Calculate percentage of roster from home state"""
    try:
        unitid = school_data['unitid'] if 'unitid' in school_data else school_data.get('unitid')
        home_state = school_data['state_abbr'] if 'state_abbr' in school_data else school_data.get('state_abbr', '')
        
        if unitid not in roster_data_full['unitid'].values or not home_state:
            return 0
        
        school_roster = roster_data_full[roster_data_full['unitid'] == unitid]
        
        # Check if we have state information in roster
        if 'top_state_1' in school_roster.columns:
            # Use top recruiting state data
            total_players = school_data.get('total_players', 0)
            if total_players == 0:
                return 0
            
            # Count players from home state - check all top states
            home_state_count = 0
            top_state_1 = str(school_data.get('top_state_1', '')).strip()
            top_state_2 = str(school_data.get('top_state_2', '')).strip()
            top_state_3 = str(school_data.get('top_state_3', '')).strip()
            
            if top_state_1 == home_state:
                home_state_count += school_data.get('top_state_1_count', 0)
            if top_state_2 == home_state:
                home_state_count += school_data.get('top_state_2_count', 0)
            if top_state_3 == home_state:
                home_state_count += school_data.get('top_state_3_count', 0)
            
            return round((home_state_count / total_players) * 100, 1) if total_players > 0 else 0
        
        return 0
    except Exception as e:
        print(f"Error calculating in-state recruiting: {e}")
        return 0
        return 0

def get_playing_time_by_class(school_data):
    """Get average games played by class year"""
    try:
        # Use roster count data as proxy
        return {
            'Fr': school_data.get('count_Fr', 0),
            'So': school_data.get('count_So', 0),
            'Jr': school_data.get('count_Jr', 0),
            'Sr': school_data.get('count_Sr', 0)
        }
    except:
        return {'Fr': 0, 'So': 0, 'Jr': 0, 'Sr': 0}

def inches_to_feet_inches(inches):
    """Convert decimal inches to feet'inches" format"""
    if pd.isna(inches) or not inches or inches == 0:
        return "N/A"
    feet = int(inches // 12)
    remaining_inches = int(round(inches % 12))
    return f"{feet}'{remaining_inches}\""

def get_position_depth(school_data):
    """Get roster count by position group from actual roster data"""
    try:
        prev_team_id = school_data.get('prev_team_id')
        
        if pd.isna(prev_team_id):
            return {'P': 0, 'C': 0, 'IF': 0, 'OF': 0}
        
        prev_team_id_int = int(float(prev_team_id))
        
        # Get most recent year's roster (2025)
        team_roster = roster_data_full[
            (roster_data_full['prev_team_id'] == prev_team_id_int) & 
            (roster_data_full['year'] == 2025)
        ]
        
        if team_roster.empty:
            return {'P': 0, 'C': 0, 'IF': 0, 'OF': 0}
        
        # Count by position groups
        pitchers = 0
        catchers = 0
        infielders = 0
        outfielders = 0
        
        for _, player in team_roster.iterrows():
            pos = str(player.get('position', '')).strip().upper()
            
            # Pitchers: P, RHP, LHP, etc.
            if 'P' in pos and pos != 'DH':
                pitchers += 1
            # Catchers
            elif pos == 'C':
                catchers += 1
            # Infielders: 1B, 2B, 3B, SS, IF, INF
            elif any(x in pos for x in ['1B', '2B', '3B', 'SS', 'IF', 'INF']) and 'OF' not in pos:
                infielders += 1
            # Outfielders: OF, LF, CF, RF
            elif 'OF' in pos or any(x in pos for x in ['LF', 'CF', 'RF']):
                outfielders += 1
        
        return {
            'P': pitchers,
            'C': catchers,
            'IF': infielders,
            'OF': outfielders
        }
    except Exception as e:
        print(f"Error calculating position depth: {e}")
        return {'P': 0, 'C': 0, 'IF': 0, 'OF': 0}

def calculate_trajectory_display(school_data):
    """Create display for team trajectory metric with line chart"""
    trajectory = calculate_team_trajectory(school_data, merged_data)
    
    if not trajectory or 'years' not in trajectory:
        return html.Div([
            html.P("Historical data not available", className='text-muted')
        ])
    
    # Create line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=trajectory['years'],
        y=trajectory['win_pcts'],
        mode='lines+markers',
        line=dict(color=trajectory['color'], width=3),
        marker=dict(size=8),
        connectgaps=False,  # Don't connect lines across missing years
        hovertemplate='%{x}: %{y:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Win %",
        yaxis=dict(range=[0, 100]),
        height=250,
        margin=dict(l=40, r=20, t=20, b=40),
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e0e0e0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#e0e0e0')
    
    return html.Div([
        html.Div([
            html.Span(trajectory['indicator'], style={
                'fontSize': '2rem',
                'color': trajectory['color'],
                'marginRight': '10px'
            }),
            html.Span(f"{trajectory['trend'].title()}", style={
                'fontSize': '1.2rem',
                'fontWeight': 'bold'
            })
        ], style={'marginBottom': '10px'}),
        dcc.Graph(figure=fig, config={'displayModeBar': False}),
        html.Small(f"Current Win%: {trajectory['current_pct']:.1f}%", className='text-muted')
    ])

def calculate_instate_display(school_data):
    """Create display for in-state recruiting metric"""
    instate_pct = calculate_instate_recruiting(school_data, roster_data)
    
    # Create a simple progress bar as gauge
    return html.Div([
        html.Div([
            html.Strong(f"{instate_pct}%"),
            html.Span(" from home state", className='text-muted ms-2')
        ], style={'marginBottom': '10px'}),
        dbc.Progress(
            value=instate_pct,
            color="info" if instate_pct > 30 else "secondary",
            style={'height': '20px'}
        ),
        html.Small([
            html.Span(f"Top states: ", className='text-muted'),
            f"{school_data.get('top_state_1', 'N/A')} ({school_data.get('top_state_1_count', 0)}), ",
            f"{school_data.get('top_state_2', 'N/A')} ({school_data.get('top_state_2_count', 0)})"
        ], style={'marginTop': '5px', 'display': 'block'})
    ])

def calculate_class_distribution_display(school_data):
    """Create display for playing time by class"""
    class_data = get_playing_time_by_class(school_data)
    total = sum(class_data.values())
    
    return html.Div([
        html.Div([
            html.Div([
                html.Span("Fr: ", style={'fontWeight': 'bold'}),
                html.Span(f"{class_data['Fr']} ", style={'marginRight': '5px'}),
                html.Small(f"({class_data['Fr']/total*100:.0f}%)" if total > 0 else "(0%)", className='text-muted')
            ], style={'marginBottom': '5px'}),
            html.Div([
                html.Span("So: ", style={'fontWeight': 'bold'}),
                html.Span(f"{class_data['So']} ", style={'marginRight': '5px'}),
                html.Small(f"({class_data['So']/total*100:.0f}%)" if total > 0 else "(0%)", className='text-muted')
            ], style={'marginBottom': '5px'}),
            html.Div([
                html.Span("Jr: ", style={'fontWeight': 'bold'}),
                html.Span(f"{class_data['Jr']} ", style={'marginRight': '5px'}),
                html.Small(f"({class_data['Jr']/total*100:.0f}%)" if total > 0 else "(0%)", className='text-muted')
            ], style={'marginBottom': '5px'}),
            html.Div([
                html.Span("Sr: ", style={'fontWeight': 'bold'}),
                html.Span(f"{class_data['Sr']} ", style={'marginRight': '5px'}),
                html.Small(f"({class_data['Sr']/total*100:.0f}%)" if total > 0 else "(0%)", className='text-muted')
            ])
        ]),
        html.Hr(style={'margin': '10px 0'}),
        html.Small(f"Total Players: {total}", className='text-muted')
    ])

def calculate_position_depth_display(school_data):
    """Create display for position depth"""
    positions = get_position_depth(school_data)
    
    # Safety check
    if positions is None or not isinstance(positions, dict):
        positions = {'P': 0, 'C': 0, 'IF': 0, 'OF': 0}
    
    total = sum(positions.values())
    
    return html.Div([
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Strong("P"),
                        html.Div(f"{positions['P']}", style={'fontSize': '1.5rem', 'color': '#003366'})
                    ], className='text-center')
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Strong("C"),
                        html.Div(f"{positions['C']}", style={'fontSize': '1.5rem', 'color': '#003366'})
                    ], className='text-center')
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Strong("IF"),
                        html.Div(f"{positions['IF']}", style={'fontSize': '1.5rem', 'color': '#003366'})
                    ], className='text-center')
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Strong("OF"),
                        html.Div(f"{positions['OF']}", style={'fontSize': '1.5rem', 'color': '#003366'})
                    ], className='text-center')
                ], width=3)
            ])
        ]),
        html.Hr(style={'margin': '10px 0'}),
        html.Small([
            html.Span("Avg Heights: ", className='text-muted'),
            f"P: {inches_to_feet_inches(school_data.get('avg_p_height_in', 0))} | ",
            f"Others: {inches_to_feet_inches(school_data.get('avg_other_height_in', 0))}"
        ])
    ])

print(f"Loaded {len(merged_data)} schools")

# Load NCAA schools index for logo slugs
print("Loading NCAA schools index...")
try:
    ncaa_index_response = requests.get('https://ncaa-api.henrygd.me/schools-index', timeout=10)
    if ncaa_index_response.status_code == 200:
        ncaa_schools = ncaa_index_response.json()
        # Create a mapping from NCAA name to slug
        # API returns list of {slug, name, long}
        ncaa_name_to_slug = {school.get('name', ''): school.get('slug', '') for school in ncaa_schools if school.get('name')}
        ncaa_long_to_slug = {school.get('long', ''): school.get('slug', '') for school in ncaa_schools if school.get('long')}
        print(f"Loaded {len(ncaa_schools)} NCAA school slugs")
    else:
        ncaa_name_to_slug = {}
        ncaa_long_to_slug = {}
        print("Failed to load NCAA schools index")
except Exception as e:
    print(f"Error loading NCAA schools index: {e}")
    ncaa_name_to_slug = {}
    ncaa_long_to_slug = {}

# ============================================================================
# COLLEGE SCORECARD API FUNCTIONS
# ============================================================================

def fetch_college_scorecard_data(unitid):
    """
    Fetch college data from College Scorecard API using UNITID
    Returns a dictionary with additional metrics
    """
    try:
        params = {
            'api_key': COLLEGE_SCORECARD_API_KEY,
            'id': int(unitid)
        }
        
        response = requests.get(COLLEGE_SCORECARD_API_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('results') and len(data['results']) > 0:
                result = data['results'][0]
                print(f"Successfully fetched data for: {result.get('school', {}).get('name', 'Unknown')}")
                return result
            else:
                print(f"No results found for unitid {unitid}")
        else:
            print(f"API Error {response.status_code}: {response.text[:200]}")
        
        return None
        
    except Exception as e:
        print(f"Error fetching College Scorecard data for unitid {unitid}: {e}")
        return None

def format_currency(value):
    """Format value as currency"""
    if value is None or pd.isna(value):
        return 'N/A'
    return f"${value:,.0f}"

def format_percentage(value):
    """Format value as percentage"""
    if value is None or pd.isna(value):
        return 'N/A'
    return f"{value * 100:.1f}%"

def get_school_logo_url(school_name, ncaa_name=None):
    """Generate NCAA API logo URL from school name using the schools index"""
    # First try to match with NCAA_name.x field if provided
    if ncaa_name and ncaa_name in ncaa_name_to_slug:
        slug = ncaa_name_to_slug[ncaa_name]
        return f"https://ncaa-api.henrygd.me/logo/{slug}.svg"
    
    # Try matching with long name
    if school_name in ncaa_long_to_slug:
        slug = ncaa_long_to_slug[school_name]
        return f"https://ncaa-api.henrygd.me/logo/{slug}.svg"
    
    # Fallback: try to find partial match
    school_lower = school_name.lower()
    for ncaa_name, slug in ncaa_name_to_slug.items():
        if ncaa_name.lower() in school_lower or school_lower in ncaa_name.lower():
            return f"https://ncaa-api.henrygd.me/logo/{slug}.svg"
    
    # Last resort: create a slug from the school name
    clean_name = school_name.lower()
    clean_name = clean_name.replace('university', '').replace('college', '').replace('state', '')
    clean_name = clean_name.replace(' of ', ' ').replace(' at ', ' ')
    clean_name = clean_name.strip()
    words = [w for w in clean_name.split() if len(w) > 2]
    if words:
        clean_name = '-'.join(words)  # Join all significant words with hyphens
    clean_name = clean_name.replace(' ', '-').replace("'", '').replace('.', '')
    return f"https://ncaa-api.henrygd.me/logo/{clean_name}.svg"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_distance(home_lat, home_lon, school_lat, school_lon):
    """Calculate distance in miles between two coordinates"""
    return geodesic((home_lat, home_lon), (school_lat, school_lon)).miles

def geocode_zip(zipcode):
    """Geocode a US zip code to latitude/longitude"""
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="ncaa_baseball_finder")
        location = geolocator.geocode(f"{zipcode}, USA")
        if location:
            return {'lat': location.latitude, 'lon': location.longitude}
    except Exception as e:
        print(f"Error geocoding zip {zipcode}: {e}")
    return None

# ============================================================================
# UI CONSTANTS
# ============================================================================

# Division choices
DIVISION_OPTIONS = [
    {'label': 'Division 1', 'value': 1},
    {'label': 'Division 2', 'value': 2},
    {'label': 'Division 3', 'value': 3}
]

# Region choices - map numeric codes to readable names
REGION_MAP = {
    0.0: 'U.S. Service Schools',
    1.0: 'New England (CT, ME, MA, NH, RI, VT)',
    2.0: 'Mid East (DE, DC, MD, NJ, NY, PA)',
    3.0: 'Great Lakes (IL, IN, MI, OH, WI)',
    4.0: 'Plains (IA, KS, MN, MO, NE, ND, SD)',
    5.0: 'Southeast (AL, AR, FL, GA, KY, LA, MS, NC, SC, TN, VA, WV)',
    6.0: 'Southwest (AZ, NM, OK, TX)',
    7.0: 'Rocky Mountains (CO, ID, MT, UT, WY)',
    8.0: 'Far West (AK, CA, HI, NV, OR, WA)',
    9.0: 'Outlying Areas (AS, FM, GU, MH, MP, PW, PR, VI)'
}
REGIONS = sorted(merged_data['region'].dropna().unique().tolist())
REGION_OPTIONS = [{'label': REGION_MAP.get(r, f'Region {r}'), 'value': r} for r in REGIONS]

# Conference choices
CONFERENCES = sorted(merged_data['Conference_Name'].dropna().unique().tolist())
CONFERENCE_OPTIONS = [{'label': c, 'value': c} for c in CONFERENCES]

# Locale choices - map IPEDS codes to readable names
LOCALE_MAP = {
    11.0: 'City: Large',
    12.0: 'City: Midsize', 
    13.0: 'City: Small',
    21.0: 'Suburb: Large',
    22.0: 'Suburb: Midsize',
    23.0: 'Suburb: Small',
    31.0: 'Town: Fringe',
    32.0: 'Town: Distant',
    33.0: 'Town: Remote',
    41.0: 'Rural: Fringe',
    42.0: 'Rural: Distant',
    43.0: 'Rural: Remote'
}
LOCALES = sorted(merged_data['locale'].dropna().unique().tolist())
LOCALE_OPTIONS = [{'label': LOCALE_MAP.get(l, f'Locale {l}'), 'value': l} for l in LOCALES]

# Control type choices (public/private)
CONTROL_MAP = {1: 'Public', 2: 'Private nonprofit', 3: 'Private for-profit'}
merged_data['control_label'] = merged_data['control'].map(CONTROL_MAP)
CONTROL_OPTIONS = [{'label': v, 'value': k} for k, v in CONTROL_MAP.items()]

# Religious affiliation mapping (IPEDS codes)
RELIGIOUS_MAP = {
    22.0: 'American Evangelical Lutheran Church',
    24.0: 'African Methodist Episcopal Zion Church',
    27.0: 'Assemblies of God Church',
    28.0: 'Brethren Church',
    30.0: 'Roman Catholic',
    33.0: 'Wisconsin Evangelical Lutheran Synod',
    34.0: 'Christ and Missionary Alliance Church',
    35.0: 'Christian Reformed Church',
    36.0: 'Evangelical Congregational Church',
    37.0: 'Evangelical Covenant Church of America',
    38.0: 'Evangelical Free Church of America',
    39.0: 'Evangelical Lutheran Church',
    40.0: 'International United Pentecostal Church',
    41.0: 'Free Will Baptist Church',
    42.0: 'Interdenominational',
    43.0: 'Mennonite Brethren Church',
    44.0: 'Moravian Church',
    45.0: 'North American Baptist',
    47.0: 'Pentecostal Holiness Church',
    48.0: 'Christian Churches and Churches of Christ',
    49.0: 'Reformed Church in America',
    50.0: 'Episcopal Church, Reformed',
    51.0: 'African Methodist Episcopal',
    52.0: 'American Baptist',
    53.0: 'American Lutheran',
    54.0: 'Baptist',
    55.0: 'Christian Methodist Episcopal',
    57.0: 'Church of God',
    58.0: 'Church of Brethren',
    59.0: 'Church of the Nazarene',
    60.0: 'Cumberland Presbyterian',
    61.0: 'Christian Church (Disciples of Christ)',
    64.0: 'Free Methodist',
    65.0: 'Friends',
    66.0: 'Presbyterian Church (USA)',
    67.0: 'Lutheran Church in America',
    68.0: 'Lutheran Church - Missouri Synod',
    69.0: 'Mennonite Church',
    71.0: 'United Methodist',
    73.0: 'Protestant Episcopal',
    74.0: 'Churches of Christ',
    75.0: 'Southern Baptist',
    76.0: 'United Church of Christ',
    77.0: 'Protestant, not specified',
    78.0: 'Multiple Protestant Denomination',
    79.0: 'Other Protestant',
    80.0: 'Jewish',
    81.0: 'Reformed Presbyterian Church',
    84.0: 'United Brethren Church',
    87.0: 'Missionary Church Inc',
    88.0: 'Undenominational',
    89.0: 'Wesleyan',
    91.0: 'Greek Orthodox',
    92.0: 'Russian Orthodox',
    93.0: 'Unitarian Universalist',
    94.0: 'Latter Day Saints (Mormon Church)',
    95.0: 'Seventh Day Adventists',
    97.0: 'The Presbyterian Church in America',
    99.0: 'Other',
    100.0: 'Original Free Will Baptist',
    101.0: 'Ecumenical Christian',
    102.0: 'Evangelical Christian',
    103.0: 'Presbyterian',
    105.0: 'General Baptist',
    106.0: 'Muslim',
    107.0: 'Plymouth Brethren',
    108.0: 'Original Church of God'
}
# Get non-affiliated value (most common)
NON_AFFILIATED = -2.0
RELIGIOUS_AFFILIATIONS = sorted([v for v in merged_data['relaffil'].dropna().unique() if v != NON_AFFILIATED])
RELIGIOUS_OPTIONS = [{'label': 'Non-affiliated', 'value': NON_AFFILIATED}] + \
                    [{'label': RELIGIOUS_MAP.get(r, f'Code {int(r)}'), 'value': r} for r in RELIGIOUS_AFFILIATIONS]

# Enrollment size categories
ENROLLMENT_CATEGORIES = [
    {'label': 'Extra-Small (< 1k)', 'value': 'extra-small', 'range': [0, 999]},
    {'label': 'Small (1k - 3k)', 'value': 'small', 'range': [1000, 2999]},
    {'label': 'Small-Mid (3k - 7k)', 'value': 'small-mid', 'range': [3000, 6999]},
    {'label': 'Medium (7k - 15k)', 'value': 'medium', 'range': [7000, 14999]},
    {'label': 'Mid-Large (15k - 30k)', 'value': 'mid-large', 'range': [15000, 29999]},
    {'label': 'Extra Large (30k+)', 'value': 'extra-large', 'range': [30000, 999999]}
]
ENROLLMENT_VALUES = [cat['value'] for cat in ENROLLMENT_CATEGORIES]

# Month choices for climate
MONTH_OPTIONS = [
    {'label': 'Annual', 'value': 'annual'},
    {'label': 'January', 'value': 1},
    {'label': 'February', 'value': 2},
    {'label': 'March', 'value': 3},
    {'label': 'April', 'value': 4},
    {'label': 'May', 'value': 5},
    {'label': 'June', 'value': 6},
    {'label': 'July', 'value': 7},
    {'label': 'August', 'value': 8},
    {'label': 'September', 'value': 9},
    {'label': 'October', 'value': 10},
    {'label': 'November', 'value': 11},
    {'label': 'December', 'value': 12}
]

# ============================================================================
# LAYOUT
# ============================================================================

# Sidebar filters
sidebar = dbc.Col([
    # User authentication menu
    html.Div([
        html.Div(id='user-menu-container', children=create_user_menu(), className='mb-3')
    ]),
    
    html.H4(id='school-counter', className='mb-3 school-counter'),
    html.Hr(),
    
    # Reset button
    dbc.Button('Reset All Filters', id='reset-filters', color='secondary', className='w-100 mb-3'),
    
    # Accordion with filters
    dbc.Accordion([
        # Location Panel
        dbc.AccordionItem([
            dbc.Label('Home Zip Code'),
            dbc.Input(id='home-zip', type='text', value='21703', placeholder='e.g., 90210'),
            
            html.Div(className='mb-3'),
            
            dbc.Label('Max Distance (miles)'),
            dcc.Slider(
                id='distance-filter',
                min=0,
                max=2500,
                step=50,
                value=2500,
                marks={i: str(i) for i in range(0, 2501, 500)},
                tooltip={'placement': 'bottom', 'always_visible': True}
            ),
            
            html.Div(className='mb-3'),
            
            # Region filter - now as collapsible accordion item
            dbc.Accordion([
                dbc.AccordionItem([
                    dcc.Dropdown(
                        id='region-filter',
                        options=REGION_OPTIONS,
                        value=REGIONS,
                        multi=True
                    ),
                ], title=[html.I(className='fas fa-globe me-2'), 'Region'], item_id='region-sub')
            ], start_collapsed=True, flush=True),
            
        ], title=[html.I(className='fas fa-map-marker-alt me-2'), 'Location'], item_id='location'),
        
        # Climate Panel
        dbc.AccordionItem([
            dbc.Label('Select month'),
            dcc.Dropdown(
                id='clim-month',
                options=MONTH_OPTIONS,
                value=1,
                clearable=False
            ),
            
            html.Div(className='mb-3'),
            
            dbc.Label('Avg. Temp (°F)'),
            dcc.RangeSlider(
                id='temp-filter',
                min=0,
                max=100,
                step=1, 
                value=[0, 100],
                marks={i: str(i) for i in range(0, 101, 20)},
                tooltip={'placement': 'bottom', 'always_visible': True}
            ),
            
            html.Div(className='mb-3'),
            
            dbc.Label('Avg. Precipitation (mm/day)'),
            dcc.RangeSlider(
                id='precip-filter',
                min=0,
                max=10,
                step=0.1,
                value=[0, 10],
                marks={i: str(i) for i in range(0, 11, 2)},
                tooltip={'placement': 'bottom', 'always_visible': True}
            ),
            
            html.Div(className='mb-3'),
            
            dbc.Label('Avg. Cloud Cover (%)'),
            dcc.RangeSlider(
                id='cloud-filter',
                min=0,
                max=100,
                step=1,
                value=[0, 100],
                marks={i: str(i) for i in range(0, 101, 20)},
                tooltip={'placement': 'bottom', 'always_visible': True}
            ),
            
        ], title=[html.I(className='fas fa-cloud-sun me-2'), 'Climate'], item_id='climate'),
        
        # Team Attributes Panel
        dbc.AccordionItem([
            dbc.Label('Division'),
            dcc.Checklist(
                id='division-filter',
                options=DIVISION_OPTIONS,
                value=[1, 2, 3],
                inline=True
            ),
            
            html.Div(className='mb-3'),
            
            dbc.Label('Winning Pct (%)'),
            dcc.RangeSlider(
                id='win-pct-filter',
                min=0,
                max=100,
                step=1,
                value=[0, 100],
                marks={i: str(i) for i in range(0, 101, 20)},
                tooltip={'placement': 'bottom', 'always_visible': True}
            ),
            
            html.Div(className='mb-3'),
            
            dbc.Label('Conference'),
            dbc.Input(
                id='conference-search',
                type='text',
                placeholder='Search conferences...',
                className='mb-2'
            ),
            dbc.Row([
                dbc.Col([
                    dbc.Button('Select All', id='conference-select-all', size='sm', color='primary', className='w-100')
                ], width=6),
                dbc.Col([
                    dbc.Button('Deselect All', id='conference-deselect-all', size='sm', color='secondary', className='w-100')
                ], width=6)
            ], className='mb-2'),
            html.Div([
                dcc.Checklist(
                    id='conference-filter',
                    options=CONFERENCE_OPTIONS,
                    value=CONFERENCES,
                    labelStyle={'display': 'block'},
                    inputStyle={'marginRight': '8px'}
                )
            ], style={'maxHeight': '200px', 'overflowY': 'auto', 'border': '1px solid #ced4da', 'borderRadius': '4px', 'padding': '8px'}),
            
        ], title=[html.I(className='fas fa-baseball-ball me-2'), 'Team Attributes'], item_id='team'),
        
        # Demographics Panel
        dbc.AccordionItem([
            # Locale sub-accordion
            html.Details([
                html.Summary('Locale', style={'cursor': 'pointer', 'fontWeight': 'bold'}),
                html.Div([
                    dcc.Dropdown(
                        id='locale-filter',
                        options=LOCALE_OPTIONS,
                        value=LOCALES,
                        multi=True
                    )
                ], className='mt-2')
            ]),
            
            html.Div(className='mb-3'),
            
            # Control sub-accordion
            html.Details([
                html.Summary('Control (Public/Private)', style={'cursor': 'pointer', 'fontWeight': 'bold'}),
                html.Div([
                    dcc.Checklist(
                        id='control-filter',
                        options=CONTROL_OPTIONS,
                        value=list(CONTROL_MAP.keys()),
                        inline=False
                    )
                ], className='mt-2')
            ]),
            
            html.Div(className='mb-3'),
            
            # Enrollment sub-accordion
            html.Details([
                html.Summary('Enrollment Size', style={'cursor': 'pointer', 'fontWeight': 'bold'}),
                html.Div([
                    dcc.Checklist(
                        id='enrollment-filter',
                        options=[{'label': cat['label'], 'value': cat['value']} for cat in ENROLLMENT_CATEGORIES],
                        value=ENROLLMENT_VALUES,
                        labelStyle={'display': 'block', 'marginBottom': '8px'},
                        inputStyle={'marginRight': '8px'}
                    )
                ], className='mt-2')
            ]),
            
            html.Div(className='mb-3'),
            
            # Religious Affiliation sub-accordion
            html.Details([
                html.Summary('Religious Affiliation', style={'cursor': 'pointer', 'fontWeight': 'bold'}),
                html.Div([
                    dbc.Input(
                        id='religious-search',
                        type='text',
                        placeholder='Search affiliations...',
                        className='mb-2 mt-2'
                    ),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button('Select All', id='religious-select-all', size='sm', color='primary', className='w-100')
                        ], width=6),
                        dbc.Col([
                            dbc.Button('Deselect All', id='religious-deselect-all', size='sm', color='secondary', className='w-100')
                        ], width=6)
                    ], className='mb-2'),
                    html.Div([
                        dcc.Checklist(
                            id='religious-filter',
                            options=RELIGIOUS_OPTIONS,
                            value=[NON_AFFILIATED] + RELIGIOUS_AFFILIATIONS,
                            labelStyle={'display': 'block'},
                            inputStyle={'marginRight': '8px'}
                        )
                    ], style={'maxHeight': '200px', 'overflowY': 'auto', 'border': '1px solid #ced4da', 'borderRadius': '4px', 'padding': '8px'})
                ], className='mt-2')
            ]),
            
        ], title=[html.I(className='fas fa-users me-2'), 'Demographics'], item_id='demographics'),
        
        # Academic & Financial Panel
        dbc.AccordionItem([
            dbc.Checklist(
                id='usnews-ranked-filter',
                options=[{'label': ' US News-ranked schools only', 'value': 'ranked'}],
                value=[],
                className='mb-3'
            ),
            
            dbc.Label('Acceptance Rate (%)'),
            dcc.RangeSlider(
                id='accept-rate-filter',
                min=0,
                max=100,
                step=1,
                value=[0, 100],
                marks={i: str(i) for i in range(0, 101, 20)},
                tooltip={'placement': 'bottom', 'always_visible': True}
            ),
            
            html.Div(className='mb-3'),
            
            dbc.Label('Avg. SAT Score'),
            dcc.RangeSlider(
                id='sat-filter',
                min=800,
                max=1600,
                step=10,
                value=[800, 1600],
                marks={i: str(i) for i in range(800, 1601, 200)},
                tooltip={'placement': 'bottom', 'always_visible': True}
            ),
            
        ], title=[html.I(className='fas fa-graduation-cap me-2'), 'Academic & Financial'], item_id='academic'),
        
    ], start_collapsed=True, active_item='location', always_open=False)
    
], width={'size': 12, 'md': 3}, className='sidebar', style={'height': '100vh', 'overflowY': 'auto', 'padding': '20px'})

# Main content area
main_tabs = dbc.Tabs([
    # Map Tab
    dbc.Tab([
        html.Div([
            dcc.Graph(id='baseball-map', style={'height': '70vh'}, config={'doubleClick': False})
        ], className='map-container'),
        html.Div(id='map-school-info', className='mt-3')
    ], label='Map', tab_id='tab-map'),
    
    # Filtered School List Tab
    dbc.Tab([
        dbc.Row([
            dbc.Col([
                dbc.Button('Add Selected Rows to Saved List', id='add-to-saved', color='primary', className='mb-2 w-100')
            ], width={'size': 12, 'md': 4}),
            dbc.Col([
                dbc.Input(id='school-search', type='text', placeholder='Search schools by name...', className='mb-2')
            ], width={'size': 12, 'md': 8})
        ]),
        html.Hr(),
        html.Div(id='filtered-table')
    ], label='Filtered School List', tab_id='tab-filtered'),
    
    # Saved List Tab
    dbc.Tab([
        html.Div([
            dbc.Button('Remove Selected Rows', id='remove-from-saved', color='danger', className='me-2 mb-2'),
            dbc.Button('Clear Entire Saved List', id='clear-saved', color='warning', className='mb-2')
        ], className='d-flex flex-wrap'),
        html.Hr(),
        html.Div(id='saved-table')
    ], label='Saved List', tab_id='tab-saved'),
    
    # Roster Metrics Tab
    dbc.Tab([
        html.Div(id='roster-metrics')
    ], label='Metrics', tab_id='tab-metrics'),

    # Profile Tab
    dbc.Tab([
        html.Div(id='profile-page', className='p-3')
    ], label='Profile', tab_id='tab-profile'),
], id='main-tabs', active_tab='tab-map')

main_content = dbc.Col([
    main_tabs
], width={'size': 12, 'md': 9})

# App layout
print("Creating layout...")
app.layout = dbc.Container([
    # Session stores for Firebase authentication
    create_session_stores(),
    dcc.Store(id='search-tracker', data={}),  # Track user searches
    
    dcc.Store(id='saved-schools', data=[]),
    dcc.Store(id='home-location', data=None),
    dcc.Store(id='filter-state', data={}),  # Store for all filter values
    dcc.Store(id='filtered-data-store', data=[]),  # Store filtered table data
    dcc.Store(id='current-school-unitid', data=None),  # Track current school for team metrics
    dcc.Store(id='map-click-state', data={'last_unitid': None, 'last_time': 0}),  # Track map clicks for double-click
    dcc.Store(id='map-selected-unitid', data=None),  # Track currently clicked unitid for add button
    
    # Modal for detailed metrics
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("School Metrics")),
        dbc.ModalBody(id='metrics-modal-content'),
        dbc.ModalFooter([
            dbc.Button(
                "Team Metrics",
                id="open-team-metrics-btn",
                color="info",
                className="me-auto",
                n_clicks=0
            ),
            dbc.Button("Close", id="close-metrics-modal", className="ms-auto", n_clicks=0)
        ])
    ], id='metrics-modal', size='xl', is_open=False),
    
    # Modal for team metrics
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Team Metrics")),
        dbc.ModalBody(id='team-metrics-modal-content'),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-team-metrics-modal", className="ms-auto", n_clicks=0)
        )
    ], id='team-metrics-modal', size='xl', is_open=False),
    
    # Firebase authentication modals
    create_login_modal(),
    create_saved_schools_modal(),
    create_analytics_modal(),
    
    dbc.Row([sidebar, main_content])
], fluid=True, style={'padding': '0'})
print("Layout created successfully")

# ============================================================================
# CALLBACKS
# ============================================================================

# Update home location when zip code changes
@app.callback(
    Output('home-location', 'data'),
    Input('home-zip', 'value'),
    prevent_initial_call=False
)
def update_home_location(zipcode):
    """Geocode home zip code to coordinates"""
    if zipcode:
        return geocode_zip(zipcode)
    return None

# Conference search and filter callbacks
@app.callback(
    Output('conference-filter', 'options'),
    Input('conference-search', 'value')
)
def filter_conference_options(search_term):
    """Filter conference options based on search term"""
    if not search_term:
        return CONFERENCE_OPTIONS
    search_lower = search_term.lower()
    return [opt for opt in CONFERENCE_OPTIONS if search_lower in opt['label'].lower()]

# Religious affiliation search and filter callbacks
@app.callback(
    Output('religious-filter', 'options'),
    Input('religious-search', 'value')
)
def filter_religious_options(search_term):
    """Filter religious affiliation options based on search term"""
    if not search_term:
        return RELIGIOUS_OPTIONS
    search_lower = search_term.lower()
    return [opt for opt in RELIGIOUS_OPTIONS if search_lower in opt['label'].lower()]

# Callback to update filter state store when any filter changes
@app.callback(
    Output('filter-state', 'data'),
    Input('division-filter', 'value'),
    Input('conference-filter', 'value'),
    Input('region-filter', 'value'),
    Input('locale-filter', 'value'),
    Input('control-filter', 'value'),
    Input('win-pct-filter', 'value'),
    Input('accept-rate-filter', 'value'),
    Input('sat-filter', 'value'),
    Input('distance-filter', 'value'),
    Input('temp-filter', 'value'),
    Input('precip-filter', 'value'),
    Input('cloud-filter', 'value'),
    Input('clim-month', 'value'),
    Input('usnews-ranked-filter', 'value'),
    Input('enrollment-filter', 'value'),
    Input('religious-filter', 'value'),
    Input('home-location', 'data'),
)
def update_filter_state(divisions, conferences, regions, locales, controls,
                       win_pct, accept_rate, sat_range, distance,
                       temp_range, precip_range, cloud_range, clim_month, usnews_ranked, 
                       enrollment_range, religious_affils, home_location):
    """Store all filter values in a single state object"""
    try:
        return {
            'divisions': divisions,
            'conferences': conferences,
            'regions': regions,
            'locales': locales,
            'controls': controls,
            'win_pct': win_pct,
            'accept_rate': accept_rate,
            'sat_range': sat_range,
            'distance': distance,
            'temp_range': temp_range,
            'precip_range': precip_range,
            'cloud_range': cloud_range,
            'clim_month': clim_month,
            'usnews_ranked': usnews_ranked,
            'enrollment_range': enrollment_range,
            'religious_affils': religious_affils,
            'home_location': home_location
        }
    except Exception as e:
        print(f"Error in update_filter_state: {e}")
        return {}

# Update school counter from filter state
@app.callback(
    Output('school-counter', 'children'),
    Input('filter-state', 'data')
)
def update_counter(filter_state):
    try:
        if not filter_state:
            return html.Span([
                "Displaying ",
                html.Span(str(len(merged_data)), className='count-number'),
                f" of {len(merged_data)} schools"
            ])
        
        filtered = filter_data_from_state(filter_state)
        total = len(merged_data)
        return html.Span([
            "Displaying ",
            html.Span(str(len(filtered)), className='count-number'),
            f" of {total} schools"
        ])
    except Exception as e:
        print(f"Error in update_counter: {e}")
        import traceback
        traceback.print_exc()
        return "Error loading schools"

def filter_data_from_state(filter_state):
    """Apply all filters using state dict"""
    return filter_data(
        filter_state.get('divisions', [1, 2, 3]),
        filter_state.get('conferences', CONFERENCES),
        filter_state.get('regions', REGIONS),
        filter_state.get('locales', LOCALES),
        filter_state.get('controls', list(CONTROL_MAP.keys())),
        filter_state.get('win_pct', [0, 100]),
        filter_state.get('accept_rate', [0, 100]),
        filter_state.get('sat_range', [800, 1600]),
        filter_state.get('distance', 2500),
        filter_state.get('temp_range', [0, 100]),
        filter_state.get('precip_range', [0, 10]),
        filter_state.get('cloud_range', [0, 100]),
        filter_state.get('clim_month', 1),
        filter_state.get('usnews_ranked', []),
        filter_state.get('enrollment_range', ENROLLMENT_VALUES),
        filter_state.get('religious_affils', [NON_AFFILIATED] + RELIGIOUS_AFFILIATIONS),
        filter_state.get('home_location', None)
    )

def filter_data(divisions, conferences, regions, locales, controls, 
                win_pct, accept_rate, sat_range, distance, 
                temp_range, precip_range, cloud_range, clim_month, usnews_ranked=[], 
                enrollment_range=None, religious_affils=[], home_location=None):
    """Apply all filters to the data"""
    try:
        print(f"filter_data called: divisions={divisions}, conferences={type(conferences)}, regions={type(regions)}")
        df = merged_data.copy()
        
        # Apply distance filter if home location is set
        if home_location and distance and distance < 2500:
            df['distance_from_home'] = df.apply(
                lambda row: calculate_distance(
                    home_location['lat'], home_location['lon'],
                    row['latitude'], row['longitude']
                ) if pd.notna(row['latitude']) and pd.notna(row['longitude']) else 9999,
                axis=1
            )
            df = df[df['distance_from_home'] <= distance]
        
        # Apply US News ranking filter
        if 'ranked' in usnews_ranked:
            df = df[df['US_Rank'].notna()]
        
        # Apply filters
        if divisions:
            df = df[df['division'].isin(divisions)]
        
        if conferences:
            df = df[df['Conference_Name'].isin(conferences)]
        
        if regions:
            df = df[df['region'].isin(regions)]
        
        if locales:
            df = df[df['locale'].isin(locales)]
        
        if controls:
            df = df[df['control'].isin(controls)]
        
        # Enrollment filter - convert categories to ranges
        if enrollment_range:
            if isinstance(enrollment_range, list) and len(enrollment_range) > 0:
                # Check if it's categorical values or numeric range
                if isinstance(enrollment_range[0], str):
                    # Categorical - convert to range filter
                    enrollment_masks = []
                    for cat_value in enrollment_range:
                        cat = next((c for c in ENROLLMENT_CATEGORIES if c['value'] == cat_value), None)
                        if cat:
                            min_val, max_val = cat['range']
                            enrollment_masks.append((df['ugds'].fillna(0) >= min_val) & (df['ugds'].fillna(0) <= max_val))
                    if enrollment_masks:
                        combined_mask = enrollment_masks[0]
                        for mask in enrollment_masks[1:]:
                            combined_mask = combined_mask | mask
                        df = df[combined_mask]
                else:
                    # Legacy numeric range support
                    df = df[(df['ugds'].fillna(0) >= enrollment_range[0]) & (df['ugds'].fillna(0) <= enrollment_range[1])]
        
        # Religious affiliation filter
        if religious_affils:
            # Handle non-affiliated schools (those with NaN or -2)
            if NON_AFFILIATED in religious_affils:
                df = df[(df['relaffil'].isin(religious_affils)) | (df['relaffil'].isna())]
            else:
                df = df[df['relaffil'].isin(religious_affils)]
        
        # Numeric filters
        df = df[(df['win_pct'] >= win_pct[0]) & (df['win_pct'] <= win_pct[1])]
        df = df[(df['accept_rate_pct'] >= accept_rate[0]) & (df['accept_rate_pct'] <= accept_rate[1])]
        df = df[(df['sat_score'] == 0) | ((df['sat_score'] >= sat_range[0]) & (df['sat_score'] <= sat_range[1]))]
        
        # Climate filtering using long format data
        if clim_month != 'annual':
            month_data = climate_monthly[climate_monthly['month'] == clim_month].copy()
            
            # Apply temperature filter
            month_data = month_data[
                (month_data['t2m'].isna()) | 
                ((month_data['t2m'] >= temp_range[0]) & (month_data['t2m'] <= temp_range[1]))
            ]
            
            # Apply precipitation filter
            month_data = month_data[
                (month_data['prectotcorr'].isna()) | 
                ((month_data['prectotcorr'] >= precip_range[0]) & (month_data['prectotcorr'] <= precip_range[1]))
            ]
            
            # Apply cloud cover filter
            month_data = month_data[
                (month_data['cloud_amt'].isna()) | 
                ((month_data['cloud_amt'] >= cloud_range[0]) & (month_data['cloud_amt'] <= cloud_range[1]))
            ]
            
            # Filter to schools that pass climate filters
            passing_unitids = month_data['unitid'].unique()
            df = df[df['unitid'].isin(passing_unitids)]
        
        return df
    except Exception as e:
        print(f"Error in filter_data: {e}")
        import traceback
        traceback.print_exc()
        return merged_data.copy()  # Return all data on error

# Update map markers
@app.callback(
    Output('baseball-map', 'figure'),
    Input('filter-state', 'data')
)
def update_map(filter_state):
    try:
        if not filter_state:
            filtered = merged_data.copy()
        else:
            filtered = filter_data_from_state(filter_state)
        
        print(f"Creating map with {len(filtered)} schools")
        
        # Define colors by division
        division_colors = {
            1: '#1f77b4',  # Blue for Division 1
            2: '#0d47a1',  # Dark Blue for Division 2
            3: '#7b1fa2'   # Purple for Division 3
        }
        
        # Create hover text with just school name
        filtered['hover_text'] = '<b>' + filtered['inst_name'] + '</b>'
        
        # Map division to color
        filtered['marker_color'] = filtered['division'].map(division_colors).fillna('#1f77b4')
        
        # Create the map figure
        fig = go.Figure(go.Scattermap(
            lat=filtered['latitude'],
            lon=filtered['longitude'],
            mode='markers',
            marker=dict(size=8, color=filtered['marker_color']),
            text=filtered['hover_text'],
            hovertemplate='<b>%{text}</b><extra></extra>',
            customdata=filtered[['unitid', 'inst_name']].values,
            name='Schools',
            hoverinfo='skip'
        ))
        
        # Enable event+select click mode to ensure click events fire reliably
        fig.update_layout(
            clickmode='event+select',
            map=dict(
                style='open-street-map',
                center=dict(lat=39.8283, lon=-98.5795),
                zoom=3.5
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=800,
            hoverlabel=dict(namelength=-1)
        )
        
        print(f"Successfully created map with {len(filtered)} schools")
        return fig
    except Exception as e:
        print(f"Error in update_map: {e}")
        import traceback
        traceback.print_exc()
        # Return empty map on error
        return go.Figure(go.Scattermap(
            lat=[39.8283],
            lon=[-98.5795],
            mode='markers',
            marker=dict(size=0)
        ))

# Handle map clicks: show info on single click, add to saved on double-click
@app.callback(
    Output('map-school-info', 'children'),
    Output('saved-schools', 'data', allow_duplicate=True),
    Output('map-click-state', 'data'),
    Output('map-selected-unitid', 'data'),
    Input('baseball-map', 'clickData'),
    State('saved-schools', 'data'),
    State('map-click-state', 'data'),
    prevent_initial_call=True
)
def handle_map_click(clickData, saved_schools, click_state):
    try:
        if not clickData or not clickData.get('points'):
            return dash.no_update, dash.no_update, click_state, dash.no_update
        point = clickData['points'][0]
        custom = point.get('customdata')
        if custom is None or len(custom) == 0 or custom[0] is None:
            return dash.no_update, dash.no_update, click_state, dash.no_update
        unitid = int(float(custom[0]))
        school_name = custom[1] if len(custom) > 1 else 'Unknown'

        now = time.time()
        state = click_state or {'last_unitid': None, 'last_time': 0}
        last_unitid = state.get('last_unitid')
        last_time = float(state.get('last_time', 0))

        # Detect double-click: same unitid within 900ms
        if last_unitid == unitid and (now - last_time) < 0.9:
            updated = saved_schools[:] if saved_schools else []
            if unitid not in updated:
                updated.append(unitid)
            # Show confirmation message and reset click state
            info_card = dbc.Alert(
                f"✓ {school_name} added to Saved List!",
                color="success",
                dismissable=True,
                duration=3000
            )
            return info_card, updated, {'last_unitid': None, 'last_time': 0}, unitid
        else:
            # Single click: show school info
            school_data = merged_data[merged_data['unitid'] == unitid].iloc[0] if unitid in merged_data['unitid'].values else None
            if school_data is not None:
                def safe_int(val):
                    try:
                        return int(float(val))
                    except Exception:
                        return None

                def fmt_int(val, suffix=''):
                    v = safe_int(val)
                    return f"{v}{suffix}" if v is not None else "N/A"

                div_val = safe_int(school_data.get('division'))
                division_txt = f"D{div_val}" if div_val is not None else "N/A"
                wins_txt = fmt_int(school_data.get('wins'))
                losses_txt = fmt_int(school_data.get('losses'))
                winpct_txt = fmt_int(school_data.get('win_pct'), suffix='%')
                accept_txt = fmt_int(school_data.get('accept_rate_pct'), suffix='%')
                enroll_txt = fmt_int(school_data.get('ugds'))
                city = school_data.get('city', 'N/A')
                state = school_data.get('state_abbr', '')
                
                # Get school logo
                ncaa_name = school_data.get('NCAA_Name.x')
                logo_url = get_school_logo_url(school_data.get('inst_name', 'Unknown'), ncaa_name)

                info_card = dbc.Card([
                    dbc.CardHeader(
                        dbc.Row([
                            dbc.Col([
                                html.Img(src=logo_url, style={'height': '40px', 'marginRight': '10px'})
                            ], width='auto', className='d-flex align-items-center'),
                            dbc.Col([
                                html.H5(school_data.get('inst_name', 'Unknown'), className='mb-0')
                            ], className='d-flex align-items-center')
                        ], className='align-items-center')
                    ),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Strong('Division: '),
                                html.Span(division_txt)
                            ], width=3),
                            dbc.Col([
                                html.Strong('Record: '),
                                html.Span(f"{wins_txt}-{losses_txt} ({winpct_txt})")
                            ], width=3),
                            dbc.Col([
                                html.Strong('Conference: '),
                                html.Span(school_data.get('Conference_Name', 'N/A'))
                            ], width=6)
                        ], className='mb-2'),
                        dbc.Row([
                            dbc.Col([
                                html.Strong('Accept Rate: '),
                                html.Span(accept_txt)
                            ], width=4),
                            dbc.Col([
                                html.Strong('Enrollment: '),
                                html.Span(f"{enroll_txt:,}" if isinstance(enroll_txt, int) else enroll_txt)
                            ], width=4),
                            dbc.Col([
                                html.Strong('Location: '),
                                html.Span(f"{city}, {state}" if state else city)
                            ], width=4)
                        ])
                    ]),
                    dbc.CardFooter([
                        dbc.Button(
                            "Add to Saved List",
                            id='map-add-to-saved',
                            color='primary',
                            size='sm',
                            n_clicks=0,
                            className='me-2'
                        ),
                        html.Small('', className='text-muted')
                    ])
                ], className='border-primary')
            else:
                info_card = None
            # Record first click
            return info_card, dash.no_update, {'last_unitid': unitid, 'last_time': now}, unitid
    except Exception as e:
        print(f"Error handling map click: {e}")
        import traceback
        traceback.print_exc()
        return dash.no_update, dash.no_update, click_state, dash.no_update

# Add to saved via map info button
@app.callback(
    Output('saved-schools', 'data', allow_duplicate=True),
    Input('map-add-to-saved', 'n_clicks'),
    State('map-selected-unitid', 'data'),
    State('saved-schools', 'data'),
    prevent_initial_call=True
)
def add_map_selected_to_saved(n_clicks, unitid, saved_schools):
    try:
        if not n_clicks or unitid is None:
            return dash.no_update
        updated = saved_schools[:] if saved_schools else []
        if unitid not in updated:
            updated.append(unitid)
        return updated
    except Exception as e:
        print(f"Error adding map selected to saved: {e}")
        return dash.no_update

# Update filtered school list table
@app.callback(
    Output('filtered-table', 'children'),
    Output('filtered-data-store', 'data'),
    Input('filter-state', 'data'),
    Input('school-search', 'value')
)
def update_filtered_table(filter_state, search_text):
    try:
        if not filter_state:
            filtered = merged_data.copy()
        else:
            filtered = filter_data_from_state(filter_state)
        
        # Apply search filter if search text provided
        if search_text:
            filtered = filtered[filtered['inst_name'].str.contains(search_text, case=False, na=False)]
        
        # Select columns to display
        display_cols = ['inst_name', 'division', 'Conference_Name', 
                       'wins', 'losses', 'win_pct', 'accept_rate_pct', 'ugds']
        
        # Only include columns that exist
        display_cols = [col for col in display_cols if col in filtered.columns]
        
        # Add unitid for tracking selections
        if 'unitid' not in display_cols:
            display_cols = ['unitid'] + display_cols
        
        table_data = filtered[display_cols].copy()
        
        # Create DataTable with row selection and sorting
        return dash_table.DataTable(
            id='filtered-datatable',
            columns=[
                {'name': 'School', 'id': 'inst_name'},
                {'name': 'Div', 'id': 'division'},
                {'name': 'Conference', 'id': 'Conference_Name'},
                {'name': 'W', 'id': 'wins'},
                {'name': 'L', 'id': 'losses'},
                {'name': 'Win%', 'id': 'win_pct'},
                {'name': 'Accept%', 'id': 'accept_rate_pct'},
                {'name': 'Enrollment', 'id': 'ugds'}
            ],
            data=table_data.to_dict('records'),
            row_selectable='multi',
            selected_rows=[],
            sort_action='native',
            style_table={'overflowX': 'auto', 'overflowY': 'auto', 'maxHeight': '600px'},
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }]
        ), table_data.to_dict('records')
    except Exception as e:
        print(f"Error in update_filtered_table: {e}")
        import traceback
        traceback.print_exc()
        return html.Div("Error loading table"), []

# Add selected rows to saved list
@app.callback(
    Output('saved-schools', 'data'),
    Input('add-to-saved', 'n_clicks'),
    State('filtered-datatable', 'selected_rows'),
    State('filtered-data-store', 'data'),
    State('saved-schools', 'data'),
    prevent_initial_call=True
)
def add_to_saved(n_clicks, selected_rows, table_data, saved_schools):
    try:
        if not selected_rows or not table_data:
            return saved_schools or []
        
        # Get selected school unitids
        selected_unitids = [table_data[i]['unitid'] for i in selected_rows]
        
        # Add to saved list (avoid duplicates)
        saved_set = set(saved_schools or [])
        saved_set.update(selected_unitids)
        
        print(f"Added {len(selected_unitids)} schools to saved list. Total saved: {len(saved_set)}")
        return list(saved_set)
    except Exception as e:
        print(f"Error in add_to_saved: {e}")
        import traceback
        traceback.print_exc()
        return saved_schools or []

# Display saved schools table
@app.callback(
    Output('saved-table', 'children'),
    Input('saved-schools', 'data')
)
def update_saved_table(saved_unitids):
    try:
        if not saved_unitids:
            return html.Div("No schools saved yet. Use the Filtered School List tab to select and add schools.")
        
        # Get saved schools data
        saved_data = merged_data[merged_data['unitid'].isin(saved_unitids)].copy()
        
        display_cols = ['unitid', 'inst_name', 'division', 'Conference_Name', 
                       'wins', 'losses', 'win_pct', 'accept_rate_pct', 'ugds']
        display_cols = [col for col in display_cols if col in saved_data.columns]
        
        table_data = saved_data[display_cols]
        
        return dash_table.DataTable(
            id='saved-datatable',
            columns=[
                {'name': 'School', 'id': 'inst_name'},
                {'name': 'Div', 'id': 'division'},
                {'name': 'Conference', 'id': 'Conference_Name'},
                {'name': 'W', 'id': 'wins'},
                {'name': 'L', 'id': 'losses'},
                {'name': 'Win%', 'id': 'win_pct'},
                {'name': 'Accept%', 'id': 'accept_rate_pct'},
                {'name': 'Enrollment', 'id': 'ugds'}
            ],
            data=table_data.to_dict('records'),
            row_selectable='multi',
            selected_rows=[],
            sort_action='native',
            page_size=20,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }]
        )
    except Exception as e:
        print(f"Error in update_saved_table: {e}")
        import traceback
        traceback.print_exc()
        return html.Div("Error loading saved schools")

# Remove selected rows from saved list
@app.callback(
    Output('saved-schools', 'data', allow_duplicate=True),
    Input('remove-from-saved', 'n_clicks'),
    State('saved-datatable', 'selected_rows'),
    State('saved-datatable', 'data'),
    State('saved-schools', 'data'),
    prevent_initial_call=True
)
def remove_from_saved(n_clicks, selected_rows, table_data, saved_schools):
    try:
        if not selected_rows or not table_data:
            return saved_schools or []
        
        # Get selected school unitids to remove
        remove_unitids = [table_data[i]['unitid'] for i in selected_rows]
        
        # Remove from saved list
        saved_set = set(saved_schools or [])
        saved_set.difference_update(remove_unitids)
        
        print(f"Removed {len(remove_unitids)} schools from saved list. Remaining: {len(saved_set)}")
        return list(saved_set)
    except Exception as e:
        print(f"Error in remove_from_saved: {e}")
        return saved_schools or []

# Clear entire saved list
@app.callback(
    Output('saved-schools', 'data', allow_duplicate=True),
    Input('clear-saved', 'n_clicks'),
    prevent_initial_call=True
)
def clear_saved(n_clicks):
    print("Cleared saved list")
    return []

# Display roster metrics cards for saved schools
@app.callback(
    Output('roster-metrics', 'children'),
    Input('saved-schools', 'data')
)
def update_roster_metrics(saved_unitids):
    try:
        if not saved_unitids:
            return html.Div([
                html.H4("No schools in saved list", className="text-center mt-5"),
                html.P("Add schools from the Filtered School List tab to view their roster metrics here.", 
                       className="text-center text-muted")
            ])
        
        # Get saved schools data
        saved_schools_data = merged_data[merged_data['unitid'].isin(saved_unitids)].copy()
        
        # Create cards for each school
        cards = []
        for _, school in saved_schools_data.iterrows():
            ncaa_name = school.get('NCAA_name.x', None)
            logo_url = get_school_logo_url(school['inst_name'], ncaa_name)
            
            # Get school URL from scorecard API if available
            school_url = None
            try:
                scorecard_data = fetch_college_scorecard_data(school['unitid'])
                if scorecard_data:
                    school_url = scorecard_data.get('school', {}).get('school_url')
            except:
                pass
            
            # Create school name element (link if URL available, otherwise plain text)
            if school_url and school_url.startswith('http'):
                school_name_element = html.A(
                    school['inst_name'],
                    href=school_url,
                    target='_blank',
                    className="mb-0",
                    style={'color': '#003366', 'textDecoration': 'none', 'fontWeight': 'bold', 'fontSize': '1.25rem'}
                )
            else:
                school_name_element = html.H5(school['inst_name'], className="mb-0")
            
            card = dbc.Card([
                dbc.CardHeader([
                    dbc.Row([
                        dbc.Col([
                            html.Img(
                                src=logo_url,
                                style={
                                    'height': '50px',
                                    'width': '50px',
                                    'objectFit': 'contain'
                                },
                                alt=school['inst_name']
                            )
                        ], width=2, className='d-flex align-items-center justify-content-center'),
                        dbc.Col([
                            school_name_element,
                            html.P(
                                f"{school.get('city', 'N/A')}, {school.get('state_abbr', 'N/A')}",
                                className="text-muted mb-0",
                                style={'fontSize': '0.9rem'}
                            )
                        ], width=10, className='d-flex flex-column justify-content-center')
                    ])
                ]),
                dbc.CardBody([
                    html.Div([
                        html.Strong("Division: "), f"{school.get('division', 'N/A')}"
                    ]),
                    html.Div([
                        html.Strong("Conference: "), f"{school.get('Conference_Name', 'N/A')}"
                    ]),
                    html.Div([
                        html.Strong("Record: "), 
                        f"{int(school.get('wins', 0) if pd.notna(school.get('wins', 0)) else 0)}-{int(school.get('losses', 0) if pd.notna(school.get('losses', 0)) else 0)} ({school.get('win_pct', 0) if pd.notna(school.get('win_pct', 0)) else 0:.0f}%)"
                    ]),
                    html.Div([
                        html.Strong("Acceptance Rate: "), f"{school.get('accept_rate_pct', 0):.0f}%"
                    ]),
                    html.Hr(),
                    
                    dbc.Button(
                        "View School Metrics",
                        id={'type': 'view-metrics-btn', 'index': school['unitid']},
                        color="primary",
                        size="sm",
                        className="w-100"
                    )
                ])
            ], className="mb-3", style={'cursor': 'pointer'})
            
            cards.append(
                dbc.Col(card, width=12, md=6, lg=4, className="mb-3")
            )
        
        return dbc.Container([
            html.H4(f"Saved Schools ({len(saved_unitids)})", className="mb-4"),
            dbc.Row(cards)
        ], fluid=True)
        
    except Exception as e:
        print(f"Error in update_roster_metrics: {e}")
        import traceback
        traceback.print_exc()
        return html.Div("Error loading roster metrics")

# Show detailed metrics modal when card is clicked
@app.callback(
    Output('metrics-modal', 'is_open'),
    Output('metrics-modal-content', 'children'),
    Output('current-school-unitid', 'data'),  # Store current school
    Input({'type': 'view-metrics-btn', 'index': dash.ALL}, 'n_clicks'),
    State('metrics-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_metrics_modal(n_clicks, is_open):
    try:
        if not any(n_clicks):
            return is_open, "", None
        
        # Get which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return is_open, "", None
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        unitid = eval(button_id)['index']
        
        # Get school data
        school = merged_data[merged_data['unitid'] == unitid].iloc[0]
        
        # Get roster data for this school
        school_roster = roster_data[roster_data['unitid'] == unitid] if 'unitid' in roster_data.columns else pd.DataFrame()
        
        # Fetch College Scorecard data
        scorecard_data = fetch_college_scorecard_data(unitid)
        
        # Extract scorecard fields
        if scorecard_data:
            try:
                latest = scorecard_data.get('latest', {})
                cost = latest.get('cost', {})
                admissions = latest.get('admissions', {})
                student = latest.get('student', {})
                completion = latest.get('completion', {})
                earnings = latest.get('earnings', {})
                aid = latest.get('aid', {})
                
                tuition_in_state = cost.get('tuition', {}).get('in_state')
                tuition_out_state = cost.get('tuition', {}).get('out_of_state')
                net_price = cost.get('avg_net_price', {}).get('overall')
                
                sat_scores = admissions.get('sat_scores', {})
                sat_avg = sat_scores.get('average', {}).get('overall')
                act_scores = admissions.get('act_scores', {})
                act_avg = act_scores.get('midpoint', {}).get('cumulative')
                
                retention_rate = student.get('retention_rate', {}).get('four_year', {}).get('full_time')
                completion_rate = completion.get('completion_rate_4yr_150nt')
                median_earnings = earnings.get('10_yrs_after_entry', {}).get('median')
                median_debt = aid.get('median_debt', {}).get('completers', {}).get('overall')
                
            except Exception as e:
                print(f"Error extracting scorecard data: {e}")
                tuition_in_state = tuition_out_state = net_price = None
                sat_avg = act_avg = None
                retention_rate = completion_rate = median_earnings = median_debt = None
        else:
            tuition_in_state = tuition_out_state = net_price = None
            sat_avg = act_avg = None
            retention_rate = completion_rate = median_earnings = median_debt = None
        
        # Create detailed metrics page
        ncaa_name = school.get('NCAA_name.x', '')
        logo_url = get_school_logo_url(school['inst_name'], ncaa_name)
        
        # Get school URL
        school_url = None
        if scorecard_data:
            school_url = scorecard_data.get('school', {}).get('school_url')
        
        # Create school name element (link if URL available)
        if school_url and school_url.startswith('http'):
            school_name_element = html.A(
                school['inst_name'],
                href=school_url,
                target='_blank',
                style={'color': '#003366', 'textDecoration': 'none'}
            )
        else:
            school_name_element = school['inst_name']
        
        content = dbc.Container([
            # Header with School Info Badges and Logo
            dbc.Row([
                dbc.Col([
                    html.H2(school_name_element, className="mb-3"),
                    html.P(f"{school.get('city', '')}, {school.get('state_abbr', '')}", className="text-muted mb-3"),
                    # School Info Badges (like College Scorecard)
                    html.Div([
                        # Years (based on highest degree - using 4-year as default for colleges)
                        html.Div([
                            html.Div([
                                html.Img(src="https://collegescorecard.ed.gov/school-icons/four.svg", 
                                        style={'width': '30px', 'height': '30px'})
                            ], style={
                                'width': '50px',
                                'height': '50px',
                                'borderRadius': '50%',
                                'backgroundColor': '#e8eaf6',
                                'display': 'flex',
                                'alignItems': 'center',
                                'justifyContent': 'center',
                                'marginBottom': '8px'
                            }),
                            html.Div("Year", style={'fontWeight': '500', 'fontSize': '14px', 'textAlign': 'center'})
                        ], style={'display': 'inline-block', 'marginRight': '30px', 'verticalAlign': 'top'}),
                        
                        # Control/Ownership
                        html.Div([
                            html.Div([
                                html.Img(src="https://collegescorecard.ed.gov/school-icons/public.svg" if school.get('control') == 1.0 
                                        else "https://collegescorecard.ed.gov/school-icons/private.svg",
                                        style={'width': '30px', 'height': '30px'})
                            ], style={
                                'width': '50px',
                                'height': '50px',
                                'borderRadius': '50%',
                                'backgroundColor': '#e8eaf6',
                                'display': 'flex',
                                'alignItems': 'center',
                                'justifyContent': 'center',
                                'marginBottom': '8px'
                            }),
                            html.Div(
                                "Public" if school.get('control') == 1.0 else ("Private Nonprofit" if school.get('control') == 2.0 else "Private For-Profit"),
                                style={'fontWeight': '500', 'fontSize': '14px', 'textAlign': 'center', 'maxWidth': '100px'}
                            )
                        ], style={'display': 'inline-block', 'marginRight': '30px', 'verticalAlign': 'top'}),
                        
                        # Locale (City/Town/Rural)
                        html.Div([
                            html.Div([
                                html.Img(src="https://collegescorecard.ed.gov/school-icons/city.svg" if school.get('locale', 0) >= 11 and school.get('locale', 0) <= 13 
                                        else ("https://collegescorecard.ed.gov/school-icons/suburban.svg" if school.get('locale', 0) >= 21 and school.get('locale', 0) <= 23
                                        else ("https://collegescorecard.ed.gov/school-icons/town.svg" if school.get('locale', 0) >= 31 and school.get('locale', 0) <= 33
                                        else "https://collegescorecard.ed.gov/school-icons/rural.svg")),
                                        style={'width': '30px', 'height': '30px'})
                            ], style={
                                'width': '50px',
                                'height': '50px',
                                'borderRadius': '50%',
                                'backgroundColor': '#e8eaf6',
                                'display': 'flex',
                                'alignItems': 'center',
                                'justifyContent': 'center',
                                'marginBottom': '8px'
                            }),
                            html.Div(
                                "City" if school.get('locale', 0) >= 11 and school.get('locale', 0) <= 13 
                                else ("Suburb" if school.get('locale', 0) >= 21 and school.get('locale', 0) <= 23
                                else ("Town" if school.get('locale', 0) >= 31 and school.get('locale', 0) <= 33
                                else "Rural")),
                                style={'fontWeight': '500', 'fontSize': '14px', 'textAlign': 'center'}
                            )
                        ], style={'display': 'inline-block', 'marginRight': '30px', 'verticalAlign': 'top'}),
                        
                        # Size
                        html.Div([
                            html.Div([
                                html.Img(src="https://collegescorecard.ed.gov/school-icons/small.svg" if school.get('ugds', 0) < 2000 
                                        else ("https://collegescorecard.ed.gov/school-icons/medium.svg" if school.get('ugds', 0) < 15000 
                                        else "https://collegescorecard.ed.gov/school-icons/large.svg"),
                                        style={'width': '30px', 'height': '30px'})
                            ], style={
                                'width': '50px',
                                'height': '50px',
                                'borderRadius': '50%',
                                'backgroundColor': '#e8eaf6',
                                'display': 'flex',
                                'alignItems': 'center',
                                'justifyContent': 'center',
                                'marginBottom': '8px'
                            }),
                            html.Div(
                                "Small" if school.get('ugds', 0) < 2000 
                                else ("Medium" if school.get('ugds', 0) < 15000 else "Large"),
                                style={'fontWeight': '500', 'fontSize': '14px', 'textAlign': 'center'}
                            )
                        ], style={'display': 'inline-block', 'marginRight': '30px', 'verticalAlign': 'top'}),
                    ], className="mb-4")
                ], width=9),
                dbc.Col([
                    html.Div([
                        html.Img(
                            src=logo_url,
                            style={
                                'maxHeight': '150px',
                                'maxWidth': '100%',
                                'objectFit': 'contain'
                            },
                            alt=school['inst_name']
                        )
                    ], className='text-center')
                ], width=3, className='d-flex align-items-center justify-content-center')
            ], className="mb-4"),
            
            # Athletic Stats Row
            html.H5("Athletic Performance", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Record", className="text-muted mb-2"),
                            html.H3(f"{int(school.get('wins', 0) if pd.notna(school.get('wins', 0)) else 0)}-{int(school.get('losses', 0) if pd.notna(school.get('losses', 0)) else 0)}", className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Win %", className="text-muted mb-2"),
                            html.H3(f"{school.get('win_pct', 0):.0f}%", className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Division", className="text-muted mb-2"),
                            html.H3(f"{school.get('division', 'N/A')}", className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Roster Size", className="text-muted mb-2"),
                            html.H3(f"{len(school_roster)}" if not school_roster.empty else "N/A", className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3)
            ], className="mb-4"),
            
            # Academic Stats Row
            html.H5("Academic Profile", className="mb-3 mt-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Acceptance Rate", className="text-muted mb-2"),
                            html.H3(f"{school.get('accept_rate_pct', 0):.0f}%", className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("SAT Average", className="text-muted mb-2"),
                            html.H3(f"{int(sat_avg)}" if sat_avg else "N/A", className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("ACT Average", className="text-muted mb-2"),
                            html.H3(f"{int(act_avg)}" if act_avg else "N/A", className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Enrollment", className="text-muted mb-2"),
                            html.H3(f"{int(school.get('ugds', 0)):,}", className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3)
            ], className="mb-4"),
            
            # Financial Information
            html.H5("Cost & Financial Aid", className="mb-3 mt-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("In-State Tuition", className="text-muted mb-2"),
                            html.H4(format_currency(tuition_in_state), className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Out-of-State Tuition", className="text-muted mb-2"),
                            html.H4(format_currency(tuition_out_state), className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Avg Net Price", className="text-muted mb-2"),
                            html.H4(format_currency(net_price), className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Median Debt", className="text-muted mb-2"),
                            html.H4(format_currency(median_debt), className="mb-0")
                        ])
                    ], className="text-center")
                ], width=3)
            ], className="mb-4"),
            
            # Outcomes
            html.H5("Student Outcomes", className="mb-3 mt-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Retention Rate", className="text-muted mb-2"),
                            html.H4(format_percentage(retention_rate), className="mb-0")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("4-Year Completion", className="text-muted mb-2"),
                            html.H4(format_percentage(completion_rate), className="mb-0")
                        ])
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Median Earnings (10yr)", className="text-muted mb-2"),
                            html.H4(format_currency(median_earnings), className="mb-0")
                        ])
                    ], className="text-center")
                ], width=4)
            ], className="mb-4")
            
        ], fluid=True)
        
        return not is_open, content, unitid
        
    except Exception as e:
        print(f"Error in toggle_metrics_modal: {e}")
        import traceback
        traceback.print_exc()
        return is_open, html.Div("Error loading metrics"), None

# Close modal callback
@app.callback(
    Output('metrics-modal', 'is_open', allow_duplicate=True),
    Input('close-metrics-modal', 'n_clicks'),
    State('metrics-modal', 'is_open'),
    prevent_initial_call=True
)
def close_modal(n_clicks, is_open):
    if n_clicks:
        return False
    return is_open

# Reset all filters
@app.callback(
    Output('home-zip', 'value'),
    Output('distance-filter', 'value'),
    Output('clim-month', 'value'),
    Output('temp-filter', 'value'),
    Output('precip-filter', 'value'),
    Output('cloud-filter', 'value'),
    Output('region-filter', 'value'),
    Output('division-filter', 'value'),
    Output('win-pct-filter', 'value'),
    Output('conference-filter', 'value'),
    Output('locale-filter', 'value'),
    Output('control-filter', 'value'),
    Output('accept-rate-filter', 'value'),
    Output('sat-filter', 'value'),
    Output('usnews-ranked-filter', 'value'),
    Output('enrollment-filter', 'value'),
    Output('religious-filter', 'value'),
    Input('reset-filters', 'n_clicks'),
    Input('conference-select-all', 'n_clicks'),
    Input('conference-deselect-all', 'n_clicks'),
    Input('religious-select-all', 'n_clicks'),
    Input('religious-deselect-all', 'n_clicks'),
    State('conference-filter', 'options'),
    State('religious-filter', 'options'),
    prevent_initial_call=True
)
def reset_filters(reset_clicks, conf_select_all, conf_deselect_all, 
                  relig_select_all, relig_deselect_all, conference_options, religious_options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'conference-select-all':
        # Only update conference filter
        return (dash.no_update, dash.no_update, dash.no_update, dash.no_update, 
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, 
                dash.no_update, [opt['value'] for opt in conference_options], 
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, dash.no_update)
    elif button_id == 'conference-deselect-all':
        # Only update conference filter
        return (dash.no_update, dash.no_update, dash.no_update, dash.no_update, 
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, 
                dash.no_update, [], 
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, dash.no_update)
    elif button_id == 'religious-select-all':
        # Only update religious filter
        return (dash.no_update, dash.no_update, dash.no_update, dash.no_update, 
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, 
                dash.no_update, dash.no_update,
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, [opt['value'] for opt in religious_options])
    elif button_id == 'religious-deselect-all':
        # Only update religious filter
        return (dash.no_update, dash.no_update, dash.no_update, dash.no_update, 
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, 
                dash.no_update, dash.no_update,
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, [])
    else:
        # Reset all filters
        return (
            '21703',  # home-zip
            2500,  # distance
            1,  # clim-month (January)
            [0, 100],  # temp
            [0, 10],  # precip
            [0, 100],  # cloud
            REGIONS,  # regions
            [1, 2, 3],  # divisions
            [0, 100],  # win-pct
            CONFERENCES,  # conferences
            LOCALES,  # locales
            list(CONTROL_MAP.keys()),  # control
            [0, 100],  # accept-rate
            [800, 1600],  # sat
            [],  # usnews-ranked
            ENROLLMENT_VALUES,  # enrollment
            [NON_AFFILIATED] + RELIGIOUS_AFFILIATIONS,  # religious
        )

# Open team metrics modal
@app.callback(
    Output('team-metrics-modal', 'is_open'),
    Output('team-metrics-modal-content', 'children'),
    Input('open-team-metrics-btn', 'n_clicks'),
    Input('close-team-metrics-modal', 'n_clicks'),
    State('team-metrics-modal', 'is_open'),
    State('current-school-unitid', 'data'),
    prevent_initial_call=True
)
def toggle_team_metrics_modal(open_clicks, close_clicks, is_open, unitid):
    """Open/close team metrics modal and populate with baseball-specific metrics"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, ""
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'close-team-metrics-modal':
        return False, ""
    
    if button_id == 'open-team-metrics-btn' and unitid:
        try:
            # Get school data
            school = merged_data[merged_data['unitid'] == unitid].iloc[0]
            
            # Get logo
            ncaa_name = school.get('NCAA_name.x', '')
            logo_url = get_school_logo_url(school['inst_name'], ncaa_name)
            
            # Get school URL
            school_url = None
            try:
                scorecard_data = fetch_college_scorecard_data(unitid)
                if scorecard_data:
                    school_url = scorecard_data.get('school', {}).get('school_url')
            except:
                pass
            
            # Pre-calculate charts to avoid multiple function calls
            state_charts = get_state_distribution_charts(school)
            fig_2025, fig_multi = state_charts if state_charts else (None, None)
            
            # Calculate freshman retention rate
            retention_rate = calculate_freshman_retention(school)
            
            # Get current head coach and record from team_coach_metrics
            prev_team_id = school.get('prev_team_id')
            head_coach_info = None
            if pd.notna(prev_team_id):
                try:
                    prev_team_id_int = int(float(prev_team_id))
                    current_coach = coach_metrics[
                        (coach_metrics['prev_team_id'] == prev_team_id_int) & 
                        (coach_metrics['Year'] == 2026)
                    ]
                    if not current_coach.empty:
                        coach_row = current_coach.iloc[0]
                        coach_name = coach_row.get('Head_Coach', 'Unknown')
                        wins_at_team = coach_row.get('Wins_At_Team', 0)
                        losses_at_team = coach_row.get('Losses_At_Team', 0)
                        seasons_at_team = coach_row.get('Seasons_At_Team', 0)
                        coach_stats_url = coach_row.get('Coach_Stats_URL', '')
                        
                        win_pct = int((wins_at_team / (wins_at_team + losses_at_team) * 100)) if (wins_at_team + losses_at_team) > 0 else 0
                        
                        head_coach_info = {
                            'name': coach_name,
                            'wins': int(wins_at_team) if pd.notna(wins_at_team) else 0,
                            'losses': int(losses_at_team) if pd.notna(losses_at_team) else 0,
                            'win_pct': win_pct,
                            'seasons': int(seasons_at_team) if pd.notna(seasons_at_team) else 0,
                            'url': coach_stats_url if pd.notna(coach_stats_url) and coach_stats_url else None
                        }
                except Exception as e:
                    print(f"Error getting coach info: {e}")
                    prev_team_id_int = None
            
            # Create school name element
            if school_url and school_url.startswith('http'):
                school_name_element = html.A(
                    school['inst_name'],
                    href=school_url,
                    target='_blank',
                    style={'color': '#003366', 'textDecoration': 'none'}
                )
            else:
                school_name_element = school['inst_name']
            
            # Get nickname and conference
            nickname = school.get('Nickname', '')
            conference = school.get('Conference_Name', '')
            
            # Create team metrics content
            content = dbc.Container([
                # Header with Logo
                dbc.Row([
                    dbc.Col([
                        html.H2(school_name_element, className="mb-1"),
                        html.P(
                            [
                                html.Span(f"{nickname}", style={'fontWeight': '500', 'fontSize': '1.1rem'}),
                                html.Span(f" • {conference}", className="text-muted")
                            ] if nickname and conference else (
                                html.Span(f"{nickname or conference}", style={'fontWeight': '500', 'fontSize': '1.1rem'}) if nickname or conference else ""
                            ),
                            className="mb-2"
                        ),
                        html.P(f"{school.get('city', '')}, {school.get('state_abbr', '')}", className="text-muted mb-1"),
                    ] + ([
                        html.Div([
                            html.P([
                                html.Strong("Head Coach: "),
                                html.A(
                                    head_coach_info['name'],
                                    href=head_coach_info['url'],
                                    target='_blank',
                                    style={'color': '#003366', 'textDecoration': 'underline'}
                                ) if head_coach_info.get('url') else html.Span(head_coach_info['name'])
                            ], className="mb-0"),
                            html.P([
                                html.Span(f"Coaches Record: {head_coach_info['wins']}-{head_coach_info['losses']} ({head_coach_info['win_pct']}%)", className="text-muted"),
                                html.Br(),
                                html.Span(f"Seasons at {school['inst_name']}: {head_coach_info['seasons']}", className="text-muted", style={'fontSize': '0.9rem'})
                            ], className="mb-0")
                        ])
                    ] if head_coach_info else []), width=9),
                    dbc.Col([
                        html.Div([
                            html.Img(
                                src=logo_url,
                                style={
                                    'maxHeight': '150px',
                                    'maxWidth': '100%',
                                    'objectFit': 'contain'
                                },
                                alt=school['inst_name']
                            )
                        ], className='text-center')
                    ], width=3, className='d-flex align-items-center justify-content-center')
                ], className="mb-4"),
                
                # Team Trajectory Section
                html.H5("Team Trajectory", className="mb-3"),
                dbc.Card([
                    dbc.CardBody([
                        calculate_trajectory_display(school)
                    ])
                ], className="mb-4"),
                
                # Recruiting Section
                html.H5("Recruiting Profile", className="mb-3"),
                # Pie charts row
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("2025 Season", className="mb-2 text-center"),
                                dcc.Graph(
                                    figure=fig_2025,
                                    config={'displayModeBar': False}
                                ) if fig_2025 is not None else html.P("No roster data available", className="text-muted text-center")
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("2022-2025", className="mb-2 text-center"),
                                dcc.Graph(
                                    figure=fig_multi,
                                    config={'displayModeBar': False}
                                ) if fig_multi is not None else html.P("No roster data available", className="text-muted text-center")
                            ])
                        ])
                    ], width=6)
                ], className="mb-3"),
                # Freshman retention gauge
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Freshman Retention Rate", className="text-center mb-2"),
                                html.P("Avg % of Freshmen who return the following year", className="text-center text-muted mb-3", style={'fontSize': '12px'}),
                                dcc.Graph(
                                    figure=go.Figure(go.Indicator(
                                        mode="gauge+number",
                                        value=retention_rate if retention_rate is not None else 0,
                                        domain={'x': [0, 1], 'y': [0, 1]},
                                        number={'suffix': '%'},
                                        title={'text': "Fr. Retention %", 'font': {'size': 16}},
                                        gauge={
                                            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                                            'bar': {'color': "darkblue"},
                                            'bgcolor': "white",
                                            'borderwidth': 2,
                                            'bordercolor': "gray",
                                            'steps': [
                                                {'range': [0, 40], 'color': '#ffcccb'},
                                                {'range': [40, 60], 'color': '#fff4cc'},
                                                {'range': [60, 80], 'color': '#ccffcc'},
                                                {'range': [80, 100], 'color': '#90ee90'}
                                            ],
                                            'threshold': {
                                                'line': {'color': "red", 'width': 4},
                                                'thickness': 0.75,
                                                'value': 85
                                            }
                                        }
                                    )).update_layout(
                                        height=300,
                                        margin=dict(l=20, r=20, t=40, b=20)
                                    ),
                                    config={'displayModeBar': False}
                                ) if retention_rate is not None else html.P("No retention data available", className="text-muted text-center")
                            ])
                        ])
                    ], width=12)
                ], className="mb-4"),
                
                # Roster Composition
                html.H5("Roster Composition", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Players by Class", className="mb-3"),
                                calculate_class_distribution_display(school)
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Position Depth", className="mb-3"),
                                calculate_position_depth_display(school)
                            ])
                        ])
                    ], width=6)
                ], className="mb-4")
                
            ], fluid=True)
            
            return True, content
            
        except Exception as e:
            print(f"Error opening team metrics modal: {e}")
            import traceback
            traceback.print_exc()
            return False, html.Div(f"Error loading team metrics: {str(e)}")
    
    return is_open, ""

# ============================================================================
# FIREBASE AUTHENTICATION CALLBACKS
# ============================================================================

# Register all Firebase authentication callbacks
register_auth_callbacks(app)

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
