"""Local LLM-based transaction extraction using LM Studio or other OpenAI-compatible APIs."""

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from openai import OpenAI
from PIL import Image


class LocalLLMExtractor:
    """Extract structured transaction data from text using local LLM (LM Studio)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: str = "lm-studio",  # LM Studio doesn't need real API key
    ):
        """Initialize the local LLM extractor.

        Args:
            base_url: Base URL for the local LLM server (default: http://localhost:1234/v1)
            model: Model name to use (default: auto-detect from server)
            api_key: API key (not needed for LM Studio, but required by OpenAI client)
        """
        self.base_url = base_url or os.getenv(
            "LM_STUDIO_URL", "http://localhost:1234/v1"
        )
        self.model = model or os.getenv("LM_STUDIO_MODEL", "local-model")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=api_key,  # LM Studio doesn't validate this
        )

    def extract_transactions(
        self,
        text: str,
        context: str = "",
        source_type: str = "document",
    ) -> List[dict]:
        """Extract transactions from text using local LLM.

        Args:
            text: Text to extract transactions from
            context: Additional context (e.g., "bank statement", "receipt")
            source_type: Type of source ("pdf", "image", "email")

        Returns:
            List of transaction dicts with keys:
                - description: str
                - amount: float
                - date: datetime
                - type: str ("card" or "cash")
                - card: str (optional)
                - category: str (optional)
                - metadata: dict (optional)
        """
        prompt = self._build_extraction_prompt(text, context, source_type)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=8096,
            )

            # Extract JSON from response
            response_text = response.choices[0].message.content
            transactions_data = self._parse_response(response_text)

            # Convert to standard format
            return self._normalize_transactions(transactions_data)

        except Exception as e:
            print(f"Error extracting transactions with local LLM: {e}")
            print(f"Make sure LM Studio is running at {self.base_url}")
            return []

    def extract_from_image(
        self,
        image_path: Path,
        context: str = "receipt",
    ) -> List[dict]:
        """Extract transactions directly from an image using multimodal model.

        For models like Gemma 3 that support vision. Images are normalized to 896x896.

        Args:
            image_path: Path to image file
            context: Additional context (e.g., "receipt", "bank statement")

        Returns:
            List of transaction dicts
        """
        try:
            # Normalize image to 896x896 for Gemma 3
            normalized_image = self._normalize_image(image_path)

            # Encode image as base64
            image_base64 = self._encode_image_base64(normalized_image)

            # Build prompt for image analysis
            prompt = f"""Analyze this {context} image and extract all financial transactions.

For each transaction, extract:
- description: Brief description of the transaction
- amount: Transaction amount (positive number only)
- date: Transaction date (YYYY-MM-DD format, or estimate based on context)
- type: "card" or "cash" (guess based on context if not specified)
- card: Card name or last 4 digits if mentioned (optional)
- category: Transaction category like "Food", "Transport", "Entertainment" etc. (optional)

IMPORTANT: Return ONLY a valid JSON array. No explanations, no markdown, no extra text.

Example format:
[
  {{
    "description": "Coffee at Starbucks",
    "amount": 5.50,
    "date": "2025-10-11",
    "type": "card",
    "card": "Visa",
    "category": "Food"
  }}
]

JSON array:"""

            # Send request with image
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            # Extract JSON from response
            response_text = response.choices[0].message.content
            transactions_data = self._parse_response(response_text)

            # Convert to standard format
            return self._normalize_transactions(transactions_data)

        except Exception as e:
            print(f"Error extracting from image with local LLM: {e}")
            print(f"Make sure your model supports multimodal input (e.g., Gemma 3)")
            return []

    def _normalize_image(self, image_path: Path) -> Image.Image:
        """Normalize image to 896x896 for Gemma 3 compatibility.

        Args:
            image_path: Path to image file

        Returns:
            Normalized PIL Image (896x896)
        """
        image = Image.open(image_path)

        # Target size for Gemma 3
        target_size = 896

        # Calculate scaling to fit within target size while maintaining aspect ratio
        width, height = image.size
        scale = min(target_size / width, target_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        # Resize image
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create new image with padding to reach 896x896
        new_image = Image.new("RGB", (target_size, target_size), (255, 255, 255))

        # Calculate padding to center the image
        paste_x = (target_size - new_width) // 2
        paste_y = (target_size - new_height) // 2

        # Paste resized image onto padded canvas
        new_image.paste(image, (paste_x, paste_y))

        return new_image

    def _encode_image_base64(self, image: Image.Image) -> str:
        """Encode PIL Image as base64 string.

        Args:
            image: PIL Image

        Returns:
            Base64 encoded string
        """
        import io

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _build_extraction_prompt(
        self, text: str, context: str, source_type: str
    ) -> str:
        """Build the prompt for the local LLM."""
        return f"""Extract all financial transactions from the following {context or source_type}.

For each transaction, extract:
- description: Brief description of the transaction
- amount: Transaction amount (positive number only)
- date: Transaction date (YYYY-MM-DD format, or estimate based on context)
- type: "card" or "cash" (guess based on context if not specified)
- card: Card name or last 4 digits if mentioned (optional)
- category: Transaction category like "Food", "Transport", "Entertainment" etc. (optional)

IMPORTANT: Return ONLY a valid JSON array. No explanations, no markdown, no extra text.

Example format:
[
  {{
    "description": "Coffee at Starbucks",
    "amount": 5.50,
    "date": "2025-10-11",
    "type": "card",
    "card": "Visa",
    "category": "Food"
  }}
]

Text to analyze:
{text}

JSON array:"""

    def _parse_response(self, response_text: str) -> List[dict]:
        """Parse LLM response to extract JSON."""
        # Try to find JSON array in response
        start_idx = response_text.find("[")
        end_idx = response_text.rfind("]") + 1

        if start_idx == -1 or end_idx == 0:
            # Try to extract from markdown code block
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            else:
                return []
        else:
            json_str = response_text[start_idx:end_idx]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Response was: {response_text[:500]}")
            return []

    def _normalize_transactions(self, transactions_data: List[dict]) -> List[dict]:
        """Normalize extracted transactions to standard format."""
        normalized = []

        for txn in transactions_data:
            try:
                # Parse date
                date_str = txn.get("date")
                if date_str:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        # Try other common formats
                        for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                            try:
                                date = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            date = datetime.now()  # Fallback to today
                else:
                    date = datetime.now()

                normalized_txn = {
                    "description": txn.get("description", "Unknown"),
                    "amount": float(txn.get("amount", 0)),
                    "date": date,
                    "type": txn.get("type", "card"),
                    "card": txn.get("card"),
                    "category": txn.get("category"),
                    "metadata": {
                        "extracted_by": "local_llm",
                        "model": self.model,
                        "base_url": self.base_url,
                    },
                }

                # Only add if valid amount
                if normalized_txn["amount"] > 0:
                    normalized.append(normalized_txn)

            except (ValueError, KeyError) as e:
                print(f"Error normalizing transaction: {e}")
                continue

        return normalized

    def test_connection(self) -> bool:
        """Test connection to local LLM server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
            )
            print(f"Successfully connected to LM Studio at {self.base_url}")
            print(f"Using model: {self.model}")
            return True
        except Exception as e:
            print(f"Failed to connect to local LLM: {e}")
            print(f"Make sure LM Studio is running at {self.base_url}")
            return False
