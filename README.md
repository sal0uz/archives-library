# 📚 Archives Library

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Django](https://img.shields.io/badge/Django-4.2-green) ![MySQL](https://img.shields.io/badge/MySQL-8.0-orange) ![Scikit-learn](https://img.shields.io/badge/Scikit--learn-1.3-red) ![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)

> Digital library with ML-powered book recommendations — TF-IDF vectorization, cosine similarity, and a Precision@5 of **0.78**.

---

## ✨ Features

- 🔍 **ML Recommendation Engine** — TF-IDF vectorization + cosine similarity (min_similarity = 0.5), serialized via `.pkl`
- 📊 **Evaluated Performance** — Precision@5 = 0.78 · Recall@10 = 0.76 on a 500-book test catalog
- ⚡ **Optimized Backend** — Response time < 2s on 12 normalized MySQL tables with application-level ML cache
- 🔐 **Secure Authentication** — OWASP-compliant login/register with role-based access
- 🔎 **Multi-criteria Search** — Filter books by title, author, category, and more
- 🧩 **9 Functional Modules** — CRUD, auth, search, recommendations, reviews, quotes, community, profile, admin dashboard
- 🏃 **Agile Delivery** — 5 sprints, 3 simulated roles, end-to-end ownership

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Django 4.2 |
| Database | MySQL 8.0 (12 normalized tables) |
| ML Pipeline | Scikit-learn 1.3 (TF-IDF, cosine similarity, `.pkl`) |
| Frontend | Bootstrap 5.3, HTML5, CSS3 |
| Version Control | Git, Agile sprints |

---

## 📁 Project Structure

```
archives_library_v3_fixed/
└── library_updated/
    ├── archives/               # Main Django app
    │   ├── models.py           # Data models
    │   ├── views.py            # Business logic
    │   ├── urls.py             # URL routing
    │   ├── admin.py            # Admin configuration
    │   └── middleware.py       # Custom middleware
    ├── archives_library/       # Django project settings
    │   ├── settings.py
    │   └── urls.py
    ├── templates/              # HTML templates
    │   └── archives/
    ├── static/                 # Static files (CSS, JS, images)
    ├── media/                  # Uploaded media files
    ├── recommendation.ipynb    # ML pipeline notebook
    ├── requirements.txt        # Python dependencies
    ├── setup_database.sql      # Database setup script
    └── manage.py
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/sal0uz/archives-library.git
cd archives-library/library_updated

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up the database
mysql -u root -p < setup_database.sql

# 4. Configure your database credentials in settings.py
# DATABASES -> NAME, USER, PASSWORD

# 5. Apply migrations
python manage.py migrate

# 6. Create admin user
python manage.py create_admin

# 7. Run the server
python manage.py runserver
```

Then open **http://127.0.0.1:8000** in your browser.

### Windows (quick setup)

```bash
setup_windows.bat
```

---

## 🤖 ML Recommendation Pipeline

The recommendation engine is built with Scikit-learn and works as follows:

1. **Vectorization** — Book descriptions are transformed using TF-IDF
2. **Similarity** — Cosine similarity computed between all book pairs
3. **Filtering** — Only pairs with similarity ≥ 0.5 are kept
4. **Serialization** — The similarity matrix is exported as a `.pkl` file and cached at application level for fast retrieval

**Performance metrics on 500-book test catalog:**
- Precision@5 = **0.78**
- Recall@10 = **0.76**

---

## 📸 Modules Overview

| Module | Description |
|---|---|
| 🏠 Home | Landing page with featured books |
| 📖 Book List | Browse and search the full catalog |
| 🔍 Recommendations | Personalized ML-based suggestions |
| 👤 Profile | User profile and reading history |
| 📚 My Library | Saved and favorite books |
| ✍️ Reviews | Community book reviews |
| 💬 Quotes | Favorite quotes from books |
| 🌍 Community | Social reading features |
| ⚙️ Admin Dashboard | Full CRUD management panel |

---

## 🔐 Security

- OWASP-compliant authentication
- Role-based access control (Admin / User)
- Protected routes and session management

---

## 👩‍💻 Author

**Salma Khatibi** — 3rd year Engineering student, EMSI Casablanca  
📧 khatibisalma05@gmail.com  
🔗 [linkedin.com/in/salma-khatibi-147768383](https://linkedin.com/in/salma-khatibi-147768383)

---

## 📄 License

This project was developed as part of an academic project at EMSI Casablanca — 2026.
