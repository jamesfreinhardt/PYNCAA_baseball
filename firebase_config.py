"""
Firebase Configuration for NCAA Baseball App
Handles authentication and Firestore database interactions
"""

import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
from datetime import datetime
import json

# Firebase Web SDK configuration (for Pyrebase - client-side auth)
firebase_web_config = {
    "apiKey": "AIzaSyDD6l5a3hFFcWpmI3M2_rzUIHiUB8XR_60",
    "authDomain": "ncaabaseball-ebe8b.firebaseapp.com",
    "projectId": "ncaabaseball-ebe8b",
    "storageBucket": "ncaabaseball-ebe8b.firebasestorage.app",
    "messagingSenderId": "953871692538",
    "appId": "1:953871692538:web:249397a1ee500762f00f43",
    "measurementId": "G-SGH5BRV0Q4",
    "databaseURL": ""  # Not using Realtime Database
}

# Initialize Pyrebase (for client-side authentication)
firebase = pyrebase.initialize_app(firebase_web_config)
auth_client = firebase.auth()

# Initialize Firebase Admin SDK (for server-side operations)
# Note: You'll need to download your service account key from Firebase Console
# and save it as 'firebase-service-account.json' in the project directory
try:
    if not firebase_admin._apps:
        # Try to load service account credentials
        service_account_path = 'firebase-service-account.json'
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase Admin initialized with service account")
        else:
            # Initialize with default credentials (for development)
            firebase_admin.initialize_app()
            db = firestore.client()
            print("Firebase Admin initialized with default credentials")
except Exception as e:
    print(f"Warning: Firebase Admin initialization failed: {e}")
    db = None


class FirebaseAuth:
    """Handle user authentication operations"""
    
    @staticmethod
    def sign_up(email, password):
        """Create a new user account"""
        try:
            user = auth_client.create_user_with_email_and_password(email, password)
            return {
                'success': True,
                'user_id': user['localId'],
                'email': email,
                'token': user['idToken']
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def sign_in(email, password):
        """Sign in an existing user"""
        try:
            user = auth_client.sign_in_with_email_and_password(email, password)
            return {
                'success': True,
                'user_id': user['localId'],
                'email': email,
                'token': user['idToken'],
                'refresh_token': user['refreshToken']
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def sign_out():
        """Sign out the current user"""
        # Client-side sign out handled by clearing session
        return {'success': True}
    
    @staticmethod
    def verify_token(id_token):
        """Verify a user's ID token"""
        try:
            if db is None:
                return {'success': False, 'error': 'Firebase Admin not initialized'}
            decoded_token = auth.verify_id_token(id_token)
            return {
                'success': True,
                'user_id': decoded_token['uid'],
                'email': decoded_token.get('email')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class UserMetrics:
    """Track and manage user metrics in Firestore"""
    
    @staticmethod
    def create_user_profile(user_id, email, display_name=None):
        """Create a new user profile in Firestore"""
        try:
            if db is None:
                return {'success': False, 'error': 'Database not initialized'}
            
            user_ref = db.collection('users').document(user_id)
            user_data = {
                'email': email,
                'display_name': display_name or email.split('@')[0],
                'created_at': datetime.utcnow(),
                'last_login': datetime.utcnow(),
                'search_count': 0,
                'saved_schools': [],
                'preferences': {}
            }
            user_ref.set(user_data)
            return {'success': True, 'user_data': user_data}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_user_profile(user_id):
        """Get user profile from Firestore"""
        try:
            if db is None:
                return {'success': False, 'error': 'Database not initialized'}
            
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                return {'success': True, 'user_data': user_doc.to_dict()}
            else:
                return {'success': False, 'error': 'User profile not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def update_last_login(user_id):
        """Update user's last login timestamp"""
        try:
            if db is None:
                return {'success': False}
            
            user_ref = db.collection('users').document(user_id)
            user_ref.update({'last_login': datetime.utcnow()})
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def track_search(user_id, search_params):
        """Track a user's search query"""
        try:
            if db is None:
                return {'success': False}
            
            # Increment search count
            user_ref = db.collection('users').document(user_id)
            user_ref.update({
                'search_count': firestore.Increment(1)
            })
            
            # Log the search
            search_ref = db.collection('user_searches').add({
                'user_id': user_id,
                'timestamp': datetime.utcnow(),
                'search_params': search_params
            })
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def save_school(user_id, school_name, school_data):
        """Save a school to user's favorites"""
        try:
            if db is None:
                return {'success': False}
            
            user_ref = db.collection('users').document(user_id)
            user_ref.update({
                f'saved_schools': firestore.ArrayUnion([{
                    'name': school_name,
                    'saved_at': datetime.utcnow(),
                    'data': school_data
                }])
            })
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_saved_schools(user_id):
        """Get user's saved schools"""
        try:
            if db is None:
                return {'success': False, 'schools': []}
            
            user_data = UserMetrics.get_user_profile(user_id)
            if user_data['success']:
                return {
                    'success': True,
                    'schools': user_data['user_data'].get('saved_schools', [])
                }
            return {'success': False, 'schools': []}
        except Exception as e:
            return {'success': False, 'error': str(e), 'schools': []}
    
    @staticmethod
    def update_preferences(user_id, preferences):
        """Update user preferences"""
        try:
            if db is None:
                return {'success': False}
            
            user_ref = db.collection('users').document(user_id)
            user_ref.update({'preferences': preferences})
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_user_analytics(user_id):
        """Get user activity analytics"""
        try:
            if db is None:
                return {'success': False}
            
            # Get user profile
            profile = UserMetrics.get_user_profile(user_id)
            if not profile['success']:
                return profile
            
            # Get search history
            searches = db.collection('user_searches')\
                .where('user_id', '==', user_id)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(50)\
                .stream()
            
            search_history = [search.to_dict() for search in searches]
            
            return {
                'success': True,
                'profile': profile['user_data'],
                'search_history': search_history
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
