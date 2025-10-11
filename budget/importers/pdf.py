"""PDF transaction importer."""

from pathlib import Path
from typing import List, Optional

import pdfplumber


class PDFImporter:
    """Import transactions from PDF documents (bank statements, receipts)."""

    def __init__(
        self,
        provider: str = "anthropic",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize PDF importer.

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

    def extract_from_file(
        self,
        pdf_path: str,
        context: str = "bank statement or receipt",
    ) -> List[dict]:
        """Extract transactions from a PDF file.

        Args:
            pdf_path: Path to PDF file
            context: Context hint for the LLM (e.g., "credit card statement")

        Returns:
            List of transaction dicts
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Extract text from PDF
        text = self._extract_text(pdf_path)

        if not text.strip():
            print(f"Warning: No text extracted from {pdf_path}")
            return []

        # Use LLM to extract transactions
        transactions = self.llm.extract_transactions(
            text=text,
            context=context,
            source_type="pdf",
        )

        # Add source metadata
        for txn in transactions:
            if "metadata" not in txn:
                txn["metadata"] = {}
            txn["metadata"]["source_file"] = str(pdf_path.name)
            txn["metadata"]["source_path"] = str(pdf_path)

        return transactions

    def _extract_text(self, pdf_path: Path) -> str:
        """Extract all text from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        text_parts = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

        return "\n\n".join(text_parts)

    def extract_from_directory(
        self,
        directory: str,
        pattern: str = "*.pdf",
        context: str = "bank statement or receipt",
    ) -> dict:
        """Extract transactions from all PDFs in a directory.

        Args:
            directory: Directory containing PDF files
            pattern: Glob pattern for PDF files (default: "*.pdf")
            context: Context hint for the LLM

        Returns:
            Dict with:
                - transactions: List[dict] - All extracted transactions
                - files_processed: int - Number of files processed
                - files_failed: int - Number of files that failed
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        all_transactions = []
        files_processed = 0
        files_failed = 0

        for pdf_file in directory.glob(pattern):
            try:
                transactions = self.extract_from_file(pdf_file, context)
                all_transactions.extend(transactions)
                files_processed += 1
                print(f"Processed {pdf_file.name}: {len(transactions)} transactions")
            except Exception as e:
                print(f"Failed to process {pdf_file.name}: {e}")
                files_failed += 1

        return {
            "transactions": all_transactions,
            "files_processed": files_processed,
            "files_failed": files_failed,
        }
