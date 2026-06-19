"""Invoice generator using ReportLab.

Generates standardized PDF invoices for OR repairs and collection receipts for IR.
"""

import os
from datetime import datetime


class InvoiceGenerator:
    def generate_invoice(self, repair_data: dict) -> str:
        """Generate a PDF invoice for a completed repair.

        Args:
            repair_data: dict with keys:
                - id, customer_name, model, imei, issues
                - parts (list of {name, qty, unit_price, selling_price})
                - service_fee, total_amount, payment_method, created_at
                - shop_name, shop_address, shop_phone

        Returns:
            str: file path to the generated PDF
        """
        # Stub — placeholder for ReportLab implementation
        # TODO: Implement ReportLab PDF generation
        output_dir = os.path.join("static", "invoices")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"invoice_{repair_data.get('id', 'unknown')}.pdf"
        filepath = os.path.join(output_dir, filename)

        # Create a simple text file as placeholder
        with open(filepath.replace(".pdf", ".txt"), "w") as f:
            f.write(f"Invoice #{repair_data.get('id')}\n")
            f.write(f"Customer: {repair_data.get('customer_name')}\n")
            f.write(f"Device: {repair_data.get('model')}\n")
            f.write(f"Total: {repair_data.get('total_amount')}\n")

        return filepath


invoice_generator = InvoiceGenerator()
