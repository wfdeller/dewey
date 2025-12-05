"""Pluggable email provider interface and implementations."""

import ssl
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmailAttachment:
    """Email attachment."""

    filename: str
    content: bytes
    content_type: str


@dataclass
class EmailMessage:
    """Email message to send."""

    to_email: str
    to_name: str | None
    subject: str
    body_html: str
    body_text: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    attachments: list[EmailAttachment] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class EmailResult:
    """Result of sending an email."""

    success: bool
    message_id: str | None = None
    error: str | None = None
    provider_response: dict | None = None


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> EmailResult:
        """Send an email message."""
        pass

    @abstractmethod
    async def validate_config(self) -> tuple[bool, str | None]:
        """Validate provider configuration. Returns (is_valid, error_message)."""
        pass


class SMTPProvider(EmailProvider):
    """SMTP email provider."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.default_from_email = from_email
        self.default_from_name = from_name

    async def send(self, message: EmailMessage) -> EmailResult:
        """Send email via SMTP."""
        try:
            # Build the message
            msg = MIMEMultipart("alternative")

            from_email = message.from_email or self.default_from_email
            from_name = message.from_name or self.default_from_name

            if from_name:
                msg["From"] = f"{from_name} <{from_email}>"
            else:
                msg["From"] = from_email

            if message.to_name:
                msg["To"] = f"{message.to_name} <{message.to_email}>"
            else:
                msg["To"] = message.to_email

            msg["Subject"] = message.subject

            if message.reply_to:
                msg["Reply-To"] = message.reply_to

            # Add custom headers
            for key, value in message.headers.items():
                msg[key] = value

            # Attach text parts
            if message.body_text:
                msg.attach(MIMEText(message.body_text, "plain", "utf-8"))
            msg.attach(MIMEText(message.body_html, "html", "utf-8"))

            # Attach files
            for attachment in message.attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{attachment.filename}"',
                )
                msg.attach(part)

            # Send via SMTP
            if self.use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.host, self.port, context=context)
            else:
                server = smtplib.SMTP(self.host, self.port)
                if self.use_tls:
                    server.starttls()

            try:
                if self.username and self.password:
                    server.login(self.username, self.password)

                server.send_message(msg)
                message_id = msg.get("Message-ID", None)

                return EmailResult(
                    success=True,
                    message_id=message_id,
                )
            finally:
                server.quit()

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return EmailResult(success=False, error=f"Authentication failed: {e}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return EmailResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return EmailResult(success=False, error=str(e))

    async def validate_config(self) -> tuple[bool, str | None]:
        """Validate SMTP configuration by attempting connection."""
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                if self.use_tls:
                    server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.quit()
            return True, None
        except Exception as e:
            return False, str(e)


class SESProvider(EmailProvider):
    """AWS SES email provider."""

    def __init__(
        self,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        configuration_set: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.configuration_set = configuration_set
        self.default_from_email = from_email
        self.default_from_name = from_name

    async def send(self, message: EmailMessage) -> EmailResult:
        """Send email via AWS SES."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            client = boto3.client(
                "ses",
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
            )

            from_email = message.from_email or self.default_from_email
            from_name = message.from_name or self.default_from_name

            if from_name:
                source = f"{from_name} <{from_email}>"
            else:
                source = from_email

            destination = {"ToAddresses": [message.to_email]}

            body = {"Html": {"Charset": "UTF-8", "Data": message.body_html}}
            if message.body_text:
                body["Text"] = {"Charset": "UTF-8", "Data": message.body_text}

            email_message = {
                "Subject": {"Charset": "UTF-8", "Data": message.subject},
                "Body": body,
            }

            kwargs: dict[str, Any] = {
                "Source": source,
                "Destination": destination,
                "Message": email_message,
            }

            if message.reply_to:
                kwargs["ReplyToAddresses"] = [message.reply_to]

            if self.configuration_set:
                kwargs["ConfigurationSetName"] = self.configuration_set

            response = client.send_email(**kwargs)

            return EmailResult(
                success=True,
                message_id=response.get("MessageId"),
                provider_response=response,
            )

        except ImportError:
            return EmailResult(
                success=False,
                error="boto3 library not installed. Install with: pip install boto3",
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"SES error ({error_code}): {error_msg}")
            return EmailResult(success=False, error=f"{error_code}: {error_msg}")
        except Exception as e:
            logger.error(f"Failed to send email via SES: {e}")
            return EmailResult(success=False, error=str(e))

    async def validate_config(self) -> tuple[bool, str | None]:
        """Validate SES configuration."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            client = boto3.client(
                "ses",
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
            )
            # Try to get send quota as a validation check
            client.get_send_quota()
            return True, None
        except ImportError:
            return False, "boto3 library not installed"
        except ClientError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)


class GraphProvider(EmailProvider):
    """Microsoft Graph API email provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        user_id: str,  # Email address of the mailbox to send from
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.default_from_email = from_email or user_id
        self.default_from_name = from_name

    async def _get_access_token(self) -> str:
        """Get OAuth2 access token for Graph API."""
        import httpx

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            response.raise_for_status()
            return response.json()["access_token"]

    async def send(self, message: EmailMessage) -> EmailResult:
        """Send email via Microsoft Graph API."""
        try:
            import httpx

            access_token = await self._get_access_token()

            # Build the Graph API message
            to_recipient = {"emailAddress": {"address": message.to_email}}
            if message.to_name:
                to_recipient["emailAddress"]["name"] = message.to_name

            graph_message = {
                "message": {
                    "subject": message.subject,
                    "body": {
                        "contentType": "HTML",
                        "content": message.body_html,
                    },
                    "toRecipients": [to_recipient],
                },
                "saveToSentItems": "true",
            }

            if message.reply_to:
                graph_message["message"]["replyTo"] = [
                    {"emailAddress": {"address": message.reply_to}}
                ]

            # Send via Graph API
            send_url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/sendMail"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    send_url,
                    json=graph_message,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 202:
                    return EmailResult(success=True)
                else:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                    return EmailResult(success=False, error=error_msg)

        except ImportError:
            return EmailResult(
                success=False,
                error="httpx library not installed",
            )
        except Exception as e:
            logger.error(f"Failed to send email via Graph API: {e}")
            return EmailResult(success=False, error=str(e))

    async def validate_config(self) -> tuple[bool, str | None]:
        """Validate Graph API configuration."""
        try:
            await self._get_access_token()
            return True, None
        except Exception as e:
            return False, str(e)


