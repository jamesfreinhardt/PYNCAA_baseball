"""
Authentication Callbacks for NCAA Baseball Dash App
Handles all Firebase authentication and user metrics interactions
"""

from dash import Input, Output, State, callback, ALL, ctx
from dash.exceptions import PreventUpdate
import json
from firebase_config import FirebaseAuth, UserMetrics
from auth_components import create_user_menu
import dash_bootstrap_components as dbc
from dash import html


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
                return result['user_data']
        return None
    
    
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
