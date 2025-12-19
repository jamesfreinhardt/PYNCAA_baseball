# Player Profile & Recruiting Tools - Implementation Plan

## Overview
Extend the NCAA Baseball app with comprehensive player profiles, athletic metrics, academic tracking, and recruiting workflow tools.

---

## Phase 1: Enhanced User Profile Data Model

### 1.1 Player Profile
**Location**: Add to `firebase_config.py` → `UserMetrics` class

```python
player_profile = {
    "height_inches": 72,  # 6'0"
    "weight_lbs": 185,
    "positions": ["SS", "2B", "OF"],  # Primary, secondary, tertiary
    "primary_position": "SS",
    "bats": "R",  # R, L, or S (switch)
    "throws": "R",  # R or L
    "grad_year": 2026,
    "high_school": "Frederick High",
    "city_state": "Frederick, MD"
}
```

**New Functions Needed**:
- `update_player_profile(user_id, profile_data)`
- `get_player_profile(user_id)`

---

### 1.2 Athletic Metrics
**Location**: Add to `firebase_config.py` → `UserMetrics` class

```python
athletic_metrics = {
    # Hitting metrics
    "exit_velocity": 92,  # mph
    "bat_speed": 75,  # mph
    
    # Speed/Running
    "sixty_yard_dash": 6.8,  # seconds
    "home_to_first": 4.2,  # seconds
    
    # Pitching (if applicable)
    "fastball_velo": 88,  # mph

    
    # Additional stats
    "pop_time": 1.95,  # catcher - seconds
    "infield_velo": 85,  # mph
    "outfield_velo": 88,  # mph
    

    
    # Last updated
    "metrics_updated": "2024-12-16"
}
```

**New Functions Needed**:
- `update_athletic_metrics(user_id, metrics_data)`
- `get_athletic_metrics(user_id)`
- `calculate_metric_percentiles(user_id)` - Compare to NCAA averages

---

### 1.3 Academic Information
**Location**: Add to `firebase_config.py` → `UserMetrics` class

```python
academic_info = {
    "gpa_unweighted": 3.75,
    "gpa_weighted": 4.2,
    "gpa_scale": 4.0,  # or 5.0
    
    "sat_total": 1320,
    "sat_math": 680,
    "sat_reading": 640,
    
    "act_composite": 28,
    "act_math": 29,
    "act_english": 27,
    "act_reading": 28,
    "act_science": 28,
    

    
    # NCAA Eligibility
    "ncaa_eligible": True,
    "core_courses_completed": 16,
    "core_gpa": 3.5,
    
    # Advanced courses
    "ap_courses": 6,
    "honors_courses": 8,
    
    "academic_updated": "2024-12-16"
}
```

**New Functions Needed**:
- `update_academic_info(user_id, academic_data)`
- `get_academic_info(user_id)`
- `calculate_ncaa_eligibility(user_id)` - Check NCAA D1/D2/D3 requirements
- `match_academic_fit(user_id, school_data)` - Compare to school requirements

---

### 1.4 User Preferences & Constraints
**Location**: Extend existing `preferences` in user profile

```python
user_preferences = {
    # Division preferences
    "preferred_divisions": [1, 2],  # Order of preference

    
    # Location constraints
    "max_distance_miles": 500,
    "preferred_regions": ["South", "Southeast"],
    "avoid_regions": [],
    
    # Financial constraints
    "max_tuition": 50000,
    "need_financial_aid": True,
    "need_athletic_scholarship": True,
    "min_scholarship_pct": 25,  # Minimum % scholarship needed
    
    # School preferences
    "preferred_conferences": ["ACC", "SEC"],
    "school_size_min": 5000,
    "school_size_max": 20000,
    "preferred_setting": ["Suburban", "City"],  # City, Suburban, Rural
    "public_private": "Either",  # Public, Private, Either
    
    # Academic preferences
    "min_academic_ranking": 100,  # US News ranking
    "preferred_majors": ["Business", "Engineering"],
    
    # Program preferences
    "min_win_percentage": 40,
    "prefer_competitive_programs": True,
    "roster_spot_importance": "High",  # Playing time vs winning program
    
    # Fit preferences
    "coaching_style_preference": "Player development",
    "team_culture_importance": "High"
}
```

