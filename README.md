# E-Commerce Backend

A minimal, production-conscious REST API backend with subcategories, brands, featured products, discounts, and limited-time offers.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | Django 5.0 |
| REST API | Django REST Framework 3.15 |
| Authentication | SimpleJWT (JWT access + refresh tokens) |
| Database | PostgreSQL 16 |
| Container runtime | Docker + Docker Compose |
| Application server | Gunicorn |
| Image handling | Pillow |
| Filtering | django-filter |
| CORS | django-cors-headers |

---

## Project Structure

```
ecommerce_backend/
├── manage.py
├── requirements.txt
├── Dockerfile
├── compose.yaml
├── .env.example
├── config/           # Django settings, URL root, WSGI/ASGI
└── apps/
    ├── accounts/     # Custom user model, JWT auth, role-based permissions
    ├── products/     # Category (+ subcategories), Brand, Product,
    │                 # Discount/Offers, central pricing service
    ├── cart/         # Authenticated customer cart (discount-aware)
    └── orders/       # Order placement with full discount snapshots
```

---

## Data Model Relationships

```
Category (root)
  └── Category (subcategory, max 1 level deep)
        └── Product ──── Brand
                    └──── Discount (time-bounded, one active at a time per product)
```

---

## Features Added (v2)

### Subcategories
- `Category.parent` self-FK, max two levels enforced at model + serializer level.
- Root categories expose `children` in the public API.
- `?category=slug` filter matches products in that root category **and** all its subcategories.
- `?subcategory=slug` targets a specific subcategory directly.

### Brands
- `Brand` model with name, slug, logo, description, active status.
- `Product.brand` FK.
- Public browse + search; admin-only create/edit/delete.

### Featured Products
- `Product.is_featured` flag + `Product.featured_order` ordering field.
- Dedicated endpoint returns only active, in-stock featured products.

### Discounts & Limited-Time Offers
- `Discount` model: PERCENTAGE or FIXED type, time-bounded window (`starts_at` / `ends_at`).
- Only one active, overlapping discount per product at any time (enforced in `model.clean()`).
- Future discounts do not apply until `starts_at`; expired ones stop automatically.
- Reused as "offers" in the public API — no separate pricing system.

### Central Pricing Service (`apps/products/pricing.py`)
- Single function `get_price_info(product)` used by all cart, order, and product serializers.
- Returns: `original_price`, `discount_type`, `discount_value`, `discount_amount`, `final_price`, `is_discounted`, `offer_title`, `offer_description`, `offer_start`, `offer_end`.
- Client-submitted prices are never trusted anywhere.

### Cart (updated)
- Each cart item now shows `original_price`, `discount_type`, `discount_amount`, `final_unit_price`, `subtotal` (at final price).
- Cart `total` is the sum of discounted line subtotals.

### Orders (updated)
- `OrderItem` now snapshots: `original_unit_price`, `discount_type`, `discount_value`, `discount_amount`, `unit_price` (final).
- Historical orders are immutable; price/discount changes never affect them.

---

## Environment Setup

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS
```

---

## Docker Requirements

- Docker Engine 24+ or Docker Desktop
- Docker Compose v2 (`docker compose` — no hyphen)

---

## Starting the Application

```bash
docker compose up --build -d
```

API: `http://localhost:8742`

---

## Running Migrations

```bash
docker compose exec web python manage.py migrate
```

> Run migrations **explicitly** as a deployment step, not automatically on startup.

---

## Seeding Default Admin Accounts (development only)

```bash
docker compose exec web python manage.py seed_admins
```

| Username | Password | Role | Django Admin |
|---|---|---|---|
| `admin` | `admin` | Admin (superuser) | ✅ |
| `staff` | `123456` | Staff | ✅ |

> ⚠ Change passwords before any shared/production use.

---

## Creating a Superuser

```bash
docker compose exec web python manage.py createsuperuser
```

---

## Django Admin

`http://localhost:8742/admin/`

Managed from Admin:
- Users (roles, is_staff, is_superuser)
- Categories + Subcategories (inline)
- Brands
- Products (with discount inline, featured flag)
- Discounts (standalone, with date hierarchy)
- Orders (with item inline, read-only financials)

---

## JWT Authentication

### Obtain tokens
```
POST /api/v1/accounts/token/
{ "username": "admin", "password": "admin" }
```

### Use access token
```
Authorization: Bearer <access_token>
```

### Refresh
```
POST /api/v1/accounts/token/refresh/
{ "refresh": "<refresh_token>" }
```

> Store tokens in memory or HttpOnly cookies. Avoid `localStorage` for long-lived tokens.

---

## API Endpoints

### Accounts

| Method | Endpoint | Auth |
|---|---|---|
| POST | `/api/v1/accounts/register/` | Public |
| POST | `/api/v1/accounts/login/` | Public |
| POST | `/api/v1/accounts/logout/` | JWT |
| GET/PATCH | `/api/v1/accounts/me/` | JWT |
| POST | `/api/v1/accounts/token/` | Public |
| POST | `/api/v1/accounts/token/refresh/` | Public |

### Categories

