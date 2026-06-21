import json
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)


HANDOVER_LABELS = {
    "sim_tray": "SIM Tray",
    "memory_card": "Memory Card",
    "charger": "Charger / Adapter",
    "cable": "Charging Cable",
    "case": "Protective Case / Cover",
}


class InvoiceGenerator:
    _styles = None

    @classmethod
    def _get_styles(cls):
        if cls._styles is None:
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                "InvoiceTitle", fontSize=22, leading=26,
                spaceAfter=6, alignment=1,
            ))
            styles.add(ParagraphStyle(
                "ShopName", fontSize=16, leading=20,
                spaceAfter=2, alignment=0,
            ))
            styles.add(ParagraphStyle(
                "ShopDetail", fontSize=9, leading=12,
                textColor=colors.grey, alignment=0,
            ))
            styles.add(ParagraphStyle(
                "SectionHeader", fontSize=11, leading=14,
                spaceBefore=10, spaceAfter=4,
                textColor=colors.HexColor("#333333"),
            ))
            styles.add(ParagraphStyle(
                "TableCell", fontSize=9, leading=12,
            ))
            styles.add(ParagraphStyle(
                "TableHeader", fontSize=9, leading=12,
                textColor=colors.white,
            ))
            styles.add(ParagraphStyle(
                "Footer", fontSize=8, leading=10,
                textColor=colors.grey, alignment=1,
            ))
            styles.add(ParagraphStyle(
                "ReceiptLine", fontSize=10, leading=14,
                fontName="Courier", spaceAfter=1,
            ))
            styles.add(ParagraphStyle(
                "ReceiptTitle", fontSize=14, leading=18,
                fontName="Courier-Bold", alignment=1, spaceAfter=4,
            ))
            styles.add(ParagraphStyle(
                "ReceiptHeader", fontSize=10, leading=14,
                fontName="Courier-Bold", spaceAfter=1,
            ))
            cls._styles = styles
        return cls._styles

    def _build_receipt_content(self, styles, repair_data, estimate=False):
        elements = []

        shop_name = repair_data.get("shop_name") or "SHOP NAME"
        shop_address = repair_data.get("shop_address") or ""
        shop_phone = repair_data.get("shop_phone") or ""

        repair_id = repair_data.get("id", "")
        created_at = repair_data.get("created_at")
        if created_at:
            date_str = created_at.strftime("%d-%m-%Y") if hasattr(created_at, "strftime") else str(created_at)[:10]
        else:
            date_str = datetime.now().strftime("%d-%m-%Y")

        customer_name = repair_data.get("customer_name") or "N/A"
        model = repair_data.get("model") or ""
        brand = repair_data.get("brand") or ""
        device = f"{brand} {model}".strip()
        imei = repair_data.get("imei") or ""
        passcode = repair_data.get("passcode") or ""
        issues = repair_data.get("issues") or ""

        handover_items_json = repair_data.get("handover_items") or "[]"
        memory_note = repair_data.get("handover_memory_note") or ""
        condition_json = repair_data.get("condition_data") or "{}"

        lines = []
        sep = "=" * 45
        dash = "-" * 45

        lines.append(Paragraph(sep, styles["ReceiptLine"]))
        title = "JOB RECEIPT" if estimate else "INVOICE"
        lines.append(Paragraph(f"<b>{shop_name}</b>", styles["ReceiptTitle"]))
        lines.append(Paragraph(title, styles["ReceiptTitle"]))
        if shop_address:
            lines.append(Paragraph(shop_address, styles["ReceiptLine"]))
        if shop_phone:
            lines.append(Paragraph(f"Tel: {shop_phone}", styles["ReceiptLine"]))
        lines.append(Paragraph(sep, styles["ReceiptLine"]))

        lines.append(Paragraph(
            f"Token ID: #{repair_id}                 Date: {date_str}",
            styles["ReceiptLine"],
        ))
        lines.append(Paragraph(f"Customer: {customer_name}", styles["ReceiptLine"]))
        lines.append(Paragraph(f"Device:   {device}", styles["ReceiptLine"]))
        if imei:
            lines.append(Paragraph(f"IMEI:     {imei}", styles["ReceiptLine"]))

        lines.append(Paragraph(dash, styles["ReceiptLine"]))
        lines.append(Paragraph(f"<b>ISSUE REPORTED:</b> {issues}", styles["ReceiptLine"]))
        if passcode:
            lines.append(Paragraph(f"PASSCODE: {passcode}", styles["ReceiptLine"]))

        try:
            handover_items = json.loads(handover_items_json) if isinstance(handover_items_json, str) else handover_items_json
        except (json.JSONDecodeError, TypeError):
            handover_items = []

        if handover_items:
            lines.append(Paragraph(dash, styles["ReceiptLine"]))
            lines.append(Paragraph("<b>ACCESSORIES RECEIVED (Checklist):</b>", styles["ReceiptLine"]))
            cols = 2
            row_items = []
            for i, key in enumerate(["sim_tray", "memory_card", "charger", "cable", "case"]):
                checked = "[X]" if key in handover_items else "[ ]"
                label = HANDOVER_LABELS.get(key, key)
                row_items.append(f" {checked} {label}")
            for i in range(0, len(row_items), cols):
                chunk = row_items[i:i + cols]
                line_str = "     ".join(chunk)
                lines.append(Paragraph(line_str, styles["ReceiptLine"]))
            if memory_note and "memory_card" in handover_items:
                lines.append(Paragraph(f"     Memory Card: {memory_note}", styles["ReceiptLine"]))

        try:
            condition = json.loads(condition_json) if isinstance(condition_json, str) else condition_json
        except (json.JSONDecodeError, TypeError):
            condition = {}

        if condition.get("screen_cracked") or condition.get("scuffs_dents") or condition.get("remarks"):
            lines.append(Paragraph(dash, styles["ReceiptLine"]))
            lines.append(Paragraph("<b>PRE-REPAIR CONDITION:</b>", styles["ReceiptLine"]))
            if condition.get("screen_cracked"):
                lines.append(Paragraph(" [X] Screen cracked", styles["ReceiptLine"]))
            if condition.get("scuffs_dents"):
                lines.append(Paragraph(" [X] Scuffs/dents on body", styles["ReceiptLine"]))
            if condition.get("remarks"):
                lines.append(Paragraph(f" Notes: {condition['remarks']}", styles["ReceiptLine"]))

        if not estimate:
            parts = repair_data.get("parts") or []
            if parts:
                lines.append(Paragraph(dash, styles["ReceiptLine"]))
                lines.append(Paragraph("<b>PARTS USED:</b>", styles["ReceiptLine"]))
                for p in parts:
                    name = p.get("part_name") or "Part"
                    qty = p.get("qty") or 0
                    price = p.get("selling_price") or p.get("unit_price") or 0
                    lines.append(Paragraph(f" {name} x{qty} @ {price:.2f}", styles["ReceiptLine"]))
                total_parts = sum(
                    (p.get("qty") or 0) * ((p.get("selling_price") or p.get("unit_price") or 0))
                    for p in parts
                )
                lines.append(Paragraph(f" Parts Total: {total_parts:.2f}", styles["ReceiptLine"]))

            service_fee = repair_data.get("service_fee") or 0
            if service_fee:
                lines.append(Paragraph(f" Service Fee: {service_fee:.2f}", styles["ReceiptLine"]))
            parts_total = sum(
                (p.get("qty") or 0) * ((p.get("selling_price") or p.get("unit_price") or 0))
                for p in (repair_data.get("parts") or [])
            )
            grand_total = parts_total + service_fee
            lines.append(Paragraph(f" <b>GRAND TOTAL: {grand_total:.2f}</b>", styles["ReceiptLine"]))

        lines.append(Paragraph(dash, styles["ReceiptLine"]))
        lines.append(Paragraph(
            "<i>Note: Please bring this receipt to collect your device.</i>",
            styles["ReceiptLine"],
        ))
        lines.append(Paragraph(
            "<i>We are not responsible for unbacked data.</i>",
            styles["ReceiptLine"],
        ))
        lines.append(Paragraph(sep, styles["ReceiptLine"]))

        elements.extend(lines)
        return elements

    def generate_invoice(self, repair_data: dict, estimate: bool = False) -> str:
        output_dir = os.path.join("static", "invoices")
        os.makedirs(output_dir, exist_ok=True)

        prefix = "estimate" if estimate else "invoice"
        filename = f"{prefix}_{repair_data.get('id', 'unknown')}.pdf"
        filepath = os.path.join(output_dir, filename)

        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            topMargin=20 * mm, bottomMargin=15 * mm,
            leftMargin=20 * mm, rightMargin=20 * mm,
        )

        styles = self._get_styles()
        elements = self._build_receipt_content(styles, repair_data, estimate=estimate)

        doc.build(elements)
        return filepath


invoice_generator = InvoiceGenerator()
