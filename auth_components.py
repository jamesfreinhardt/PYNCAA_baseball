"""
Authentication Components for NCAA Baseball Dash App
Provides login, signup, and user profile UI components
"""

from dash import html, dcc
import dash_bootstrap_components as dbc

def create_login_modal():
    """Create login/signup modal component"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Sign In", id="auth-modal-title")),
        dbc.ModalBody([
            # Tabs for Login/Signup
            dbc.Tabs([
                dbc.Tab([
                    html.Div([
                        dbc.Label("Email"),
                        dbc.Input(
                            id="login-email",
                            type="email",
                            placeholder="Enter your email",
                            className="mb-3"
                        ),
                        dbc.Label("Password"),
                        dbc.Input(
                            id="login-password",
                            type="password",
                            placeholder="Enter your password",
                            className="mb-3"
                        ),
                        html.Div(id="login-error", className="text-danger mb-3"),
                        dbc.Button(
                            "Sign In",
                            id="login-button",
                            color="primary",
                            className="w-100"
                        )
                    ], className="p-3")
                ], label="Sign In", tab_id="tab-login"),
                
                dbc.Tab([
                    html.Div([
                        dbc.Label("Email"),
                        dbc.Input(
                            id="signup-email",
                            type="email",
                            placeholder="Enter your email",
                            className="mb-3"
                        ),
                        dbc.Label("Password"),
                        dbc.Input(
                            id="signup-password",
                            type="password",
                            placeholder="Create a password",
                            className="mb-3"
                        ),
                        dbc.Label("Confirm Password"),
                        dbc.Input(
                            id="signup-password-confirm",
                            type="password",
                            placeholder="Confirm your password",
                            className="mb-3"
                        ),
                        html.Div(id="signup-error", className="text-danger mb-3"),
                        dbc.Button(
                            "Create Account",
                            id="signup-button",
                            color="success",
                            className="w-100"
                        )
                    ], className="p-3")
                ], label="Sign Up", tab_id="tab-signup")
            ], id="auth-tabs", active_tab="tab-login")
        ]),
    ], id="auth-modal", is_open=False, size="md")


def create_user_menu(is_authenticated=False, user_email=None):
    """Create user menu component for navbar"""
    if not is_authenticated:
        return dbc.Button(
            [html.I(className="fas fa-user me-2"), "Sign In"],
            id="show-auth-modal",
            color="primary",
            outline=True,
            size="sm"
        )
    else:
        return dbc.DropdownMenu([
            dbc.DropdownMenuItem(
                [html.I(className="fas fa-user me-2"), user_email or "User"],
                header=True
            ),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem(
                [html.I(className="fas fa-heart me-2"), "Saved Schools"],
                id="view-saved-schools"
            ),
            dbc.DropdownMenuItem(
                [html.I(className="fas fa-chart-line me-2"), "My Analytics"],
                id="view-analytics"
            ),
            dbc.DropdownMenuItem(
                [html.I(className="fas fa-cog me-2"), "Settings"],
                id="view-settings"
            ),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem(
                [html.I(className="fas fa-sign-out-alt me-2"), "Sign Out"],
                id="signout-button"
            )
        ], label="Account", color="primary", size="sm")


def create_saved_schools_modal():
    """Create modal to display saved schools"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Saved Schools")),
        dbc.ModalBody([
            html.Div(id="saved-schools-content", children=[
                html.P("Loading your saved schools...", className="text-muted")
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="close-saved-schools", color="secondary")
        ])
    ], id="saved-schools-modal", is_open=False, size="lg", scrollable=True)


