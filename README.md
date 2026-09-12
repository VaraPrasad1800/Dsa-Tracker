# 🧠 DSA Tracker

A **production-quality, self-hosted DSA (Data Structures & Algorithms) practice tracker** built for technical interview preparation. It combines a curated problem bank, spaced-repetition review (Leitner 5-box system), behavioral analytics with Redis caching, automated reminders, and a deterministic rule-based study plan generator.

> **TL;DR** — Track every problem you solve, review them on an optimal schedule, measure your weaknesses, and get an auto-generated day-by-day plan to interview readiness.

---

## ✨ Key Features

Built across 5 functional phases, each a complete, production-tested module.

### Phase 1 — Problem Bank & Tracking (Core Foundation)
- **Curated Problem Bank** — filter by difficulty (Easy / Medium / Hard), topic tags (Array, DP, Graphs, Stack, etc.), companies (Google, Meta, Amazon, Microsoft, Apple, …), and status.
- **CSV Importer** — `python manage.py import_dsa_problems --csv=path/to/problems.csv` with pipe‑separated tag/company parsing and idempotent slug upsert. Ships with `data/sample_problems.csv`.
- **Company-Specific Lists** — browse problems asked by each company (Thirty Days / Three Months / All periods), with frequency & acceptance rates.
- **Problem Detail Modal** — view problem description, your notes, and full code solutions.
- **Keyboard Shortcuts** — `S` mark solved, `R` mark revisit, `?` shortcuts help, `Esc` close modals.
- **User Isolation** — complete per‑user data isolation with instant multi‑user switching (`demo_user` vs `test_user`).

### Phase 2 — Spaced Repetition (Leitner 5-Box Engine)
A scientifically-backed review schedule so you never forget a problem you already solved.

| Box | Review Interval | Meaning |
|-----|----------------|---------|
| 1 | every **1 day** | Freshly learned |
| 2 | every **3 days** | Practicing |
| 3 | every **7 days** | Building recall |
| 4 | every **14 days** | Strengthening |
| 5 | every **30 days** (capped) | **Mastered** |

- **Progression Logic** — Correctly **Solving** a card promotes it to the next box (`current_box += 1`) and schedules the next review per the box interval. Marking **Needs Revisit** resets the card to Box 1 for review tomorrow.
- **Review History** — full audit trail of every box transition (`ReviewHistory` model).
- **Today's Review Page** — a distraction-free flashcard interface with a review progress bar and a Leitner box visualization.

### Phase 3 — Analytics Dashboard
- **Activity Heatmap** — 52‑week, GitHub‑style annual heatmap with daily solve counts and tooltips.
- **Topic Mastery & Strength** — visual mastery bars highlighting weak topics (<50% solved) with one‑click practice filters.
- **Difficulty Breakdown** — donut chart tracking Easy / Medium / Hard distribution.
- **Streak Tracker** — current streak (🔥), all‑time longest streak (🏆), and last solved date.
- **Placement Readiness** — a quantified readiness score with a band (Not Ready → Placement Ready) and a recommended next difficulty.
- **Redis Caching** — cached with a 6‑hour TTL and invalidated automatically on every progress update.

### Phase 4 — Reminders & Scheduled Tasks
- **Celery & Celery Beat**:
  - `send_daily_review_digest` — runs at 9:00 AM UTC, caches the daily review digest, and notifies the user.
  - `refresh_user_analytics` — runs at 12:00 PM UTC to refresh aggregations.
- **Manual Task Runner** — `python manage.py run_daily_tasks` triggers tasks immediately without daemon overhead.
- **In‑App Reminder Banner** — a top notification banner alerting users when review cards are due.

### Phase 5 — Rule-Based Study Plan Generator
A fully **deterministic heuristics engine** that plans your entire preparation:

- **30% Slots** — spaced-repetition backlog (Box 1–2 + Needs Revisit).
- **40% Slots** — weak topics (<50% solved, sorted ascending).
- **20% Slots** — Medium‑difficulty balanced practice.
- **10% Slots** — Hard push, focused in the final week.
- **Dynamic Rules** — momentum builder (Day 1 starts with Easy problems when your streak is 0), crunch-time adjustments, and Box 1 backlog clearing.
- **Day-by-Day Timeline** — calendar cards with explicit heuristic reasons ("Weak in DP", "Clear Box 1 backlog", "Hard push").
- **Readiness Score** — quantified interview readiness based on topic coverage and plan completion.

### ✨ Everything else
- **Full Authentication** — JWT‑based auth with signup, login, **email verification**, **forgot / reset password**, and refresh tokens. Email via SendGrid (console backend fallback for local dev).
- **Scraped Solutions** — server‑side solution scraper (`leetcode.ca`) fetches problem statements, explanations, multi‑language code, and time/space complexity for any LeetCode problem (never proxied to clients).
- **Bookmarks** — save problems to review later.
- **Export** — one‑click export of your full progress.

