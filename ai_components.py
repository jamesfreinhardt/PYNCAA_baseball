"""
AI Feature UI Components
Provides UI elements for AI recommendations and email generation
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_ai_recommendations_tab():
    """Create the AI Recommendations tab content"""
    return html.Div([
        dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H3([
                        html.I(className="fas fa-magic me-2"),
                        "AI-Powered School Recommendations"
                    ], className="mb-3"),
                    html.P([
                        "Get personalized college recommendations based on your preferences, ",
                        "saved schools, and filtering patterns. Our AI analyzes your profile ",
                        "to suggest schools that match your athletic and academic goals."
                    ], className="text-muted mb-4")
                ])
            ]),
            
            # Generate Recommendations Button
            dbc.Row([
                dbc.Col([
                    dbc.Button([
                        html.I(className="fas fa-sparkles me-2"),
                        "Generate Recommendations"
                    ], id="generate-recommendations-btn", color="primary", size="lg", className="mb-4")
                ], width=12, className="text-center")
            ]),
            
            # Loading Spinner
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="recommendations-loading",
                        type="default",
                        children=html.Div(id="recommendations-content")
                    )
                ])
            ])
        ], fluid=True, className="p-4")
    ])


def create_recommendation_card(recommendation: dict) -> dbc.Card:
    """
    Create a card displaying a single recommendation
    
    Args:
        recommendation: Dict with school_name, reasons, opportunity, classification
    """
    school_data = recommendation.get('school_data', {})
    school_name = school_data.get('name', recommendation.get('school_name', 'Unknown'))
    unitid = school_data.get('unitid', '')
    reasons = recommendation.get('reasons', [])
    opportunity = recommendation.get('opportunity', '')
    classification = recommendation.get('classification', 'Target')
    
    # Classification badge color
    badge_colors = {
        'Safety': 'success',
        'Target': 'primary',
        'Reach': 'warning'
    }
    badge_color = badge_colors.get(classification, 'secondary')
    
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5(school_name, className="mb-0")
                ], width=8),
                dbc.Col([
                    dbc.Badge(classification, color=badge_color, className="float-end")
                ], width=4)
            ])
        ]),
        dbc.CardBody([
            # School details
            html.Div([
                html.P([
                    html.Strong("Division: "),
                    f"{school_data.get('division', 'N/A')}"
                ], className="mb-1"),
                html.P([
                    html.Strong("Conference: "),
                    f"{school_data.get('conference', 'N/A')}"
                ], className="mb-1"),
                html.P([
                    html.Strong("Location: "),
                    f"{school_data.get('city', '')}, {school_data.get('state', '')}"
                ], className="mb-3")
            ]),
            
            # Why this school (reasons)
            html.Div([
                html.H6([
                    html.I(className="fas fa-lightbulb me-2"),
                    "Why This School:"
                ], className="text-primary"),
                html.Ul([
                    html.Li(reason) for reason in reasons
                ], className="mb-3")
            ]),
            
            # Opportunity highlight
            html.Div([
                html.H6([
                    html.I(className="fas fa-star me-2"),
                    "Key Opportunity:"
                ], className="text-success"),
                html.P(opportunity, className="mb-3")
            ]),
            
            # Action buttons
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-info-circle me-2"), "View Details"],
                        id={"type": "view-recommended-school", "index": unitid},
                        color="info",
                        outline=True,
                        size="sm",
                        className="w-100"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-heart me-2"), "Save School"],
                        id={"type": "save-recommended-school", "index": unitid},
                        color="danger",
                        outline=True,
                        size="sm",
                        className="w-100"
                    )
                ], width=6)
            ])
        ])
    ], className="mb-3 recommendation-card")


def create_email_generator_modal():
    """Create modal for email generation"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle([
            html.I(className="fas fa-envelope me-2"),
            "Draft Email to Coach"
        ])),
        dbc.ModalBody([
            # School info display
            html.Div(id="email-school-info", className="mb-3"),
            
            # Email type selection
            dbc.Row([
                dbc.Col([
                    dbc.Label("Email Type"),
                    dbc.RadioItems(
                        id="email-type-select",
                        options=[
                            {"label": "Introduction Email", "value": "introduction"},
                            {"label": "Follow-up Email", "value": "followup"}
                        ],
                        value="introduction",
                        inline=True,
                        className="mb-3"
                    )
                ])
            ]),
            
            # Tone selection
            dbc.Row([
                dbc.Col([
                    dbc.Label("Tone"),
                    dbc.RadioItems(
                        id="email-tone-select",
                        options=[
                            {"label": "Professional", "value": "professional"},
                            {"label": "Friendly", "value": "friendly"},
                            {"label": "Enthusiastic", "value": "enthusiastic"}
                        ],
                        value="professional",
                        inline=True,
                        className="mb-3"
                    )
                ])
            ]),
            
            # Additional info/context
            dbc.Row([
                dbc.Col([
                    dbc.Label("Additional Information (Optional)"),
                    dbc.Textarea(
                        id="email-additional-info",
                        placeholder="Any specific achievements, upcoming camps, or context you want to include...",
                        style={"height": "100px"},
                        className="mb-3"
                    )
                ])
            ]),
            
            # Generate button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-magic me-2"), "Generate Email"],
                        id="generate-email-btn",
                        color="primary",
                        className="w-100 mb-3"
                    )
                ])
            ]),
            
            # Loading and email display
            dcc.Loading(
                id="email-loading",
                type="default",
                children=html.Div(id="email-display-area")
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="close-email-modal", color="secondary")
        ])
    ], id="email-generator-modal", size="lg", scrollable=True, is_open=False)


