"""Image/receipt transaction importer with OCR."""

from pathlib import Path
from typing import List, Optional

from PIL import Image
import pytesseract


class ImageImporter:
    """Import transactions from images (receipts, screenshots) using OCR."""

    def __init__(
        self,
        provider: str = "anthropic",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        use_multimodal: bool = True,
    ):
        """Initialize image importer.

        Args:
            provider: LLM provider - "anthropic" or "local" (default: "anthropic")
            api_key: API key for Anthropic (not needed for local)
            base_url: Base URL for local LLM server (e.g., http://localhost:1234/v1)
            model: Model name for local LLM
            use_multimodal: Use direct image input for multimodal models (default: True)
        """
        self.provider = provider
        self.use_multimodal = use_multimodal

        if provider == "local":
            from budget.importers.llm_local import LocalLLMExtractor

            self.llm = LocalLLMExtractor(base_url=base_url, model=model)
        else:
            from budget.importers.llm import LLMExtractor

            self.llm = LLMExtractor(api_key)

    def extract_from_file(
        self,
        image_path: str,
        context: str = "receipt",
    ) -> List[dict]:
        """Extract transactions from an image file.

        Args:
            image_path: Path to image file (jpg, png, etc.)
            context: Context hint for the LLM (e.g., "store receipt")

        Returns:
            List of transaction dicts
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Check if we should use multimodal (direct image) or OCR
        if self.use_multimodal and self.provider == "local" and hasattr(
            self.llm, "extract_from_image"
        ):
            # Use direct image input for multimodal models (like Gemma 3)
            transactions = self.llm.extract_from_image(
                image_path=image_path,
                context=context,
            )
            ocr_method = "multimodal"
        else:
            # Fallback to OCR + text extraction
            text = self._extract_text_ocr(image_path)

            if not text.strip():
                print(f"Warning: No text extracted from {image_path}")
                return []

            # Use LLM to extract transactions
            transactions = self.llm.extract_transactions(
                text=text,
                context=context,
                source_type="image",
            )
            ocr_method = "pytesseract"

        # Add source metadata
        for txn in transactions:
            if "metadata" not in txn:
                txn["metadata"] = {}
            txn["metadata"]["source_file"] = str(image_path.name)
            txn["metadata"]["source_path"] = str(image_path)
            txn["metadata"]["ocr_method"] = ocr_method

        return transactions

    def _extract_text_ocr(self, image_path: Path) -> str:
        """Extract text from image using OCR.

        Args:
            image_path: Path to image file

        Returns:
            Extracted text
        """
        try:
            # Preprocess image for better OCR accuracy
            image = self.preprocess_image(image_path)

            # Perform OCR with pytesseract
            text = pytesseract.image_to_string(image)

            return text

        except Exception as e:
            print(f"Error performing OCR on image: {e}")
            return ""

    def extract_from_directory(
        self,
        directory: str,
        pattern: str = "*.{jpg,jpeg,png}",
        context: str = "receipt",
    ) -> dict:
        """Extract transactions from all images in a directory.

        Args:
            directory: Directory containing image files
            pattern: File extensions to process
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

        # Process common image formats
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
            for image_file in directory.glob(ext):
                try:
                    transactions = self.extract_from_file(image_file, context)
                    all_transactions.extend(transactions)
                    files_processed += 1
                    print(
                        f"Processed {image_file.name}: {len(transactions)} transactions"
                    )
                except Exception as e:
                    print(f"Failed to process {image_file.name}: {e}")
                    files_failed += 1

        return {
            "transactions": all_transactions,
            "files_processed": files_processed,
            "files_failed": files_failed,
        }

    def preprocess_image(self, image_path: Path) -> Image:
        """Preprocess image to improve OCR accuracy and normalize for multimodal models.

        Normalizes to 896x896 resolution for compatibility with Gemma 3 and similar models.
        Maintains aspect ratio with padding.

        Args:
            image_path: Path to image file

        Returns:
            Preprocessed PIL Image (896x896)
        """
        image = Image.open(image_path)

        # Normalize to 896x896 for Gemma 3 compatibility
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

        # Convert to grayscale for OCR
        image = new_image.convert("L")

        # Increase contrast to improve OCR
        from PIL import ImageEnhance

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)

        return image
