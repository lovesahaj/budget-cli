"""Email transaction importer for Gmail and other providers."""

import email
import imaplib
from datetime import datetime, timedelta
from email.header import decode_header
from typing import List, Optional


class EmailImporter:
    """Import transactions from email (Gmail, Outlook, etc.)."""

    def __init__(
        self,
        provider: str = "anthropic",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize email importer.

        Args:
            provider: LLM provider - "anthropic" or "local" (default: "anthropic")
            api_key: API key for Anthropic (not needed for local)
            base_url: Base URL for local LLM server (e.g., http://localhost:1234/v1)
            model: Model name for local LLM
        """
        if provider == "local":
            from budget.importers.llm_local import LocalLLMExtractor

            self.llm = LocalLLMExtractor(base_url=base_url, model=model)
        else:
            from budget.importers.llm import LLMExtractor

            self.llm = LLMExtractor(api_key)
        self.imap = None

    def connect_gmail(
        self,
        email_address: str,
        app_password: str,
    ):
        """Connect to Gmail using IMAP.

        Args:
            email_address: Gmail address
            app_password: Gmail app password (not regular password!)
                Generate at: https://myaccount.google.com/apppasswords

        Note:
            Regular Gmail passwords won't work. You must create an "App Password"
            in your Google Account settings.
        """
        try:
            self.imap = imaplib.IMAP4_SSL("imap.gmail.com")
            self.imap.login(email_address, app_password)
            print(f"Connected to Gmail: {email_address}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Gmail: {e}")

    def connect_outlook(
        self,
        email_address: str,
        password: str,
    ):
        """Connect to Outlook using IMAP.

        Args:
            email_address: Outlook email address
            password: Outlook password
        """
        try:
            self.imap = imaplib.IMAP4_SSL("outlook.office365.com")
            self.imap.login(email_address, password)
            print(f"Connected to Outlook: {email_address}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Outlook: {e}")

    def scan_for_transactions(
        self,
        days: int = 30,
        keywords: Optional[List[str]] = None,
        senders: Optional[List[str]] = None,
    ) -> List[dict]:
        """Scan emails for transactions.

        Args:
            days: Number of days to look back
            keywords: Keywords to search for (e.g., ["receipt", "payment", "order"])
            senders: Specific senders to filter (e.g., ["paypal.com", "amazon.com"])

        Returns:
            List of transaction dicts
        """
        if not self.imap:
            raise RuntimeError("Not connected to email. Call connect_gmail() first.")

        # Default keywords for transaction emails
        if keywords is None:
            keywords = [
                "receipt",
                "payment",
                "order",
                "transaction",
                "purchase",
                "invoice",
            ]

        # Select inbox
        self.imap.select("INBOX")

        # Build search criteria
        since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{since_date}")'

        # Search for emails
        _, message_numbers = self.imap.search(None, search_criteria)

        all_transactions = []
        emails_processed = 0

        for num in message_numbers[0].split():
            try:
                # Fetch email
                _, msg_data = self.imap.fetch(num, "(RFC822)")
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)

                # Get subject and sender
                subject = self._decode_header(email_message["Subject"])
                sender = email_message["From"]

                # Filter by keywords and senders
                if not self._should_process_email(subject, sender, keywords, senders):
                    continue

                # Extract body
                body = self._get_email_body(email_message)

                if not body:
                    continue

                # Extract transactions using LLM
                transactions = self.llm.extract_transactions(
                    text=body,
                    context=f"email receipt from {sender}",
                    source_type="email",
                )

                # Add email metadata
                for txn in transactions:
                    if "metadata" not in txn:
                        txn["metadata"] = {}
                    txn["metadata"]["email_subject"] = subject
                    txn["metadata"]["email_sender"] = sender
                    txn["metadata"]["email_date"] = email_message["Date"]

                all_transactions.extend(transactions)
                emails_processed += 1

                if transactions:
                    print(
                        f"Found {len(transactions)} transactions in: {subject[:50]}..."
                    )

            except Exception as e:
                print(f"Error processing email: {e}")
                continue

        print(f"Processed {emails_processed} emails, found {len(all_transactions)} transactions")
        return all_transactions

    def _should_process_email(
        self,
        subject: str,
        sender: str,
        keywords: List[str],
        senders: Optional[List[str]],
    ) -> bool:
        """Check if email should be processed."""
        # Check keywords in subject
        subject_lower = subject.lower()
        if not any(keyword.lower() in subject_lower for keyword in keywords):
            return False

        # Check sender if specified
        if senders:
            sender_lower = sender.lower()
            if not any(s.lower() in sender_lower for s in senders):
                return False

        return True

    def _decode_header(self, header: str) -> str:
        """Decode email header."""
        if not header:
            return ""

        decoded_parts = decode_header(header)
        decoded_str = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_str += part

        return decoded_str

    def _get_email_body(self, email_message) -> str:
        """Extract body text from email."""
        body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Get text parts
                if "attachment" not in content_disposition:
                    if content_type == "text/plain":
                        charset = part.get_content_charset() or "utf-8"
                        body += part.get_payload(decode=True).decode(
                            charset, errors="ignore"
                        )
        else:
            charset = email_message.get_content_charset() or "utf-8"
            body = email_message.get_payload(decode=True).decode(
                charset, errors="ignore"
            )

        return body

    def disconnect(self):
        """Disconnect from email server."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
                print("Disconnected from email")
            except Exception:
                pass
            self.imap = None

    def __del__(self):
        """Cleanup: disconnect when object is destroyed."""
        self.disconnect()
