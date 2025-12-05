"""Voter file import service for processing CSV files."""

import csv
import io
import os
import re
import tempfile
from datetime import date, datetime
from typing import BinaryIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.models.contact import Contact
from app.models.vote_history import VoteHistory
from app.models.job import Job
from app.models.user import User
from app.services.job_status import update_job_progress, delete_job_progress
from app.services.ai.field_mapper import (
    analyze_csv_headers,
    suggest_matching_strategy,
)


logger = structlog.get_logger()


# Matching strategies
MATCHING_STRATEGIES = {
    "voter_id_first": "Match by state_voter_id first, fall back to email",
    "email_first": "Match by email first, fall back to state_voter_id",
    "voter_id_only": "Only match by state_voter_id",
    "email_only": "Only match by email",
}


class VoterImportService:
    """Service for handling voter file imports."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def create_job(
        self,
        file: BinaryIO,
        filename: str,
        user: User,
    ) -> Job:
        """
        Create a new import job and save the uploaded file.

        Args:
            file: The uploaded file
            filename: Original filename
            user: The user creating the job

        Returns:
            The created Job
        """
        # Read file content
        content = file.read()
        file_size = len(content)

        # Save to temp file
        temp_dir = tempfile.gettempdir()
        job_dir = os.path.join(temp_dir, "dewey_imports", str(self.tenant_id))
        os.makedirs(job_dir, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
        file_path = os.path.join(job_dir, f"{timestamp}_{safe_filename}")

        with open(file_path, "wb") as f:
            f.write(content)

        # Count rows
        content_str = content.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(content_str))
        rows = list(reader)
        total_rows = len(rows)

        # Create job
        job = Job(
            tenant_id=self.tenant_id,
            job_type="voter_import",
            status="pending",
            original_filename=filename,
            file_path=file_path,
            file_size_bytes=file_size,
            total_rows=total_rows,
            created_by_id=user.id,
        )

        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)

        logger.info(
            "Created voter import job",
            job_id=str(job.id),
            filename=filename,
            total_rows=total_rows,
        )

        return job

    async def analyze_job(self, job_id: UUID) -> dict:
        """
        Analyze a job's file and suggest field mappings.

        Args:
            job_id: The job ID

        Returns:
            Analysis results with suggested mappings
        """
        job = await self._get_job(job_id)

        # Update status
        job.status = "analyzing"
        await self.session.commit()

        try:
            # Read file
            with open(job.file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                sample_rows = []
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    sample_rows.append(row)

            # Get AI suggestions
            mapping_result = await analyze_csv_headers(headers, sample_rows)
            strategy_result = await suggest_matching_strategy(headers, sample_rows)

            # Update job
            job.detected_headers = list(headers)
            job.suggested_mappings = {
                m["header"]: {
                    "field": m["field"],
                    "confidence": m["confidence"],
                    "reason": m.get("reason", ""),
                }
                for m in mapping_result.get("mappings", [])
            }
            job.suggested_matching_strategy = strategy_result["strategy"]
            job.matching_strategy_reason = strategy_result["reason"]
            job.status = "mapping"

            await self.session.commit()
            await self.session.refresh(job)

            return {
                "job_id": str(job.id),
                "headers": headers,
                "suggested_mappings": job.suggested_mappings,
                "vote_history_columns": mapping_result.get("vote_history_columns", []),
                "suggested_matching_strategy": job.suggested_matching_strategy,
                "matching_strategy_reason": job.matching_strategy_reason,
                "total_rows": job.total_rows,
            }

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            await self.session.commit()
            raise

    async def confirm_mappings(
        self,
        job_id: UUID,
        confirmed_mappings: dict,
        matching_strategy: str,
        create_unmatched: bool = True,
    ) -> Job:
        """
        Confirm field mappings and matching strategy.

        Args:
            job_id: The job ID
            confirmed_mappings: User-confirmed field mappings
            matching_strategy: Selected matching strategy
            create_unmatched: Whether to create new contacts for unmatched rows

        Returns:
            Updated job
        """
        job = await self._get_job(job_id)

        if matching_strategy not in MATCHING_STRATEGIES:
            raise ValueError(f"Invalid matching strategy: {matching_strategy}")

        job.confirmed_mappings = confirmed_mappings
        job.matching_strategy = matching_strategy
        job.create_unmatched = create_unmatched
        job.status = "pending"  # Ready to start processing

        await self.session.commit()
        await self.session.refresh(job)

        return job

    async def process_import(self, job_id: UUID) -> None:
        """
        Process the import job in the background.

        Args:
            job_id: The job ID
        """
        job = await self._get_job(job_id)

        if not job.confirmed_mappings or not job.matching_strategy:
            raise ValueError("Job must have confirmed mappings before processing")

        job.status = "processing"
        job.started_at = datetime.utcnow()
        await self.session.commit()

        try:
            # Read file
            with open(job.file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Process rows
            errors = []

            for i, row in enumerate(rows):
                try:
                    await self._process_row(job, row, i + 1)

                    # Update progress
                    job.rows_processed = i + 1
                    if i % 100 == 0:  # Commit every 100 rows
                        await self.session.commit()
                        await update_job_progress(
                            job.id,
                            {
                                "status": "processing",
                                "rows_processed": job.rows_processed,
                                "rows_created": job.rows_created,
                                "rows_updated": job.rows_updated,
                                "rows_skipped": job.rows_skipped,
                                "rows_errored": job.rows_errored,
                                "total_rows": job.total_rows,
                                "percent_complete": (job.rows_processed / job.total_rows) * 100 if job.total_rows else 0,
                            },
                        )

                except Exception as e:
                    job.rows_errored += 1
                    errors.append({
                        "row": i + 1,
                        "error": str(e),
                        "data": {k: str(v)[:100] for k, v in row.items()},
                    })
                    logger.warning(
                        "Error processing row",
                        job_id=str(job_id),
                        row=i + 1,
                        error=str(e),
                    )

            # Finalize
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.error_details = errors[:100]  # Keep first 100 errors

            await self.session.commit()
            await delete_job_progress(job.id)

            logger.info(
                "Completed voter import",
                job_id=str(job_id),
                rows_created=job.rows_created,
                rows_updated=job.rows_updated,
                rows_skipped=job.rows_skipped,
                rows_errored=job.rows_errored,
            )

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await self.session.commit()
            await delete_job_progress(job.id)
            raise

    async def _process_row(self, job: Job, row: dict, row_num: int) -> None:
        """Process a single row from the import file."""
        mappings = job.confirmed_mappings

        # Build contact data from mappings
        contact_data = {}
        address_data = {}
        vote_history_data = []
        explicit_vote_history = {}  # For explicit vh_* field mappings

        for header, mapping in mappings.items():
            if not mapping:
                continue

            value = row.get(header, "").strip()
            if not value:
                continue

            if mapping == "vote_history":
                # Parse vote history column (auto-detect format like "2024_GEN")
                vh = self._parse_vote_history_column(header, value)
                if vh:
                    vote_history_data.append(vh)

            elif mapping.startswith("vh_"):
                # Explicit vote history field mapping
                vh_field = mapping.replace("vh_", "")
                explicit_vote_history[vh_field] = value

            elif mapping.startswith("address_"):
                # Address fields go into address JSON
                addr_field = mapping.replace("address_", "")
                address_data[addr_field] = value

            else:
                # Regular contact field
                contact_data[mapping] = self._convert_field_value(mapping, value)

        # Build explicit vote history record if we have the required fields
        if explicit_vote_history:
            vh_record = self._build_explicit_vote_history(explicit_vote_history)
            if vh_record:
                vote_history_data.append(vh_record)

        # Build address if we have any address data
        if address_data:
            contact_data["address"] = address_data

        # Find or create contact
        contact = await self._match_contact(job, contact_data)

        if contact:
            # Update existing contact
            for field, value in contact_data.items():
                if field != "email" and value is not None:  # Don't overwrite email
                    setattr(contact, field, value)
            job.rows_updated += 1
        else:
            # No matching contact found
            if not job.create_unmatched:
                # User opted not to create new contacts
                job.rows_skipped += 1
                return

            # Create new contact - need at least some identifying info
            has_email = "email" in contact_data
            has_name = "name" in contact_data
            has_voter_id = "state_voter_id" in contact_data

            if not (has_email or has_name or has_voter_id):
                # No identifying information at all - skip
                job.rows_skipped += 1
                return

            contact = Contact(
                tenant_id=self.tenant_id,
                source="voter_import",
                source_detail=job.original_filename,
                **contact_data,
            )
            self.session.add(contact)
            await self.session.flush()  # Get the ID
            job.rows_created += 1

        # Add vote history
        for vh in vote_history_data:
            await self._add_vote_history(contact, vh, job)

    async def _match_contact(
        self,
        job: Job,
        contact_data: dict,
    ) -> Contact | None:
        """Find existing contact based on matching strategy."""
        strategy = job.matching_strategy

        if strategy == "voter_id_first":
            # Try voter ID first
            if voter_id := contact_data.get("state_voter_id"):
                result = await self.session.execute(
                    select(Contact).where(
                        Contact.tenant_id == self.tenant_id,
                        Contact.state_voter_id == voter_id,
                    )
                )
                if contact := result.scalar_one_or_none():
                    return contact

            # Fall back to email
            if email := contact_data.get("email"):
                result = await self.session.execute(
                    select(Contact).where(
                        Contact.tenant_id == self.tenant_id,
                        Contact.email == email.lower(),
                    )
                )
                return result.scalar_one_or_none()

        elif strategy == "email_first":
            # Try email first
            if email := contact_data.get("email"):
                result = await self.session.execute(
                    select(Contact).where(
                        Contact.tenant_id == self.tenant_id,
                        Contact.email == email.lower(),
                    )
                )
                if contact := result.scalar_one_or_none():
                    return contact

            # Fall back to voter ID
            if voter_id := contact_data.get("state_voter_id"):
                result = await self.session.execute(
                    select(Contact).where(
                        Contact.tenant_id == self.tenant_id,
                        Contact.state_voter_id == voter_id,
                    )
                )
                return result.scalar_one_or_none()

        elif strategy == "voter_id_only":
            if voter_id := contact_data.get("state_voter_id"):
                result = await self.session.execute(
                    select(Contact).where(
                        Contact.tenant_id == self.tenant_id,
                        Contact.state_voter_id == voter_id,
                    )
                )
                return result.scalar_one_or_none()

        elif strategy == "email_only":
            if email := contact_data.get("email"):
                result = await self.session.execute(
                    select(Contact).where(
                        Contact.tenant_id == self.tenant_id,
                        Contact.email == email.lower(),
                    )
                )
                return result.scalar_one_or_none()

        return None

    async def _add_vote_history(
        self,
        contact: Contact,
        vote_data: dict,
        job: Job,
    ) -> None:
        """Add vote history record if it doesn't exist."""
        # Check for existing record
        result = await self.session.execute(
            select(VoteHistory).where(
                VoteHistory.contact_id == contact.id,
                VoteHistory.election_date == vote_data["election_date"],
                VoteHistory.election_type == vote_data["election_type"],
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.voted = vote_data.get("voted", existing.voted)
            existing.voting_method = vote_data.get("voting_method", existing.voting_method)
        else:
            # Create new record
            vote_history = VoteHistory(
                tenant_id=self.tenant_id,
                contact_id=contact.id,
                election_name=vote_data.get("election_name", ""),
                election_date=vote_data["election_date"],
                election_type=vote_data["election_type"],
                voted=vote_data.get("voted"),
                voting_method=vote_data.get("voting_method"),
                primary_party_voted=vote_data.get("primary_party_voted"),
                job_id=job.id,
                source_file_name=job.original_filename,
            )
            self.session.add(vote_history)

    def _parse_vote_history_column(
        self,
        header: str,
        value: str,
    ) -> dict | None:
        """Parse a vote history column header and value."""
        header_lower = header.lower()

        # Patterns for common vote history column formats
        # 2024_gen, 2024_pri, 2024_spe
        year_type_match = re.match(r"(\d{4})_?(gen|pri|spe|mun|run)", header_lower)
        # g2024, p2024
        type_year_match = re.match(r"(g|p|s|m|r)(\d{4})", header_lower)
        # general2024, primary2024
        word_year_match = re.match(r"(general|primary|special|municipal|runoff)_?(\d{4})", header_lower)

        if year_type_match:
            year = int(year_type_match.group(1))
            type_code = year_type_match.group(2)
        elif type_year_match:
            type_code = type_year_match.group(1)
            year = int(type_year_match.group(2))
        elif word_year_match:
            type_word = word_year_match.group(1)
            year = int(word_year_match.group(2))
            type_code = type_word[0]  # First letter
        else:
            return None

        # Map type codes
        type_map = {
            "g": "general",
            "gen": "general",
            "general": "general",
            "p": "primary",
            "pri": "primary",
            "primary": "primary",
            "s": "special",
            "spe": "special",
            "special": "special",
            "m": "municipal",
            "mun": "municipal",
            "municipal": "municipal",
            "r": "runoff",
            "run": "runoff",
            "runoff": "runoff",
        }

        election_type = type_map.get(type_code, "general")

        # Parse value
        value_lower = value.lower().strip()
        voted = None
        voting_method = None

        # Common voted indicators
        if value_lower in ["y", "yes", "1", "true", "x", "v", "voted"]:
            voted = True
        elif value_lower in ["n", "no", "0", "false", "", "did not vote"]:
            voted = False

        # Check for voting method
        if "early" in value_lower or "ev" in value_lower:
            voting_method = "early"
            voted = True
        elif "absentee" in value_lower or "ab" in value_lower:
            voting_method = "absentee"
            voted = True
        elif "mail" in value_lower or "vbm" in value_lower:
            voting_method = "mail"
            voted = True
        elif "election day" in value_lower or "ed" in value_lower:
            voting_method = "election_day"
            voted = True

        # Default election date (November for general, varies for others)
        if election_type == "general":
            election_date = date(year, 11, 1)  # First Tuesday after first Monday
        elif election_type == "primary":
            election_date = date(year, 6, 1)  # Varies by state
        else:
            election_date = date(year, 1, 1)

        election_name = f"{year} {election_type.title()} Election"

        return {
            "election_name": election_name,
            "election_date": election_date,
            "election_type": election_type,
            "voted": voted,
            "voting_method": voting_method,
        }

    def _build_explicit_vote_history(self, vh_data: dict) -> dict | None:
        """
        Build a vote history record from explicitly mapped fields.

        Expected fields (from vh_* mappings):
        - election_name: Name of the election
        - election_date: Date of the election
        - election_type: Type (general, primary, special, etc.)
        - voted: Whether they voted (Y/N/1/0/true/false)
        - voting_method: How they voted (early, absentee, mail, election_day)
        - primary_party: Party ballot pulled (for primaries)
        """
        # We need at least election_date or election_name to create a record
        if not vh_data.get("election_date") and not vh_data.get("election_name"):
            return None

        # Parse election date
        election_date = None
        if date_str := vh_data.get("election_date"):
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y%m%d", "%m/%d/%y"]:
                try:
                    election_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue

        # If no date, try to infer from election name
        if not election_date and (name := vh_data.get("election_name")):
            # Try to extract year from name
            year_match = re.search(r"(20\d{2})", name)
            if year_match:
                year = int(year_match.group(1))
                # Default to November for general elections
                election_date = date(year, 11, 1)

        if not election_date:
            return None

        # Parse election type
        election_type = "general"  # default
        if type_str := vh_data.get("election_type"):
            type_lower = type_str.lower().strip()
            type_map = {
                "general": "general", "gen": "general", "g": "general",
                "primary": "primary", "pri": "primary", "p": "primary",
                "special": "special", "spe": "special", "s": "special",
                "municipal": "municipal", "mun": "municipal", "m": "municipal",
                "runoff": "runoff", "run": "runoff", "r": "runoff",
            }
            election_type = type_map.get(type_lower, type_lower)
        elif name := vh_data.get("election_name"):
            # Try to infer type from name
            name_lower = name.lower()
            if "primary" in name_lower or "pri" in name_lower:
                election_type = "primary"
            elif "special" in name_lower:
                election_type = "special"
            elif "municipal" in name_lower:
                election_type = "municipal"
            elif "runoff" in name_lower:
                election_type = "runoff"

        # Parse voted status
        voted = None
        if voted_str := vh_data.get("voted"):
            voted_lower = voted_str.lower().strip()
            if voted_lower in ["y", "yes", "1", "true", "x", "v", "voted"]:
                voted = True
            elif voted_lower in ["n", "no", "0", "false", "did not vote", "dnv"]:
                voted = False

        # Parse voting method
        voting_method = None
        if method_str := vh_data.get("voting_method"):
            method_lower = method_str.lower().strip()
            method_map = {
                "early": "early", "ev": "early", "early voting": "early",
                "absentee": "absentee", "ab": "absentee",
                "mail": "mail", "vbm": "mail", "vote by mail": "mail",
                "election day": "election_day", "ed": "election_day", "in person": "election_day",
            }
            voting_method = method_map.get(method_lower, method_lower)

        # Build election name if not provided
        election_name = vh_data.get("election_name")
        if not election_name:
            year = election_date.year
            election_name = f"{year} {election_type.title()} Election"

        return {
            "election_name": election_name,
            "election_date": election_date,
            "election_type": election_type,
            "voted": voted,
            "voting_method": voting_method,
            "primary_party_voted": vh_data.get("primary_party"),
        }

    def _convert_field_value(self, field: str, value: str):
        """Convert a field value to the appropriate type."""
        if not value:
            return None

        # Date fields
        if field in ["date_of_birth", "voter_registration_date"]:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y%m%d"]:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            return None

        # Email normalization
        if field == "email":
            return value.lower().strip()

        # State normalization
        if field == "state":
            return value.upper()[:2]

        return value

    async def _get_job(self, job_id: UUID) -> Job:
        """Get a job by ID, ensuring it belongs to the tenant."""
        result = await self.session.execute(
            select(Job).where(
                Job.id == job_id,
                Job.tenant_id == self.tenant_id,
            )
        )
        job = result.scalar_one_or_none()

        if not job:
            raise ValueError(f"Job not found: {job_id}")

        return job

    async def get_job(self, job_id: UUID) -> Job:
        """Public method to get a job."""
        return await self._get_job(job_id)

    async def list_jobs(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """List import jobs for the tenant."""
        # Count total
        count_result = await self.session.execute(
            select(func.count()).select_from(Job).where(
                Job.tenant_id == self.tenant_id,
                Job.job_type == "voter_import",
            )
        )
        total = count_result.scalar() or 0

        # Get jobs
        result = await self.session.execute(
            select(Job)
            .where(
                Job.tenant_id == self.tenant_id,
                Job.job_type == "voter_import",
            )
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        jobs = list(result.scalars().all())

        return jobs, total

    async def delete_job(self, job_id: UUID) -> None:
        """Delete a job and its file."""
        job = await self._get_job(job_id)

        # Delete file if exists
        if job.file_path and os.path.exists(job.file_path):
            os.remove(job.file_path)

        # Delete job
        await self.session.delete(job)
        await self.session.commit()
