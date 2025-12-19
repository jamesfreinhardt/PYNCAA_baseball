"""
AI-Powered School Recommendation Engine
Uses OpenAI GPT-4 to provide personalized college recommendations
"""

import os
import json
from typing import Dict, List, Optional
import pandas as pd
from openai import OpenAI


class SchoolRecommendationEngine:
    """Generate AI-powered school recommendations based on user preferences and filters"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key) if api_key else None
        
    def is_available(self) -> bool:
        """Check if OpenAI API is configured"""
        return self.client is not None
    
    def generate_recommendations(
        self,
        filtered_schools: pd.DataFrame,
        filter_state: Dict,
        saved_schools: List[int],
        user_profile: Optional[Dict] = None,
        num_recommendations: int = 5
    ) -> Dict:
        """
        Generate personalized school recommendations
        
        Args:
            filtered_schools: DataFrame of schools matching current filters
            filter_state: Current filter settings (divisions, conferences, etc.)
            saved_schools: List of unitids user has already saved
            user_profile: Optional user profile data (athletic metrics, academic info)
            num_recommendations: Number of schools to recommend
            
        Returns:
            Dict with 'success', 'recommendations' list, and optional 'error'
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'OpenAI API key not configured'
            }
        
        try:
            # Prepare context for AI
            context = self._prepare_context(
                filtered_schools, filter_state, saved_schools, user_profile
            )
            
            # Generate recommendations using GPT-4
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": json.dumps(context, default=str)
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse recommendations
            recommendations = self._parse_recommendations(
                response.choices[0].message.content,
                filtered_schools
            )
            
            return {
                'success': True,
                'recommendations': recommendations[:num_recommendations]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate recommendations: {str(e)}"
            }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the AI recommendation engine"""
        return """You are an expert college baseball recruiting advisor helping high school players find the best college fit.

Your task is to analyze the provided data and recommend schools that would be the best fit for the student-athlete.

Consider:
1. Athletic fit: Division level, team win percentage, roster depth, playing time opportunities
2. Academic fit: SAT scores, acceptance rates, academic rigor
3. Location preferences: Distance from home, region, locale (urban/suburban/rural)
4. Program characteristics: Conference strength, team history, coaching stability
5. Personal preferences: School size, religious affiliation, climate

For each recommendation, provide:
1. School name
2. Key reasons why it's a good fit (2-3 bullet points)
3. One specific opportunity or advantage at this school
4. Classification suggestion (Target/Reach/Safety)

Return your response as a JSON array with this structure:
[
  {
    "school_name": "School Name",
    "unitid": "school_unitid",
    "reasons": ["Reason 1", "Reason 2", "Reason 3"],
    "opportunity": "Specific opportunity or advantage",
    "classification": "Target|Reach|Safety"
  }
]

