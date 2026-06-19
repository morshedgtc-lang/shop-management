"""OCR Engine for invoice scanning.

Abstract base that can be swapped between Google Cloud Vision, Tesseract, etc.
Currently returns a stub for development.
"""

from typing import Any


class OcrEngine:
    async def process_invoice(self, image_bytes: bytes) -> list[dict[str, Any]]:
        """Parse an invoice image and return a list of line items.

        Each item dict:
          - name: str
          - model: str
          - sku: str
          - unit_price: float
          - stock_qty: int
          - brand: str (optional)
        """
        # Stub — return empty draft
        # TODO: Replace with Google Cloud Vision API call
        return []


ocr_engine = OcrEngine()
