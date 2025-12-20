# Firebase Setup Guide for NCAA Baseball App

## Overview
This app now includes Firebase authentication and Firestore database integration for user management and metrics tracking.

## Firebase Configuration

The Firebase web configuration is loaded from environment variables for security.
You need to configure your Firebase project credentials in a `.env` file.

## Setup Steps

### 1. Create `.env` File
Copy `.env.example` to `.env` and fill in your Firebase project credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Firebase configuration values (get these from your Firebase Console):
```
FIREBASE_API_KEY=your_firebase_api_key_here
FIREBASE_AUTH_DOMAIN=your_project_id.firebaseapp.com
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_project_id.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
FIREBASE_APP_ID=your_app_id
FIREBASE_MEASUREMENT_ID=your_measurement_id
```

**To get these values:**
1. Go to Firebase Console: https://console.firebase.google.com
2. Select your project (or create a new one)
3. Go to Project Settings (⚙️ icon)
4. Scroll to "Your apps" section
5. If you haven't added a web app, click "Add app" and select Web
6. Copy the config values from the Firebase SDK snippet

### 2. Enable Firebase Services in Console
Visit your Firebase Console: https://console.firebase.google.com

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

### 3. Download Service Account Key (Optional - for admin features)

1. Go to Project Settings > Service Accounts
2. Click "Generate new private key"
3. Save the JSON file as `firebase-service-account.json` in the project root
4. **IMPORTANT**: This file is already in `.gitignore` and should never be committed to version control

### 4. Install Dependencies
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

1. **Environment Variables**: Firebase configuration is now loaded from environment variables stored in `.env` file. This file is git-ignored and should never be committed to version control.

2. **API Keys**: While the Firebase web config API key can be used in client-side code, it's best practice to keep it in environment variables to avoid exposing it publicly on GitHub.

3. **Service Account Key**: The `firebase-service-account.json` file (if you download it) contains sensitive credentials and should NEVER be committed to git. This file is already in `.gitignore`.

4. **Firestore Rules**: Always set proper security rules in production. The test mode rules allow all reads/writes!

5. **Password Security**: Firebase handles password hashing and security automatically.

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
- Check that your `.env` file has the correct Firebase configuration
- Ensure all required environment variables are set

## Next Steps

1. ✅ Create `.env` file with your Firebase configuration
2. ✅ Enable Authentication in Firebase Console
3. ✅ Enable Firestore Database
4. ✅ Set Firestore security rules
5. Optional: Download service account key for admin features
6. Test the authentication flow
7. Customize user metrics tracking as needed

## Support

Firebase Documentation:
- Authentication: https://firebase.google.com/docs/auth
- Firestore: https://firebase.google.com/docs/firestore
- Python SDK: https://firebase.google.com/docs/admin/setup