---

## 🛠️ Tech Stack

**Backend**
- Python 3.10+
- Django 4.2 (LTS) *+ Django REST Framework*
- Celery 5.6 + Celery Beat (task queue & scheduling)
- Redis 8.1 (cache + broker)
- PostgreSQL (with **SQLite fallback** for local dev)
- JWT auth, django-filter, SendGrid email

**Frontend**
- React 19
- Vite 8
- Tailwind CSS
- Recharts (charts)
- TanStack Query (React Query)
- React Router 7, Framer Motion, Lucide React
- Axios (HTTP client)

**DevOps**
- Docker & Docker Compose
- Nginx (frontend container)
- Oxlint (frontend linting)

---

## 📁 Project Structure

```
Dsa Tracker/
├── backend/                    # Django REST API
│   ├── core/                   # Project config (settings, celery, urls)
│   ├── data/                   # sample_problems.csv
│   ├── tracker/                # Main app
│   │   ├── services/           # Business logic (leitner, study_plan, analytics, ...)
│   │   ├── management/commands/  # import_dsa_problems, seed_data, run_daily_tasks, ...
│   │   ├── migrations/
│   │   ├── tests/              # pytest + Django TestCase suites
│   │   ├── models.py           # Problem, Tag, Company, UserProgress, StudyPlan, ...
│   │   ├── views.py, urls.py, serializers.py, scraper.py
│   │   └── tasks.py            # Celery tasks
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── components/         # UI components (problems, analytics, study_plan, ...)
│   │   ├── pages/              # Route pages (Problems, Review, Analytics, Auth, ...)
│   │   ├── context/            # Auth, Theme, Tag providers
│   │   ├── api/client.js       # Axios client
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml          # Full-stack orchestration
├── start.ps1                   # One-click local dev launcher (Windows)
└── README.md
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- **Python 3.10+** & pip
- **Node.js 18+** & npm
- Redis (optional — falls back to in-memory cache) & PostgreSQL (optional — falls back to SQLite)

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create a virtual environment (once)
python -m venv venv

# Activate it
.\venv\Scripts\activate      # Windows PowerShell
# source venv/bin/activate   # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Seed the database: ~160 curated problems + demo users + realistic review data
python manage.py seed_data

# Start the Django development server
python manage.py runserver 8000
```

### 2. Frontend Setup

```bash
# In a second terminal
cd frontend

# Install dependencies
npm install

# Start the Vite dev server (proxies /api to the backend)
npm run dev
```

Open your browser at **`http://localhost:5173`**.

#### Windows one-click launcher
Run `start.ps1` from the project root to launch both servers at once (backend on `:8001`, frontend on `:5173`, with `/api` proxied to `:8001`).

---

## 🐳 Running with Docker Compose

Spin up the entire production-like environment — PostgreSQL, Redis, Django Web, Celery Worker, Celery Beat, and the Frontend — with one command:

```bash
docker-compose up --build
```

Services that come up:

| Service | Container | Purpose |
|---------|-----------|---------|
| `db` | `dsa_postgres` | PostgreSQL 15 database |
| `redis` | `dsa_redis` | Redis 7 (cache + broker) |
| `backend` | `dsa_backend` | Django runserver on `:8000` (migrate + seed on boot) |
| `celery_worker` | `dsa_celery_worker` | Async task worker |
| `celery_beat` | `dsa_celery_beat` | Scheduled tasks |
| `frontend` | `dsa_frontend` | Nginx-served React build on `:80` |

Access the app at:
- **Frontend**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000/api/`

---

## 🔑 Demo Accounts

Seeded by `python manage.py seed_data` (or Docker Compose automatically):

| Username | Password | Notes |
|----------|----------|-------|
| `demo_user` | `password123` | Full seeded history: 35 solved problems, boxes 1–5, 60 days of stats, an active 30‑day study plan, 7‑day current streak |
| `test_user` | `password123` | Clean slate for testing |

> On frontend you can also log in instantly via the "demo user" quick-switch buttons.

---

## 🧪 Running Tests

```bash
# Backend — full unit + integration suite (tracker app)
cd backend
.\venv\Scripts\python manage.py test tracker

# Frontend — build to verify production assets
cd ../frontend
npm run build
```

---

## ⚙️ Configuration

Copy `backend/.env.example` to `backend/.env` and adjust as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `True` | Django debug mode |
| `DJANGO_SECRET_KEY` | local-dev key | **Set a real secret in production** |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | `localhost:5432` | Leave empty to use SQLite |
| `REDIS_URL` | `redis://localhost:6379/0` | Leave empty to use in-memory cache |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | redis URL | Celery broker + result backend |
| `SENDGRID_API_KEY` | *(empty)* | Email delivery (falls back to console) |
| `FRONTEND_URL` | `http://localhost:5173` | Base URL used in verification / reset email links |

