"""Invoice generator using ReportLab.

Generates standardized PDF invoices for OR repairs and collection receipts for IR.
"""

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)


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
            cls._styles = styles
        return cls._styles

    def _build_header(self, styles, repair_data):
        elements = []
        shop_name = repair_data.get("shop_name") or "SHOP NAME"
        shop_address = repair_data.get("shop_address") or ""
        shop_phone = repair_data.get("shop_phone") or ""

        elements.append(Paragraph(shop_name, styles["ShopName"]))
        if shop_address:
            elements.append(Paragraph(shop_address, styles["ShopDetail"]))
        if shop_phone:
            elements.append(Paragraph(f"Phone: {shop_phone}", styles["ShopDetail"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
        elements.append(Spacer(1, 6))
        return elements

    def _build_title(self, styles, estimate=False):
        title = "ESTIMATE" if estimate else "INVOICE"
        return [Paragraph(title, styles["InvoiceTitle"]), Spacer(1, 4)]

    def _build_info_section(self, styles, repair_data, estimate=False):
        repair_id = repair_data.get("id", "")
        created_at = repair_data.get("created_at")
        if created_at:
            date_str = created_at.strftime("%Y-%m-%d") if hasattr(created_at, "strftime") else str(created_at)[:10]
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        doc_type = "Estimate" if estimate else "Invoice"
        customer_name = repair_data.get("customer_name") or "N/A"
        model = repair_data.get("model") or "N/A"
        imei = repair_data.get("imei") or ""
        issues = repair_data.get("issues") or ""

        info_rows = [
            [
                Paragraph(f"<b>{doc_type} #:</b> {repair_id}", styles["TableCell"]),
                Paragraph(f"<b>Date:</b> {date_str}", styles["TableCell"]),
            ],
            [
                Paragraph(f"<b>Customer:</b> {customer_name}", styles["TableCell"]),
                Paragraph("", styles["TableCell"]),
            ],
            [
                Paragraph(f"<b>Device:</b> {model}", styles["TableCell"]),
                Paragraph(f"<b>IMEI:</b> {imei}" if imei else "", styles["TableCell"]),
            ],
            [
                Paragraph(f"<b>Issues:</b> {issues}", styles["TableCell"]),
                Paragraph("", styles["TableCell"]),
            ],
        ]
        t = Table(info_rows, colWidths=[300, 200])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return [t, Spacer(1, 8)]

    def _build_parts_table(self, styles, repair_data):
        elements = []
        parts = repair_data.get("parts") or []

        elements.append(Paragraph("Parts Used", styles["SectionHeader"]))
        header = [
            Paragraph("Description", styles["TableHeader"]),
            Paragraph("Qty", styles["TableHeader"]),
            Paragraph("Unit Price", styles["TableHeader"]),
            Paragraph("Total", styles["TableHeader"]),
        ]
        table_data = [header]

        for part in parts:
            name = part.get("part_name") or part.get("name") or "Part"
            qty = part.get("qty") or 0
            unit_price = part.get("unit_price") or 0
            selling_price = part.get("selling_price") or unit_price
            row_total = qty * selling_price
            table_data.append([
                Paragraph(str(name), styles["TableCell"]),
                Paragraph(str(qty), styles["TableCell"]),
                Paragraph(f"{selling_price:.2f}", styles["TableCell"]),
                Paragraph(f"{row_total:.2f}", styles["TableCell"]),
            ])

        if not parts:
            table_data.append([
                Paragraph("No parts recorded", styles["TableCell"]),
                Paragraph("", styles["TableCell"]),
                Paragraph("", styles["TableCell"]),
                Paragraph("", styles["TableCell"]),
            ])

        t = Table(table_data, colWidths=[220, 60, 100, 100], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))
        return elements

    def _build_totals(self, styles, repair_data):
        parts = repair_data.get("parts") or []
        total_parts = sum(
            (p.get("qty") or 0) * ((p.get("selling_price") or p.get("unit_price") or 0))
            for p in parts
        )
        service_fee = repair_data.get("service_fee") or 0
        grand_total = total_parts + service_fee

        rows = [
            [Paragraph("Parts Total:", styles["TableCell"]), Paragraph(f"{total_parts:.2f}", styles["TableCell"])],
            [Paragraph("Service Fee:", styles["TableCell"]), Paragraph(f"{service_fee:.2f}", styles["TableCell"])],
        ]
        rows.append([
            Paragraph("<b>Grand Total:</b>", ParagraphStyle("gt", parent=styles["TableCell"], fontSize=12, leading=16)),
            Paragraph(f"<b>{grand_total:.2f}</b>", ParagraphStyle("gtv", parent=styles["TableCell"], fontSize=12, leading=16)),
        ])

        t = Table(rows, colWidths=[380, 100])
        t.setStyle(TableStyle([
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("LINEABOVE", (0, -1), (-1, -1), 2, colors.HexColor("#2c3e50")),
            ("TOPPADDING", (0, -1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -2), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -2), 3),
        ]))
        return [t, Spacer(1, 6)], grand_total

    def _build_payment_status(self, styles, repair_data, grand_total):
        payment_status = repair_data.get("payment_status") or "UNPAID"
        payment_method = repair_data.get("payment_method") or ""

        status_color = colors.HexColor("#27ae60") if payment_status == "PAID" else colors.HexColor("#e74c3c")
        status_text = f"Payment Status: <b>{payment_status}</b>"
        if payment_method:
            status_text += f" ({payment_method})"

        return [
            Paragraph(status_text, ParagraphStyle(
                "pstatus", fontSize=10, leading=14,
                textColor=status_color, alignment=1,
            )),
            Spacer(1, 8),
        ]

    def _build_footer(self, styles):
        return [
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")),
            Spacer(1, 4),
            Paragraph("Thank you for your business!", styles["Footer"]),
        ]

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
        elements = []
        elements.extend(self._build_header(styles, repair_data))
        elements.extend(self._build_title(styles, estimate=estimate))
        elements.extend(self._build_info_section(styles, repair_data, estimate=estimate))
        elements.extend(self._build_parts_table(styles, repair_data))
        totals_elements, grand_total = self._build_totals(styles, repair_data)
        elements.extend(totals_elements)
        elements.extend(self._build_payment_status(styles, repair_data, grand_total))
        elements.extend(self._build_footer(styles))

        doc.build(elements)
        return filepath


invoice_generator = InvoiceGenerator()