def create_email_display(email_data: dict) -> html.Div:
    """
    Create display for generated email
    
    Args:
        email_data: Dict with 'subject' and 'body'
    """
    subject = email_data.get('subject', '')
    body = email_data.get('body', '')
    
    return html.Div([
        dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            "Email generated successfully! Review and edit as needed."
        ], color="success", className="mb-3"),
        
        # Subject line
        dbc.Row([
            dbc.Col([
                dbc.Label("Subject:"),
                dbc.Input(
                    id="email-subject-edit",
                    type="text",
                    value=subject,
                    className="mb-3"
                )
            ])
        ]),
        
        # Email body
        dbc.Row([
            dbc.Col([
                dbc.Label("Email Body:"),
                dbc.Textarea(
                    id="email-body-edit",
                    value=body,
                    style={"height": "300px"},
                    className="mb-3"
                )
            ])
        ]),
        
        # Action buttons
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-copy me-2"), "Copy to Clipboard"],
                    id="copy-email-btn",
                    color="success",
                    className="me-2"
                )
            ], width="auto"),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-redo me-2"), "Regenerate"],
                    id="regenerate-email-btn",
                    color="warning",
                    outline=True
                )
            ], width="auto")
        ]),
        
        # Copy confirmation
        html.Div(id="copy-confirmation", className="mt-2")
    ])


def create_draft_email_button(unitid: str, school_name: str = "") -> dbc.Button:
    """
    Create a button to draft an email to a coach
    
    Args:
        unitid: School's unique ID
        school_name: School name for display
    """
    return dbc.Button(
        [html.I(className="fas fa-envelope me-2"), "Draft Email to Coach"],
        id={"type": "draft-email-btn", "index": unitid},
        color="primary",
        outline=True,
        size="sm",
        className="mt-2"
    )


def create_ai_feature_notice():
    """Create a notice explaining AI features are available"""
    return dbc.Alert([
        html.H6([
            html.I(className="fas fa-robot me-2"),
            "AI-Powered Features Available!"
        ], className="alert-heading"),
        html.P([
            "This app now includes AI-powered features to help with your college search:",
            html.Ul([
                html.Li("Get personalized school recommendations based on your profile and preferences"),
                html.Li("Generate professional emails to college coaches with one click")
            ])
        ]),
        html.Hr(),
        html.P([
            "Visit the ",
            html.Strong("AI Recommendations"),
            " tab to get started, or use the ",
            html.Strong("Draft Email"),
            " button on any saved school."
        ], className="mb-0")
    ], color="info", dismissable=True, id="ai-features-notice", className="mb-3")


def create_recommendation_settings_card():
    """Create a card for configuring recommendation settings"""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-cog me-2"),
            "Recommendation Settings"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Number of Recommendations"),
                    dbc.RadioItems(
                        id="num-recommendations-select",
                        options=[
                            {"label": "3 schools", "value": 3},
                            {"label": "5 schools", "value": 5},
                            {"label": "10 schools", "value": 10}
                        ],
                        value=5,
                        inline=True
                    )
                ])
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col([
                    html.P([
                        html.I(className="fas fa-info-circle me-2"),
                        "Recommendations are based on your current filters, ",
                        "saved schools, and profile information."
                    ], className="text-muted small mb-0")
                ])
            ])
        ])
    ], className="mb-3")
