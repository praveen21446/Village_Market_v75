# Village Market v68 — PostgreSQL Production Database

# Village Market

Village Market is a lightweight, full-stack e-commerce web application built as an MVP for local marketplaces. It follows a decoupled monolithic architecture with a Python REST API backend and a lightweight vanilla JavaScript client-side single-page application (SPA).

```text
Village_Market/
├── backend/            # REST API service layer
│   ├── main.py         # App entry point & route controllers
│   ├── auth.py         # Authentication, sessions, roles, & security helpers
│   ├── database.py     # SQLAlchemy DB session & connection engine
│   ├── models.py       # ORM database models
│   └── schemas.py      # Pydantic request/response validation
├── frontend/           # Static frontend assets
│   ├── index.html      # Customer-facing storefront
│   ├── admin.html      # Store management portal
│   ├── app.js          # Customer UI state & API handlers
│   ├── admin.js        # Admin UI state & API handlers
│   └── style.css       # Layout styles & responsive UI
├── database/           # Persistent local storage
├── uploads/            # Local directory for user-uploaded product assets
├── .env.example        # Environment variable configuration template
├── .gitignore          # Version control ignore definitions
├── requirements.txt    # Python dependencies
└── run.py              # Application runner script
```

## Core Components & Module Responsibilities

### 1. Authentication & Authorization (`backend/auth.py`)

- Centralizes authentication and authorization helpers for the Buyer, Farmer/Vendor, and Admin/SuperAdmin roles.
- Supports secure session/token handling with expiration limits.
- Admin credentials are loaded from environment variables (`ADMIN_ID`, `ADMIN_PASSWORD`).
- Role mapping is enforced so Customer, Vendor, and SuperAdmin permissions remain separated.
- Authentication configuration is designed to be environment-driven through `python-dotenv` variables in `.env`.

> The current MVP retains the project's OTP-based customer/farmer login flow and the dedicated Admin ID/password login while keeping the authorization layer centralized in `backend/auth.py`.

### 2. Data Layer (`backend/database.py`, `backend/models.py`, `backend/schemas.py`)

- **Production database:** PostgreSQL through SQLAlchemy + psycopg 3.
- **Schema migrations:** Alembic is the production schema authority.
- **Data Validation:** Pydantic schemas validate request/response payloads across API endpoints.
- **Local compatibility:** SQLite remains available only when explicitly selected for isolated development/tests.

Production schema changes must be created and applied through Alembic. The application no longer creates or patches production tables at import time.

### 3. API Routing & Entry Point (`backend/main.py`)

- Exposes RESTful endpoints for authentication, crop/product listings, file uploads, carts, orders, payments, reviews, notifications, vendor actions, and admin workflows.
- Serves uploaded assets from `/uploads` when local storage is enabled.
- Supports cloud-compatible object storage configuration (for example S3/R2) through environment variables.
- Supports WebSocket notifications for real-time application events.

### 4. Client Interfaces (`frontend/`)

- **Storefront (`index.html` + `app.js`):** Buyer/Farmer client application for marketplace browsing, cart/checkout, crop submission, bookings, address/location capture, order tracking, and reviews.
- **Admin Portal (`admin.html` + `admin.js`):** Dedicated administrative interface for farm/crop inspection, quantity and quality verification, final-price confirmation, order monitoring, vendor decisions, and analytics.
- **Styles (`style.css`):** Responsive styling shared across the client interfaces.

## Key Developer Action Items & Setup Guidelines

Before deploying or running the application locally:

- **Environment Setup:** Copy `.env.example` to `.env` and set a unique `SECRET_KEY`. Configure `ADMIN_ID` and `ADMIN_PASSWORD` for the Admin app.
- **Asset Directory:** Ensure the `uploads/` directory exists locally with read/write permissions for uploaded product/crop images. The application creates it automatically when needed.
- **Database Management:** Configure `DATABASE_URL` for PostgreSQL and run `python -m alembic upgrade head` before application startup.
- **Production Readiness:** PostgreSQL migration, pooling, SQLite-to-PostgreSQL data transfer, and backup/restore tooling are included. File uploads should still be moved to cloud object storage before internet deployment.
- **Secrets:** Keep `.env` out of source control. Never commit database credentials, API keys, payment keys, or messaging credentials.

