# Project Structure

This document describes the Python package layout of `iftf_duoverkoop` and the
rationale for each folder. All new code should be placed in the appropriate
sub-package rather than at the top level.

---

## Overview

```
iftf_duoverkoop/          ← Django app root (also the project package)
│
├── core/                 ← Data layer: models, auth helpers, verification codes
├── views/                ← HTTP views, split by functional area
├── forms/                ← Django forms, one module per feature area
├── dashboard/            ← Staff management dashboard (views, forms, URLs)
├── src/                  ← Low-level database helpers (db.py)
├── management/           ← Custom manage.py commands
├── migrations/           ← Database migrations (auto-generated)
├── templates/            ← HTML templates, mirroring the view package structure
├── static/               ← CSS, JS, images
├── locale/               ← Translation files (.po / .mo)
├── templatetags/         ← Custom Django template tags
│
├── urls.py               ← Root URL configuration
├── settings.py           ← Django settings
├── apps.py               ← AppConfig (registers signals via ready())
├── admin.py              ← Shim → core/admin.py
│
│   ── Backward-compat shims (do not add logic here) ──
├── models.py             → core/models.py
├── auth.py               → core/auth.py
├── verification_codes.py → core/verification_codes.py
├── forms.py              → forms/order.py
├── views.py              → views/*
├── forms_dashboard.py    → dashboard/forms.py
├── views_dashboard.py    → dashboard/views.py
└── urls_dashboard.py     → dashboard/urls.py
```

---

## core/

**Rule:** All database models and domain logic live here. Nothing else imports
from here except `src/db.py` and the view/dashboard packages.

| File | Purpose |
|---|---|
| `models.py` | All ORM models: `Association`, `Performance`, `Purchase`, `PurchaseAuditLog`, `LoginAuditLog`. Also contains Django signal receivers that record login/logout events. |
| `auth.py` | Permission group names, `setup_permission_groups()`, role helpers (`is_pos_staff`, `can_edit_purchases`, …), `get_client_ip()`, `log_purchase_action()`. |
| `verification_codes.py` | Word lists and functions for generating/validating three-word verification codes. |
| `admin.py` | All `@admin.register` decorators for the Django `/admin/` interface. |

---

## views/

Each module handles one functional area. All modules import models from
`core.models` and helpers from `core.auth`.

| File | Purpose |
|---|---|
| `auth.py` | `login_view`, `logout_view` |
| `order.py` | `order` page, `_process_order_form`, `main` redirect, `get_last_customer` |
| `history.py` | `purchase_history`, `edit_purchase`, `delete_purchase` |
| `export.py` | `export` (CSV download) |
| `verify.py` | `verify_code` (three-word code lookup) |
| `api.py` | Internal JSON endpoints: `db_info`, `get_performances_by_association`, `get_performance_prices` |

---

## forms/

| File | Purpose |
|---|---|
| `order.py` | `OrderForm` — the main ticket purchase form |

---

## dashboard/

The entire staff management dashboard. Only accessible to `is_staff` users.

| File | Purpose |
|---|---|
| `views.py` | All dashboard views + `@staff_required` decorator |
| `forms.py` | `AssociationForm`, `PerformanceForm`, `CreateUserForm`, `EditUserForm`, `LogoUploadForm` |
| `urls.py` | URL patterns for `/dashboard/**`, included with the `dashboard` namespace |

---

## src/

Low-level database helper functions (`db.py`) that abstract ORM queries used
by views and forms. Imports from `core.models`.

---

## templates/

Mirrors the view package structure:

```
templates/
├── base.html                        ← Site-wide navbar / layout
├── login.html
├── order/
│   ├── order.html
│   └── overview.html
├── purchase_history/
│   └── purchase_history.html
├── verification/
│   └── verify_code.html
└── dashboard/
    ├── base_dashboard.html          ← Dashboard sidebar layout
    ├── home.html
    ├── associations.html
    ├── association_form.html
    ├── performances.html
    ├── performance_form.html
    ├── users.html
    ├── user_form.html
    ├── audit.html
    ├── audit_detail.html
    └── system.html
```

---

## API URL Paths

All internal JSON endpoints are grouped under `/api/`:

| URL | View | Purpose |
|---|---|---|
| `/api/performance-prices/` | `views.api.get_performance_prices` | Price map for all available performances |
| `/api/performances-by-association/<name>/` | `views.api.get_performances_by_association` | Performances for a specific association |
| `/api/db-info/` | `views.api.db_info` | Database engine type |
| `/api/last-customer/` | `views.order.get_last_customer` | Last customer from current session |

---

## Adding a New Feature

1. **Model change** → edit `core/models.py`, run `makemigrations`.
2. **New view** → add to the appropriate `views/<area>.py` (or create a new
   module if the area is genuinely new).
3. **New form** → add to `forms/<area>.py`.
4. **New URL** → register in `urls.py` (or `dashboard/urls.py` for staff-only pages).
5. **New dashboard page** → add view to `dashboard/views.py`, form to
   `dashboard/forms.py`, URL to `dashboard/urls.py`, template under
   `templates/dashboard/`.
6. Do **not** add logic to the top-level shim files (`models.py`, `auth.py`,
   `views.py`, etc.).