| Method | Endpoint | Auth |
|---|---|---|
| GET | `/api/v1/categories/` | Public |
| GET | `/api/v1/categories/<slug>/` | Public |
| GET/POST | `/api/v1/categories/manage/` | Admin |
| GET/PUT/PATCH/DELETE | `/api/v1/categories/manage/<slug>/` | Admin |

### Brands

| Method | Endpoint | Auth |
|---|---|---|
| GET | `/api/v1/brands/` | Public |
| GET | `/api/v1/brands/<slug>/` | Public |
| GET | `/api/v1/brands/<slug>/products/` | Public |
| GET/POST | `/api/v1/brands/manage/` | Admin |
| GET/PUT/PATCH/DELETE | `/api/v1/brands/manage/<slug>/` | Admin |

### Products

| Method | Endpoint | Auth |
|---|---|---|
| GET | `/api/v1/products/` | Public |
| GET | `/api/v1/products/featured/` | Public |
| GET | `/api/v1/products/<slug>/` | Public |
| GET/POST | `/api/v1/products/manage/` | Staff/Admin |
| GET/PUT/PATCH/DELETE | `/api/v1/products/manage/<slug>/` | Staff/Admin |

#### Product Query Parameters

| Parameter | Example | Description |
|---|---|---|
| `search` | `?search=phone` | Search name, description, brand, category |
| `category` | `?category=electronics` | Root or sub category slug (includes children) |
| `subcategory` | `?subcategory=smartphones` | Exact subcategory slug |
| `brand` | `?brand=samsung` | Brand slug |
| `is_featured` | `?is_featured=true` | Featured products only |
| `discounted` | `?discounted=true` | Currently discounted only |
| `min_price` | `?min_price=100` | Minimum price |
| `max_price` | `?max_price=500` | Maximum price |
| `ordering` | `?ordering=price` or `?ordering=-created_at` | Sort field |
| `page` | `?page=2` | Page number |

### Offers (Limited-Time)

| Method | Endpoint | Auth |
|---|---|---|
| GET | `/api/v1/offers/` | Public — currently active offers |
| GET | `/api/v1/offers/upcoming/` | Public — upcoming (not yet started) |

### Discounts (Admin management)

| Method | Endpoint | Auth |
|---|---|---|
| GET/POST | `/api/v1/discounts/` | Admin |
| GET/PUT/PATCH/DELETE | `/api/v1/discounts/<id>/` | Admin |

#### Discount example payload

```json
{
  "product": 1,
  "title": "Weekend Sale",
  "description": "20% off this weekend only",
  "discount_type": "percentage",
  "value": "20.00",
  "starts_at": "2026-11-01T00:00:00Z",
  "ends_at": "2026-11-02T23:59:59Z",
  "is_active": true
}
```

Fixed amount example:
```json
{
  "discount_type": "fixed",
  "value": "150.00"
}
```

### Cart

| Method | Endpoint | Auth |
|---|---|---|
| GET | `/api/v1/cart/` | Customer JWT |
| POST | `/api/v1/cart/items/` | Customer JWT |
| PATCH | `/api/v1/cart/items/<id>/` | Customer JWT |
| DELETE | `/api/v1/cart/items/<id>/` | Customer JWT |

### Orders

| Method | Endpoint | Auth |
|---|---|---|
| POST | `/api/v1/orders/` | Customer JWT |
| GET | `/api/v1/orders/` | JWT (own for customer, all for staff/admin) |
| GET | `/api/v1/orders/<order_number>/` | JWT |
| POST | `/api/v1/orders/<order_number>/cancel/` | JWT |
| PATCH | `/api/v1/orders/<order_number>/status/` | Staff/Admin JWT |

---

## User Roles and Permissions

| Action | Customer | Staff | Admin |
|---|---|---|---|
| Browse products/categories/brands/offers | ✅ | ✅ | ✅ |
| Manage own cart | ✅ | ❌ | ❌ |
| Place orders | ✅ | ❌ | ❌ |
| View own orders | ✅ | ❌ | ❌ |
| View all orders | ❌ | ✅ | ✅ |
| Manage products/stock | ❌ | ✅ | ✅ |
| Update order status | ❌ | ✅ | ✅ |
| Manage categories | ❌ | ❌ | ✅ |
| Manage brands | ❌ | ❌ | ✅ |
| Manage discounts/offers | ❌ | ❌ | ✅ |
| Change payment status | ❌ | ❌ | ✅ |
| Assign user roles | ❌ | ❌ | ✅ |
| Django Admin access | ❌ | ✅ (if is_staff) | ✅ |

---

## Routine Operations

```bash
# View logs
docker compose logs -f web

# Stop (data preserved)
docker compose down

# Restart
docker compose up -d

# Django shell
docker compose exec web python manage.py shell
```

> ⚠ Never use `docker compose down -v` as a routine command — it deletes named volumes and your database.

---

## Database Backup

```bash
# Backup
docker compose exec db pg_dump -U ${DB_USER} ${DB_NAME} > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
cat backup.sql | docker compose exec -T db psql -U ${DB_USER} ${DB_NAME}
```
