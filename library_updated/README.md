# 📚 Archives Library

A full-featured digital library platform built with **Django 4.2**, **MySQL (WAMP)**, and a dark gold-and-parchment UI. Users can upload, download, rate, review, and discover books. Admins manage everything from a dedicated panel.

---

## ✨ Features

### User Side
- 🔐 Register / Login with real credentials stored in MySQL
- 🏠 Home with Trending / Popular / Latest books (real data)
- 🔍 Full-text search across titles, authors, categories
- 📖 Book detail page: metadata, source, description, download
- ⬇️ Real PDF/EPUB download directly to device
- ⭐ Real star ratings — calculated live from all user votes
- 💬 Reviews & Quotes per book
- ❤️ Like books → saved to "My Library → Favorites"
- 📚 My Library: Favorites / Downloaded / Uploaded tabs (all real)
- 🧑 Profile page with avatar upload
- ⚙️ Settings (name, email, bio, password, avatar)
- 👥 Community posts with likes and comments
- 🤖 AI recommendation engine (same category + same authors)

### Admin Side (login: admin / admin123)
- 📊 Dashboard: real-time user count, online users, downloads, reads
- 📚 Add books with cover image + PDF upload + author + category
- ✅ Approve / reject user-uploaded books
- 🗂️ Add / delete categories with emoji icons
- ✒️ Add / delete authors with photo
- 👥 Ban / unban / delete users (with duration choice)
- 🚫 Remove inappropriate reviews + auto-notify user
- 🔥 Mark books as Trending

---

## 🖥️ Requirements

| Software | Version | Download |
|---|---|---|
| Python | 3.10+ | https://python.org/downloads |
| WAMP Server | 3.3+ | https://wampserver.com |
| pip packages | see requirements.txt | (auto-installed) |

---

## 🚀 Installation (Windows + WAMP)

### Step 1 — Install & Start WAMP

1. Download and install **WampServer** from https://wampserver.com
2. Start WAMP. Wait until the tray icon turns **green**.

---

### Step 2 — Create the MySQL Database

**Option A — phpMyAdmin (easiest):**
1. Open http://localhost/phpmyadmin in your browser
2. Log in (default: user `root`, password empty)
3. Click **"New"** in the left sidebar
4. Database name: `archives_library`
5. Collation: `utf8mb4_unicode_ci`
6. Click **"Create"**

**Option B — SQL tab in phpMyAdmin:**
1. Click the **SQL** tab
2. Paste and run the contents of `setup_database.sql`

---

### Step 3 — Install Python dependencies

Open **Command Prompt** inside the project folder:

```bat
cd C:\path\to\archives_library

:: Create virtual environment
python -m venv venv

:: Activate it
venv\Scripts\activate

:: Install packages
pip install -r requirements.txt
```

> 💡 If `mysqlclient` fails to install, try:
> ```bat
> pip install mysqlclient --only-binary :all:
> ```
> Or download the wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#mysqlclient

---

### Step 4 — Configure Database (if needed)

Open `archives_library/settings.py` and verify:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'archives_library',
        'USER': 'root',
        'PASSWORD': '',       # ← your WAMP MySQL root password (default: empty)
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

---

### Step 5 — Run Migrations (creates all tables)

```bat
python manage.py makemigrations archives
python manage.py migrate
```

This creates all 15+ tables in your `archives_library` MySQL database automatically.

---

### Step 6 — Create Admin User

```bat
python manage.py create_admin
```

This creates:
- **Username:** `admin`
- **Password:** `admin123`

---

### Step 7 — Start the Server

```bat
python manage.py runserver
```

Open your browser: **http://127.0.0.1:8000**

---

### ⚡ Quick Setup (all-in-one)

Alternatively, just double-click **`setup_windows.bat`** — it does Steps 3–6 automatically.

---

## 📂 Project Structure