Focus on schools that genuinely match the student's profile and preferences. Be realistic about fit."""
    
    def _prepare_context(
        self,
        filtered_schools: pd.DataFrame,
        filter_state: Dict,
        saved_schools: List[int],
        user_profile: Optional[Dict]
    ) -> Dict:
        """Prepare context data for AI model"""
        
        # Get top schools from filtered results
        top_schools = filtered_schools.head(20).to_dict('records')
        
        # Simplify school data for AI
        simplified_schools = []
        for school in top_schools:
            simplified_schools.append({
                'name': school.get('instnm', 'Unknown'),
                'unitid': school.get('unitid'),
                'division': school.get('division'),
                'conference': school.get('Conference_Name'),
                'win_pct': school.get('win_pct', 0),
                'sat_avg': school.get('sat_avg', 0),
                'accept_rate_pct': school.get('accept_rate_pct', 100),
                'enrollment': school.get('ugds', 0),
                'state': school.get('state', ''),
                'locale': school.get('locale'),
                'control': school.get('control'),
                'latitude': school.get('latitude'),
                'longitude': school.get('longitude')
            })
        
        # Extract user preferences from filter state
        preferences = {
            'divisions': filter_state.get('divisions', []),
            'conferences': filter_state.get('conferences', []),
            'regions': filter_state.get('regions', []),
            'enrollment_prefs': filter_state.get('enrollment', []),
            'sat_range': filter_state.get('sat_range', [800, 1600]),
            'accept_rate_range': filter_state.get('accept_rate', [0, 100]),
            'distance_from_home': filter_state.get('distance', 2500)
        }
        
        # Add user profile if available
        context = {
            'available_schools': simplified_schools,
            'user_preferences': preferences,
            'saved_schools_count': len(saved_schools) if saved_schools else 0
        }
        
        if user_profile:
            context['user_profile'] = {
                'athletic_metrics': user_profile.get('athletic_metrics', {}),
                'academic_info': user_profile.get('academic_info', {})
            }
        
        return context
    
    def _parse_recommendations(
        self,
        ai_response: str,
        filtered_schools: pd.DataFrame
    ) -> List[Dict]:
        """Parse AI response and match with actual school data"""
        try:
            # Try to extract JSON from response
            if '```json' in ai_response:
                json_start = ai_response.find('```json') + 7
                json_end = ai_response.find('```', json_start)
                ai_response = ai_response[json_start:json_end].strip()
            elif '```' in ai_response:
                json_start = ai_response.find('```') + 3
                json_end = ai_response.find('```', json_start)
                ai_response = ai_response[json_start:json_end].strip()
            
            recommendations = json.loads(ai_response)
            
            # Enhance recommendations with full school data
            enhanced_recommendations = []
            for rec in recommendations:
                school_name = rec.get('school_name', '')
                unitid = rec.get('unitid')
                
                # Try to find matching school
                if unitid:
                    school_data = filtered_schools[filtered_schools['unitid'] == unitid]
                else:
                    school_data = filtered_schools[
                        filtered_schools['instnm'].str.contains(school_name, case=False, na=False)
                    ]
                
                if not school_data.empty:
                    school = school_data.iloc[0].to_dict()
                    enhanced_recommendations.append({
                        **rec,
                        'school_data': {
                            'unitid': school.get('unitid'),
                            'name': school.get('instnm'),
                            'division': school.get('division'),
                            'conference': school.get('Conference_Name'),
                            'win_pct': school.get('win_pct'),
                            'sat_avg': school.get('sat_avg'),
                            'accept_rate_pct': school.get('accept_rate_pct'),
                            'state': school.get('state'),
                            'city': school.get('city')
                        }
                    })
            
            return enhanced_recommendations
            
        except json.JSONDecodeError as e:
            # Fallback: return empty list if parsing fails
            print(f"Failed to parse AI recommendations: {e}")
            return []


