# Mechanic Shop API

A Flask REST API for a mechanic shop. Customers book service tickets, mechanics get
assigned to those tickets, and parts are pulled from an inventory. Includes JWT-based
authentication with role separation (customer vs mechanic tokens), password hashing,
rate limiting, response caching, and pagination.

Every endpoint is documented in an interactive Swagger UI at
[`/api/docs`](#interactive-api-documentation) and covered by a
[unittest suite](#running-the-tests) of 73 tests.

## What this API does

- **Customer accounts** — register, log in, get a bearer token, view your own service
  tickets, update your profile, delete your account. Passwords are hashed at rest.
- **Mechanic accounts** — same pattern, but mechanic tokens are the ones authorized to
  modify inventory and other mechanics' records.
- **Service tickets** — a customer opens a ticket; one or many mechanics get assigned;
  parts can be added from inventory with quantities.
- **Inventory** — CRUD on parts. Adding a part to a ticket that already has that same
  part accumulates the quantity rather than creating a duplicate row.
- **A ranked query** — `/mechanics/most-tickets` returns mechanics ordered by how many
  tickets they've worked on (single `GROUP BY` query, not N+1).
- **Two rate-limited login endpoints** (5/minute each) plus default limits (20/hour,
  100/day per endpoint) as blanket protection.
- **Interactive documentation** — a Swagger UI page describing all 24 endpoints, with
  request/response shapes and worked examples, served from a static OpenAPI spec.
- **An automated test suite** — 73 unittest cases, at least one per route, roughly half
  of them exercising failure paths.

## Tech stack

| Layer | Library |
|---|---|
| Web framework | Flask 3.1 |
| ORM | Flask-SQLAlchemy 3.1 (SQLAlchemy 2.0 `Mapped`/`mapped_column` style) |
| Schemas | flask-marshmallow + marshmallow-sqlalchemy |
| Auth tokens | python-jose (HS256 JWT) |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` (scrypt) |
| Rate limiting | Flask-Limiter (in-memory storage) |
| Caching | Flask-Caching (in-memory `SimpleCache`) |
| Database | MySQL 8+ via `mysql-connector-python` (SQLite for tests) |
| Env loading | python-dotenv |
| API docs | flask-swagger-ui serving a static Swagger 2.0 spec |
| Testing | `unittest` (standard library) + Flask's test client |

## Data model

| Model | Table | Notes |
|---|---|---|
| `Customer` | `customers` | unique `email` + `phone`; hashed `password`; has many service tickets |
| `Mechanic` | `mechanics` | unique `email`; hashed `password`; has many service tickets |
| `Service_Ticket` | `service_tickets` | belongs to one customer; has many mechanics; has many parts (via junction model) |
| `Inventory` | `inventory` | catalog of parts (`name`, `price`) |
| `Service_Ticket_Inventory` | `service_ticket_inventory` | **junction model** with a `quantity` column — an association object, not a bare `db.Table`, because the link carries data of its own |
| — | `service_mechanics` | plain junction table between tickets and mechanics |

The two junctions are shaped differently on purpose: mechanic-on-ticket is a binary
fact (either they're assigned or they aren't) so a bare `db.Table` suffices, while
part-on-ticket needs to record *how many*, which forces a full model.

## Project structure

```
mechanic_shop_api/
├── app.py                                     # entry: build app, create_all, run
├── config.py                                  # config classes; reads .env
├── requirements.txt
├── Mechanic_Shop_API.postman_collection.json  # 60-request test suite
├── .env                                       # NOT committed - you create this
├── instance/                                  # auto-created by Flask; holds testing.db (gitignored)
├── tests/                                     # unittest suite - one file per blueprint
│   ├── test_customers.py
│   ├── test_mechanics.py
│   ├── test_service_tickets.py
│   └── test_inventory.py
└── app/
    ├── __init__.py                            # create_app(): init extensions, register blueprints + Swagger UI
    ├── extensions.py                          # ma, limiter, cache singletons
    ├── models.py                              # all models
    ├── static/swagger.yaml                    # OpenAPI spec served at /api/docs
    ├── utils/util.py                          # encode_token, encode_mechanic_token, @token_required, @mechanic_token_required
    └── blueprints/
        ├── customers/       (__init__.py, routes.py, schemas.py)
        ├── mechanics/
        ├── service_tickets/
        └── inventory/
```

Each blueprint folder follows the same three-file pattern: `__init__.py` creates the
`Blueprint` and imports `routes` at the bottom (order matters — the trailing import is
what registers the decorated routes onto the blueprint), `routes.py` holds the
endpoints, `schemas.py` holds the marshmallow schemas.

## Prerequisites

- **Python 3.11+** (tested on 3.13)
- **MySQL 8+** running locally, or a remote instance you have credentials for
- Git

## Setup

**1. Clone the repo and create a virtual environment**

```bash
python -m venv venv
```

Activate it — Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source venv/bin/activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Create the MySQL database**

```bash
mysql -u root -p -e "CREATE DATABASE mechanic_shop_db;"
```

(Use whatever database name matches `DB_NAME` in your `.env` — see next step.)

**4. Create a `.env` file** in the project root — see [The `.env` file](#the-env-file).

**5. Run the server**

```bash
python app.py
```

`app.py` calls `db.create_all()` inside an app context on startup, so the tables are
created automatically the first time you run it. The API is served at
`http://127.0.0.1:5000`.

## The `.env` file

`.env` holds database credentials and the JWT signing secret. It's **not committed** —
you must create it in the project root before the app will start.

```
DB_PASS=your_mysql_root_password
DB_NAME=mechanic_shop_db
DB_HOST=localhost
SECRET_KEY=any_random_string_at_least_32_chars_long
```

`config.py` reads `DB_PASS`, `DB_NAME`, `DB_HOST` via `python-dotenv` and assembles:

```
mysql+mysqlconnector://root:{DB_PASS}@localhost/{DB_NAME}
```

`SECRET_KEY` is loaded separately by `app/utils/util.py` and used to sign every JWT
issued by `/customers/login` and `/mechanics/login`. If it's missing, every login
attempt fails at token-encode time. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **Note:** `db.create_all()` only creates tables that don't already exist — it never
> alters one. If you change a model after the tables exist, drop the affected table
> and restart, or use Flask-Migrate/Alembic for real schema management.

## Authentication

Two token types, same signature secret, distinguished by a `role` claim in the JWT
payload. Both tokens expire after 1 hour.

- **Customer tokens** (`role: "customer"`) — issued by `POST /customers/login`.
  Required for `/my-tickets`, `PUT /customers/`, `DELETE /customers/`.
- **Mechanic tokens** (`role: "mechanic"`) — issued by `POST /mechanics/login`.
  Required for anything that modifies inventory or mechanic records.

Send the token in the `Authorization` header:

```
Authorization: Bearer <token>
```

`@token_required` accepts any valid token; `@mechanic_token_required` additionally
verifies `role == "mechanic"` and returns **403 Forbidden** for a valid *customer*
token — that's the layer that separates shop staff from customers.

## Interactive API documentation

With the server running, open:

```
http://127.0.0.1:5000/api/docs
```

Every endpoint is browsable there — grouped by category, with the exact request body it
expects, the exact response it returns, and a **Try it out** button that sends real
requests against your running server.

**How it's wired up.** `app/__init__.py` registers a `flask_swagger_ui` blueprint that
mounts the UI at `/api/docs` and points it at `app/static/swagger.yaml`. The spec is a
hand-maintained Swagger 2.0 file rather than something generated from docstrings, so the
docs are a deliberate artifact and not a side effect of code comments.

The spec has two halves:

- **`paths`** — one entry per endpoint: HTTP method, tag, summary, description, path and
  body parameters, and every response code it can return. Token-protected routes carry a
  `security` key pointing at one of the two definitions (`customerBearer`,
  `mechanicBearer`), which is what puts the padlock on those operations in the UI.
- **`definitions`** — the reusable *shapes*. Payload definitions describe what goes in
  (`CreateCustomerPayload`, `UpdateCustomerPayload`, …), response definitions describe
  what comes back (`CustomerResponse`, `ServiceTicketResponse`, …). Defining a shape once
  and `$ref`-ing it means a change to the customer shape is a single edit, not four.

| | |
|---|---|
| Endpoints documented | 24 (across 15 paths) |
| Definitions | 21 |
| Responses with worked examples | 61 of 63 |

The two responses without an example are the `429` rate-limit responses on the login
routes — Flask-Limiter returns an HTML error page rather than JSON, so a JSON example
there would be inaccurate.

To authorize a protected request from the UI: run `POST /customers/login` (or
`/mechanics/login`), copy the `token` out of the response, click **Authorize** at the top
of the page, and enter `Bearer <token>`.

## Endpoints

Base URL: `http://127.0.0.1:5000`

The tables below are a quick reference; `/api/docs` is the authoritative, always-current
version with full request/response shapes.

Legend: 🔓 public · 🔑 customer token required · 🔧 mechanic token required

### Customers — `/customers`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/customers/` | 🔓 | Register a customer. Body: `name`, `email`, `phone`, `password`. |
| POST | `/customers/login` | 🔓 | Exchange email+password for a bearer token. **Rate-limited: 5/minute.** |
| GET | `/customers/` | 🔓 | Paginated list. Query: `page` (default 1), `per_page` (default 10, max 100). **Cached 60s, keyed by query string.** |
| GET | `/customers/<int:customer_id>` | 🔓 | Retrieve one customer. |
| GET | `/customers/my-tickets` | 🔑 | Service tickets belonging to the logged-in customer. |
| PUT | `/customers/` | 🔑 | Update *your own* record (partial). No id in URL — the token identifies you. Hashing is re-applied automatically if `password` is included. |
| DELETE | `/customers/` | 🔑 | Delete *your own* account. |

### Mechanics — `/mechanics`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/mechanics/` | 🔓 | Register a mechanic. Body: `name`, `email`, `phone`, `salary`, `password`. Public so the first mechanic can be created. |
| POST | `/mechanics/login` | 🔓 | Bearer token. **Rate-limited: 5/minute.** |
| GET | `/mechanics/` | 🔓 | List all mechanics. |
| GET | `/mechanics/most-tickets` | 🔓 | Mechanics ranked by ticket count (busiest first). Includes zero-count mechanics via `LEFT OUTER JOIN`. |
| PUT | `/mechanics/<int:mechanic_id>` | 🔧 | Update a mechanic (any mechanic may update any). |
| DELETE | `/mechanics/<int:mechanic_id>` | 🔧 | Delete a mechanic. |

### Inventory — `/inventory`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/inventory/` | 🔧 | Create a part. |
| GET | `/inventory/` | 🔓 | List all parts. |
| GET | `/inventory/<int:part_id>` | 🔓 | Retrieve one part. |
| PUT | `/inventory/<int:part_id>` | 🔧 | Update a part (partial). |
| DELETE | `/inventory/<int:part_id>` | 🔧 | Delete a part. Cascade removes any junction rows linking it to tickets; the tickets themselves survive. |

### Service tickets — `/service-tickets`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/service-tickets/` | 🔓 | Create a ticket for an existing customer. 404 if the customer doesn't exist. |
| GET | `/service-tickets/` | 🔓 | List all tickets, each with nested `mechanics` and `parts` (with quantities). |
| PUT | `/service-tickets/<int:ticket_id>/assign-mechanic/<int:mechanic_id>` | 🔓 | Add one mechanic to a ticket. |
| PUT | `/service-tickets/<int:ticket_id>/remove-mechanic/<int:mechanic_id>` | 🔓 | Remove one mechanic. |
| PUT | `/service-tickets/<int:ticket_id>/edit` | 🔓 | Bulk add/remove mechanics. Body: `{"add_ids": [...], "remove_ids": [...]}` (either key optional). |
| POST | `/service-tickets/<int:ticket_id>/add-part/<int:part_id>` | 🔓 | Add a part to a ticket. Optional body: `{"quantity": N}` (defaults to 1). If the part is already on the ticket, quantities **accumulate** instead of duplicating the row (enforced by the composite primary key on the junction). |

### Example request bodies

Register a customer:

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "phone": "555-0100",
  "password": "correct-horse-battery-staple"
}
```

Log in:

```json
{ "email": "ada@example.com", "password": "correct-horse-battery-staple" }
```

Create a service ticket (`service_date` must be `YYYY-MM-DD`):

```json
{
  "VIN": "1HGCM82633A004352",
  "service_date": "2026-08-15",
  "service_desc": "Replaced front brake pads and rotors",
  "customer_id": 1
}
```

Bulk-edit mechanics on a ticket:

```json
{ "add_ids": [2, 5], "remove_ids": [3] }
```

Add 3 brake pads to a ticket:

```json
{ "quantity": 3 }
```

### Notes on request/response bodies

- **`id` is dump-only** — it appears in responses but a client cannot set it.
- **`password` is load-only** — accepted on create/update, never included in any response.
- **`service_date`** must be an ISO date string (`YYYY-MM-DD`), not a datetime.
- Successful mutations echo the full resource back (including nested `mechanics` and
  `parts` on ticket responses), so the client rarely needs a follow-up `GET`.

## Rate limiting

Every route is protected by the Limiter, which uses `get_remote_address` (client IP)
as the bucket key and stores counters in-memory.

- **`POST /customers/login`** — `5/minute` explicit
- **`POST /mechanics/login`** — `5/minute` explicit
- **Every other endpoint** — `20/hour` and `100/day` defaults, applied **per endpoint,
  per IP**

Explicit limits *replace* the defaults (Flask-Limiter's `override_defaults=True` is
the default), so the two login endpoints have no daily/hourly ceiling — only the
5/minute rule. Every other endpoint gets the 20/hour and 100/day rules and nothing
else.

If you see `429 Too Many Requests` during rapid testing, wait ~60 seconds for the
window to slide, or restart the Flask server (in-memory storage resets on restart).

## Running the tests

```bash
python -m unittest discover -s tests -v
```

No server and no MySQL needed — the tests use Flask's test client to send requests
directly through the app, backed by SQLite.

**73 tests across four files**, one per blueprint:

| File | Tests | Covers |
|---|---|---|
| `tests/test_customers.py` | 17 | registration, login, pagination, profile update, deletion |
| `tests/test_mechanics.py` | 16 | registration, login, workload ranking, mechanic-only routes |
| `tests/test_service_tickets.py` | 23 | ticket creation, mechanic assignment, bulk edit, parts |
| `tests/test_inventory.py` | 17 | catalog CRUD, mechanic-only enforcement, cascade delete |

Every one of the 24 routes is exercised by at least one test.

**Negative tests.** 41 of the assertions target failure paths — 20 × `400`, 15 × `404`,
4 × `403`, 2 × `401`. These cover missing required fields, duplicate emails, wrong
passwords, absent and malformed tokens, customer tokens on mechanic-only routes, and
operations against IDs that don't exist.

**How the tests are structured.** `setUp` builds a fresh app and drops/recreates every
table before each test, so no test can be influenced by data another left behind. Each
file keeps small helpers at the top — `create_customer()`, `auth_header()` and friends —
so an individual test only states what makes it different. Because the protected routes
identify you from the JWT rather than the URL, `auth_header()` performs a real login and
returns `{'Authorization': 'Bearer <token>'}`.

Tests assert on effects, not just status codes: the delete tests follow up with a `GET`
and expect a `404`, and the partial-update tests assert that a field they *didn't* send
came back unchanged.

**`TestingConfig` differs from `DevelopmentConfig` in three ways**, all of which matter:

| Setting | Why |
|---|---|
| `SQLALCHEMY_DATABASE_URI = sqlite:///testing.db` | no MySQL needed; Flask puts the file in `instance/`, which is gitignored |
| `CACHE_TYPE = 'NullCache'` | `SimpleCache` would serve a cached `GET /customers/` from an earlier request and make tests fail on stale data |
| `RATELIMIT_ENABLED = False` | the suite makes far more requests than the 20/hour default limit allows, and would otherwise start returning `429` mid-run |

## Testing with Postman

Import `Mechanic_Shop_API.postman_collection.json` (**Import → File** in Postman).
It contains 60 requests across four folders (Customers, Mechanics, Inventory, Service
Tickets), covering every endpoint's happy path along with its error cases (missing
tokens, wrong role, duplicate email, invalid quantity, missing records, etc.) — 79
assertions in total.