**New Functions Needed**:
- `update_user_preferences(user_id, preferences)`
- `get_user_preferences(user_id)`
- `filter_schools_by_preferences(user_id)` - Auto-filter based on preferences

---

## Phase 2: School Categorization System

### 2.1 Target/Reach/Safety Classification
**Location**: New file `school_classification.py`

```python
def classify_school(user_profile, athletic_metrics, academic_info, school_data):
    """
    Classify a school as Target, Reach, or Safety based on:
    - Athletic fit (stats vs team averages)
    - Academic fit (GPA/SAT vs school averages)
    - Roster needs (positions, grad year)
    - Admission competitiveness
    """
    
    scores = {
        'athletic_fit': calculate_athletic_fit(),
        'academic_fit': calculate_academic_fit(),
        'roster_fit': calculate_roster_need(),
        'admission_competitiveness': get_admission_difficulty()
    }
    
    # Weighted classification algorithm
    if overall_score > 75:
        return "Safety"
    elif overall_score > 50:
        return "Target"
    else:
        return "Reach"
```

**Classification Factors**:

**Athletic Fit**:
- Player's exit velo vs team average
- 60-yard dash vs position requirements
- Stats (BA, ERA) vs team stats
- Position depth chart analysis

**Academic Fit**:
- GPA vs school's 25th-75th percentile
- SAT/ACT vs school requirements
- NCAA eligibility status

**Roster Fit**:
- Graduating seniors at position
- Current roster depth at position
- Recruiting class size/needs

**Admission Difficulty**:
- Acceptance rate
- Athletic recruitment advantage
- Academic strength of applicant

---

### 2.2 UI Components for Classification
**Location**: Add to `auth_components.py`

```python
def create_school_classification_buttons():
    """Buttons to mark schools as Target/Reach/Safety"""
    return dbc.ButtonGroup([
        dbc.Button("🎯 Target", id="mark-target", color="primary", outline=True),
        dbc.Button("🚀 Reach", id="mark-reach", color="warning", outline=True),
        dbc.Button("✅ Safety", id="mark-safety", color="success", outline=True)
    ])

def create_classification_badge(classification):
    """Display school classification badge"""
    colors = {
        "Target": "primary",
        "Reach": "warning", 
        "Safety": "success"
    }
    icons = {
        "Target": "🎯",
        "Reach": "🚀",
        "Safety": "✅"
    }
    return dbc.Badge(
        f"{icons[classification]} {classification}",
        color=colors[classification],
        className="ms-2"
    )
```

**Add to School Metrics Modal**:
- Classification buttons below school name
- Auto-suggest classification based on algorithm
- User can override and manually classify
- Save classification to Firestore

---

### 2.3 Firestore Data Structure
**Collection**: `user_school_classifications`

```json
{
  "user_id_school_id": {
    "user_id": "abc123",
    "school_name": "Stanford University",
    "unitid": 12345,
    "classification": "Reach",
    "auto_suggested": "Reach",
    "manually_set": false,
    "classification_scores": {
      "athletic_fit": 65,
      "academic_fit": 45,
      "roster_fit": 70,
      "overall": 58
    },
    "notes": "Great engineering program, top team",
    "contact_info": {
      "coach_name": "David Esquer",
      "email": "desquer@stanford.edu",
      "last_contact": "2024-11-15"
    },
    "classified_date": "2024-12-16",
    "interest_level": "High"
  }
}
```

---

## Phase 3: Recruiting Checklist Page

### 3.1 New Tab in Main Content
**Location**: Add to `app.py` layout