### Environment selection
- **SQLite + in-memory cache + eager Celery** → run without any env vars (zero infrastructure).
- **PostgreSQL + Redis + real Celery** → set the env vars above (or use Docker Compose).

---

## 📡 API Reference

All endpoints are under the `/api/` prefix. Auth via JWT Bearer token (`Authorization: Bearer <token>`); demo users can be fetched from `/api/auth/me/`.

### Problems
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/problems/` | List problems with filters (`difficulty`, `topic`, `company`, `status`, `search`) + count pills |
| `GET` | `/api/problems/tags/` | All tags with problem counts |
| `GET` | `/api/problems/companies/` | All companies with problem counts |
| `GET` | `/api/problems/by-company/<company_id>/` | Problems for a specific company |
| `GET` | `/api/problems/<id>/` | Problem detail + requesting user's progress |
| `GET` | `/api/problems/<id>/solution/` | Scraped solution (code, explanation, complexity) |

### Progress & Spaced Repetition
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/user-progress/` | Update progress (`problem_id`, `status`, `notes`, `code_solution`) |
| `GET` | `/api/user-progress/stats/` | Solve stats, streak, weak topics, due count |
| `GET` | `/api/user-progress/due-today/` | Problems due for review today (Leitner) |
| `GET` | `/api/user-progress/<id>/history/` | Audit trail of Leitner box transitions |
| `GET` | `/api/spaced-repetition/stats/` | Box 1–5 distribution + due today count |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/analytics/dashboard/` | Placement-readiness summary (totals, readiness, weak areas) |
| `GET` | `/api/analytics/heatmap/` | 52-week activity heatmap (cached in Redis) |
| `GET` | `/api/analytics/topic-breakdown/` | Topic mastery % + weak topic flags |
| `GET` | `/api/analytics/streaks/` | Current / longest streak, last solved date |
| `GET` | `/api/analytics/difficulty-breakdown/` | Easy / Medium / Hard breakdown |
| `GET` | `/api/analytics/timeline/` | Solved vs attempted volume over time |

### Reminders & Study Plans
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/reminders/digest/` | Daily review digest |
| `POST` | `/api/study-plans/generate/` | Generate rule-based plan (`target_date`, `problems_per_day`) |
| `GET` | `/api/study-plans/active/` | Active plan with day-by-day problem allocations |
| `GET` | `/api/study-plans/<id>/progress/` | Plan completion, on-pace indicator, readiness score |

### Auth & Account
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/signup/` (or `/register/`) | Register a new account |
| `POST` | `/api/auth/login/` | Log in, receive JWT + refresh token |
| `POST` | `/api/auth/verify-email/` | Verify email using emailed token |
| `POST` | `/api/auth/resend-verification/` | Resend verification email |
| `POST` | `/api/auth/forgot-password/` | Request password reset |
| `POST` | `/api/auth/reset-password/` | Reset password with emailed token |
| `POST` | `/api/auth/refresh-token/` | Refresh an expired access token |
| `GET` | `/api/auth/me/` | Current user profile + available demo users |
| `POST` | `/api/bookmarks/toggle/` | Add / remove a bookmark |
| `GET` | `/api/bookmarks/` | List bookmarked problems |
| `GET` | `/api/export/progress/` | Export full progress |

---

## 🛠️ Management Commands

```bash
# Seed the database (problems + demo users + sample data)
python manage.py seed_data

# Bulk-import problems from a CSV file
python manage.py import_dsa_problems --csv=path/to/problems.csv

# Import company-specific questions from company CSV data
python manage.py import_company_questions

# Run scheduled daily tasks immediately (no Celery daemon needed)
python manage.py run_daily_tasks

# Send a test email (verify SendGrid / console backend config)
python manage.py send_test_email
```

---

## 🧠 How the Study Plan & Leitner Engine Work

**Leitner State Machine** — every problem you solve lives in one of 5 boxes, each with a growing review interval. Get it right → move up a box; get it wrong → drop to Box 1. This biases your practice toward the problems and topics your brain is about to forget.

**Study Plan Generator** — picks problems deterministically every day using weighted heuristics (spaced-rep backlog, weak topics, medium balance, hard push) and annotates each day with the *reason* it chose what it did — so you always know *why* today's set matters.

---

## 📄 License

This project is for personal / educational use. LeetCode problem content and solution data belong to their respective owners.

---

## 🙌 Acknowledgements

- Curated problem & company data from open LeetCode lists / CSV dumps.
- Solution explanations & code sourced (server-side) from [leetcode.ca](https://leetcode.ca).