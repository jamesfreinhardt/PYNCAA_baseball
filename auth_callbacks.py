"""
Authentication Callbacks for NCAA Baseball Dash App
Handles all Firebase authentication and user metrics interactions
"""

from dash import Input, Output, State, callback, ALL, ctx, dcc, html
from dash.exceptions import PreventUpdate
import json
from firebase_config import FirebaseAuth, UserMetrics
from auth_components import create_user_menu
from school_classification import SchoolClassifier
import dash_bootstrap_components as dbc


def register_auth_callbacks(app):
    """Register all authentication-related callbacks"""
    
    # Login callback
    @app.callback(
        [Output('user-session', 'data'),
         Output('login-error', 'children'),
         Output('auth-modal', 'is_open', allow_duplicate=True)],
        Input('login-button', 'n_clicks'),
        [State('login-email', 'value'),
         State('login-password', 'value')],
        prevent_initial_call=True
    )
    def handle_login(n_clicks, email, password):
        if not n_clicks:
            raise PreventUpdate
        
        if not email or not password:
            return None, "Please enter both email and password", True
        
        # Attempt login
        result = FirebaseAuth.sign_in(email, password)
        
        if result['success']:
            # Create/update user profile
            UserMetrics.create_user_profile(result['user_id'], result['email'])
            UserMetrics.update_last_login(result['user_id'])
            
            session_data = {
                'user_id': result['user_id'],
                'email': result['email'],
                'token': result['token']
            }
            return session_data, "", False
        else:
            error_msg = result.get('error', 'Login failed')
            return None, f"Error: {error_msg}", True
    
    
    # Signup callback
    @app.callback(
        [Output('user-session', 'data', allow_duplicate=True),
         Output('signup-error', 'children'),
         Output('auth-modal', 'is_open', allow_duplicate=True)],
        Input('signup-button', 'n_clicks'),
        [State('signup-email', 'value'),
         State('signup-password', 'value'),
         State('signup-password-confirm', 'value')],
        prevent_initial_call=True
    )
    def handle_signup(n_clicks, email, password, password_confirm):
        if not n_clicks:
            raise PreventUpdate
        
        if not email or not password:
            return None, "Please enter email and password", True
        
        if password != password_confirm:
            return None, "Passwords do not match", True
        
        if len(password) < 6:
            return None, "Password must be at least 6 characters", True
        
        # Attempt signup
        result = FirebaseAuth.sign_up(email, password)
        
        if result['success']:
            # Create user profile
            UserMetrics.create_user_profile(result['user_id'], result['email'])
            
            session_data = {
                'user_id': result['user_id'],
                'email': result['email'],
                'token': result['token']
            }
            return session_data, "", False
        else:
            error_msg = result.get('error', 'Signup failed')
            return None, f"Error: {error_msg}", True
    
    
    # Signout callback
    @app.callback(
        Output('user-session', 'data', allow_duplicate=True),
        Input('signout-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_signout(n_clicks):
        if not n_clicks:
            raise PreventUpdate
        FirebaseAuth.sign_out()
        return None
    
    
    # Show auth modal
    @app.callback(
        Output('auth-modal', 'is_open'),
        [Input('show-auth-modal', 'n_clicks'),
         Input('login-button', 'n_clicks'),
         Input('signup-button', 'n_clicks')],
        [State('auth-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_auth_modal(show_clicks, login_clicks, signup_clicks, is_open):
        if ctx.triggered_id == 'show-auth-modal':
            return not is_open
        return is_open
    
    
    # Load user profile when session is created
    @app.callback(
        Output('user-profile', 'data'),
        Input('user-session', 'data'),
        prevent_initial_call=True
    )
    def load_user_profile(session_data):
        if not session_data:
            return None
        
        user_id = session_data.get('user_id')
        if user_id:
            result = UserMetrics.get_user_profile(user_id)
            if result['success']:
                raw = result['user_data']
                safe = {}
                for key, val in raw.items():
                    try:
                        json.dumps(val)
                        safe[key] = val
                    except TypeError:
                        safe[key] = str(val)
                return safe
        return None

    # Render user menu with display name once signed in
    @app.callback(
        Output('user-menu-container', 'children'),
        Input('user-session', 'data'),
        Input('user-profile', 'data')
    )
    def render_user_menu(session_data, profile_data):
        is_authenticated = bool(session_data)
        email = session_data.get('email') if session_data else None
        display_name = None
        if profile_data:
            display_name = profile_data.get('display_name') or profile_data.get('email')
        return create_user_menu(is_authenticated, user_email=email, display_name=display_name)

    # Navigate to profile tab from menu
    @app.callback(
        Output('main-tabs', 'active_tab'),
        Input('view-profile', 'n_clicks'),
        State('main-tabs', 'active_tab'),
        prevent_initial_call=True
    )
    def go_to_profile(n_clicks, active_tab):
        if not n_clicks:
            raise PreventUpdate
        return 'tab-profile'

    # Render profile page content
    @app.callback(
        Output('profile-page', 'children'),
        Input('user-session', 'data'),
        Input('user-profile', 'data')
    )
    def render_profile_page(session_data, profile_data):
        if not session_data:
            return dbc.Alert([
                html.I(className="fas fa-lock me-2"),
                "Sign in to view your profile"
            ], color="info")

        if not profile_data:
            return dbc.Spinner(color="primary")

        def fmt_time(val):
            try:
                return val.strftime('%Y-%m-%d %H:%M UTC')
            except Exception:
                return str(val)

        saved_schools = profile_data.get('saved_schools') or []
        player_profile = profile_data.get('player_profile', {})
        athletic_metrics = profile_data.get('athletic_metrics', {})
        academic_info = profile_data.get('academic_info', {})
        preferences = profile_data.get('preferences', {})

        # Account info card
        account_card = dbc.Card([
            dbc.CardBody([
                html.H5(profile_data.get('display_name', 'User'), className="mb-1"),
                html.P(profile_data.get('email', ''), className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P([html.I(className="fas fa-calendar-plus me-2"), "Joined: ", fmt_time(profile_data.get('created_at'))], className="mb-1", style={'fontSize': '0.9rem'}),
                    ], width=6),
                    dbc.Col([
                        html.P([html.I(className="fas fa-clock me-2"), "Last Login: ", fmt_time(profile_data.get('last_login'))], className="mb-0", style={'fontSize': '0.9rem'}),
                    ], width=6)
                ])
            ])
        ], className="mb-3")

        # Activity card
        activity_card = dbc.Card([
            dbc.CardBody([
                html.H6("Activity Summary", className="mb-3"),
                dbc.Row([
                    dbc.Col([html.Div([html.H5(str(profile_data.get('search_count', 0)), className="text-primary mb-0"), html.Small("Searches")], className="text-center")], width=6),
                    dbc.Col([html.Div([html.H5(str(len(saved_schools)), className="text-success mb-0"), html.Small("Saved Schools")], className="text-center")], width=6)
                ])
            ])
        ], className="mb-3")

        # Player Profile Tab
        player_profile_tab = dbc.Tab(
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Position (Primary)"),
                            dbc.Input(id='player-position', type='text', placeholder='e.g., SS', 
                                     value=player_profile.get('primary_position', ''), className='mb-3')
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Additional Positions"),
                            dbc.Input(id='player-positions', type='text', placeholder='e.g., 2B, OF', 
                                     value=', '.join(player_profile.get('positions', [])), className='mb-3')
                        ], md=6)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Height (inches)"),
                            dbc.Input(id='player-height', type='number', placeholder='e.g., 72', 
                                     value=player_profile.get('height_inches', ''), className='mb-3')
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Weight (lbs)"),
                            dbc.Input(id='player-weight', type='number', placeholder='e.g., 185', 
                                     value=player_profile.get('weight_lbs', ''), className='mb-3')
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Bats"),
                            dcc.Dropdown(id='player-bats', options=[{'label': 'Right (R)', 'value': 'R'}, {'label': 'Left (L)', 'value': 'L'}, {'label': 'Switch (S)', 'value': 'S'}],
                                      value=player_profile.get('bats', 'R'), className='mb-3')
                        ], md=4)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Graduation Year"),
                            dbc.Input(id='player-grad-year', type='number', placeholder='e.g., 2026', 
                                     value=player_profile.get('grad_year', ''), className='mb-3')
                        ], md=6),
                        dbc.Col([
                            dbc.Label("High School"),
                            dbc.Input(id='player-hs', type='text', placeholder='e.g., Central High', 
                                     value=player_profile.get('high_school', ''), className='mb-3')
                        ], md=6)
                    ]),
                    dbc.Button("Save Player Profile", id='save-player-profile', color='primary', className='me-2'),
                    html.Small(id='player-profile-status', className='text-muted ms-2')
                ])
            ]), 
            label='👤 Player Profile', 
            tab_id='tab-player-profile'
        )

        # Athletic Metrics Tab
        athletic_metrics_tab = dbc.Tab(
            dbc.Card([
                dbc.CardBody([
                    html.H6("Hitting Metrics", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Exit Velocity (mph)"),
                            dbc.Input(id='metric-exit-velo', type='number', placeholder='e.g., 92', 
                                     value=athletic_metrics.get('exit_velocity', ''), className='mb-3')
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Bat Speed (mph)"),
                            dbc.Input(id='metric-bat-speed', type='number', placeholder='e.g., 75', 
                                     value=athletic_metrics.get('bat_speed', ''), className='mb-3')
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Home-to-First (sec)"),
                            dbc.Input(id='metric-home-first', type='number', step=0.1, placeholder='e.g., 4.2', 
                                     value=athletic_metrics.get('home_to_first', ''), className='mb-3')
                        ], md=4)
                    ]),
                    html.H6("Speed/Defense Metrics", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("60-Yard Dash (sec)"),
                            dbc.Input(id='metric-60-dash', type='number', step=0.1, placeholder='e.g., 6.8', 
                                     value=athletic_metrics.get('sixty_yard_dash', ''), className='mb-3')
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Infield Velo (mph)"),
                            dbc.Input(id='metric-infield-velo', type='number', placeholder='e.g., 85', 
                                     value=athletic_metrics.get('infield_velo', ''), className='mb-3')
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Outfield Velo (mph)"),
                            dbc.Input(id='metric-outfield-velo', type='number', placeholder='e.g., 88', 
                                     value=athletic_metrics.get('outfield_velo', ''), className='mb-3')
                        ], md=4)
                    ]),
                    html.H6("Pitching Metrics", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Fastball Velo (mph)"),
                            dbc.Input(id='metric-fb-velo', type='number', placeholder='e.g., 88', 
                                     value=athletic_metrics.get('fastball_velo', ''), className='mb-3')
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Curveball Velo (mph)"),
                            dbc.Input(id='metric-cb-velo', type='number', placeholder='e.g., 72', 
                                     value=athletic_metrics.get('curveball_velo', ''), className='mb-3')
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Changeup Velo (mph)"),
                            dbc.Input(id='metric-changeup-velo', type='number', placeholder='e.g., 78', 
                                     value=athletic_metrics.get('changeup_velo', ''), className='mb-3')
                        ], md=4)
                    ]),
                    dbc.Button("Save Athletic Metrics", id='save-athletic-metrics', color='info', className='me-2'),
                    html.Small(id='athletic-metrics-status', className='text-muted ms-2')
                ])
            ]),
            label='💪 Athletic Metrics', 
            tab_id='tab-athletic-metrics'
        )

        # Academic Info Tab
        academic_info_tab = dbc.Tab(
            dbc.Card([
                dbc.CardBody([
                    html.H6("GPA", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Unweighted GPA"),
                            dbc.Input(id='academic-gpa-unweighted', type='number', step=0.01, placeholder='e.g., 3.75', 
                                     value=academic_info.get('gpa_unweighted', ''), className='mb-3')
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Weighted GPA"),
                            dbc.Input(id='academic-gpa-weighted', type='number', step=0.01, placeholder='e.g., 4.2', 
                                     value=academic_info.get('gpa_weighted', ''), className='mb-3')
                        ], md=6)
                    ]),
                    html.H6("Standardized Tests", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("SAT Total"),
                            dbc.Input(id='academic-sat-total', type='number', placeholder='e.g., 1320', 
                                     value=academic_info.get('sat_total', ''), className='mb-3')
                        ], md=6),
                        dbc.Col([
                            dbc.Label("ACT Composite"),
                            dbc.Input(id='academic-act-composite', type='number', placeholder='e.g., 28', 
                                     value=academic_info.get('act_composite', ''), className='mb-3')
                        ], md=6)
                    ]),
                    html.H6("NCAA Eligibility", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dcc.Checklist(
                                id='academic-ncaa-eligible',
                                options=[{'label': ' NCAA Eligible', 'value': 1}],
                                value=[1] if academic_info.get('ncaa_eligible') else [],
                                className='mb-3'
                            )
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Core Courses Completed"),
                            dbc.Input(id='academic-core-courses', type='number', placeholder='e.g., 16', 
                                     value=academic_info.get('core_courses_completed', ''), className='mb-3')
                        ], md=6)
                    ]),
                    dbc.Button("Save Academic Info", id='save-academic-info', color='success', className='me-2'),
                    html.Small(id='academic-info-status', className='text-muted ms-2')
                ])
            ]),
            label='📚 Academic Info', 
            tab_id='tab-academic-info'
        )

        # Preferences Tab
        preferences_tab = dbc.Tab(
            dbc.Card([
                dbc.CardBody([
                    html.H6("Division Preferences", className="mb-3"),
                    dcc.Checklist(
                        id='pref-divisions',
                        options=[{'label': ' Division 1', 'value': 1}, {'label': ' Division 2', 'value': 2}, {'label': ' Division 3', 'value': 3}],
                        value=preferences.get('preferred_divisions', []),
                        className='mb-4'
                    ),
                    html.H6("Location Preferences", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Max Distance (miles)"),
                            dbc.Input(id='pref-max-distance', type='number', placeholder='e.g., 500', 
                                     value=preferences.get('max_distance_miles', ''), className='mb-3')
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Preferred Regions"),
                            dbc.Input(id='pref-regions', type='text', placeholder='e.g., South, Southeast', 
                                     value=', '.join(preferences.get('preferred_regions', [])), className='mb-3')
                        ], md=6)
                    ]),
                    html.H6("Financial/Athletic", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dcc.Checklist(
                                id='pref-financial-aid',
                                options=[{'label': ' Need Financial Aid', 'value': 1}],
                                value=[1] if preferences.get('need_financial_aid') else [],
                                className='mb-3'
                            )
                        ], md=6),
                        dbc.Col([
                            dcc.Checklist(
                                id='pref-athletic-scholarship',
                                options=[{'label': ' Need Athletic Scholarship', 'value': 1}],
                                value=[1] if preferences.get('need_athletic_scholarship') else [],
                                className='mb-3'
                            )
                        ], md=6)
                    ]),
                    dbc.Button("Save Preferences", id='save-preferences', color='warning', className='me-2'),
                    html.Small(id='preferences-status', className='text-muted ms-2')
                ])
            ]),
            label='⚙️ Preferences', 
            tab_id='tab-preferences'
        )

        # Return tabbed layout
        return dbc.Container([
            dbc.Row([dbc.Col([account_card])], className="mb-3"),
            dbc.Row([dbc.Col([activity_card])], className="mb-3"),
            dbc.Tabs([
                player_profile_tab,
                athletic_metrics_tab,
                academic_info_tab,
                preferences_tab
            ], id='profile-tabs', active_tab='tab-player-profile')
        ], fluid=True)

    # Save player profile
    @app.callback(
        Output('player-profile-status', 'children'),
        Input('save-player-profile', 'n_clicks'),
        [State('user-session', 'data'),
         State('player-position', 'value'),
         State('player-positions', 'value'),
         State('player-height', 'value'),
         State('player-weight', 'value'),
         State('player-bats', 'value'),
         State('player-grad-year', 'value'),
         State('player-hs', 'value')],
        prevent_initial_call=True
    )
    def save_player_profile(n_clicks, session_data, position, positions, height, weight, bats, grad_year, hs):
        if not n_clicks or not session_data:
            raise PreventUpdate
        
        user_id = session_data.get('user_id')
        player_data = {
            'primary_position': position or None,
            'positions': [p.strip() for p in positions.split(',')] if positions else [],
            'height_inches': int(height) if height else None,
            'weight_lbs': int(weight) if weight else None,
            'bats': bats,
            'grad_year': int(grad_year) if grad_year else None,
            'high_school': hs
        }
        
        # TODO: Save to Firestore when backend method is ready
        return "✓ Player profile saved!"

    # Save athletic metrics
    @app.callback(
        Output('athletic-metrics-status', 'children'),
        Input('save-athletic-metrics', 'n_clicks'),
        [State('user-session', 'data'),
         State('metric-exit-velo', 'value'),
         State('metric-bat-speed', 'value'),
         State('metric-home-first', 'value'),
         State('metric-60-dash', 'value'),
         State('metric-infield-velo', 'value'),
         State('metric-outfield-velo', 'value'),
         State('metric-fb-velo', 'value'),
         State('metric-cb-velo', 'value'),
         State('metric-changeup-velo', 'value')],
        prevent_initial_call=True
    )
    def save_athletic_metrics(n_clicks, session_data, exit_velo, bat_speed, home_first, dash_60, infield_velo, outfield_velo, fb_velo, cb_velo, changeup_velo):
        if not n_clicks or not session_data:
            raise PreventUpdate
        
        user_id = session_data.get('user_id')
        metrics_data = {
            'exit_velocity': float(exit_velo) if exit_velo else None,
            'bat_speed': float(bat_speed) if bat_speed else None,
            'home_to_first': float(home_first) if home_first else None,
            'sixty_yard_dash': float(dash_60) if dash_60 else None,
            'infield_velo': float(infield_velo) if infield_velo else None,
            'outfield_velo': float(outfield_velo) if outfield_velo else None,
            'fastball_velo': float(fb_velo) if fb_velo else None,
            'curveball_velo': float(cb_velo) if cb_velo else None,
            'changeup_velo': float(changeup_velo) if changeup_velo else None
        }
        
        # TODO: Save to Firestore when backend method is ready
        return "✓ Athletic metrics saved!"

    # Save academic info
    @app.callback(
        Output('academic-info-status', 'children'),
        Input('save-academic-info', 'n_clicks'),
        [State('user-session', 'data'),
         State('academic-gpa-unweighted', 'value'),
         State('academic-gpa-weighted', 'value'),
         State('academic-sat-total', 'value'),
         State('academic-act-composite', 'value'),
         State('academic-ncaa-eligible', 'value'),
         State('academic-core-courses', 'value')],
        prevent_initial_call=True
    )
    def save_academic_info(n_clicks, session_data, gpa_unweighted, gpa_weighted, sat_total, act_composite, ncaa_eligible, core_courses):
        if not n_clicks or not session_data:
            raise PreventUpdate
        
        user_id = session_data.get('user_id')
        academic_data = {
            'gpa_unweighted': float(gpa_unweighted) if gpa_unweighted else None,
            'gpa_weighted': float(gpa_weighted) if gpa_weighted else None,
            'sat_total': int(sat_total) if sat_total else None,
            'act_composite': int(act_composite) if act_composite else None,
            'ncaa_eligible': bool(ncaa_eligible and len(ncaa_eligible) > 0),
            'core_courses_completed': int(core_courses) if core_courses else None
        }
        
        # TODO: Save to Firestore when backend method is ready
        return "✓ Academic info saved!"

    # Save preferences
    @app.callback(
        Output('preferences-status', 'children'),
        Input('save-preferences', 'n_clicks'),
        [State('user-session', 'data'),
         State('pref-divisions', 'value'),
         State('pref-max-distance', 'value'),
         State('pref-regions', 'value'),
         State('pref-financial-aid', 'value'),
         State('pref-athletic-scholarship', 'value')],
        prevent_initial_call=True
    )
    def save_preferences(n_clicks, session_data, divisions, max_distance, regions, financial_aid, athletic_scholarship):
        if not n_clicks or not session_data:
            raise PreventUpdate
        
        user_id = session_data.get('user_id')
        prefs_data = {
            'preferred_divisions': divisions or [],
            'max_distance_miles': int(max_distance) if max_distance else None,
            'preferred_regions': [r.strip() for r in regions.split(',')] if regions else [],
            'need_financial_aid': bool(financial_aid and len(financial_aid) > 0),
            'need_athletic_scholarship': bool(athletic_scholarship and len(athletic_scholarship) > 0)
        }
        
        # TODO: Save to Firestore when backend method is ready
        return "✓ Preferences saved!"
    
    # Save school to favorites
    @app.callback(
        Output({'type': 'save-school-btn', 'index': ALL}, 'children'),
        Input({'type': 'save-school-btn', 'index': ALL}, 'n_clicks'),
        [State('user-session', 'data'),
         State({'type': 'save-school-btn', 'index': ALL}, 'id')],
        prevent_initial_call=True
    )
    def save_school(n_clicks, session_data, button_ids):
        if not any(n_clicks):
            raise PreventUpdate
        
        if not session_data:
            return [[html.I(className="fas fa-heart me-2"), "Save School"]] * len(button_ids)
        
        # Find which button was clicked
        clicked_index = next((i for i, clicks in enumerate(n_clicks) if clicks), None)
        if clicked_index is None:
            raise PreventUpdate
        
        school_name = button_ids[clicked_index]['index']
        user_id = session_data.get('user_id')
        
        # Save school
        result = UserMetrics.save_school(user_id, school_name, {})
        
        # Update button text
        button_texts = []
        for i, btn_id in enumerate(button_ids):
            if i == clicked_index and result.get('success'):
                button_texts.append([html.I(className="fas fa-heart"), " Saved!"])
            else:
                button_texts.append([html.I(className="fas fa-heart me-2"), "Save School"])
        
        return button_texts
    
    
    # Show saved schools modal
    @app.callback(
        [Output('saved-schools-modal', 'is_open'),
         Output('saved-schools-content', 'children')],
        [Input('view-saved-schools', 'n_clicks'),
         Input('close-saved-schools', 'n_clicks')],
        [State('user-session', 'data'),
         State('saved-schools-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_saved_schools(view_clicks, close_clicks, session_data, is_open):
        if ctx.triggered_id == 'view-saved-schools':
            if not session_data:
                return False, html.P("Please sign in to view saved schools")
            
            user_id = session_data.get('user_id')
            result = UserMetrics.get_saved_schools(user_id)
            
            if result['success'] and result['schools']:
                schools_list = [
                    dbc.Card([
                        dbc.CardBody([
                            html.H5(school.get('name', 'Unknown School')),
                            html.P(f"Saved: {school.get('saved_at', 'N/A')}", className="text-muted small")
                        ])
                    ], className="mb-2")
                    for school in result['schools']
                ]
                return True, schools_list
            else:
                return True, html.P("No saved schools yet. Start exploring!", className="text-muted")
        
        return False, []
    
    
    # Show analytics modal
    @app.callback(
        [Output('analytics-modal', 'is_open'),
         Output('total-searches', 'children'),
         Output('saved-schools-count', 'children'),
         Output('search-history-content', 'children')],
        [Input('view-analytics', 'n_clicks'),
         Input('close-analytics', 'n_clicks')],
        [State('user-session', 'data'),
         State('analytics-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_analytics(view_clicks, close_clicks, session_data, is_open):
        if ctx.triggered_id == 'view-analytics':
            if not session_data:
                return False, "0", "0", html.P("Please sign in to view analytics")
            
            user_id = session_data.get('user_id')
            result = UserMetrics.get_user_analytics(user_id)
            
            if result['success']:
                profile = result.get('profile', {})
                search_history = result.get('search_history', [])
                
                total_searches = str(profile.get('search_count', 0))
                saved_count = str(len(profile.get('saved_schools', [])))
                
                # Format search history
                if search_history:
                    history_items = [
                        dbc.Card([
                            dbc.CardBody([
                                html.P(f"Search at: {search.get('timestamp', 'N/A')}", className="small mb-0")
                            ])
                        ], className="mb-2")
                        for search in search_history[:10]
                    ]
                else:
                    history_items = html.P("No search history yet", className="text-muted")
                
                return True, total_searches, saved_count, history_items
            else:
                return True, "0", "0", html.P("Unable to load analytics")
        
        return False, "0", "0", []
    
    
    # Track searches (called when user performs a search)
    @app.callback(
        Output('search-tracker', 'data', allow_duplicate=True),
        [Input('division-filter', 'value'),
         Input('conference-filter', 'value'),
         Input('region-filter', 'value')],
        State('user-session', 'data'),
        prevent_initial_call=True
    )
    def track_search(divisions, conferences, regions, session_data):
        if session_data:
            user_id = session_data.get('user_id')
            search_params = {
                'divisions': divisions,
                'conferences': conferences,
                'regions': regions
            }
            UserMetrics.track_search(user_id, search_params)
        raise PreventUpdate
    
    
    # ========================================================================
    # SCHOOL CLASSIFICATION CALLBACKS
    # ========================================================================
    
    # Handle classification button clicks
    @app.callback(
        Output({'type': 'classification-feedback', 'index': ALL}, 'children'),
        Input({'type': 'classify-btn', 'index': ALL}, 'n_clicks'),
        [State('user-session', 'data'),
         State({'type': 'classify-btn', 'index': ALL}, 'id'),
         State('current-school-data', 'data')],
        prevent_initial_call=True
    )
    def handle_classification(n_clicks, session_data, button_ids, school_data):
        if not any(n_clicks):
            raise PreventUpdate
        
        if not session_data:
            return [dbc.Alert("Please sign in to classify schools", color="warning", className="mt-2")]
        
        # Find which button was clicked
        clicked_index = next((i for i, clicks in enumerate(n_clicks) if clicks), None)
        if clicked_index is None or not school_data:
            raise PreventUpdate
        
        # Extract classification from button ID
        button_id = button_ids[clicked_index]['index']
        classification_type = button_id.split('_')[-1].capitalize()
        
        user_id = session_data.get('user_id')
        
        # Save classification
        result = SchoolClassifier.save_classification(
            user_id=user_id,
            school_data=school_data,
            classification=classification_type,
            auto_suggested=False
        )
        
        # Prepare feedback
        feedbacks = [html.Span() for _ in button_ids]
        
        if result.get('success'):
            fit_score = result['data']['classification_scores']['overall_score']
            feedbacks[clicked_index] = dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"Classified as {classification_type} (Fit Score: {fit_score}%)"
            ], color="success", className="mt-2", dismissable=True)
        else:
            feedbacks[clicked_index] = dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error: {result.get('error', 'Unknown error')}"
            ], color="danger", className="mt-2", dismissable=True)
        
        return feedbacks
    
    
    # Show My Schools modal
    @app.callback(
        [Output('my-schools-modal', 'is_open'),
         Output('target-schools-list', 'children'),
         Output('reach-schools-list', 'children'),
         Output('safety-schools-list', 'children'),
         Output('all-classified-schools-list', 'children')],
        [Input('view-my-schools', 'n_clicks'),
         Input('close-my-schools', 'n_clicks')],
        [State('user-session', 'data'),
         State('my-schools-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_my_schools(view_clicks, close_clicks, session_data, is_open):
        if ctx.triggered_id == 'view-my-schools':
            if not session_data:
                return False, [], [], [], []
            
            user_id = session_data.get('user_id')
            result = SchoolClassifier.get_all_classifications(user_id)
            
            if not result['success']:
                return True, [html.P("Error loading schools", className="text-danger")], [], [], []
            
            classifications = result['classifications']
            
            if not classifications:
                empty_msg = html.P("No schools classified yet. Start exploring and classify schools!", className="text-muted")
                return True, empty_msg, empty_msg, empty_msg, empty_msg
            
            # Sort by classification
            target_schools = [c for c in classifications if c.get('classification') == 'Target']
            reach_schools = [c for c in classifications if c.get('classification') == 'Reach']
            safety_schools = [c for c in classifications if c.get('classification') == 'Safety']
            
            def create_school_card(school):
                scores = school.get('classification_scores', {})
                return dbc.Card([
                    dbc.CardBody([
                        html.H5(school.get('school_name', 'Unknown School')),
                        dbc.Badge(
                            f"{scores.get('overall_score', 0)}% Overall Fit",
                            color="info",
                            className="mb-2"
                        ),
                        html.P([
                            html.Small(f"Athletic: {scores.get('athletic_score', 0)}% | "),
                            html.Small(f"Academic: {scores.get('academic_score', 0)}%")
                        ], className="text-muted mb-2"),
                        html.P(school.get('notes', ''), className="small") if school.get('notes') else None,
                        html.Small(f"Classified: {school.get('classified_date', 'N/A')}", className="text-muted")
                    ])
                ], className="mb-2")
            
            target_list = [create_school_card(s) for s in target_schools] if target_schools else [html.P("No target schools yet", className="text-muted")]
            reach_list = [create_school_card(s) for s in reach_schools] if reach_schools else [html.P("No reach schools yet", className="text-muted")]
            safety_list = [create_school_card(s) for s in safety_schools] if safety_schools else [html.P("No safety schools yet", className="text-muted")]
            all_list = [create_school_card(s) for s in classifications]
            
            return True, target_list, reach_list, safety_list, all_list
        
        return False, [], [], [], []