```python
dbc.Tab([
    html.Div(id='recruiting-checklist-content')
], label='📋 Recruiting Checklist')
```

### 3.2 Checklist Structure
**Location**: New file `recruiting_checklist.py`

```python
RECRUITING_CHECKLIST = {
    "freshman_year": {
        "title": "Freshman Year (9th Grade)",
        "tasks": [
            {
                "id": "register_ncaa",
                "task": "Register with NCAA Eligibility Center",
                "description": "Create account at eligibilitycenter.org",
                "priority": "High",
                "deadline": "Before sophomore year",
                "resources": ["https://web3.ncaa.org/ecwr3/"]
            },
            {
                "id": "build_profile",
                "task": "Complete Athletic Profile",
                "description": "Enter height, weight, positions, stats",
                "priority": "High"
            },
            {
                "id": "plan_courses",
                "task": "Plan NCAA Core Courses",
                "description": "Work with counselor on 16 core courses",
                "priority": "High"
            },
            {
                "id": "start_highlights",
                "task": "Start Building Highlight Video",
                "description": "Collect game footage for future recruiting video",
                "priority": "Medium"
            }
        ]
    },
    
    "sophomore_year": {
        "title": "Sophomore Year (10th Grade)",
        "tasks": [
            {
                "id": "take_psat",
                "task": "Take PSAT",
                "description": "Practice for SAT/ACT",
                "priority": "High",
                "deadline": "October"
            },
            {
                "id": "create_target_list",
                "task": "Create Initial Target School List",
                "description": "Research 20-30 schools",
                "priority": "High"
            },
            {
                "id": "attend_camps",
                "task": "Attend Summer Showcases/Camps",
                "description": "Get exposure to college coaches",
                "priority": "High",
                "deadline": "Summer"
            },
            {
                "id": "update_metrics",
                "task": "Record Athletic Metrics",
                "description": "60-yard, exit velo, pitching velo",
                "priority": "Medium"
            }
        ]
    },
    
    "junior_year": {
        "title": "Junior Year (11th Grade) - CRITICAL YEAR",
        "tasks": [
            {
                "id": "take_sat_act",
                "task": "Take SAT/ACT",
                "description": "Take tests multiple times to maximize score",
                "priority": "Critical",
                "deadline": "Spring semester"
            },
            {
                "id": "contact_coaches",
                "task": "Begin Contacting Coaches",
                "description": "Email coaches at target schools",
                "priority": "Critical",
                "deadline": "September 1st (D1/D2)"
            },
            {
                "id": "create_highlight_video",
                "task": "Create Recruiting Highlight Video",
                "description": "3-5 minute video showcasing skills",
                "priority": "Critical",
                "deadline": "Fall"
            },
            {
                "id": "attend_showcases",
                "task": "Attend Major Showcases",
                "description": "PG, PBR, or regional showcases",
                "priority": "Critical",
                "deadline": "Summer"
            },
            {
                "id": "unofficial_visits",
                "task": "Schedule Unofficial Visits",
                "description": "Visit top 10-15 schools",
                "priority": "High"
            },
            {
                "id": "refine_school_list",
                "task": "Narrow School List to 15-20",
                "description": "Classify as Target/Reach/Safety",
                "priority": "High"
            }
        ]
    },
    
    "senior_year_fall": {
        "title": "Senior Year Fall (12th Grade)",
        "tasks": [
            {
                "id": "official_visits",
                "task": "Schedule Official Visits",
                "description": "5 official visits allowed (D1/D2)",
                "priority": "Critical",
                "deadline": "September-November"
            },
            {
                "id": "finalize_list",
                "task": "Finalize School List",
                "description": "5-10 realistic options",
                "priority": "Critical"
            },
            {
                "id": "submit_applications",
                "task": "Submit College Applications",
                "description": "Early Action/Decision if committed",
                "priority": "Critical",
                "deadline": "November 1st (Early) / Jan 1st (Regular)"
            },
            {
                "id": "verify_transcripts",
                "task": "Send Final Transcripts to NCAA",
                "description": "Verify eligibility status",
                "priority": "Critical"
            },
            {
                "id": "nli_signing",
                "task": "National Letter of Intent",
                "description": "Sign NLI if committing (D1/D2)",
                "priority": "Critical",
                "deadline": "Early Signing: November"
            }
        ]
    },
    
    "senior_year_spring": {
        "title": "Senior Year Spring",
        "tasks": [
            {
                "id": "final_decision",
                "task": "Make Final College Decision",
                "description": "Commit to school by May 1st",
                "priority": "Critical",
                "deadline": "May 1st"
            },
            {
                "id": "housing_registration",
                "task": "Complete Housing Registration",
                "description": "Submit housing preferences",
                "priority": "High"
            },
            {
                "id": "summer_preparation",
                "task": "Summer Training Plan",
                "description": "Get workout plan from college coaches",
                "priority": "High"
            }
        ]
    }
}
```

