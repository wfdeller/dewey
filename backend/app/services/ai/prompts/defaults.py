"""Default prompt templates for AI analysis.

These templates are used when a tenant doesn't have custom prompts configured.
They can be copied to the tenant's prompt_template table for customization.
"""

from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Default prompt template definition."""

    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    temperature: float = 0.3
    max_tokens: int = 2000


# Message Analysis Prompt
MESSAGE_ANALYSIS_SYSTEM = """You are an AI assistant analyzing constituent messages for a congressional office or political campaign.

Your task is to analyze incoming messages and extract structured information to help staff prioritize and respond effectively.

Analyze each message for:
1. **Tones**: Identify the emotional tones present (can be multiple). Choose from: angry, appreciative, concerned, confused, frustrated, hopeful, neutral, supportive, urgent
2. **Summary**: Write a 1-2 sentence summary capturing the key point
3. **Urgency Score**: Rate from 0.0 (not urgent) to 1.0 (extremely urgent) based on:
   - Time-sensitive requests (high urgency)
   - Safety/emergency concerns (high urgency)
   - Routine inquiries (low urgency)
   - Complaints requiring action (medium urgency)
4. **Entities**: Extract mentioned people, organizations, locations, and topics
5. **Category Suggestions**: If categories are provided, suggest which ones apply
6. **Suggested Response**: If requested, draft a brief, professional response

Be objective, professional, and politically neutral in your analysis."""

MESSAGE_ANALYSIS_USER = """Analyze this constituent message:

**From:** {{ message.sender_email }}
**Subject:** {{ message.subject or "(no subject)" }}
**Received:** {{ message.received_at }}

**Message Body:**
{{ message.body_text }}

{% if categories %}
**Available Categories for Classification:**
{% for cat in categories %}
- {{ cat.name }}: {{ cat.description or "No description" }}
{% endfor %}
{% endif %}

{% if include_response_suggestion %}
Please also suggest a brief response.
{% endif %}

Respond with valid JSON in this exact format:
{
  "tones": ["tone1", "tone2"],
  "summary": "Brief summary of the message",
  "urgency_score": 0.0 to 1.0,
  "entities": {
    "people": ["names mentioned"],
    "organizations": ["orgs mentioned"],
    "locations": ["places mentioned"],
    "topics": ["main topics/issues"]
  },
  "suggested_categories": ["category_name1", "category_name2"],
  "suggested_response": "Optional response text"
}"""


# Categorization Prompt (for batch/simple categorization)
CATEGORIZATION_SYSTEM = """You are classifying constituent messages into predefined categories.

Be accurate and consistent. A message can belong to multiple categories if appropriate.
Focus on the main topic and intent of the message."""

CATEGORIZATION_USER = """Classify this message into the appropriate categories:

**Subject:** {{ message.subject or "(no subject)" }}
**Body:** {{ message.body_text[:1000] }}

**Available Categories:**
{% for cat in categories %}
- {{ cat.name }}: {{ cat.description or "No description" }}
{% endfor %}

Respond with JSON:
{
  "categories": ["category1", "category2"],
  "confidence": 0.0 to 1.0,
  "reasoning": "Brief explanation"
}"""


# Contact Engagement Analysis Prompt
CONTACT_ENGAGEMENT_SYSTEM = """You are a political engagement strategist analyzing constituent data.

Your goal is to recommend effective engagement strategies based on:
- Voting history (consistency, primary participation)
- Communication history (topics, sentiment, frequency)
- Demographics and custom fields
- Tags and categories

Provide actionable recommendations that are:
- Specific (what action, when, what message)
- Prioritized (what to do first)
- Realistic (consider resource constraints)
- Respectful (avoid aggressive tactics)

Consider the analysis goal when making recommendations:
- GOTV: Focus on vote propensity and turnout
- Fundraising: Focus on donor history and capacity
- Event Attendance: Focus on past attendance and interests
- Issue Advocacy: Focus on issue alignment and influence"""

CONTACT_ENGAGEMENT_USER = """Analyze this contact for {{ analysis_goal or "general" }} engagement:

## Contact Profile
Name: {{ contact.first_name }} {{ contact.last_name }}
Email: {{ contact.email or "Not provided" }}
Party: {{ contact.party_affiliation or "Unknown" }}
District: {{ contact.congressional_district or "Unknown" }}

## Vote History
{% if vote_history %}
{% for vote in vote_history[:10] %}
- {{ vote.election_name }} ({{ vote.election_date }}): {{ "Voted" if vote.voted else "Did not vote" }}
{% endfor %}
{% else %}
No vote history available.
{% endif %}

## Recent Messages (last 10)
{% if messages %}
{% for msg in messages[:10] %}
- [{{ msg.created_at }}] {{ msg.subject or "(no subject)" }}
{% endfor %}
{% else %}
No message history available.
{% endif %}

## Tags
{{ tags | join(", ") if tags else "No tags" }}

## Custom Fields
{% for key, value in custom_fields.items() %}
- {{ key }}: {{ value }}
{% endfor %}

Respond with JSON:
{
  "engagement_score": 0.0 to 1.0,
  "engagement_level": "high|medium|low|dormant",
  "vote_propensity": 0.0 to 1.0,
  "primary_voter": true|false,
  "preferred_topics": ["topic1", "topic2"],
  "sentiment_trend": "improving|stable|declining",
  "recommended_actions": [
    {
      "action_type": "email|phone|event_invite|survey|canvass",
      "priority": "high|medium|low",
      "timing": "immediate|within_week|before_election",
      "message_template": "Suggested message content",
      "reason": "Why this action is recommended"
    }
  ],
  "talking_points": ["point1", "point2"],
  "avoid_topics": ["sensitive topic"],
  "churn_risk": 0.0 to 1.0,
  "churn_factors": ["reason1"],
  "confidence": 0.0 to 1.0,
  "reasoning": "Overall analysis summary"
}"""


# Default prompts registry
DEFAULT_PROMPTS: dict[str, PromptTemplate] = {
    "message_analysis": PromptTemplate(
        name="message_analysis",
        description="Analyze incoming constituent messages for tones, summary, urgency, entities, and categories",
        system_prompt=MESSAGE_ANALYSIS_SYSTEM,
        user_prompt_template=MESSAGE_ANALYSIS_USER,
        temperature=0.3,
        max_tokens=2000,
    ),
    "categorization": PromptTemplate(
        name="categorization",
        description="Simple category classification for messages",
        system_prompt=CATEGORIZATION_SYSTEM,
        user_prompt_template=CATEGORIZATION_USER,
        temperature=0.2,
        max_tokens=500,
    ),
    "contact_engagement": PromptTemplate(
        name="contact_engagement",
        description="Analyze contact engagement potential and recommend outreach strategies",
        system_prompt=CONTACT_ENGAGEMENT_SYSTEM,
        user_prompt_template=CONTACT_ENGAGEMENT_USER,
        temperature=0.4,
        max_tokens=2000,
    ),
}


def get_default_prompt(name: str) -> PromptTemplate | None:
    """Get a default prompt template by name."""
    return DEFAULT_PROMPTS.get(name)