## Local Development

### Buyer / Farmer server

```text
http://127.0.0.1:8000/
```

Run with:

```text
start_windows.bat
```

### Admin server

```text
http://127.0.0.1:8001/admin
```

Run with:

```text
start_admin.bat
```

### Admin credentials

Primary development credentials:

```text
Admin ID: admin
Password: looser@123
```

For a real deployment, override them using `.env`.

## Marketplace Workflow

Farmer submits crop → Admin visits farm and verifies quantity/quality → Admin confirms final price → Approved crop becomes visible to buyers → Buyer places an order → Farmer accepts/rejects the requested quantity → Admin confirms accepted orders → Admin enables tracking → Admin marks the order shipped → Buyer receives a 6-digit delivery OTP → Admin verifies the buyer OTP after delivery → Order moves to Delivered Orders.


## v46 language update
English, Telugu (తెలుగు), and Hindi (हिन्दी) are supported from the language selector. The selected language is persisted in the browser.

## v48 updates
- Farmer Add Crop now selects Category first; Crop Name is filtered by the selected category.
- Quality/Grade is now an option dropdown (Premium, Grade A, Grade B, Grade C).
- Buyer marketplace/cart/orders show harvest date. Future-harvest orders show that delivery will happen after harvest.
- Farmer live location now maps coordinates and reverse-geocoded address data into farm address, village, mandal/taluk, district, state, PIN and landmark fields when available.
- Farmer Dashboard and Orders dynamic UI supports English, Telugu and Hindi.
- Buyer Cart and Orders dynamic UI supports English, Telugu and Hindi.
- Removed the Pay securely buyer action. Order stages are now Order confirmed -> Order accepted (admin will contact buyer) -> Track your order -> Shipped -> Delivered.
- Admin Orders includes Buyer Contacted · Enable Tracking after farmer acceptance.


## v49 order-status flow

Buyer-facing order flow is now documented and enforced as:

**Order confirmed → Order accepted + “Our admin team will contact you.” → Admin: “Buyer Contacted · Enable Tracking” → Track your order → Shipped → Delivered**

The farmer still accepts/rejects the order from the Farmer Orders page; that internal action is what changes the buyer status from **Order confirmed** to **Order accepted**. It is intentionally not shown as an extra buyer-facing status step.


## v53
- Buyer **Track your order** is now a clickable link that opens a dedicated tracking progress view for that order.

## v55 updates
- Removed the configurable low-stock threshold from Add Crop. Marketplace visibility now uses a fixed 10 kg minimum.
- Approved crops below 10 kg are automatically hidden from buyers and the farmer receives a low-stock notification with an Add Stock action.
- Buyer delivery addresses and farmer farm addresses are saved to the account and can be selected again on future orders/crop listings.
- Crop rejection now opens a dedicated admin rejection page with a required reason field.
- Crop Approvals now also shows published marketplace items, and admin can remove any published crop from the buyer marketplace.

## v56 updates
- Buyer and farmer notifications now have an X dismiss control; dismissing removes that notification for the signed-in user.
- Farmer Farm Business dashboard now shows full details for every crop, including photo, category, quantities, expected/final price, grade, harvest date, description, complete farm address/location, listing status, and admin note/reason.
- Rejected and admin-removed crops remain visible to the farmer with the complete admin reason.
- Admin Remove from Marketplace now opens a dedicated page with crop/farmer details and a required removal reason instead of a browser popup.

## v57 delivery workflow and UI update
- Buyer Marketplace no longer shows **Book Crop**; ordering is through **Add to Cart** and checkout only.
- Saved buyer/farmer addresses are shown as larger reusable address cards for better visibility.


