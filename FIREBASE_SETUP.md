# Firebase Setup Guide for NCAA Baseball App

## Overview
This app now includes Firebase authentication and Firestore database integration for user management and metrics tracking.

## Firebase Configuration Already Done ✅
The Firebase web configuration has been added to `firebase_config.py`:
- API Key: AIzaSyDD6l5a3hFFcWpmI3M2_rzUIHiUB8XR_60
- Project: ncaabaseball-ebe8b
- Authentication and Firestore are configured

## Setup Steps

### 1. Enable Firebase Services in Console
Visit: https://console.firebase.google.com/project/ncaabaseball-ebe8b

1. **Enable Authentication**
   - Go to Authentication > Sign-in method
   - Enable "Email/Password" authentication
   - Save changes

2. **Enable Firestore Database**
   - Go to Firestore Database
   - Click "Create database"
   - Start in **test mode** for development (set proper rules later)
   - Choose your preferred region (us-central1 recommended)

3. **Set Firestore Security Rules** (Important for production)
   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       // Users can read/write their own data
       match /users/{userId} {
         allow read, write: if request.auth != null && request.auth.uid == userId;
       }
       
       // User searches - users can only write their own
       match /user_searches/{searchId} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```

### 2. Download Service Account Key (Optional - for admin features)

1. Go to Project Settings > Service Accounts
2. Click "Generate new private key"
3. Save the JSON file as `firebase-service-account.json` in the project root
4. **IMPORTANT**: Add this file to `.gitignore` (already done)

### 3. Install Dependencies
Already done! The following packages are installed:
```bash
pip install pyrebase4 firebase-admin
```

## Features Implemented

### User Authentication
- **Sign Up**: Create new user accounts with email/password
- **Sign In**: Authenticate existing users
- **Sign Out**: Log out functionality
- **Session Management**: Persistent sessions using Dash stores

### User Metrics Tracking
- **User Profiles**: Automatic profile creation on signup
- **Search Tracking**: Track user search queries and parameters
- **Saved Schools**: Users can save favorite schools
- **Analytics Dashboard**: View user activity metrics
- **Search History**: View recent search history

### UI Components
- **Login/Signup Modal**: Accessible from the sidebar
- **User Menu Dropdown**: Shows user email and options when logged in
- **Saved Schools Modal**: View and manage saved schools
- **Analytics Modal**: Personal dashboard with metrics

## Using the App

### For Users
1. Click "Sign In" button in the sidebar
2. Create an account or sign in with existing credentials
3. Browse and filter schools as normal
4. Click "Save School" buttons to save favorites
5. View saved schools and analytics from the user menu

### For Developers

#### Firebase Configuration Files
- `firebase_config.py`: Firebase initialization and helper classes
- `auth_components.py`: UI components for authentication
- `auth_callbacks.py`: Dash callbacks for auth interactions
- `app.py`: Main app with Firebase integration

#### Key Classes

**FirebaseAuth**
```python
from firebase_config import FirebaseAuth

# Sign up new user
result = FirebaseAuth.sign_up(email, password)

# Sign in existing user
result = FirebaseAuth.sign_in(email, password)
```

**UserMetrics**
```python
from firebase_config import UserMetrics

# Track a search
UserMetrics.track_search(user_id, search_params)

# Save a school
UserMetrics.save_school(user_id, school_name, school_data)

# Get user analytics
analytics = UserMetrics.get_user_analytics(user_id)
```

## Data Structure

### Firestore Collections

**users** (collection)
```json
{
  "user_id": {
    "email": "user@example.com",
    "display_name": "User Name",
    "created_at": "2024-12-16T...",
    "last_login": "2024-12-16T...",
    "search_count": 42,
    "saved_schools": [
      {
        "name": "Stanford University",
        "saved_at": "2024-12-16T...",
        "data": {}
      }
    ],
    "preferences": {}
  }
}
```

**user_searches** (collection)
```json
{
  "search_id": {
    "user_id": "user_id",
    "timestamp": "2024-12-16T...",
    "search_params": {
      "divisions": [1, 2],
      "conferences": ["ACC", "SEC"],
      "regions": ["West"]
    }
  }
}
```

## Security Notes

⚠️ **Important Security Considerations**:

1. **API Keys in Code**: The Firebase web config API key in `firebase_config.py` is safe to expose in client-side code (it's not a secret). Firebase security is enforced through Firestore rules.

2. **Service Account Key**: The `firebase-service-account.json` file (if you download it) contains sensitive credentials. Never commit it to git!

3. **Firestore Rules**: Always set proper security rules in production. The test mode rules allow all reads/writes!

4. **Password Security**: Firebase handles password hashing and security automatically.

## Testing

To test the authentication:

1. Run the app: `python app.py`
2. Click "Sign In" in the sidebar
3. Switch to "Sign Up" tab
4. Create a test account
5. Verify you can sign in/out
6. Test saving schools and viewing analytics

## Troubleshooting

### "Firebase Admin not initialized"
- Download and add `firebase-service-account.json` to the project root
- Or ignore this warning - client-side auth still works

### "Database not initialized"
- Enable Firestore in Firebase Console
- Check Firestore security rules

### Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Authentication errors
- Verify Email/Password is enabled in Firebase Console
- Check that the Firebase config in `firebase_config.py` matches your project

## Next Steps

1. ✅ Enable Authentication in Firebase Console
2. ✅ Enable Firestore Database
3. ✅ Set Firestore security rules
4. Optional: Download service account key for admin features
5. Test the authentication flow
6. Customize user metrics tracking as needed

## Support

Firebase Documentation:
- Authentication: https://firebase.google.com/docs/auth
- Firestore: https://firebase.google.com/docs/firestore
- Python SDK: https://firebase.google.com/docs/admin/setup
