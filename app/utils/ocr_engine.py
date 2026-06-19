"""OCR Engine for invoice scanning.

Uses Google Cloud Vision when available, with graceful fallback.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    from google.cloud import vision
    from google.cloud.vision import ImageAnnotatorClient

    GCV_AVAILABLE = True
except ImportError:
    GCV_AVAILABLE = False
    logger.warning("google-cloud-vision is not installed — OCR disabled")


SKU_PATTERN = re.compile(r"[A-Z0-9]{3,20}", re.ASCII)
PRICE_PATTERN = re.compile(r"\d+[.,]\d{2}")
QTY_PATTERN = re.compile(r"\b\d+\b")
BRAND_NAMES = {
    "samsung", "lg", "sony", "panasonic", "philips", "toshiba", "hitachi",
    "sharp", "dell", "hp", "lenovo", "acer", "asus", "apple", "bose",
    "jbl", "logitech", "canon", "nikon", "epson", "brother",
}


def _guess_brand(text: str) -> str:
    text_lower = text.lower()
    for brand in BRAND_NAMES:
        if brand in text_lower:
            return brand.capitalize()
    return ""


def _parse_number(raw: str) -> float:
    cleaned = raw.replace(",", ".").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_items(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    price_candidates: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current.get("name"):
                price_candidates.sort(key=lambda x: _parse_number(x), reverse=True)
                if price_candidates:
                    current["unit_price"] = _parse_number(price_candidates[0])
                if "stock_qty" not in current:
                    current["stock_qty"] = 1
                current.setdefault("unit_price", 0.0)
                current.setdefault("stock_qty", 1)
                current.setdefault("brand", _guess_brand(current.get("name", "")))
                items.append(current)
                current = {}
                price_candidates = []
            continue

        if PRICE_PATTERN.search(stripped):
            price_candidates.append(stripped)

        if not current.get("name"):
            current["name"] = stripped
            brand = _guess_brand(stripped)
            if brand:
                current["brand"] = brand

        if SKU_PATTERN.fullmatch(stripped) and not current.get("sku"):
            current["sku"] = stripped

        qty_match = QTY_PATTERN.match(stripped)
        if qty_match and not current.get("stock_qty"):
            val = int(qty_match.group())
            if 1 <= val <= 9999:
                current["stock_qty"] = val

    if current.get("name"):
        price_candidates.sort(key=lambda x: _parse_number(x), reverse=True)
        if price_candidates:
            current["unit_price"] = _parse_number(price_candidates[0])
        current.setdefault("unit_price", 0.0)
        current.setdefault("stock_qty", 1)
        current.setdefault("brand", _guess_brand(current.get("name", "")))
        items.append(current)

    return items


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
          - supplier_barcode: str (optional)
          - selling_price: float (optional)
          - wholesale_price: float (optional)
          - box_number: int (optional)
          - shelf_number: int (optional)
        """
        if not GCV_AVAILABLE:
            logger.warning("GCV not available — returning empty results")
            return []

        try:
            client: ImageAnnotatorClient = ImageAnnotatorClient()
            image = vision.Image(content=image_bytes)
            response = client.text_detection(image=image)

            if response.error.message:
                logger.error("GCV error: %s", response.error.message)
                return []

            if not response.text_annotations:
                logger.info("No text detected in image")
                return []

            full_text = response.text_annotations[0].description
            lines = full_text.splitlines()
            logger.info("OCR extracted %d lines from image", len(lines))

            raw_items = _parse_items(lines)

            result: list[dict[str, Any]] = []
            for item in raw_items:
                result.append({
                    "name": item.get("name", ""),
                    "model": item.get("model", ""),
                    "sku": item.get("sku", ""),
                    "unit_price": item.get("unit_price", 0.0),
                    "stock_qty": item.get("stock_qty", 1),
                    "brand": item.get("brand", ""),
                    "supplier_barcode": item.get("supplier_barcode", ""),
                    "selling_price": item.get("selling_price", 0.0),
                    "wholesale_price": item.get("wholesale_price", 0.0),
                    "box_number": item.get("box_number", 0),
                    "shelf_number": item.get("shelf_number", 0),
                })

            logger.info("OCR parsed %d items from invoice", len(result))
            return result

        except Exception:
            logger.exception("OCR processing failed")
            return []


ocr_engine = OcrEngine()
