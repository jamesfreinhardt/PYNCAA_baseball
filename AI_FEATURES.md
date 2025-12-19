# AI Features - NCAA Baseball School Finder

This document describes the AI-powered features added to the NCAA Baseball School Finder application.

## Overview

The application now includes two major AI-powered features:
1. **AI School Recommendations** - Personalized college recommendations based on your preferences
2. **Email Draft Generator** - Automated email drafting for contacting college coaches

Both features use OpenAI's GPT-4 API to provide intelligent, context-aware assistance.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The requirements.txt now includes the OpenAI Python SDK (`openai>=1.12.0`).

### 2. Configure OpenAI API Key

Add your OpenAI API key to the `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

You can obtain an API key from [OpenAI Platform](https://platform.openai.com/api-keys).

**Important:** Keep your API key secure and never commit it to version control. The `.env` file is already in `.gitignore`.

### 3. Verify Setup

When you run the app, check the console output:
- ✅ If configured: AI features will be available
- ⚠️ If not configured: "Warning: OpenAI API key not configured. AI features will be disabled."

## Features

### AI School Recommendations

**Location:** Main app → "AI Recommendations" tab (magic wand icon)

**What it does:**
- Analyzes your current filter settings (divisions, conferences, regions, etc.)
- Considers your saved schools and preferences
- Uses your user profile data (if logged in) including athletic metrics and academic info
- Generates 5 personalized school recommendations with detailed explanations

**How to use:**
1. Navigate to the "AI Recommendations" tab
2. Apply filters to narrow down your preferences (optional but recommended)
3. Click "Generate Recommendations"
4. Review the AI-generated recommendations, each including:
   - School name and key details
   - Reasons why it's a good fit (2-3 bullet points)
   - Key opportunity or advantage
   - Classification suggestion (Target/Reach/Safety)
   - Action buttons (View Details, Save School)

**Recommendations consider:**
- Athletic fit: Division level, win percentage, roster opportunities
- Academic fit: SAT scores, acceptance rates
- Location: Distance from home, region, locale preferences
- Program characteristics: Conference strength, team history
- Personal preferences: School size, religious affiliation, climate

### Email Draft Generator

**Location:** Saved schools cards → "Draft Email to Coach" button

**What it does:**
- Generates professional, personalized emails to college coaches
- Creates both introduction and follow-up emails
- Adapts tone based on your selection (professional, friendly, enthusiastic)
- Includes specific details about the school and program

**How to use:**
1. Save schools you're interested in to your "Saved List"
2. Click the "Draft Email to Coach" button on any saved school card
3. In the modal:
   - Select email type: Introduction or Follow-up
   - Choose tone: Professional, Friendly, or Enthusiastic
   - Add any additional context (achievements, camps, etc.)
   - Click "Generate Email"
4. Review and edit the generated email
5. Click "Copy to Clipboard" to copy the complete email
6. Paste into your email client and send

**Email includes:**
- Professional greeting and introduction
- Why you're interested in this specific program
- Your relevant achievements and statistics
- Academic credentials
- Clear call-to-action
- Professional closing

**Tips for better emails:**
- Fill out your user profile with athletic metrics and academic info
- Add specific context in the "Additional Information" field
- Review and personalize the generated email before sending
- Mention specific details about the program (coaches, facilities, etc.)

## Technical Details

### Architecture

**Files:**
- `ai_recommendations.py` - Core AI logic (SchoolRecommendationEngine, EmailGenerator classes)
- `ai_components.py` - UI components for AI features
- `assets/ai-features.js` - Client-side clipboard functionality
- `app.py` - Main app with AI callbacks integrated

**Key Classes:**

1. **SchoolRecommendationEngine**
   - `generate_recommendations()` - Main recommendation generation method
   - Uses GPT-4 with structured prompts
   - Returns list of recommendations with school data and reasoning

2. **EmailGenerator**
   - `generate_introduction_email()` - Creates introduction emails
   - `generate_followup_email()` - Creates follow-up emails
   - Uses GPT-4 with email-specific prompts
   - Returns structured email data (subject, body)

### API Usage

**Model:** GPT-4 (gpt-4)
**Temperature:** 0.7 (balanced creativity and consistency)
**Max Tokens:** 
- Recommendations: 2000 tokens
- Emails: 600-800 tokens

**Cost Estimation (as of 2024):**
- Recommendation generation: ~$0.03-0.05 per request
- Email generation: ~$0.01-0.02 per email

### Error Handling

The implementation includes comprehensive error handling:
- Graceful degradation when API key is not configured
- User-friendly error messages in the UI
- Fallback parsing for AI responses
- Console logging for debugging

### Privacy & Security

- API key is stored in environment variables (never in code)
- User data is only sent to OpenAI for processing (not stored)
- No personal information is logged
- Follows OpenAI's data usage policies

## Firebase Integration

When users are logged in, the AI features can access:
- User athletic metrics (exit velo, pitching velo, etc.)
- Academic information (GPA, SAT scores, etc.)
- Saved schools and search history
- Profile preferences

This data is used to generate more personalized recommendations and emails.

## Customization

### Modifying Prompts

The system prompts can be customized in `ai_recommendations.py`:
- `SchoolRecommendationEngine._get_system_prompt()` - Recommendation prompt
- `EmailGenerator._get_email_system_prompt()` - Email generation prompt

### Adding New Features

To add new AI features:
1. Add new methods to `ai_recommendations.py`
2. Create UI components in `ai_components.py`
3. Add callbacks in `app.py`
4. Update this documentation

## Troubleshooting

### "AI features are not available"
- Check that `OPENAI_API_KEY` is set in `.env`
- Verify the API key is valid
- Check console for error messages

### Recommendations not generating
- Ensure you have schools in your filtered results
- Check your filter settings aren't too restrictive
- Verify API key has sufficient credits
- Check console for error messages

### Email not generating
- Ensure you've selected a school
- Fill in user profile data for better results
- Check API key is valid
- Review console for errors

### Copy to clipboard not working
- Check if browser supports clipboard API
- Try using keyboard shortcut (Ctrl+C / Cmd+C)
- Manually select and copy the text

## Future Enhancements

Potential improvements for the AI features:
- [ ] Recommendation history tracking
- [ ] Email template library
- [ ] A/B testing different prompts
- [ ] Integration with actual email clients
- [ ] Multi-language support
- [ ] Voice-to-text for email drafting
- [ ] AI-powered school comparison tool
- [ ] Automated follow-up reminders
- [ ] Success tracking (responses received)

## Support

For issues or questions:
1. Check the console output for error messages
2. Verify your OpenAI API key is configured correctly
3. Review this documentation
4. Check the OpenAI API status page
5. Contact support with error details

## License

These AI features are part of the NCAA Baseball School Finder application and follow the same license terms.