## v60 Delivery Partner Removal
- Removed the Delivery Partner portal, onboarding, verification, OTP handoff, delivery assignment, delivery partner admin navigation, and `start_delivery.bat`.
- Order flow is now: Buyer order confirmed → Farmer accepts → Admin confirms → Admin enables tracking → Shipped → Delivered.
- Admin retains direct order monitoring and cancellation controls.


## v61 Marketplace Remaining-Stock Fix

- Fixed a marketplace visibility bug where a crop disappeared as soon as any buyer placed an order.
- A crop now remains visible while its **remaining available stock is at least 10 kg**, even if another order for that crop is still waiting for farmer confirmation.
- Stock continues to be reserved immediately when an order is placed, preventing buyers from ordering more than the real remaining quantity.
- When remaining stock falls below 10 kg, the existing low-stock rule hides the crop and alerts the farmer to add stock.
- Rejected/cancelled orders still restore their reserved quantity, so the crop automatically becomes visible again when available stock returns to 10 kg or more.


## v62 delivery confirmation
Delivery is completed only after the buyer gives the 6-digit Delivery OTP to Admin. Admin enters and verifies the OTP; only then is the order marked Delivered.


## v63 update
- Admin Orders now has separate Active Orders and Delivered Orders tabs with live counts. Delivered orders automatically move to Delivered Orders after buyer OTP verification.


## v64 stability/test update
- Loaded `.env` automatically so `ADMIN_ID`, `ADMIN_PASSWORD`, `DATABASE_URL`, storage, email/SMS and payment environment settings are actually applied when the Windows launchers are used.
- OTP generation now uses the `secrets` module.
- Single-order API now requires a delivery address, matching cart checkout behavior.
- Prevented an account from ordering its own crop.
- Hidden low-stock crops from direct public crop-detail access, matching marketplace visibility rules.
- Cart now removes stale/unavailable crop entries and prevents adding more than the currently available stock in 10 kg increments.
- Cart order submission is protected against accidental double-click duplicate orders.
- WebSocket URLs automatically use `wss://` on HTTPS deployments.
- Added automated end-to-end regression tests covering authentication, crop approval/rejection/removal, cart/order creation, bookings visibility, farmer decisions, cancellations/stock restoration, admin order transitions, delivery OTP, reviews, addresses, notifications, stock updates, and admin/farmer dashboards.

Run regression tests with:

```text
run_tests.bat
```


## v65 changes
- Primary admin password is `looser@123` unless overridden by `ADMIN_PASSWORD` in `.env`.
- Admin portal now includes an **Admins** page where an authenticated admin can create or remove additional admin accounts.
- Removed demo/pre-filled Buyer name and phone values from the login form.
- Removed the demo credentials hint from the Admin login form.


## v67 regression fixes
- Prevents the same phone number from silently changing Buyer/Farmer role and making orders appear to disappear.
- Resets OTP state when Buyer/Farmer role is changed.
- Clears stale login tokens before starting a fresh OTP login.
- Adds client-side phone/name/OTP validation.
- Removes remaining generated/default user-name behavior and prompt defaults.
- Forces v67 frontend cache refresh.
- Keeps the v65 Admin management feature and admin password configuration.
- Regression suite: 5 test groups passing.


## v68 PostgreSQL production database
- PostgreSQL is now the production database target (`postgresql+psycopg://...`).
- Added Alembic migration configuration and initial schema migration.
- Removed runtime `create_all()` and ad-hoc `ALTER TABLE` schema mutation from `backend/main.py`.
- Added configurable PostgreSQL connection pooling.
- Added `scripts/migrate_sqlite_to_postgres.py` for one-time migration of existing v67 SQLite data.
- Added timestamped PostgreSQL backup and restore tooling (`backup_postgres.bat`, `restore_postgres.bat`).
- Added `migrate_database.bat`; normal Windows launchers apply pending migrations before startup.
- Added Docker Compose PostgreSQL 16 service for local/staging setup.
- See `POSTGRESQL_SETUP.md` for setup, migration, backup, restore and future migration workflow.