**How to run it:**

1. Start the server (`python app.py`).
2. Open the collection in Postman.
3. Click **Run** → **Run Mechanic Shop API**.
4. Watch the results.

**How chained state works:** the create requests capture the new record's id (and
generated email) into collection variables that later requests consume. So the
service-ticket requests automatically target the customer, mechanic, and part
created earlier in the same run.

**Re-running:** unique columns like email and phone are suffixed with Postman's
`{{$timestamp}}` dynamic variable, so a re-run against the same database never
collides. 1 or 2 back-to-back runs work fine; a 3rd within 60 seconds trips the
login rate limits (predictable — restart the server or wait a minute).

**What each run leaves behind:** one customer, one mechanic, one service ticket, one
part. This is deliberate — the Inventory and Service Tickets folders need those to
exist. Harmless for a class-project cadence.

The collection's `baseUrl` variable defaults to `http://127.0.0.1:5000`. Change it in
one place if you run the server on a different host or port.

## Known limitations

- **`token_required` does not verify the `role` claim.** A mechanic's token would
  technically pass authentication on customer-only routes; the mechanic-id-as-customer-id
  mismatch usually causes a downstream 404, but this is a real gap.
  `@mechanic_token_required` *does* check the claim, so the reverse direction (a customer
  token on a mechanic route) is correctly rejected with a 403 — and is covered by tests.
- **Every `/service-tickets` route is unauthenticated.** Anyone who can reach the API can
  open tickets, reassign mechanics, and attach parts to any ticket, including tickets
  belonging to other customers. Customers and inventory both have auth; service tickets
  do not.
- **`POST /mechanics/` is public**, so anyone can create a mechanic account and thereby
  obtain the mechanic token needed to write to inventory. Deliberate for a class project
  (the first mechanic has to come from somewhere) but not something to ship.
- **Rate-limit counters are in-memory**, so they reset whenever the server restarts and
  are not shared across processes.

### Recently resolved

- `requirements.txt` was UTF-16 encoded and missing several packages the app imports,
  including `flask-swagger-ui` — a clean `pip install -r requirements.txt` failed at
  startup. Regenerated as UTF-8 with all 33 packages.
- `POST /customers/login` returned **200** on bad credentials instead of 401, and raised
  a **500** on a malformed body because it caught `KeyError` where marshmallow raises
  `ValidationError`. Both fixed; the route now mirrors `POST /mechanics/login`.