### 3.3 Checklist UI Components
**Location**: New file `recruiting_checklist_components.py`

```python
def create_checklist_item(task, completed=False, user_notes=""):
    """Create a checklist item with checkbox and details"""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Checkbox(
                        id={"type": "checklist-item", "index": task["id"]},
                        checked=completed,
                        className="task-checkbox"
                    )
                ], width=1),
                dbc.Col([
                    html.H6(task["task"], className="mb-1"),
                    html.P(task["description"], className="text-muted small mb-2"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Badge(
                                task.get("priority", "Medium"),
                                color="danger" if task.get("priority") == "Critical" else "warning"
                            )
                        ], width="auto"),
                        dbc.Col([
                            html.Small(f"⏰ {task.get('deadline', 'No deadline')}")
                        ], width="auto") if task.get('deadline') else None
                    ]),
                    # User notes section
                    dbc.Collapse([
                        dbc.Textarea(
                            id={"type": "task-notes", "index": task["id"]},
                            value=user_notes,
                            placeholder="Add notes...",
                            size="sm",
                            className="mt-2"
                        )
                    ], id={"type": "notes-collapse", "index": task["id"]}, is_open=False),
                    # Resources if available
                    html.Div([
                        html.Small("📚 Resources: "),
                        html.Ul([
                            html.Li(html.A(url, href=url, target="_blank"))
                            for url in task.get("resources", [])
                        ], className="small")
                    ]) if task.get("resources") else None
                ], width=11)
            ])
        ])
    ], className="mb-2")

def create_year_section(year_key, year_data, user_progress):
    """Create a section for each year's tasks"""
    tasks = year_data["tasks"]
    completed_tasks = sum(1 for t in tasks if user_progress.get(t["id"], False))
    progress = (completed_tasks / len(tasks)) * 100 if tasks else 0
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5(year_data["title"], className="mb-0"),
            dbc.Progress(
                value=progress,
                label=f"{completed_tasks}/{len(tasks)} completed",
                className="mt-2"
            )
        ]),
        dbc.CardBody([
            html.Div([
                create_checklist_item(
                    task,
                    completed=user_progress.get(task["id"], False),
                    user_notes=user_progress.get(f"{task['id']}_notes", "")
                )
                for task in tasks
            ])
        ])
    ], className="mb-4")
```

### 3.4 Firestore Data Structure
**Collection**: `user_recruiting_progress`

```json
{
  "user_id": {
    "current_grade": 11,
    "grad_year": 2026,
    "tasks": {
      "register_ncaa": {
        "completed": true,
        "completed_date": "2023-09-15",
        "notes": "Account created, ID: ABC123456"
      },
      "take_sat_act": {
        "completed": true,
        "completed_date": "2024-05-10",
        "notes": "SAT: 1320 (plan to retake in Aug)",
        "reminder_date": "2024-08-01"
      },
      "contact_coaches": {
        "completed": false,
        "notes": "Draft emails ready, sending Sept 1st",
        "reminder_date": "2024-09-01"
      }
    },
    "overall_progress": 35,  // percentage
    "last_updated": "2024-12-16"
  }
}
```

