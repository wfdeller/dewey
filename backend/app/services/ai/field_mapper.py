"""AI-powered field mapping for voter file imports."""

import json
import re
from typing import TypedDict

import anthropic

from app.core.config import get_settings


class FieldMapping(TypedDict):
    """Suggested field mapping with confidence."""

    field: str
    confidence: float
    reason: str


class MatchingStrategyResult(TypedDict):
    """Suggested matching strategy."""

    strategy: str
    reason: str
    confidence: float


# Contact fields that can be mapped
MAPPABLE_CONTACT_FIELDS = [
    # Core identity
    "email",
    "first_name",
    "last_name",
    "middle_name",
    "name",  # Full name
    "prefix",
    "suffix",

    # Contact info
    "phone",
    "mobile_phone",
    "work_phone",
    "secondary_email",

    # Address
    "address_street",
    "address_street2",
    "address_city",
    "address_state",
    "address_zip",
    "address_county",

    # Geographic/political
    "state",
    "zip_code",
    "county",
    "congressional_district",
    "state_legislative_district",
    "precinct",
    "school_district",
    "municipal_district",

    # Voter info
    "state_voter_id",
    "party_affiliation",
    "voter_status",
    "voter_registration_date",
    "modeled_party",

    # Demographics
    "date_of_birth",
    "gender",
    "pronouns",

    # Socioeconomic
    "income_bracket",
    "education_level",
    "homeowner_status",
    "marital_status",

    # Professional
    "occupation",
    "employer",
    "job_title",

    # Communication
    "preferred_language",
    "communication_preference",
]

# Vote history column patterns (election columns)
VOTE_HISTORY_PATTERNS = [
    r"^\d{4}_?(gen|pri|spe|mun|run)",  # 2024_gen, 2024pri
    r"^(g|p|s|m|r)\d{4}",  # g2024, p2024
    r"^(general|primary|special|municipal)\d{4}",  # general2024
    r"^\d{4}_(general|primary|special|municipal)",  # 2024_general
    r"^vote_\d{4}",  # vote_2024
    r"^voted_\d{4}",  # voted_2024
    r"^election_\d{4}",  # election_2024
    r"^\d{2}/\d{2}/\d{4}",  # Date format columns
]


FIELD_MAPPING_PROMPT = """You are analyzing CSV headers from a voter file to map them to a contact database.

Given these CSV headers and sample data, suggest which contact database field each header maps to.

Available contact fields:
{available_fields}

CSV Headers and sample values:
{headers_with_samples}

For each header, respond with a JSON object containing:
- header: the original header name
- field: the best matching contact field, or "vote_history" if it's a voting record column, or null if no match
- confidence: 0.0 to 1.0 indicating how confident you are
- reason: brief explanation of the mapping

Also identify any columns that appear to be vote history columns (election dates/participation).

Respond ONLY with valid JSON in this format:
{{
  "mappings": [
    {{"header": "FirstName", "field": "first_name", "confidence": 0.95, "reason": "Direct match to first name field"}},
    ...
  ],
  "vote_history_columns": ["2024_gen", "2022_pri", ...]
}}
"""

MATCHING_STRATEGY_PROMPT = """You are analyzing a voter file to recommend the best matching strategy.

Based on the available columns and data quality, recommend how to match records to existing contacts.

Available matching strategies:
- voter_id_first: Match by state_voter_id first, fall back to email
- email_first: Match by email first, fall back to state_voter_id
- voter_id_only: Only match by state_voter_id (no fallback)
- email_only: Only match by email (no fallback)

CSV Headers:
{headers}

Sample data (first 5 rows):
{sample_data}

Consider:
1. Does the file have state_voter_id? Is it populated for most rows?
2. Does the file have email? Is it populated for most rows?
3. What's the likely use case (voter file update vs. email list enrichment)?

Respond ONLY with valid JSON:
{{
  "strategy": "voter_id_first",
  "confidence": 0.9,
  "reason": "File has voter IDs for 95% of rows, making it the most reliable match key"
}}
"""


