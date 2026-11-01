# DineFlow - Premium QR-Based Multi-Restaurant Food Ordering Suite

**Live Production URL:** [https://cafeqr-p428.onrender.com](https://cafeqr-p428.onrender.com)  
**GitHub Repository:** [https://github.com/instagramredirectip/cafeqr](https://github.com/instagramredirectip/cafeqr)

DineFlow is an enterprise-grade, multi-tenant digital restaurant ordering platform built with **Python, Django, MySQL, Bootstrap 5, and JavaScript**. Designed with a warm luxury palette (Cream `#FDF3EC`, Coral `#F15B43`, Terracotta `#8C3025`, and Burgundy `#32150F`), it offers customers a frictionless contactless ordering experience and gives restaurant managers a live kitchen dashboard.

---

## Key Features

1. **Multi-Restaurant Architecture & Strict Multi-Tenant Isolation:**
   - Single shared database with row-level ownership relationships.
   - Dedicated public URL per venue: `/r/<restaurant-slug>/menu/`.
   - Separate menu categories, dishes, add-ons, pricing, tables, and orders.
   - Strict server-side permission checks preventing one restaurant from accessing another's orders or menu items.

2. **Customer Experience & Digital Menu:**
   - Mobile-first responsive UI with two-column layout on handheld devices.
   - Dietary indicators: Pure Veg (green square) and Non-Veg (crimson triangle).
   - Dynamic food customization modal (spice preference, toppings/add-ons checklist, special kitchen requests, and real-time price tallying).
   - Persistent shopping cart in `localStorage` isolated per restaurant slug.
   - Sticky mobile bottom cart summary bar.
   - Live order tracking screen with auto-polling (Pending → Accepted → Preparing → Ready → Completed).

3. **Core QR Code System:**
   - Restaurant-wide menu QR codes.
   - **Table-Specific QR Codes**: Embeds table number directly (e.g. `/r/saffron-sage/menu/?table=5`). Table number is auto-filled and locked on checkout.
   - Configurable `SITE_BASE_URL` ensuring QR codes work across mobile carrier 4G/5G networks.
   - Downloadable PNG images and a print-ready stand card layout (`/owner/qr/print/`) with the instruction *"Scan to View Menu & Order"*.

4. **Security & Financial Integrity:**
   - **Zero Client Trust:** All prices, add-on costs, taxes, and delivery fees are recomputed on the server using database records and `DecimalField` precision. Client attempts to tamper with prices are ignored.
   - Database transactions (`transaction.atomic`) guarantee atomicity during order generation.
   - Historical snapshot fields: `item_name` and `unit_price` are captured at order time, preserving historical billing accuracy even if menu prices change later.
   - Cryptographically random order numbers (e.g. `ORD-20261101-ABCD`) and UUID4 `access_token` for safe customer status lookup without sequential enumeration risks.

5. **Restaurant Owner Dashboard:**
   - Real-time KPI cards: Today's Orders, Today's Sales, Active Kitchen Orders, Menu Health.
   - Live background polling for incoming orders with visual alerts.
   - Complete Menu and Category Management (add/edit dishes, upload food photography, change prices, reorder, and instant 1-click availability toggling).
   - Order fulfillment manager (advance statuses, view customer phone and special requests).
   - Dining table generator and QR manager.

---

## Technology Stack

- **Backend:** Python 3.14+, Django 5.2 (Django ORM)
- **Database:** MySQL (Production) / SQLite3 (Immediate local dev fallback)
- **Database Driver:** PyMySQL (pure Python, native Windows compatibility)
- **Image Processing:** Pillow
- **QR Code Engine:** `qrcode` with PIL image generation
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap 5.3, Bootstrap Icons

---

## Directory Structure

```text
testprompt/
├── manage.py
├── requirements.txt
├── .env.example
├── .env
├── restaurant_platform/
│   ├── __init__.py          # PyMySQL installation hook
│   ├── settings.py          # Unified MySQL / SQLite dynamic engine
│   ├── urls.py              # Root router + static/media serving
│   ├── wsgi.py
│   └── asgi.py
├── ordering/
│   ├── models.py            # Restaurant, Staff, Tables, Categories, Food, Addons, Orders
│   ├── views_customer.py    # Public menu, food modal API, checkout, tracking
│   ├── views_owner.py       # Dashboard, order manager, menu editor, QR generator
│   ├── views_public.py      # Platform gateway
│   ├── decorators.py        # Restaurant staff permission verification
│   ├── context_processors.py
│   ├── urls.py
│   ├── tests.py             # 9 comprehensive automated tests
│   └── management/
│       └── commands/
│           └── seed_sample_data.py
├── static/
│   ├── css/theme.css        # DineFlow warm cream, coral, burgundy palette
│   └── js/cart.js           # Restaurant-isolated cart & checkout logic
├── templates/
│   ├── base.html
│   └── ordering/
│       ├── home.html
│       ├── customer_menu.html
│       ├── order_status.html
│       └── owner/
│           ├── base_owner.html
│           ├── login.html
│           ├── dashboard.html
│           ├── orders_list.html
│           ├── order_detail.html
│           ├── menu_list.html
│           ├── food_form.html
│           ├── categories.html
│           ├── qr_management.html
│           ├── print_qr.html
│           └── settings.html
└── media/                   # User-uploaded logos, food photos, and QR codes
```

---

## Quickstart & Local Setup

### 1. Activate Environment & Install Dependencies

```powershell
# Create & activate venv
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Copy `.env.example` to `.env`:

```ini
SECRET_KEY=your-secure-secret-key
DEBUG=True
ALLOWED_HOSTS=*
SITE_BASE_URL=http://127.0.0.1:8000

# To use SQLite for instant zero-config testing:
DB_ENGINE=sqlite3

# To use MySQL:
# DB_ENGINE=mysql
# DB_NAME=restaurant_db
# DB_USER=root
# DB_PASSWORD=your_mysql_password
# DB_HOST=127.0.0.1
# DB_PORT=3306
```

### 3. Run Migrations & Seed Sample Data

```powershell
python manage.py migrate
python manage.py seed_sample_data
```

### 4. Start the Development Server

```powershell
python manage.py runserver 0.0.0.0:8000
```

Open your browser at `http://127.0.0.1:8000`.

---

## Seeded Demo Accounts & Credentials

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin` | `AdminPass123!` | Django admin access (`/admin/`) |
| **Owner (Venue 1)** | `owner_saffron` | `OwnerPass123!` | Saffron & Sage Royal Kitchen (`/owner/dashboard/`) |
| **Owner (Venue 2)** | `owner_bella` | `OwnerPass123!` | Trattoria Bella Vista (`/owner/dashboard/`) |

### Demo URLs to Explore:
- **Platform Homepage:** `http://127.0.0.1:8000/`
- **Saffron & Sage Menu:** `http://127.0.0.1:8000/r/saffron-sage/menu/`
- **Table 5 Scanned Menu:** `http://127.0.0.1:8000/r/saffron-sage/menu/?table=5`
- **Bella Vista Menu:** `http://127.0.0.1:8000/r/bella-vista/menu/`
- **Owner Dashboard Login:** `http://127.0.0.1:8000/owner/login/`

---

## MySQL Setup Guide for Windows

To connect DineFlow to a local or production MySQL server:

1. Open MySQL Command Line Client or PowerShell:
   ```sql
   CREATE DATABASE restaurant_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'dineflow_user'@'localhost' IDENTIFIED BY 'StrongPassword123!';
   GRANT ALL PRIVILEGES ON restaurant_db.* TO 'dineflow_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. Update your `.env` file:
   ```ini
   DB_ENGINE=mysql
   DB_NAME=restaurant_db
   DB_USER=dineflow_user
   DB_PASSWORD=StrongPassword123!
   DB_HOST=127.0.0.1
   DB_PORT=3306
   ```

3. Run migrations:
   ```powershell
   python manage.py migrate
   python manage.py seed_sample_data
   ```

*Note: DineFlow uses `PyMySQL` pre-configured in `restaurant_platform/__init__.py`, meaning you do **not** need Microsoft Visual C++ Build Tools to compile `mysqlclient`.*

---

## Running Automated Tests

Run the test suite verifying access controls, price security, QR generation, and full order lifecycle:

```powershell
python manage.py test ordering
```

All 9 test cases will run and report `OK`.

---

## Production Deployment Checklist

1. **Security Settings:**
   - In `.env`, set `DEBUG=False`.
   - Set `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`.
   - Generate a strong `SECRET_KEY`.
   - Set `SITE_BASE_URL=https://yourdomain.com`.
   - Enable HTTPS redirection:
     ```python
     SECURE_SSL_REDIRECT = True
     SESSION_COOKIE_SECURE = True
     CSRF_COOKIE_SECURE = True
     ```

2. **Static & Media Collection:**
   ```powershell
   python manage.py collectstatic --noinput
   ```

3. **WSGI Server & Reverse Proxy:**
   - Use `gunicorn` (Linux) or `Waitress` (Windows) behind `Nginx` or `Caddy`.
   - Configure Nginx to serve `/static/` and `/media/` directly for maximum throughput.

4. **Database Backups:**
   - Regular automated dumps using `mysqldump`:
     ```powershell
     mysqldump -u root -p restaurant_db > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql
     ```
   - Store offsite in Cloud Storage (AWS S3, GCP Cloud Storage).

