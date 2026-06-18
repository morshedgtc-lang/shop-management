-- Shop Management System - Database Migration
-- Run this on existing Railway PostgreSQL database
-- For NEW databases: tables are auto-created by SQLAlchemy on startup

-- ============================================================
-- PRICING MODEL
-- ============================================================
ALTER TABLE parts ADD COLUMN IF NOT EXISTS selling_price FLOAT DEFAULT 0;
ALTER TABLE parts ADD COLUMN IF NOT EXISTS supplier_barcode VARCHAR DEFAULT '';
ALTER TABLE repair_parts ADD COLUMN IF NOT EXISTS selling_price FLOAT DEFAULT 0;
ALTER TABLE repair_parts ADD COLUMN IF NOT EXISTS returned_qty INTEGER DEFAULT 0;
ALTER TABLE repairs ADD COLUMN IF NOT EXISTS service_fee FLOAT DEFAULT 0;

-- ============================================================
-- PART SKU
-- ============================================================
ALTER TABLE parts ADD COLUMN IF NOT EXISTS sku VARCHAR;
ALTER TABLE parts ADD COLUMN IF NOT EXISTS brand_id INTEGER REFERENCES brands(id);
ALTER TABLE parts ADD COLUMN IF NOT EXISTS model_id INTEGER REFERENCES device_models(id);
ALTER TABLE parts ADD COLUMN IF NOT EXISTS part_type_id INTEGER REFERENCES part_types(id);

-- ============================================================
-- CATALOG TABLES (created by SQLAlchemy, but run if needed)
-- ============================================================
CREATE TABLE IF NOT EXISTS brands (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL UNIQUE,
  active BOOLEAN DEFAULT TRUE,
  sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS device_models (
  id SERIAL PRIMARY KEY,
  brand_id INTEGER REFERENCES brands(id),
  name VARCHAR NOT NULL,
  active BOOLEAN DEFAULT TRUE,
  sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS part_categories (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL UNIQUE,
  sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS part_types (
  id SERIAL PRIMARY KEY,
  category_id INTEGER REFERENCES part_categories(id),
  name VARCHAR NOT NULL,
  active BOOLEAN DEFAULT TRUE,
  sort_order INTEGER DEFAULT 0
);

-- ============================================================
-- SUPPLIER TABLES
-- ============================================================
CREATE TABLE IF NOT EXISTS suppliers (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL,
  phone VARCHAR DEFAULT '',
  address VARCHAR DEFAULT '',
  notes TEXT DEFAULT '',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supplier_payments (
  id SERIAL PRIMARY KEY,
  supplier_id INTEGER REFERENCES suppliers(id),
  amount FLOAT DEFAULT 0,
  method VARCHAR DEFAULT 'cash',
  date VARCHAR,
  notes TEXT DEFAULT '',
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- PURCHASE ORDER TABLES
-- ============================================================
CREATE TABLE IF NOT EXISTS purchase_orders (
  id SERIAL PRIMARY KEY,
  po_number VARCHAR UNIQUE NOT NULL,
  supplier_id INTEGER REFERENCES suppliers(id),
  status VARCHAR DEFAULT 'draft',
  payment_type VARCHAR DEFAULT 'credit',
  notes TEXT DEFAULT '',
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
  id SERIAL PRIMARY KEY,
  po_id INTEGER REFERENCES purchase_orders(id),
  part_id INTEGER REFERENCES parts(id),
  sku VARCHAR DEFAULT '',
  qty_ordered INTEGER DEFAULT 1,
  qty_received INTEGER DEFAULT 0,
  cost_price FLOAT DEFAULT 0,
  invoice_price FLOAT DEFAULT 0,
  selling_price FLOAT DEFAULT 0,
  part_status VARCHAR DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS purchase_order_receipts (
  id SERIAL PRIMARY KEY,
  po_id INTEGER REFERENCES purchase_orders(id),
  invoice_number VARCHAR,
  invoice_date VARCHAR,
  notes TEXT DEFAULT '',
  received_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_order_receipt_items (
  id SERIAL PRIMARY KEY,
  receipt_id INTEGER REFERENCES purchase_order_receipts(id),
  po_item_id INTEGER REFERENCES purchase_order_items(id),
  qty_received INTEGER DEFAULT 0,
  cost_price FLOAT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS purchase_order_discrepancies (
  id SERIAL PRIMARY KEY,
  po_id INTEGER REFERENCES purchase_orders(id),
  po_item_id INTEGER REFERENCES purchase_order_items(id),
  field VARCHAR NOT NULL,
  expected FLOAT DEFAULT 0,
  actual FLOAT DEFAULT 0,
  note TEXT DEFAULT '',
  created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- AUTO-POPULATE SKU FOR EXISTING PARTS
-- ============================================================
UPDATE parts SET sku = 'PART-' || LPAD(CAST(id AS VARCHAR), 3, '0') WHERE sku IS NULL;

-- Add unique constraint on SKU (after population)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'parts_sku_unique') THEN
    ALTER TABLE parts ADD CONSTRAINT parts_sku_unique UNIQUE (sku);
  END IF;
END $$;