class SendGridProvider(EmailProvider):
    """SendGrid email provider."""

    def __init__(
        self,
        api_key: str,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        self.api_key = api_key
        self.default_from_email = from_email
        self.default_from_name = from_name

    async def send(self, message: EmailMessage) -> EmailResult:
        """Send email via SendGrid."""
        try:
            import httpx

            from_email = message.from_email or self.default_from_email
            from_name = message.from_name or self.default_from_name

            payload = {
                "personalizations": [
                    {
                        "to": [{"email": message.to_email, "name": message.to_name}]
                        if message.to_name
                        else [{"email": message.to_email}]
                    }
                ],
                "from": {"email": from_email, "name": from_name}
                if from_name
                else {"email": from_email},
                "subject": message.subject,
                "content": [
                    {"type": "text/html", "value": message.body_html},
                ],
            }

            if message.body_text:
                payload["content"].insert(0, {"type": "text/plain", "value": message.body_text})

            if message.reply_to:
                payload["reply_to"] = {"email": message.reply_to}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code in (200, 202):
                    message_id = response.headers.get("X-Message-Id")
                    return EmailResult(success=True, message_id=message_id)
                else:
                    return EmailResult(
                        success=False,
                        error=f"SendGrid error {response.status_code}: {response.text}",
                    )

        except ImportError:
            return EmailResult(
                success=False,
                error="httpx library not installed",
            )
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {e}")
            return EmailResult(success=False, error=str(e))

    async def validate_config(self) -> tuple[bool, str | None]:
        """Validate SendGrid configuration."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # Check API key by getting user profile
                response = await client.get(
                    "https://api.sendgrid.com/v3/user/profile",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code == 200:
                    return True, None
                else:
                    return False, f"Invalid API key: {response.status_code}"
        except Exception as e:
            return False, str(e)


def get_email_provider(
    provider_type: str,
    config: dict,
    from_email: str | None = None,
    from_name: str | None = None,
) -> EmailProvider:
    """Factory function to create an email provider from configuration."""

    if provider_type == "smtp":
        return SMTPProvider(
            host=config["host"],
            port=config["port"],
            username=config.get("username"),
            password=config.get("password"),  # Should be decrypted before passing
            use_tls=config.get("use_tls", True),
            use_ssl=config.get("use_ssl", False),
            from_email=from_email,
            from_name=from_name,
        )

    elif provider_type == "ses":
        return SESProvider(
            region=config["region"],
            access_key_id=config["access_key_id"],
            secret_access_key=config["secret_access_key"],  # Should be decrypted
            configuration_set=config.get("configuration_set"),
            from_email=from_email,
            from_name=from_name,
        )

    elif provider_type == "graph":
        return GraphProvider(
            client_id=config["client_id"],
            client_secret=config["client_secret"],  # Should be decrypted
            tenant_id=config["tenant_id"],
            user_id=config["user_id"],
            from_email=from_email,
            from_name=from_name,
        )

    elif provider_type == "sendgrid":
        return SendGridProvider(
            api_key=config["api_key"],  # Should be decrypted
            from_email=from_email,
            from_name=from_name,
        )

    else:
        raise ValueError(f"Unknown email provider type: {provider_type}")