---

## Phase 4: Profile & Preferences UI

### 4.1 New "My Profile" Page
**Location**: Add modal or new tab

Components needed:
1. **Player Profile Form**
   - Height/Weight input
   - Position selection (multi-select)
   - Bats/Throws dropdowns
   - Grad year
   - High school info

2. **Athletic Metrics Form**
   - Exit velocity, 60-yard dash inputs
   - Pitching velocities (if applicable)
   - Season stats
   - Last updated date

3. **Academic Info Form**
   - GPA inputs (weighted/unweighted)
   - SAT/ACT scores
   - Class rank
   - AP/Honors courses

4. **Preferences Form**
   - Division preferences
   - Distance/Region filters
   - Financial constraints
   - School preferences

### 4.2 Profile Completion Progress
Show progress bar:
- Profile: 25%
- Athletic Metrics: 25%
- Academic Info: 25%
- Preferences: 25%

Encourage users to complete their profile for better school matching.

---

## Phase 5: Advanced Matching Algorithm

### 5.1 School Fit Score
**Location**: New file `school_matching.py`

```python
def calculate_fit_score(user_id, school_unitid):
    """
    Calculate comprehensive fit score (0-100) based on:
    - Athletic fit (40%)
    - Academic fit (30%)
    - Preferences match (20%)
    - Roster needs (10%)
    """
    
    user_data = get_complete_user_profile(user_id)
    school_data = get_school_data(school_unitid)
    
    scores = {
        'athletic': calculate_athletic_fit_score(user_data, school_data),
        'academic': calculate_academic_fit_score(user_data, school_data),
        'preferences': calculate_preferences_match(user_data, school_data),
        'roster': calculate_roster_need_score(user_data, school_data)
    }
    
    weighted_score = (
        scores['athletic'] * 0.40 +
        scores['academic'] * 0.30 +
        scores['preferences'] * 0.20 +
        scores['roster'] * 0.10
    )
    
    return {
        'overall_score': weighted_score,
        'breakdown': scores,
        'recommendation': get_recommendation(weighted_score)
    }
```

---

## Implementation Timeline

### Week 1: Data Model & Backend
- [ ] Update `firebase_config.py` with new data structures
- [ ] Create `school_classification.py`
- [ ] Create `recruiting_checklist.py`
- [ ] Add Firestore collections

### Week 2: UI Components
- [ ] Create profile forms in `auth_components.py`
- [ ] Create classification buttons
- [ ] Create checklist UI components
- [ ] Add "My Profile" modal

### Week 3: Callbacks & Logic
- [ ] Profile update callbacks
- [ ] Classification callbacks
- [ ] Checklist progress tracking
- [ ] Fit score calculation

### Week 4: Integration & Testing
- [ ] Add profile/checklist tabs to main app
- [ ] Integrate classification into school metrics
- [ ] Test all features
- [ ] User testing & refinement

---

## File Structure
```
PYNCAABaseball/
├── firebase_config.py (UPDATED - add profile methods)
├── auth_components.py (UPDATED - add profile forms)
├── auth_callbacks.py (UPDATED - add profile callbacks)
├── school_classification.py (NEW)
├── recruiting_checklist.py (NEW)
├── recruiting_checklist_components.py (NEW)
├── school_matching.py (NEW)
└── app.py (UPDATED - add new tabs/features)
```

---

## Next Steps

1. **Review this plan** - Any changes or additions?
2. **Prioritize features** - Which to build first?
3. **Start implementation** - Begin with Phase 1?

Ready to proceed when you are! 🚀
