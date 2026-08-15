# Mechanic Shop API

A Flask REST API for a mechanic shop, built with the application factory pattern and
organized into blueprints by resource. Customers book service tickets, and mechanics are
assigned to those tickets through a many-to-many relationship.

## Tech stack

- **Flask** — application factory (`create_app`) with one blueprint per resource
- **Flask-SQLAlchemy** — ORM models using the SQLAlchemy 2.0 `Mapped` / `mapped_column` style
- **Flask-Marshmallow / marshmallow-sqlalchemy** — schemas auto-generated from the models
- **MySQL** — via `mysql-connector-python`

## Project structure

```
mechanic_shop_api/
├── app.py                  # entry point: builds the app, creates tables, runs the server
├── config.py               # config classes, reads DB settings from .env
├── requirements.txt
├── Mechanic_Shop_API.postman_collection.json
└── app/
    ├── __init__.py         # create_app(): init extensions, register blueprints
    ├── extensions.py       # Marshmallow instance
    ├── models.py           # Customer, Mechanic, Service_Ticket, service_mechanics
    └── blueprints/
        ├── customers/      # __init__.py, routes.py, schemas.py
        ├── mechanics/
        └── service_tickets/
```

Each blueprint folder follows the same pattern: `__init__.py` creates the `Blueprint` and
then imports `routes` at the bottom, `routes.py` defines the endpoints, and `schemas.py`
defines the Marshmallow schemas used to serialize and deserialize that resource.

## Data model

| Model | Table | Notes |
|---|---|---|
| `Customer` | `customers` | unique `email` and `phone`; has many service tickets |
| `Mechanic` | `mechanics` | unique `email`; has many service tickets |
| `Service_Ticket` | `service_tickets` | belongs to one customer; has many mechanics |
| — | `service_mechanics` | junction table joining tickets and mechanics |

The many-to-many is exposed as relationship attributes on both sides — `ticket.mechanics`
and `mechanic.service_tickets` — so assigning a mechanic is just a list `append`.

## Setup

**1. Clone and create a virtual environment**

```bash
python -m venv venv
```

Activate it — on Windows PowerShell:

```bash
venv\Scripts\Activate.ps1
```

On macOS/Linux:

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

**4. Create a `.env` file** — see the section below.

**5. Run the server**

```bash
python app.py
```

`app.py` calls `db.create_all()` inside an app context on startup, so the tables are
created automatically the first time you run it. The API is served at
`http://127.0.0.1:5000`.

## The `.env` file

`.env` holds the database credentials and is **not committed to the repository** — it's
listed in `.gitignore` so passwords stay out of version control. You must create it
yourself in the project root before the app will start.

```
DB_PASS=your_mysql_root_password
DB_NAME=mechanic_shop_db
DB_HOST=localhost
```

`config.py` loads these with `python-dotenv` and assembles the connection string:

```
mysql+mysqlconnector://root:{DB_PASS}@localhost/{DB_NAME}
```

Without `.env`, the values come back as `None` and the connection fails.

> Note: `db.create_all()` only creates tables that don't already exist — it never alters
> one. If you change a model after the tables exist, drop the affected table and restart
> so it gets rebuilt.

## Endpoints

Base URL: `http://127.0.0.1:5000`

### Customers — `/customers`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/customers/` | Create a customer. 400 if the email is already in use. |
| GET | `/customers/` | Retrieve all customers. |
| GET | `/customers/<int:customer_id>` | Retrieve one customer. 404 if not found. |
| PUT | `/customers/<int:customer_id>` | Update a customer. Partial — send only the fields you want changed. |
| DELETE | `/customers/<int:customer_id>` | Delete a customer. 404 if not found. |

### Mechanics — `/mechanics`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/mechanics/` | Create a mechanic. 400 if the email is already in use. |
| GET | `/mechanics/` | Retrieve all mechanics. |
| PUT | `/mechanics/<int:mechanic_id>` | Update a mechanic. Partial. 404 if not found. |
| DELETE | `/mechanics/<int:mechanic_id>` | Delete a mechanic. 404 if not found. |

### Service tickets — `/service-tickets`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/service-tickets/` | Create a ticket for an existing customer. 404 if the customer doesn't exist. |
| GET | `/service-tickets/` | Retrieve all tickets, each with its assigned mechanics nested. |
| PUT | `/service-tickets/<int:ticket_id>/assign-mechanic/<int:mechanic_id>` | Assign a mechanic to a ticket. No body needed. 400 if already assigned. |
| PUT | `/service-tickets/<int:ticket_id>/remove-mechanic/<int:mechanic_id>` | Remove a mechanic from a ticket. 400 if not assigned. |

### Example request bodies

Create a customer:

```json
{
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "555-0100"
}
```

Create a mechanic:

```json
{
    "name": "Grace Hopper",
    "email": "grace@example.com",
    "phone": "555-0200",
    "salary": 60000
}
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

### A note on request bodies

Schemas reject unknown fields rather than ignoring them, so a typo'd key returns a 400
with a message like `{"nmae": ["Unknown field."]}`. `id` is dump-only — it appears in
responses but cannot be set from a request body.

## Testing with Postman

Import `Mechanic_Shop_API.postman_collection.json` into Postman
(**Import → File**). It contains 26 requests across three folders, covering every
endpoint along with its error cases (duplicate email, missing required field, missing
record, double assignment).

Start the server, then run the whole collection with the Collection Runner, or send
requests individually. The create requests save the new record's `id` into a collection
variable, so the service ticket requests automatically target the customer and mechanic
created earlier — run the collection top to bottom and it wires itself together. Each
request also asserts its expected status code in the **Tests** tab.

The collection defines a `baseUrl` variable set to `http://127.0.0.1:5000`; change it in
one place if you run the server on a different host or port.
