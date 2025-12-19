"""
School Classification System
Classifies schools as Target, Reach, or Safety based on athletic and academic fit
"""

import pandas as pd
import numpy as np
from firebase_config import UserMetrics, db
from datetime import datetime


class SchoolClassifier:
    """Handle school classification logic and storage"""
    
    @staticmethod
    def calculate_athletic_fit(user_metrics, school_data):
        """
        Calculate athletic fit score (0-100)
        Higher score = better fit/more likely to play
        """
        if not user_metrics:
            return 50  # Default if no metrics
        
        score = 50  # Base score
        
        # Win percentage factor (lower = easier to make roster)
        win_pct = school_data.get('win_pct', 50)
        if win_pct < 40:
            score += 20  # Easier roster spot
        elif win_pct < 60:
            score += 10
        elif win_pct > 75:
            score -= 10  # Competitive roster
        
        # Division factor
        division = school_data.get('division', 1)
        if division == 3:
            score += 15
        elif division == 2:
            score += 5
        
        # Could add more sophisticated metrics here when available:
        # - Compare user's exit velo to team averages
        # - Compare user's pitching velo to team averages
        # - Position depth chart analysis
        
        return min(max(score, 0), 100)
    
    @staticmethod
    def calculate_academic_fit(user_academic, school_data):
        """
        Calculate academic fit score (0-100)
        Higher score = more likely to be admitted
        """
        if not user_academic:
            return 50  # Default if no academic info
        
        score = 50  # Base score
        
        # SAT comparison
        user_sat = user_academic.get('sat_total', 0)
        school_sat = school_data.get('sat_avg', 0)
        
        if user_sat and school_sat:
            sat_diff = user_sat - school_sat
            if sat_diff > 100:
                score += 20  # Well above average
            elif sat_diff > 0:
                score += 10  # Above average
            elif sat_diff > -100:
                score -= 10  # Below average
            else:
                score -= 20  # Well below average
        
        # GPA comparison (if available in future)
        user_gpa = user_academic.get('gpa_unweighted', 0)
        # Would compare to school's average GPA when available
        
        # Acceptance rate factor
        accept_rate = school_data.get('accept_rate_pct', 50)
        if accept_rate > 70:
            score += 15  # Easier admission
        elif accept_rate > 50:
            score += 5
        elif accept_rate < 20:
            score -= 15  # Very competitive
        elif accept_rate < 35:
            score -= 5
        
        return min(max(score, 0), 100)
    
    @staticmethod
    def calculate_overall_fit(user_id, school_data):
        """
        Calculate overall fit score combining athletic and academic
        Returns score and breakdown
        """
        # Get user data
        user_profile = UserMetrics.get_user_profile(user_id)
        
        athletic_metrics = {}
        academic_info = {}
        
        if user_profile.get('success'):
            user_data = user_profile.get('user_data', {})
            athletic_metrics = user_data.get('athletic_metrics', {})
            academic_info = user_data.get('academic_info', {})
        
        # Calculate component scores
        athletic_score = SchoolClassifier.calculate_athletic_fit(athletic_metrics, school_data)
        academic_score = SchoolClassifier.calculate_academic_fit(academic_info, school_data)
        
        # Weighted overall score (60% athletic, 40% academic)
        overall_score = (athletic_score * 0.6) + (academic_score * 0.4)
        
        return {
            'overall_score': round(overall_score, 1),
            'athletic_score': round(athletic_score, 1),
            'academic_score': round(academic_score, 1)
        }
    
    @staticmethod
    def auto_classify(overall_score):
        """
        Auto-classify school based on overall fit score
        75+ = Safety, 50-75 = Target, <50 = Reach
        """
        if overall_score >= 75:
            return "Safety"
        elif overall_score >= 50:
            return "Target"
        else:
            return "Reach"
    
    @staticmethod
    def save_classification(user_id, school_data, classification, auto_suggested=False, notes=""):
        """
        Save school classification to Firestore
        """
        try:
            if db is None:
                return {'success': False, 'error': 'Database not initialized'}
            
            # Create unique document ID
            school_name = school_data.get('instnm', 'Unknown')
            unitid = school_data.get('unitid', 'unknown')
            doc_id = f"{user_id}_{unitid}"
            
            # Calculate fit scores
            fit_scores = SchoolClassifier.calculate_overall_fit(user_id, school_data)
            
            classification_data = {
                'user_id': user_id,
                'school_name': school_name,
                'unitid': str(unitid),
                'classification': classification,
                'auto_suggested': auto_suggested,
                'classification_scores': fit_scores,
                'notes': notes,
                'classified_date': datetime.utcnow(),
                'last_updated': datetime.utcnow()
            }
            
            # Save to Firestore
            db.collection('user_school_classifications').document(doc_id).set(classification_data)
            
            return {'success': True, 'data': classification_data}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_classification(user_id, unitid):
        """
        Get existing classification for a school
        """
        try:
            if db is None:
                return {'success': False, 'classification': None}
            
            doc_id = f"{user_id}_{unitid}"
            doc = db.collection('user_school_classifications').document(doc_id).get()
            
            if doc.exists:
                return {'success': True, 'classification': doc.to_dict()}
            else:
                return {'success': True, 'classification': None}
                
        except Exception as e:
            return {'success': False, 'error': str(e), 'classification': None}
    
    @staticmethod
    def get_all_classifications(user_id):
        """
        Get all school classifications for a user
        """
        try:
            if db is None:
                return {'success': False, 'classifications': []}
            
            docs = db.collection('user_school_classifications')\
                .where('user_id', '==', user_id)\
                .stream()
            
            classifications = [doc.to_dict() for doc in docs]
            
            return {'success': True, 'classifications': classifications}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'classifications': []}
    
    @staticmethod
    def update_classification_notes(user_id, unitid, notes):
        """
        Update notes for a classification
        """
        try:
            if db is None:
                return {'success': False}
            
            doc_id = f"{user_id}_{unitid}"
            db.collection('user_school_classifications').document(doc_id).update({
                'notes': notes,
                'last_updated': datetime.utcnow()
            })
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_classification_summary(user_id):
        """
        Get summary of classifications by type
        """
        result = SchoolClassifier.get_all_classifications(user_id)
        
        if not result['success']:
            return {'target': 0, 'reach': 0, 'safety': 0, 'total': 0}
        
        classifications = result['classifications']
        
        summary = {
            'target': sum(1 for c in classifications if c.get('classification') == 'Target'),
            'reach': sum(1 for c in classifications if c.get('classification') == 'Reach'),
            'safety': sum(1 for c in classifications if c.get('classification') == 'Safety'),
            'total': len(classifications)
        }
        
        return summary