def create_analytics_modal():
    """Create modal to display user analytics"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("My Analytics")),
        dbc.ModalBody([
            html.Div(id="analytics-content", children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(id="total-searches", children="0", className="text-primary"),
                                html.P("Total Searches", className="text-muted mb-0")
                            ])
                        ], className="mb-3")
                    ], md=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(id="saved-schools-count", children="0", className="text-success"),
                                html.P("Saved Schools", className="text-muted mb-0")
                            ])
                        ], className="mb-3")
                    ], md=6)
                ]),
                html.Hr(),
                html.H5("Recent Search History"),
                html.Div(id="search-history-content")
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="close-analytics", color="secondary")
        ])
    ], id="analytics-modal", is_open=False, size="lg", scrollable=True)


def create_school_save_button(school_name):
    """Create a button to save a school to favorites"""
    return dbc.Button(
        [html.I(className="fas fa-heart me-2"), "Save School"],
        id={"type": "save-school-btn", "index": school_name},
        color="danger",
        outline=True,
        size="sm",
        className="mt-2"
    )


def create_school_classification_buttons(school_name="", unitid="", current_classification=None):
    """Create Target/Reach/Safety classification buttons"""
    return html.Div([
        html.H6("Classify This School:", className="mb-2"),
        dbc.ButtonGroup([
            dbc.Button(
                [html.I(className="fas fa-bullseye me-1"), "Target"],
                id={"type": "classify-btn", "index": f"{unitid}_target"},
                color="primary",
                outline=current_classification != "Target",
                size="sm",
                className="classification-btn"
            ),
            dbc.Button(
                [html.I(className="fas fa-rocket me-1"), "Reach"],
                id={"type": "classify-btn", "index": f"{unitid}_reach"},
                color="warning",
                outline=current_classification != "Reach",
                size="sm",
                className="classification-btn"
            ),
            dbc.Button(
                [html.I(className="fas fa-check-circle me-1"), "Safety"],
                id={"type": "classify-btn", "index": f"{unitid}_safety"},
                color="success",
                outline=current_classification != "Safety",
                size="sm",
                className="classification-btn"
            )
        ], className="w-100 mb-3"),
        html.Div(id={"type": "classification-feedback", "index": unitid}, className="mt-2")
    ])


def create_classification_badge(classification, fit_score=None):
    """Create a badge showing school classification"""
    if not classification:
        return html.Span()
    
    colors = {
        "Target": "primary",
        "Reach": "warning",
        "Safety": "success"
    }
    
    icons = {
        "Target": "fas fa-bullseye",
        "Reach": "fas fa-rocket",
        "Safety": "fas fa-check-circle"
    }
    
    badge_content = [
        html.I(className=f"{icons.get(classification, 'fas fa-tag')} me-1"),
        classification
    ]
    
    if fit_score is not None:
        badge_content.append(f" ({fit_score}%)")
    
    return dbc.Badge(
        badge_content,
        color=colors.get(classification, "secondary"),
        className="ms-2",
        pill=True
    )


def create_fit_score_card(fit_scores):
    """Create a card displaying fit scores breakdown"""
    if not fit_scores:
        return html.Div()
    
    overall = fit_scores.get('overall_score', 0)
    athletic = fit_scores.get('athletic_score', 0)
    academic = fit_scores.get('academic_score', 0)
    
    return dbc.Card([
        dbc.CardBody([
            html.H6("Fit Score Analysis", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4(f"{overall}%", className="text-primary mb-0"),
                        html.Small("Overall Fit", className="text-muted")
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.H5(f"{athletic}%", className="text-info mb-0"),
                        html.Small("Athletic Fit", className="text-muted")
                    ], className="text-center")
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.H5(f"{academic}%", className="text-success mb-0"),
                        html.Small("Academic Fit", className="text-muted")
                    ], className="text-center")
                ], width=4)
            ]),
            html.Hr(className="my-2"),
            html.Small([
                html.I(className="fas fa-info-circle me-1"),
                "Higher scores indicate better fit and higher likelihood of success"
            ], className="text-muted")
        ])
    ], className="mb-3")


def create_my_schools_modal():
    """Modal to view classified schools by category"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("My Schools")),
        dbc.ModalBody([
            dbc.Tabs([
                dbc.Tab([
                    html.Div(id="target-schools-list", className="p-3")
                ], label="🎯 Target Schools", tab_id="tab-target"),
                dbc.Tab([
                    html.Div(id="reach-schools-list", className="p-3")
                ], label="🚀 Reach Schools", tab_id="tab-reach"),
                dbc.Tab([
                    html.Div(id="safety-schools-list", className="p-3")
                ], label="✅ Safety Schools", tab_id="tab-safety"),
                dbc.Tab([
                    html.Div(id="all-classified-schools-list", className="p-3")
                ], label="All Classified", tab_id="tab-all")
            ], id="my-schools-tabs", active_tab="tab-target")
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="close-my-schools", color="secondary")
        ])
    ], id="my-schools-modal", size="lg", scrollable=True, is_open=False)


# Session storage components for maintaining user state
def create_session_stores():
    """Create dcc.Store components for user session management"""
    return html.Div([
        dcc.Store(id='user-session', storage_type='session'),  # Stores user_id and token
        dcc.Store(id='user-profile', storage_type='session'),  # Stores user profile data
        dcc.Location(id='url', refresh=False)  # For handling redirects
    ])