async def analyze_csv_headers(
    headers: list[str],
    sample_rows: list[dict],
) -> dict:
    """
    Use AI to analyze CSV headers and suggest field mappings.

    Args:
        headers: List of column headers from the CSV
        sample_rows: First few rows of data as dicts

    Returns:
        Dict with suggested mappings and vote history columns
    """
    settings = get_settings()

    # Build headers with sample values
    headers_with_samples = []
    for header in headers:
        samples = [str(row.get(header, ""))[:50] for row in sample_rows[:3]]
        samples_str = ", ".join([f'"{s}"' for s in samples if s])
        headers_with_samples.append(f'- {header}: {samples_str or "(empty)"}')

    prompt = FIELD_MAPPING_PROMPT.format(
        available_fields=", ".join(MAPPABLE_CONTACT_FIELDS),
        headers_with_samples="\n".join(headers_with_samples),
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-3-haiku-20240307",  # Fast, cheap model for this task
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the response
        response_text = message.content[0].text
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
            return result

    except Exception as e:
        # Fall back to rule-based matching if AI fails
        return _fallback_field_mapping(headers, sample_rows)

    return _fallback_field_mapping(headers, sample_rows)


async def suggest_matching_strategy(
    headers: list[str],
    sample_rows: list[dict],
) -> MatchingStrategyResult:
    """
    Use AI to suggest the best matching strategy.

    Args:
        headers: List of column headers
        sample_rows: Sample data rows

    Returns:
        Suggested strategy with explanation
    """
    settings = get_settings()

    # Build sample data string
    sample_str = json.dumps(sample_rows[:5], indent=2, default=str)

    prompt = MATCHING_STRATEGY_PROMPT.format(
        headers=", ".join(headers),
        sample_data=sample_str,
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
            return MatchingStrategyResult(
                strategy=result.get("strategy", "email_first"),
                reason=result.get("reason", "Default strategy"),
                confidence=result.get("confidence", 0.5),
            )

    except Exception:
        pass

    # Fallback: determine based on column presence
    return _fallback_matching_strategy(headers, sample_rows)


def _fallback_field_mapping(
    headers: list[str],
    sample_rows: list[dict],
) -> dict:
    """
    Rule-based fallback for field mapping when AI is unavailable.
    """
    mappings = []
    vote_history_columns = []

    # Common header variations
    header_map = {
        # Email variations
        "email": "email",
        "email_address": "email",
        "emailaddress": "email",
        "e-mail": "email",
        "mail": "email",

        # Name variations
        "first_name": "first_name",
        "firstname": "first_name",
        "first": "first_name",
        "fname": "first_name",
        "given_name": "first_name",

        "last_name": "last_name",
        "lastname": "last_name",
        "last": "last_name",
        "lname": "last_name",
        "surname": "last_name",
        "family_name": "last_name",

        "middle_name": "middle_name",
        "middlename": "middle_name",
        "middle": "middle_name",
        "mname": "middle_name",

        "full_name": "name",
        "fullname": "name",
        "name": "name",

        "prefix": "prefix",
        "title": "prefix",
        "salutation": "prefix",

        "suffix": "suffix",
        "name_suffix": "suffix",

        # Phone variations
        "phone": "phone",
        "phone_number": "phone",
        "phonenumber": "phone",
        "telephone": "phone",

        "mobile": "mobile_phone",
        "mobile_phone": "mobile_phone",
        "cell": "mobile_phone",
        "cell_phone": "mobile_phone",
        "cellphone": "mobile_phone",

        # Address variations
        "address": "address_street",
        "street": "address_street",
        "street_address": "address_street",
        "address1": "address_street",
        "address_1": "address_street",

        "address2": "address_street2",
        "address_2": "address_street2",
        "apt": "address_street2",
        "unit": "address_street2",

        "city": "address_city",
        "town": "address_city",

        "state": "state",
        "st": "state",
        "state_code": "state",

        "zip": "zip_code",
        "zip_code": "zip_code",
        "zipcode": "zip_code",
        "postal_code": "zip_code",
        "postal": "zip_code",

        "county": "county",

        # Voter fields
        "voter_id": "state_voter_id",
        "state_voter_id": "state_voter_id",
        "voter_file_id": "state_voter_id",
        "sos_voter_id": "state_voter_id",
        "voter_registration_number": "state_voter_id",

        "party": "party_affiliation",
        "party_affiliation": "party_affiliation",
        "registered_party": "party_affiliation",
        "party_code": "party_affiliation",

        "voter_status": "voter_status",
        "registration_status": "voter_status",

        "precinct": "precinct",
        "precinct_id": "precinct",
        "voting_precinct": "precinct",

        "congressional_district": "congressional_district",
        "cd": "congressional_district",
        "congress_dist": "congressional_district",

        "state_senate": "state_legislative_district",
        "state_house": "state_legislative_district",
        "legislative_district": "state_legislative_district",

        "school_district": "school_district",
        "school_dist": "school_district",

        # Demographics
        "dob": "date_of_birth",
        "date_of_birth": "date_of_birth",
        "birth_date": "date_of_birth",
        "birthdate": "date_of_birth",

        "gender": "gender",
        "sex": "gender",
    }

    for header in headers:
        header_lower = header.lower().strip()

        # Check for vote history patterns
        is_vote_history = False
        for pattern in VOTE_HISTORY_PATTERNS:
            if re.match(pattern, header_lower, re.IGNORECASE):
                is_vote_history = True
                vote_history_columns.append(header)
                break

        if is_vote_history:
            mappings.append({
                "header": header,
                "field": "vote_history",
                "confidence": 0.8,
                "reason": "Matches vote history pattern",
            })
        elif header_lower in header_map:
            mappings.append({
                "header": header,
                "field": header_map[header_lower],
                "confidence": 0.9,
                "reason": "Direct header match",
            })
        else:
            mappings.append({
                "header": header,
                "field": None,
                "confidence": 0.0,
                "reason": "No match found",
            })

    return {
        "mappings": mappings,
        "vote_history_columns": vote_history_columns,
    }


def _fallback_matching_strategy(
    headers: list[str],
    sample_rows: list[dict],
) -> MatchingStrategyResult:
    """
    Rule-based fallback for matching strategy.
    """
    headers_lower = [h.lower() for h in headers]

    has_voter_id = any(
        h in ["voter_id", "state_voter_id", "voter_file_id", "sos_voter_id"]
        for h in headers_lower
    )
    has_email = any(
        h in ["email", "email_address", "emailaddress"]
        for h in headers_lower
    )

    if has_voter_id and has_email:
        # Check which has better data quality
        voter_id_filled = 0
        email_filled = 0

        for row in sample_rows:
            for key, value in row.items():
                if key.lower() in ["voter_id", "state_voter_id"] and value:
                    voter_id_filled += 1
                if key.lower() in ["email", "email_address"] and value:
                    email_filled += 1

        if voter_id_filled >= email_filled:
            return MatchingStrategyResult(
                strategy="voter_id_first",
                reason="Voter ID has better data coverage",
                confidence=0.7,
            )
        else:
            return MatchingStrategyResult(
                strategy="email_first",
                reason="Email has better data coverage",
                confidence=0.7,
            )

    elif has_voter_id:
        return MatchingStrategyResult(
            strategy="voter_id_only",
            reason="Only voter ID available for matching",
            confidence=0.8,
        )

    elif has_email:
        return MatchingStrategyResult(
            strategy="email_only",
            reason="Only email available for matching",
            confidence=0.8,
        )

    else:
        return MatchingStrategyResult(
            strategy="email_first",
            reason="No clear match field, defaulting to email-first",
            confidence=0.3,
        )
