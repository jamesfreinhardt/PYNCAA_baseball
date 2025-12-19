"""
Test script for AI features
Verifies that AI components can be created and rendered
"""

import sys
from dash import html
import dash_bootstrap_components as dbc

# Import AI components
from ai_components import (
    create_ai_recommendations_tab,
    create_email_generator_modal,
    create_recommendation_card,
    create_email_display,
    create_draft_email_button,
    create_ai_feature_notice,
    create_recommendation_settings_card
)

# Import AI engines
from ai_recommendations import SchoolRecommendationEngine, EmailGenerator

def test_ai_engines():
    """Test AI engine initialization"""
    print("Testing AI engines...")
    
    rec_engine = SchoolRecommendationEngine()
    email_gen = EmailGenerator()
    
    print(f"✓ SchoolRecommendationEngine initialized")
    print(f"  - Available: {rec_engine.is_available()}")
    
    print(f"✓ EmailGenerator initialized")
    print(f"  - Available: {email_gen.is_available()}")
    
    return True

def test_ui_components():
    """Test UI component creation"""
    print("\nTesting UI components...")
    
    # Test recommendations tab
    tab = create_ai_recommendations_tab()
    print("✓ AI recommendations tab created")
    
    # Test email modal
    modal = create_email_generator_modal()
    print("✓ Email generator modal created")
    
    # Test recommendation card
    sample_rec = {
        'school_name': 'Test University',
        'reasons': ['Great program', 'Good location', 'Strong academics'],
        'opportunity': 'Open roster spots in your position',
        'classification': 'Target',
        'school_data': {
            'unitid': 12345,
            'name': 'Test University',
            'division': 1,
            'conference': 'Test Conference',
            'city': 'Test City',
            'state': 'TS'
        }
    }
    card = create_recommendation_card(sample_rec)
    print("✓ Recommendation card created")
    
    # Test email display
    sample_email = {
        'subject': 'Introduction - Baseball Recruiting',
        'body': 'Dear Coach,\n\nThis is a test email.\n\nBest regards,\nStudent'
    }
    email_display = create_email_display(sample_email)
    print("✓ Email display created")
    
    # Test draft email button
    button = create_draft_email_button('12345', 'Test School')
    print("✓ Draft email button created")
    
    # Test AI feature notice
    notice = create_ai_feature_notice()
    print("✓ AI feature notice created")
    
    # Test recommendation settings card
    settings = create_recommendation_settings_card()
    print("✓ Recommendation settings card created")
    
    return True

def test_component_structure():
    """Verify component structure"""
    print("\nTesting component structure...")
    
    # Check that components return expected types
    tab = create_ai_recommendations_tab()
    assert isinstance(tab, html.Div), "Tab should be html.Div"
    print("✓ Tab structure valid")
    
    modal = create_email_generator_modal()
    assert isinstance(modal, dbc.Modal), "Modal should be dbc.Modal"
    print("✓ Modal structure valid")
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("AI Features Test Suite")
    print("=" * 60)
    
    try:
        test_ai_engines()
        test_ui_components()
        test_component_structure()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
