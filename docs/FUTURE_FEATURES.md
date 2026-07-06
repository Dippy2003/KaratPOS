# KaratPOS — Future Feature Ideas

A running list of features not yet built, grouped by effort. This is a wishlist for future development, not a commitment or roadmap with dates.

---

## Quick wins (small effort, real value)

- **Multi-language UI (Sinhala/Tamil)** — most of the target shops' staff would benefit from this more than almost anything else on this list; PySide6 supports Qt Linguist translation files natively.
- **Receipt logo upload** — Settings already has a `receipt_logo_path` field defined in the schema but it's never wired into the UI or the PDF receipt. Quick to finish.
- **Custom low-stock thresholds per category from the UI** — the field exists (`Category.low_stock_threshold`) but there's currently no screen to edit it after seeding; it's only set programmatically.
- **Production WSGI server for the phone bridge** — Flask's built-in dev server (the one that prints "do not use in production") is fine for a LAN scanning bridge, but swapping to `waitress` (pure-Python, no extra system deps) would remove that warning for a polished demo.

## Medium effort, meaningfully expands the product

- **Alembic migrations** — right now schema changes rely on `create_all()`, which only adds new tables, never alters existing ones. Any future column change on a real deployed shop's database would need manual SQL. Alembic is the standard fix.
- **Jewelry design/photo catalog** — items already have a `photo_path` field; building out a proper image picker + thumbnail grid in Inventory would make the catalog visually useful, not just data-only.
- **Customer loyalty / points program** — `total_spent` is already tracked per customer; a tiered rewards system building on that is a natural next step.
- **SMS/WhatsApp notifications** — "your repair is ready," "your advance order balance is due," etc. Sri Lanka has several SMS gateway APIs; this is the one place where going online briefly would be worth it as an opt-in feature.
- **Sri Lanka VAT-compliant invoice format** — current tax handling is a flat generic percentage; a real deployment would likely need proper VAT invoice numbering/formatting rules.

## Bigger, more ambitious additions

- **Multi-branch support** — one gold rate feed, shared customer/item catalog, but per-branch inventory and sales reporting. Currently the whole system assumes a single shop.
- **Cloud backup sync (opt-in)** — keep the offline-first core, but let an Admin optionally push the nightly backup to Google Drive/S3 for disaster recovery, without making it a hard dependency.
- **Insurance valuation certificate generator** — a formatted PDF certifying an item's weight/purity/value for customer insurance purposes; the underlying data (`hallmark_certificate_no`, weight, purity) already exists.
- **Barcode scale integration** — some jewelry shops use a digital scale that outputs weight over USB/serial; auto-filling `net_weight_g` from a live scale reading instead of manual entry would remove a common data-entry error.

---

*Last reviewed: 2026-07-06, after all 10 build phases were complete.*
