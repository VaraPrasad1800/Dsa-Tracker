# 🧠 DSA Tracker

[![CI](https://github.com/VaraPrasad1800/Dsa-Tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/VaraPrasad1800/Dsa-Tracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Django 4.2](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.2-purple.svg)](https://vitejs.dev/)

A modern, production-ready **Data Structures & Algorithms practice tracking, spaced repetition revision, and technical interview preparation platform**.

---

## 🎯 Overview

Preparing for technical software engineering interviews presents a fundamental challenge: **algorithmic retention and the forgetting curve**. Candidates often spend dozens of hours solving complex Dynamic Programming, Tree, or Graph problems, only to lose the critical intuitions and edge-case awareness several weeks later when facing a live technical screen.

**DSA Tracker** solves this problem by acting as an intelligent preparation command center and retention engine:
- **Tracks Practice & Progress**: Direct integration with canonical problem sets (e.g. LeetCode) allows engineers to practice under authentic judge conditions while capturing granular audit trails, notes, approach intuitions, and code snippets in a single platform.
- **Scientifically Scheduled Revision**: Eliminates manual tracking by scheduling daily reviews through an automated **Leitner 5-box spaced repetition system**.
- **Behavioral Analytics & Readiness**: Translates daily practice into quantified metrics, including 52-week activity heatmaps, topic mastery percentages, streak monitoring, and placement readiness ratings.
- **Company-Targeted Preparation**: Aggregates questions asked by top tech employers across specific interview recency windows (30 days, 3 months, 6 months, All) with appearance frequency and acceptance rates.
- **Mock Interview Simulation**: Provides timed technical screen simulations under realistic constraints with automated score calculation and actionable follow-ups.

---

## ✨ Core Features

### 🔐 Authentication & Account Management
- **Stateless JWT Authentication**: Secure access tokens with refresh token rotation and database-backed revocation (`RefreshToken` store).
- **Mandatory Email Verification**: Single-use cryptographic token verification delivered via SendGrid Web API v3 with click-tracking disabled and idempotent "already-used" detection.
- **Password Reset**: Tokenized, secure forgot-password and reset-password workflow with expiration handling.
- **Demo Access**: Instant evaluation accounts (`demo_user`, `test_user`) pre-seeded for rapid testing.

### 📚 Problem Bank & Explorer
- **Curated Algorithmic Catalog**: Hundreds of curated DSA questions classified by canonical numbering (e.g. `#1 Two Sum`), difficulty (`Easy`, `Medium`, `Hard`), and topic categories.
- **External Canonical Practice**: Direct problem links to official LeetCode problems, allowing users to solve against battle-tested online judges before logging progress.
- **Multi-Faceted Search & Filtering**: Real-time debounced text search, difficulty filters, topic tags, company filters, and solve status (`Solved`, `Unsolved`, `Needs Revisit`, `Skipped`, `Bookmarked`).
- **Personal Notes & Code Snippets**: Attach markdown notes (intuition, complexities, pitfalls) and syntax-highlighted optimal code implementations to any problem.
- **Keyboard Shortcuts**: Rapid navigation workflow (`S` to mark solved, `R` for needs revisit, `?` for shortcut modal, `Esc` to close).

### 🔁 Leitner Spaced Repetition (5-Box Engine)
- **Scientific Review Intervals**:
  - **Box 1**: 1 Day (Freshly learned or recently failed)
  - **Box 2**: 3 Days (Building initial recall)
  - **Box 3**: 7 Days (Consolidating patterns)
  - **Box 4**: 14 Days (Strengthening retention)
  - **Box 5**: 30 Days (Long-term mastery)
- **Deterministic Progression**:
  - Successfully reviewing or solving a problem promotes it to the next box (`current_box += 1`) and schedules the next review date.
  - Marking a problem as "Needs Revisit" immediately resets it to **Box 1** for next-day review.
- **"Today's Review" Mode**: Distraction-free review dashboard presenting overdue and due-today problems with progress tracking and box distribution visualizations.
- **Audit Logging**: Every box promotion, demotion, and skip is logged in `ReviewHistory`.

### 📊 Behavioral Analytics & Placement Readiness
- **52-Week GitHub-Style Heatmap**: Annual visual activity grid tracking daily solves and consistency, cached in Redis with a 6-hour TTL and automated invalidation.
- **Topic Mastery Breakdown**: Visual progress bars mapping solved vs. total problems per tag, automatically flagging weak areas (<50% solve rate).
- **Customizable Target Focus Areas**: Users can select up to 5 priority focus topics or let the platform automatically select their lowest-mastery topics with one-click practice shortcuts.
- **Placement Readiness Metric**: Weighted heuristic prioritizing Medium and Hard difficulty coverage across readiness bands (*Not Ready*, *Progressing*, *Interview Ready*, *Placement Ready*).
- **Streak Tracker**: Tracks current consecutive solve streak, all-time longest streak, and last active solve dates.

### 🏢 Company-Wise Problem Collections
- **Top Tech Employers**: Curated directories for companies including Google, Amazon, Meta, Microsoft, Apple, Uber, and more.
- **Recency Windows**: Filter questions asked within specific hiring windows: *Thirty Days*, *Three Months*, *Six Months*, or *All*.
- **Interview Frequency & Acceptance Rates**: Real interview appearance frequencies and acceptance rate benchmarks.

### ⏱️ Timed Mock Interview Mode
- **Simulated Technical Screens**: Configurable mock interview sessions (30, 45, or 60 minutes; 2 or 3 problems) with difficulty presets or company sets.
- **Live Countdown Timer**: Session-persisted countdown clock tracking time remaining.
- **Canonical Practice Links**: One-click navigation to external LeetCode problems during active sessions.
- **Deterministic Scoring**: Points awarded per solved problem with bonuses for complete sessions, automatic activity logging, and follow-up study recommendations.

### 🎯 Gamification, Challenges & Study Plans
- **Study Plan Generator**: Rule-based heuristic schedule generator producing day-by-day practice timelines based on user target dates and weak topics.
- **Time-Bounded Challenges**: Custom and template-driven challenges (Count, Timed, Topic, Difficulty, Company, Review) with server-authoritative deadline validation.
- **Milestone Achievements**: Deterministic badge unlocks (First Solve, Streak Milestones, Topic Mastery, Difficulty Milestones).
- **Server-Authoritative Points**: Point rewards for solves, streaks, and challenges with weekly leaderboard resets.

### 🔔 In-App Notifications & Reminders
- **Notification Dropdown**: Non-intrusive alert center for due reviews, expiring challenges, completed goals, and achievement unlocks.
- **Automated Celery Beat Reminders**: Scheduled daily review digests and deadline reminders.

### 📖 Solution & Editorial Access
- **Two-Tier Editorial Cache**: Problem explanations, asymptotic complexities ($O(N)$ time/space), and multi-language implementations (Python, C++, Java, Go) cached in PostgreSQL with a 7-day TTL and rate-limited upstream fetching.

---

## 🛠️ Technology Stack

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite 8
- **Routing**: React Router v7
- **Server State & Caching**: TanStack React Query v5
- **HTTP Client**: Axios (with centralized JWT request & 401 refresh interceptors)
- **Styling**: Tailwind CSS, PostCSS, Autoprefixer
- **UI Components & Icons**: Lucide React, Framer Motion
- **Data Visualizations**: Recharts, Three.js, React Three Fiber
- **Notifications**: React Hot Toast
- **Testing & Quality**: Vitest, React Testing Library, Oxlint

### Backend
- **Framework**: Django 4.2 (LTS)
- **API Engine**: Django REST Framework (DRF)
- **Database**: PostgreSQL 15 (with SQLite fallback for zero-dependency local dev)
- **Caching**: Redis 7 (with Django LocMemCache fallback)
- **Background Worker & Scheduler**: Celery 5.3 + Celery Beat
- **Authentication**: Custom JWT Authentication (PyJWT, HS256)
- **Email Delivery**: SendGrid Python SDK (v6+) via custom `SendGridBackend`
- **API Documentation**: OpenAPI 3.0 via `drf-spectacular` (Swagger & Redoc)
- **Application Monitoring**: Sentry SDK (APM & Error Tracking)
- **WSGI Server**: Gunicorn

### Infrastructure & Deployment
- **Frontend Hosting**: Vercel (Edge network, automated SPA rewrites)
- **Backend Hosting**: Render (Docker container web service)
- **Database**: Render PostgreSQL / Managed PostgreSQL
- **Cache & Broker**: Render Redis / Upstash Redis
- **Containerization**: Docker, Docker Compose

---

## 🏗️ System Architecture

```
[User Browser (React 19 SPA)]
           |
           | HTTPS / REST JSON (JWT Bearer Authorization)
           v
+----------------------------------------------------------------+
|                   DJANGO REST FRAMEWORK (Backend)              |
|  - RequestID Middleware & Throttling (120 req/hr)              |
|  - Custom JWTAuthentication (HS256 Access & Refresh Rotation)  |
|  - Leitner Spaced Repetition Engine                            |
|  - Behavioral Analytics Aggregator                             |
|  - Solution Scraper & Formatter (leetcode.ca)                  |
|  - Study Plan & Challenge Services                             |
+----------------------------------------------------------------+
      |                           |                       |
      | PostgreSQL Queries        | Cache (6h TTL)        | Celery Task Dispatch
      v                           v                       v
+---------------+        +----------------+      +---------------------+
|  PostgreSQL   |        |  Redis (v7)    |      | Celery Worker & Beat|
| - Problem Bank|        | - Django Cache |      | - Daily digests     |
| - User Progress|       | - Celery Broker|      | - Deadline audits   |
| - Review Logs |        | - Celery Backend|     | - Analytics refresh |
| - Auth/Tokens |        +----------------+      | - Points reset      |
+---------------+                                +---------------------+
```

---

## 📦 Project Structure

```
dsa-tracker/
├── .github/
│   └── workflows/
│       └── ci.yml                     # GitHub Actions CI (Backend & Frontend tests)
├── backend/
│   ├── core/                          # Django project configuration
│   │   ├── celery.py                  # Celery app & beat configuration
│   │   ├── settings.py                # Environment-driven Django settings
│   │   ├── urls.py                    # Root URL routing & Swagger schema
│   │   └── wsgi.py                    # Production WSGI application entry
│   ├── data/                          # Seed datasets & mappings
│   │   ├── company_problems/          # Company-wise interview CSV datasets
│   │   ├── leetcode_mapping.json      # Authoritative LeetCode problem catalog
│   │   └── sample_problems.csv        # Core bootstrap problem dataset
│   ├── tracker/                       # Primary Django application
│   │   ├── management/commands/       # Data ingestion & administrative commands
│   │   │   ├── import_company_questions.py # Company dataset importer
│   │   │   ├── import_dsa_problems.py      # Canonical CSV importer
│   │   │   ├── seed_data.py                # Local development seed data
│   │   │   └── cleanup_expired_tokens.py   # Token maintenance command
│   │   ├── services/                  # Business logic services
│   │   │   ├── analytics.py           # Heatmap, streaks, readiness heuristics
│   │   │   ├── auth_tokens.py         # Token generation & SHA-256 hashing
│   │   │   ├── challenge_service.py   # Challenge validation & progress checks
│   │   │   ├── email_service.py       # Transactional email rendering & delivery
│   │   │   ├── leitner.py             # 5-box spaced repetition state machine
│   │   │   ├── points_service.py      # Server-authoritative point calculation
│   │   │   └── study_plan.py          # Heuristic study schedule generator
│   │   ├── utils/
│   │   │   └── problem_formatter.py   # Problem statement & example normalizer
│   │   ├── authentication.py          # Custom JWTAuthentication class
│   │   ├── email_backends.py          # SendGrid SDK backend with click-tracking handling
│   │   ├── models.py                  # PostgreSQL relational schema
│   │   ├── scraper.py                 # Two-stage leetcode.ca solution scraper
│   │   ├── serializers.py             # DRF serializers
│   │   ├── tasks.py                   # Celery asynchronous tasks
│   │   └── views.py                   # DRF API endpoints
│   ├── Dockerfile                     # Production backend Docker container
│   └── requirements.txt               # Pinned Python dependencies
├── frontend/
│   ├── public/                        # Static assets & favicons
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js              # Axios client with JWT interceptors
│   │   ├── components/                # Modular React UI components
│   │   │   ├── analytics/             # Heatmaps, difficulty donuts, mastery bars
│   │   │   ├── common/                # Modals, toasts, skeleton cards, error boundaries
│   │   │   ├── dashboard/             # Focus areas, summary widgets
│   │   │   ├── problems/              # Problem table, cards, filters, notes editor
│   │   │   └── spaced_repetition/     # Flashcard reviews, box visualizers
│   │   ├── context/                   # React Contexts (Auth, Theme, Tags)
│   │   ├── pages/                     # Routed page components
│   │   │   ├── auth/                  # Login, Signup, Verify Email, Password Reset
│   │   │   ├── AchievementsPage.jsx
│   │   │   ├── AnalyticsPage.jsx
│   │   │   ├── ChallengesPage.jsx
│   │   │   ├── CompaniesPage.jsx
│   │   │   ├── CompanyProblemsPage.jsx
│   │   │   ├── InterviewModePage.jsx
│   │   │   ├── ProblemsPage.jsx
│   │   │   ├── SolutionPage.jsx
│   │   │   └── TodaysReviewPage.jsx
│   │   ├── App.jsx                    # Root component & React Router v7 routes
│   │   └── main.jsx                   # React DOM entry point
│   ├── Dockerfile                     # Frontend container definition
│   ├── package.json                   # Pinned Node dependencies
│   ├── tailwind.config.js             # Tailwind CSS styling configuration
│   ├── vercel.json                    # Vercel SPA routing rewrite configuration
│   └── vite.config.js                 # Vite bundler configuration & local dev proxy
├── docker-compose.yml                 # Full-stack multi-container composition
└── README.md                          # Public repository documentation
```

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- *(Optional)* Docker & Docker Compose
- *(Optional)* PostgreSQL & Redis (defaults to SQLite and in-memory cache if not installed)

---

### Method A: Standard Local Setup (Recommended for Development)

#### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (uses local SQLite by default)
python manage.py migrate

# Seed initial problem dataset and demo accounts
python manage.py seed_data

# Start the Django development server
python manage.py runserver 8000
```
*The API is now running at `http://127.0.0.1:8000/api/` with Swagger UI at `http://127.0.0.1:8000/api/docs/`.*

#### 2. Frontend Setup
```bash
# In a separate terminal, navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
*The React application will be available at `http://localhost:5173/`.*

---

### Method B: Containerized Setup via Docker Compose

To spin up the entire production-like environment (PostgreSQL 15, Redis 7, Django backend, Celery worker, Celery beat, and Frontend) in a single command:

```bash
docker-compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/api/`

---

## 🔑 Environment Variables

The project reads configuration from environment variables with sensible defaults for local development. Never commit real credentials to version control.

### Backend (`backend/.env`)

| Variable Name | Required | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `DEBUG` | No | `True` | Set to `False` in production. |
| `DJANGO_SECRET_KEY` | Yes (Prod) | Insecure dev key | Django cryptographic secret key. |
| `ALLOWED_HOSTS` | No | `*` | Comma-separated list of allowed hostnames. |
| `POSTGRES_DB` | No | `""` *(uses SQLite)* | PostgreSQL database name. |
| `POSTGRES_USER` | No | `""` | PostgreSQL username. |
| `POSTGRES_PASSWORD` | No | `""` | PostgreSQL password. |
| `POSTGRES_HOST` | No | `localhost` | PostgreSQL host. |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port. |
| `REDIS_URL` | No | `""` *(uses LocMem)* | Redis URL for application caching. |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/0` | Celery message broker endpoint. |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/0` | Celery task result backend. |
| `CELERY_ALWAYS_EAGER` | No | `False` | Run Celery tasks synchronously (useful in tests). |
| `CORS_ALLOWED_ORIGINS` | Yes (Prod) | `""` *(allows all)* | Comma-separated list of allowed frontend origins. |
| `FRONTEND_URL` | No | `http://localhost:5173` | Frontend URL used for email links. |
| `SENDGRID_API_KEY` | Yes (Prod) | `""` *(console backend)* | SendGrid API key for transactional emails. |
| `DEFAULT_FROM_EMAIL` | No | `DSA Tracker <no-reply@dsatracker.app>` | Sender email header. |
| `JWT_SECRET_KEY` | No | Sourced from `SECRET_KEY` | Secret key used to sign JWTs. |
| `JWT_EXPIRATION_HOURS` | No | `1` | Access token lifetime in hours. |
| `JWT_REFRESH_EXPIRATION_HOURS` | No | `168` *(7 days)* | Refresh token lifetime in hours. |
| `SENTRY_DSN` | No | `""` | Sentry error reporting DSN. |

### Frontend (`frontend/.env`)

| Variable Name | Required | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | No | `"/api"` *(proxied in Vite)* | Base URL for the Django REST API (e.g. `https://api.domain.com/api`). |

---

## 🌐 Production Deployment Summary

- **Frontend (Vercel)**:
  - Deployed as a single-page application.
  - `VITE_API_BASE_URL` configured in Vercel project settings pointing to the Render web service.
  - SPA routing guaranteed via `vercel.json` rewrite configuration.
- **Backend (Render)**:
  - Docker-based web service building from `backend/Dockerfile`.
  - Runs database migrations on startup and serves via Gunicorn.
- **Data & Scheduling**:
  - PostgreSQL instance for persistence.
  - Managed Redis instance for Celery brokering and caching.
  - Celery background worker and Celery Beat scheduler running containerized tasks.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.