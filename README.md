<div align="center">

# KaratPOS

### Offline Jewelry Shop ERP / POS Management System

A complete, installable, offline-first desktop ERP & Point-of-Sale system built for jewelry shops in Sri Lanka — with live gold-rate-driven pricing, QR-based inventory, mixed payments, old-gold exchange, and full audit trails.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![SQLite](https://img.shields.io/badge/SQLite-Embedded_DB-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-CC2927?style=for-the-badge&logo=python&logoColor=white)](https://www.sqlalchemy.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-QR_Scanning-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![Flask](https://img.shields.io/badge/Flask-Phone_Bridge-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Academic_Project-lightgrey?style=for-the-badge)]()
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)]()
[![Status](https://img.shields.io/badge/Status-In_Development-yellow?style=for-the-badge)]()

</div>

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Core Domain Rule — Dynamic Gold Pricing](#core-domain-rule--dynamic-gold-pricing)
- [Features](#features)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Roles & Permissions](#roles--permissions)
- [Getting Started](#getting-started)
- [Default Login Credentials](#default-login-credentials)
- [Running the App](#running-the-app)
- [Build Order / Roadmap](#build-order--roadmap)
- [Packaging as a Windows Installer](#packaging-as-a-windows-installer)
- [Non-Functional Guarantees](#non-functional-guarantees)
- [Things This System Deliberately Does NOT Do](#things-this-system-deliberately-does-not-do)
- [Contributing / Branching Model](#contributing--branching-model)

---

## Overview

KaratPOS is a **university final-year project**: a full offline ERP/POS system tailored to how Sri Lankan jewelry shops actually operate. Everything runs on a single Windows PC — no internet, no cloud database, no subscription. All data lives in one SQLite file (`data/jewelry_pos.db`) that can be backed up by copying it.

The system is built phase-by-phase (see [Build Order](#build-order--roadmap)) so that at every stage there is a **runnable, demoable** application.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Language | **Python 3.11+** | Fast to build, huge ecosystem, easy to package |
| Desktop UI | **PySide6 (Qt for Python)** | LGPL-licensed, native look, powerful widgets |
| Database | **SQLite via SQLAlchemy ORM** | Zero-config, single-file, fully offline |
| QR Generation | **qrcode + Pillow** | Item tags, phone-bridge URL QR |
| QR Scanning (webcam) | **OpenCV + pyzbar** | Live camera decode inside a Qt dialog |
| Phone Camera Bridge | **Flask + html5-qrcode (JS)** | LAN-only mobile scanning, no cloud |
| PDF Generation | **ReportLab** | Receipts, tags, reports |
| Thermal Printing | **python-escpos** | Optional 80mm receipt printer support |
| Charts & Analytics | **matplotlib + pandas** | Dashboard charts, sales forecasting |
| Password Security | **bcrypt** | Salted password hashing |
| Packaging | **PyInstaller + Inno Setup** | Produces `JewelryPOS_Setup.exe` |

---

## Core Domain Rule — Dynamic Gold Pricing

This is the heart of the system. **Item prices are never stored.** Every price is calculated live:

```
item_price =  (net_weight_g × gold_rate_per_g_for_purity)
            + making_charge        (flat Rs. OR % of gold value)
            + stone_value
            − discount
            + tax
```

- Admin enters the **daily gold rate** each morning, per purity (24K / 22K / 21K / 18K).
- Gold rates are stored as an **append-only history table** — never overwritten.
- Every screen that shows an item price computes it live from the **latest rate**.
- If today's rate hasn't been entered, POS shows a warning banner and can optionally **block sales** until it is (configurable).

### Price Snapshot Rule (critical)

When a sale completes, the invoice line **freezes** a full snapshot: gold rate used, net weight, making charge applied, stone value, discount, tax, and final line total. Reopening an old invoice always shows the **original numbers** — never a live recalculation.

---

## Features

<table>
<tr><td width="50%" valign="top">

**Sales & POS**
- USB barcode/QR scanner input
- Manual search by code/name
- Live webcam QR scanning (OpenCV + pyzbar)
- Optional phone-camera scanning bridge (LAN)
- Real-time price breakdown per item
- Mixed payments (cash + card + old gold, etc.)
- Invoice-level & line-level discounts with admin approval threshold
- Atomic "Complete Sale" transaction (all-or-nothing)
- PDF + thermal receipt printing, reprint with watermark

**Inventory**
- Full item CRUD with live price preview
- QR tag generation + batch PDF printing
- Stock-take mode (scan vs. expected reconciliation)
- Low-stock alerts per category

</td><td width="50%" valign="top">

**Back Office**
- Customer CRUD + purchase history
- Supplier & purchase management
- Old gold exchange / buy-back with scrap tracking
- Returns & exchanges (full/partial, restock or scrap)
- Repair job tracking with printable tickets
- Advance orders with installment payments

**Admin & Reporting**
- Role-based access (Admin / Cashier / Sales)
- Full audit log of every sensitive action
- Daily/date-range/monthly/yearly sales reports
- Stock valuation at today's gold rate
- Profit per item/category, slow-moving stock
- Next-30-day sales forecast (pandas trend)
- Automatic daily SQLite backups (last 30 kept)

</td></tr>
</table>

---

## Project Structure

```
KaratPOS/
├── jewelry_pos/
│   ├── main.py                  # Application entry point
│   ├── app/
│   │   ├── database/            # models.py, db.py, seed.py
│   │   ├── services/            # business logic (auth, pricing, sales, reports...)
│   │   ├── ui/                  # one module per screen/window
│   │   ├── scanning/            # webcam_scanner.py, phone_bridge.py
│   │   ├── printing/            # receipt_pdf.py, thermal.py, tag_printer.py
│   │   └── utils/               # config.py, validators, helpers
│   ├── data/                    # SQLite db + daily backups (git-ignored)
│   ├── assets/                  # icons, images
│   ├── build/                   # PyInstaller spec, installer.iss
│   ├── requirements.txt
│   └── venv/                    # local virtual environment (git-ignored)
└── README.md
```

---

## Database Schema

16 core tables, all with `id`, `created_at`, `updated_at`; financial/inventory tables use **soft delete** (`is_deleted`) — nothing important is ever hard-deleted.

<details>
<summary><strong>Click to expand full table list</strong></summary>

| # | Table | Purpose |
|---|---|---|
| 1 | `users` | Login accounts, bcrypt password hash, role |
| 2 | `gold_rates` | Append-only daily rate history per purity |
| 3 | `categories` | Ring, Chain, Necklace, Bangle, Earring, Pendant, Bracelet, Other |
| 4 | `suppliers` | Supplier contacts |
| 5 | `items` | Inventory — weight/purity/making-charge inputs, **no stored price** |
| 6 | `customers` | Customer profiles + cached total spend |
| 7 | `invoices` | Sale header — totals, payment status |
| 8 | `invoice_items` | **Frozen price snapshot** per line item |
| 9 | `payments` | One row per payment method (mixed payments) |
| 10 | `old_gold_receipts` | Buy-back records, tied to a sale or standalone |
| 11 | `returns` | Return/exchange records with refund + restock logic |
| 12 | `purchases` / `purchase_items` | Goods received from suppliers |
| 13 | `repairs` | Repair job tracking |
| 14 | `audit_logs` | Every sensitive action, who + when |
| 15 | `settings` | Key/value shop configuration |
| 16 | `advance_orders` / `advance_payments` | Custom orders with installment plans |

</details>

---

## Roles & Permissions

| Role | Can Access |
|---|---|
| **ADMIN** | Everything — gold rates, users, item management, invoice cancellation, returns, reports, settings, backups, audit log |
| **CASHIER** | POS, complete sales, print/reprint receipts, own transaction history, customer lookup/create |
| **SALES** | Inventory browse/search, customer management, repairs — no selling, no rate entry |

Role checks are enforced in **both** the UI (hidden/disabled controls) and the **service layer** (never trust the UI alone).

---

## Getting Started

### Prerequisites

- **Windows 10/11**
- **Python 3.11+** installed and on PATH
- A webcam (optional — only needed for live QR scanning)

### Installation

```powershell
git clone https://github.com/Dippy2003/KaratPOS.git
cd KaratPOS/jewelry_pos

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### First Run

```powershell
python main.py
```

On first launch, the app will automatically:
1. Create `data/jewelry_pos.db`
2. Seed default users, categories, sample gold rates, sample items and customers
3. Show the login screen

---

## Default Login Credentials

> ⚠️ These are seeded for demo purposes only. Change them immediately in a real deployment — the app will prompt you to on first login.

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | ADMIN |
| `cashier` | `cashier123` | CASHIER |
| `sales` | `sales123` | SALES |

---

## Running the App

```powershell
cd jewelry_pos
venv\Scripts\activate
python main.py
```

- Login with any of the credentials above.
- The sidebar navigation automatically adapts to the logged-in role.
- All data is local — closing the app safely releases any in-progress cart reservations on next launch.

---

## Build Order / Roadmap

The system is built in demoable phases. ✅ = must run and be testable before moving on.

| Phase | Scope | Status |
|---|---|---|
| **1** | Foundation — schema, DB init/seed, login, role-based nav shell | ✅ Complete |
| **2** | Gold rate management, inventory CRUD, QR tag printing | 🔄 In Progress |
| **3** | POS core — cart, pricing, mixed payments, atomic sale, receipts *(MVP)* | ⏳ Planned |
| **4** | Webcam QR scanning in POS | ⏳ Planned |
| **5** | Customers, old gold exchange, transaction history, cancellations | ⏳ Planned |
| **6** | Returns & exchanges | ⏳ Planned |
| **7** | Suppliers, purchases, repairs, advance orders/installments | ⏳ Planned |
| **8** | Reports & analytics, audit log viewer, stock take, low-stock alerts | ⏳ Planned |
| **9** | Settings, backups, thermal printing | ⏳ Planned |
| **10** | Phone scanning bridge, PyInstaller + Inno Setup packaging, polish | ⏳ Planned |

---

## Packaging as a Windows Installer

*(Final phase — not yet implemented)*

1. **PyInstaller** bundles the app into `dist/JewelryPOS/` (one-folder mode), including OpenCV/pyzbar DLLs.
2. **Inno Setup** (`build/installer.iss`) produces `JewelryPOS_Setup.exe` with Start Menu + desktop shortcuts.
3. Database and backups are written to a **writable app-data folder** — never inside `Program Files`.
4. First run on a fresh install auto-creates the DB and seeds it, then shows the login screen.

---

## Non-Functional Guarantees

- ✅ **Atomic transactions** — Complete Sale, Returns, and Cancellations either fully succeed or fully roll back.
- ✅ **Concurrency-safe** — items are `RESERVED` the moment they're added to a cart, preventing double-selling; orphaned reservations are released on next startup.
- ✅ **No floats for money** — all currency columns use `Numeric(12,2)`, handled as Python `Decimal`.
- ✅ **Fully offline** — no internet calls anywhere in the core system.
- ✅ **Clean layering** — UI → Services → Models. No raw SQL in UI code.
- ✅ **Soft deletes** — invoices, items, and customers are never hard-deleted.

---

## Things This System Deliberately Does NOT Do

- ❌ Store a calculated price on an item (always computed live)
- ❌ Recalculate old invoices with today's rate (always reads the frozen snapshot)
- ❌ Use `float` for any money value
- ❌ Hard-delete invoices, payments, items, or customers
- ❌ Require an internet connection for any core feature
- ❌ Put business logic inside UI event handlers

---

## Contributing / Branching Model

This project follows a simple Git Flow:

```
main            ← stable, demoable milestones only
 └── develop    ← integration branch
      └── feature/phaseN-description   ← one branch per phase/feature
```

Each feature branch is merged into `develop` via a merge commit once its phase is demoable, and `develop` is periodically merged into `main`.