```
archives_library/
│
├── archives/                    ← Main Django app
│   ├── models.py                ← All database models
│   ├── views.py                 ← All page & API views
│   ├── urls.py                  ← URL routing
│   ├── admin.py                 ← Django admin registration
│   ├── context_processors.py   ← Global template variables
│   ├── middleware.py            ← Online user tracking
│   └── management/
│       └── commands/
│           └── create_admin.py ← python manage.py create_admin
│
├── archives_library/            ← Django project config
│   ├── settings.py              ← Database, media, auth config
│   ├── urls.py                  ← Root URL dispatcher
│   └── wsgi.py
│
├── templates/
│   └── archives/
│       ├── base.html            ← Navbar, modals, JS framework
│       ├── auth.html            ← Login / Sign up page
│       ├── home.html            ← Main library page
│       ├── book_detail.html     ← Book page with download/rate/review
│       ├── book_list.html       ← Search results / category filter
│       ├── my_library.html      ← Favorites / Downloads / Uploads
│       ├── profile.html         ← User profile
│       ├── settings.html        ← Account settings
│       ├── community.html       ← Community posts
│       ├── quotes.html          ← All book quotes
│       ├── reviews_page.html    ← All book reviews
│       ├── authors.html         ← Authors directory
│       ├── categories.html      ← Categories grid
│       ├── partials/
│       │   └── book_card.html   ← Reusable book card
│       └── admin/
│           ├── base_admin.html  ← Admin layout
│           ├── dashboard.html   ← Stats + recent activity
│           ├── books.html       ← Add/approve/delete books
│           ├── categories.html  ← Add/delete categories
│           ├── authors.html     ← Add/delete authors
│           ├── users.html       ← Ban/unban/delete users
│           └── reviews.html     ← Moderate reviews
│
├── media/                       ← Uploaded files (auto-created)
│   ├── covers/                  ← Book cover images
│   ├── books/                   ← PDF/EPUB files
│   └── avatars/                 ← User profile photos
│       authors/                 ← Author photos
│
├── static/                      ← CSS/JS static files
├── requirements.txt
├── setup_database.sql
├── setup_windows.bat
└── manage.py
```

---

## 🗄️ Database Tables (MySQL / phpMyAdmin)

After `python manage.py migrate`, these tables appear in phpMyAdmin:

| Table | Description |
|---|---|
| `lib_user` | All registered users + admin |
| `lib_book` | Books with cover, PDF path, metadata |
| `lib_author` | Authors with photo |
| `lib_category` | Book categories with emoji |
| `lib_rating` | User ratings (1-5★) — used for real avg calculation |
| `lib_review` | User reviews/comments with moderation status |
| `lib_quote` | User-submitted quotes |
| `lib_like` | Book likes (user ↔ book) |
| `lib_download` | Download log (user ↔ book) |
| `lib_readlog` | Read/view log |
| `lib_communitypost` | Community discussion posts |
| `lib_postcomment` | Comments on community posts |
| `lib_sitestats` | Daily visitor/search counters |

---

## 👤 User Roles

| Role | Access |
|---|---|
| **Guest** | Auth page only |
| **User** | Full library — browse, download, rate, review, upload |
| **Admin** (`is_staff=True` OR `is_superuser=True`) | Admin panel — manage books, users, reviews |

---

## 🔧 Common Issues

**`mysqlclient` install error on Windows:**
```bat
pip install mysqlclient --only-binary :all:
```
Or install MySQL Connector: https://dev.mysql.com/downloads/connector/python/

**"Access denied for user root":**
→ Check your WAMP MySQL password in phpMyAdmin, update `settings.py`

**"Table doesn't exist" error:**
```bat
python manage.py migrate
```

**Port 8000 already in use:**
```bat
python manage.py runserver 8080
```
Then open http://127.0.0.1:8080

**Media files not loading:**
Make sure DEBUG = True in settings.py (it is by default)

---

## 🌐 Access URLs

| URL | Description |
|---|---|
| http://127.0.0.1:8000/ | Login / Register page |
| http://127.0.0.1:8000/home/ | Main library |
| http://127.0.0.1:8000/admin-panel/ | Admin dashboard |
| http://127.0.0.1:8000/django-admin/ | Django built-in admin |
| http://localhost/phpmyadmin | phpMyAdmin (via WAMP) |

---

## 📝 First Steps After Setup

1. **Login as admin** (admin / admin123)
2. **Add categories** → Admin Panel → Categories
3. **Add authors** → Admin Panel → Authors (with photo)
4. **Add books** → Admin Panel → Books (with cover + PDF)
5. **Approve books** and mark some as **Trending**
6. Register a **normal user** to test the user experience

---

*Built with Django 4.2 · MySQL via WAMP · Pillow for images · Pure HTML/CSS/JS frontend*