class EmailGenerator:
    """Generate AI-powered emails to college coaches"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key) if api_key else None
    
    def is_available(self) -> bool:
        """Check if OpenAI API is configured"""
        return self.client is not None
    
    def generate_introduction_email(
        self,
        school_data: Dict,
        user_profile: Dict,
        tone: str = "professional",
        additional_info: str = ""
    ) -> Dict:
        """
        Generate introduction email to a college coach
        
        Args:
            school_data: School information (name, division, conference, etc.)
            user_profile: Student-athlete profile (name, position, grad year, metrics)
            tone: Email tone ("professional", "friendly", "enthusiastic")
            additional_info: Any additional context or notes to include
            
        Returns:
            Dict with 'success', 'email' dict (subject, body), and optional 'error'
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'OpenAI API key not configured'
            }
        
        try:
            prompt = self._build_email_prompt(
                school_data, user_profile, tone, additional_info, email_type="introduction"
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_email_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            email_content = self._parse_email(response.choices[0].message.content)
            
            return {
                'success': True,
                'email': email_content
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate email: {str(e)}"
            }
    
    def generate_followup_email(
        self,
        school_data: Dict,
        user_profile: Dict,
        previous_contact: Optional[str] = None,
        tone: str = "professional"
    ) -> Dict:
        """
        Generate follow-up email to a college coach
        
        Args:
            school_data: School information
            user_profile: Student-athlete profile
            previous_contact: Optional context about previous communication
            tone: Email tone
            
        Returns:
            Dict with 'success', 'email' dict (subject, body), and optional 'error'
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'OpenAI API key not configured'
            }
        
        try:
            prompt = self._build_email_prompt(
                school_data, user_profile, tone, previous_contact or "", email_type="followup"
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_email_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=600
            )
            
            email_content = self._parse_email(response.choices[0].message.content)
            
            return {
                'success': True,
                'email': email_content
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate email: {str(e)}"
            }
    
    def _get_email_system_prompt(self) -> str:
        """Get system prompt for email generation"""
        return """You are an expert at crafting recruiting emails for high school baseball players contacting college coaches.

Your emails should:
1. Be concise (250-350 words for introduction, 150-200 for follow-up)
2. Highlight the student's relevant achievements and interests
3. Show genuine interest in the specific program
4. Include a clear call-to-action
5. Be professionally formatted
6. Avoid clichés and generic statements
7. Be personalized to the specific school and program

Return emails in this JSON format:
{
  "subject": "Email subject line",
  "body": "Email body with proper paragraphs separated by \\n\\n"
}

The body should include:
- Greeting
- Brief introduction
- Why interested in this specific program
- Relevant achievements/stats
- Academic credentials
- Call to action (requesting meeting, camp info, etc.)
- Professional closing"""
    
    def _build_email_prompt(
        self,
        school_data: Dict,
        user_profile: Dict,
        tone: str,
        additional_info: str,
        email_type: str
    ) -> str:
        """Build prompt for email generation"""
        
        school_name = school_data.get('name', school_data.get('instnm', 'the university'))
        conference = school_data.get('conference', school_data.get('Conference_Name', ''))
        division = school_data.get('division', '')
        
        student_name = user_profile.get('name', 'Student')
        grad_year = user_profile.get('graduation_year', '')
        position = user_profile.get('position', 'baseball player')
        high_school = user_profile.get('high_school', '')
        
        # Get athletic metrics if available
        athletic_metrics = user_profile.get('athletic_metrics', {})
        academic_info = user_profile.get('academic_info', {})
        
        if email_type == "introduction":
            prompt = f"""Generate a {tone} introduction email from a high school baseball player to the coach at {school_name}.

Student Information:
- Name: {student_name}
- Graduation Year: {grad_year}
- Position: {position}
- High School: {high_school}
"""
        else:  # followup
            prompt = f"""Generate a {tone} follow-up email from a high school baseball player to the coach at {school_name}.

Student Information:
- Name: {student_name}
- Graduation Year: {grad_year}
- Position: {position}
"""
        
        if athletic_metrics:
            prompt += f"\nAthletic Metrics: {json.dumps(athletic_metrics)}"
        
        if academic_info:
            prompt += f"\nAcademic Information: {json.dumps(academic_info)}"
        
        prompt += f"""

School Information:
- School: {school_name}
- Division: {division}
- Conference: {conference}

"""
        
        if additional_info:
            prompt += f"\nAdditional Context: {additional_info}\n"
        
        prompt += "\nGenerate an email that is personalized, professional, and compelling."
        
        return prompt
    
    def _parse_email(self, ai_response: str) -> Dict:
        """Parse AI response to extract subject and body"""
        try:
            # Try to extract JSON from response
            if '```json' in ai_response:
                json_start = ai_response.find('```json') + 7
                json_end = ai_response.find('```', json_start)
                ai_response = ai_response[json_start:json_end].strip()
            elif '```' in ai_response:
                json_start = ai_response.find('```') + 3
                json_end = ai_response.find('```', json_start)
                ai_response = ai_response[json_start:json_end].strip()
            
            email_data = json.loads(ai_response)
            
            return {
                'subject': email_data.get('subject', 'Introduction - Baseball Recruiting'),
                'body': email_data.get('body', '')
            }
            
        except json.JSONDecodeError:
            # Fallback parsing if JSON fails
            lines = ai_response.split('\n')
            subject = "Introduction - Baseball Recruiting"
            body = ai_response
            
            # Try to find subject line
            for i, line in enumerate(lines):
                if 'subject:' in line.lower():
                    subject = line.split(':', 1)[1].strip()
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            return {
                'subject': subject,
                'body': body
            }
