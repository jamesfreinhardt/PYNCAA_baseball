# NCAA Baseball School Finder - AI Coding Agent Instructions

## Project Overview
NCAA Baseball School Finder is a **Plotly Dash web application** for exploring college baseball programs with interactive filtering across athletic, academic, climate, and geographic dimensions. The app uses **Dash callbacks** for reactive state management and integrates **Firebase for authentication** and user metrics tracking.

**Tech Stack:** Python, Dash, Plotly, Pandas, Firebase, Geopy

## Architecture Essentials

### Core Data Flow
1. **Data Loading** (`app.py` lines 48-73): Six CSV files pre-loaded into memory
   - `input_filtered.csv`: Base NCAA school roster data
   - `climate_data_processed.csv` & `climate_data_monthly_long.csv`: Monthly climate aggregates
   - `combined_ncaa_rosters.csv`: Detailed player roster with positions/heights
   - `team_history_updated.csv`: 10-year win% trends by `prev_team_id`
   - `team_coach_metrics.csv`: Coach-specific metadata

2. **Merged Dataset**: `merged_data` combines school + climate data, filters NaN coordinates, derives fields (`win_pct`, `accept_rate_pct`, `sat_score`)

3. **Filter Architecture**: All UI filters → `update_filter_state` callback (line 1231) → centralized dict → `filter_data_from_state()` (line 1307) → reusable `filter_data()` function (line 1329)
   - Pattern: Callbacks update a `dcc.Store` ("filter-state"), which triggers all dependent outputs
   - Climate filters work on `climate_monthly` long-format data, merging back to school-level

### Component Organization
- **`app.py`**: Main dashboard (2500+ lines) - layout, callbacks, display functions
- **`auth_components.py`**: UI component factories (modals, buttons, badges)
- **`auth_callbacks.py`**: Firebase auth workflow callbacks
- **`firebase_config.py`**: Auth & Firestore integration (`FirebaseAuth`, `UserMetrics` classes)
- **`school_classification.py`**: Academic/athletic fit scoring (`SchoolClassifier` class)

### State Management Pattern
Dash stores act as single source of truth:
- `filter-state`: All active filters (dict)
- `saved-schools`: List of unitid integers
- `current-school-unitid`: For modal context
- `home-location`: Geocoded zip coordinates
- `user-session`: Firebase user data

**Never maintain reactive state in callback globals**—always use `dcc.Store`.

## Key Development Patterns

### Roster Metrics Calculation
Functions like `calculate_team_trajectory()` (line 77), `get_position_depth()` (line 349), `calculate_freshman_retention()` (line 234) require matching by `prev_team_id` (not `unitid`):
- Join school data to `roster_data` or `roster_data_full` on `prev_team_id`
- Year format: "2024-25" → convert to ending year (2025) for sorting
- Handle missing data gracefully; print diagnostic logs

### School Logo Resolution
`get_school_logo_url()` (line 621) builds NCAA API URLs via fuzzy matching:
1. Try `ncaa_name_to_slug` dictionary (from remote API call at startup)
2. Fall back to slug generated from school name
3. Returns SVG URL: `https://ncaa-api.henrygd.me/logo/{slug}.svg`

### Geographic Distance
`calculate_distance()` uses `geopy.distance.geodesic` (line 654). Applied in `filter_data()` only if `home_location` set (line 1346). Always check for NaN coordinates before calling.

### Climate Filtering
Climate data exists in two forms:
- **Aggregated** (`climate_data`): One row per school with annual stats
- **Monthly** (`climate_monthly`): Long format with rows per school-month; used for month-specific filtering

Filter by joining on `unitid` after filtering climate rows (line 1406-1424).

### Modal + Nested Tab Pattern
Detailed metrics modal (line 1095) uses `pattern-matching callbacks` (line 1800+):
```python
Input({'type': 'view-metrics-btn', 'index': dash.ALL}, 'n_clicks')
```
This allows dynamic buttons without explicit ID registration.

## Firebase Integration

### Authentication Flow
- **Client-side**: `pyrebase` (line 29 in firebase_config.py) - sign up/sign in via REST
- **Server-side**: `firebase-admin` (line 33) - secure backend operations (Firestore writes)
- Service account key: Optional, stored as `firebase-service-account.json` (git-ignored)

### Firestore Collections
- `/users/{user_id}`: User profiles, preferences
- `/user_searches/{searchId}`: Search history
- Firestore security rules enforce user-level access; see `FIREBASE_SETUP.md` for rules

### Key Methods
- `FirebaseAuth.sign_in()`, `sign_up()`: Return `{'success', 'user_id', 'email', 'token'}`
- `UserMetrics.save_school()`: Stores school to user's Firestore doc
- `UserMetrics.track_search()`: Logs filter params for analytics

## Filter Dependencies
**Critical:** Filter options update based on search inputs:
- Conference search (line 1207) → filters `CONFERENCE_OPTIONS` dynamically
- Religious affiliation search (line 1219) → filters `RELIGIOUS_OPTIONS`
- **Both use case-insensitive substring matching**

## Common Gotchas

1. **Missing Data Fields**: Not all schools have roster data. Always check `prev_team_id` is not NaN before querying `roster_data`.
2. **Year Parsing**: Team history uses "YYYY-YY" format (e.g., "2024-25"). Convert manually in calculations.
3. **Enrollment Ranges**: Filter expects categorical values (e.g., `['small', 'medium']`) converted to numeric ranges at line 1379+.
4. **SAT Scores**: Zero means "not available"; filter logic (line 1402) preserves rows with SAT=0.
5. **Callback Order**: `update_filter_state` must fire before dependent callbacks. Keep as first callback to compute filter dict.

## Running & Debugging

```bash
python app.py  # Starts Dash server on http://localhost:8050
```

**Debug Mode**: Add `debug=True` to `app = dash.Dash()` (line 35) for hot reload and better error messages.

**Print Diagnostics**: Functions like `calculate_team_trajectory()` include `print()` statements for logging; check terminal when features fail silently.

## Adding Features: Common Tasks

### Add New Filter Type
1. Add UI component to sidebar accordion (lines 800-1100)
2. Add to `@app.callback` inputs for `update_filter_state` (line 1231)
3. Add logic in `filter_data()` function (line 1329+)
4. Update `filter_state` return dict and `filter_data_from_state()` mapping

### Add Roster Metric Card
1. Create calculation function (e.g., `calculate_metric_name()`)
2. Add to `update_roster_metrics()` callback (line 1683)
3. Render in a `dbc.Card` with `.rounded` styling
4. Wire "View Details" button to metrics modal (pattern-matching ID)

### Fix Merged Data Issue
Use `merged_data.copy()` when modifying in callbacks to avoid stale data. Reset filters recomputes from original `merged_data` (line 2155+).

## Conventions

- **Variable Naming**: Use snake_case; `prev_team_id` (not `prevTeamId`)
- **Error Handling**: Wrap metric functions in try-except; return `None` or default dict on failure, print traceback
- **HTML IDs**: Use hyphens for multi-word IDs (`'home-zip'`, `'school-counter'`)
- **Styling**: Bootstrap classes via `dbc` + custom CSS in `assets/custom-style.css`

## Testing Quick Reference

**Manual Testing Workflow:**
1. Change a filter (e.g., division)
2. Verify school counter updates (line 1285)
3. Verify map updates (line 1441)
4. Check console for print diagnostics

**Common Test Cases:**
- Empty filter results → should show "Displaying 0 of X schools"
- No roster data for school → roster metric functions return `None`, display "N/A"
- Invalid zip code → `geocode_zip()` returns `None`, distance filter disables
