# 🧠 DSA Tracker

[![CI](https://github.com/VaraPrasad1800/Dsa-Tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/VaraPrasad1800/Dsa-Tracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Django 4.2](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.2-purple.svg)](https://vitejs.dev/)

A modern, full-stack **Data Structures & Algorithms practice tracking, spaced repetition revision, and technical interview preparation platform**.

---

## 🎯 Overview

Preparing for technical software engineering interviews presents a fundamental challenge: **algorithmic retention and the forgetting curve**. Candidates often solve complex Dynamic Programming, Tree, or Graph problems, only to lose the critical intuitions and edge-case awareness several weeks later.

**DSA Tracker** provides an organized local and production-ready preparation workflow:
- **Tracks Practice & Progress**: Direct integration with canonical problem sets allows engineers to practice under authentic conditions while logging notes, approach intuitions, problem statements, and code snippets in a single platform.
- **Scientifically Scheduled Revision**: Eliminates manual tracking by scheduling daily reviews through an automated **Leitner 5-box spaced repetition system**.
- **Behavioral Analytics & Readiness**: Translates daily practice into quantified metrics, including a 52-week activity heatmap, topic mastery percentages, streak monitoring, and interview readiness heuristics.
- **Company-Targeted Preparation**: Aggregates questions asked by top tech employers across specific interview recency windows (30 days, 3 months, 6 months, All) with appearance frequencies, server-side pagination, and instant numeric question search.
- **Mock Interview Simulation**: Provides timed technical screen simulations under realistic constraints with direct problem links and score tracking.
- **High-Performance Architecture**: Zero N+1 queries across company listings, tags, review queues, and analytics, with persistent connection pooling and resilient in-memory or Redis caching.
- **Declarative Routing**: Full client-side React Router v7 routing with URL deep-linking, query parameter synchronization, and browser history navigation.

---

## ✨ Core Features

### 🔐 Authentication & Account Management
- **Stateless JWT Authentication**: Secure access tokens with refresh token rotation and database-backed revocation (`RefreshToken` store).
- **Email Verification**: Cryptographic token verification delivered via SendGrid (production) or console email backend (local development).
- **Password Reset**: Tokenized, secure forgot-password and reset-password workflow with expiration handling.
- **Pre-seeded Demo Accounts**: Evaluation accounts (`demo_user`, `test_user`) pre-configured with realistic solve histories and spaced repetition states.

### 📚 Problem Bank & Explorer
- **Curated Algorithmic Catalog**: 3,300+ DSA questions classified by canonical numbering (e.g. `#1 Two Sum`), difficulty (`Easy`, `Medium`, `Hard`), and topic categories.
- **External Practice Links**: Direct links to canonical problems on LeetCode for authentic online judging.
- **Multi-Faceted Search & Filtering**: Real-time debounced text search, difficulty filters, topic tags, company filters, and solve status (`Solved`, `Unsolved`, `Needs Revisit`, `Bookmarked`).
- **Deterministic Priority Sorting**: Sort problems by Most Asked, Problem Number (`#`), or difficulty (Easy, Medium, Hard).
- **Embedded Problem Statement Viewer**: Dedicated modal tab presenting problem descriptions, examples, and constraints.
- **Personal Notes & Code Snippets**: Attach markdown notes (intuition, complexities, pitfalls) and syntax-highlighted code implementations.
- **Resilient UI States**: Explicit error state cards with quick-retry capabilities when the backend is unreachable.

### 🔁 Leitner Spaced Repetition (5-Box Engine)
- **Review Intervals**:
  - **Box 1**: 1 Day (Freshly learned or recently failed)
  - **Box 2**: 3 Days (Building initial recall)
  - **Box 3**: 7 Days (Consolidating patterns)
  - **Box 4**: 14 Days (Strengthening retention)
  - **Box 5**: 30 Days (Long-term mastery)
- **Deterministic Progression**:
  - Solving a problem promotes it to the next box (`current_box += 1`) and schedules the next review date.
  - Marking a problem as "Needs Revisit" immediately resets it to **Box 1** for next-day review.
- **"Today's Review" Dashboard**: Focused review interface presenting overdue and due-today problems with box distribution metrics.
- **Audit Logging**: Every promotion and reset is recorded in `ReviewHistory`.

### 📊 Behavioral Analytics & Placement Readiness
- **52-Week Activity Heatmap**: Visual activity grid tracking daily solves and consistency over the past year.
- **Topic Mastery Breakdown**: Visual progress bars mapping solved vs. total problems per tag, automatically flagging weak areas (<50% solve rate).
- **Customizable Focus Areas**: Select priority focus topics or let the platform recommend lowest-mastery topics with one-click practice shortcuts.
- **Placement Readiness Metric**: Weighted heuristic calculating coverage across Easy, Medium, and Hard tiers.
- **Streak Tracker**: Tracks current consecutive solve streak, all-time longest streak, and last active solve dates.

### 🏢 Company-Wise Problem Collections
- **Top Tech Employers**: Curated directories for hundreds of companies (Google, Amazon, Meta, Microsoft, Apple, Uber, etc.).
- **Server-Side Pagination & Caching**: Paginated catalog with user solved-count indicators computed via batched queries.
- **Numeric Search**: Instantly locate questions across company question lists by typing the problem number (e.g. `123` or `#123`).
- **Recency Windows**: Filter questions asked within specific hiring windows: *Thirty Days*, *Three Months*, *Six Months*, or *All*.
- **Direct Deep Linking**: Dedicated URLs for every employer problem set (`/companies/:companySlug`).

### ⏱️ Timed Mock Interview Mode
- **Simulated Technical Screens**: Configurable mock interview sessions (30, 45, or 60 minutes; 2 or 3 problems) with difficulty presets or company sets.
- **Live Countdown Timer**: Session-persisted countdown clock tracking time remaining.
- **Direct Practice Links**: "Open on LeetCode" one-click navigation on every problem card.
- **Optimistic State Updates**: Instant mark-as-solved UI feedback with automatic background reconciliation.

### 🎯 Gamification, Challenges & Study Plans
- **Study Plan Generator**: Rule-based heuristic schedule generator producing day-by-day practice timelines.
- **Time-Bounded Challenges**: Custom and template-driven challenges with server-authoritative deadline validation.
- **Milestone Achievements**: Deterministic badge unlocks (First Solve, Streak Milestones, Topic Mastery, Difficulty Milestones).
- **Points & Leaderboard**: Point rewards for solves, streaks, and challenges with weekly resets.

---

## 🛠️ Technology Stack

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite 8.2
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
- **Database**: SQLite (default zero-dependency local dev) / PostgreSQL 15 (production)
- **Caching**: LocMemCache (default local dev) / Redis 7 (production)
- **Background Worker & Scheduler**: Celery 5.3 + Celery Beat (supports synchronous eager execution in local dev)
- **Authentication**: Custom JWT Authentication (PyJWT, HS256)
- **Email Delivery**: Console backend (local dev) / SendGrid Python SDK (production)
- **API Documentation**: OpenAPI 3.0 via `drf-spectacular` (Swagger UI & Redoc)
- **Application Monitoring**: Sentry SDK (optional APM & error tracking)
- **Testing**: Django Test Runner (`CaptureQueriesContext`, N+1 query assertions)
- **WSGI Server**: Gunicorn

---

## 🏗️ System Architecture

```
[User Browser (React 19 SPA)]
           |
           | HTTP REST JSON (JWT Bearer Authorization)
           v
+----------------------------------------------------------------+
|                   DJANGO REST FRAMEWORK (Backend)              |
|  - RequestID Middleware & Throttling (120 req/hr)              |
|  - Custom JWTAuthentication (HS256 Access & Refresh Rotation)  |
|  - Leitner Spaced Repetition Engine (5-Box SRS)                |
|  - Behavioral Analytics Aggregator (Zero N+1 Batched Queries)   |
|  - Company Directory & Pagination (50/page)                    |
|  - Solution Scraper & Formatter (leetcode.ca)                  |
|  - Study Plan & Challenge Services                             |
+----------------------------------------------------------------+
       |                           |                       |
       | SQLite / PostgreSQL       | LocMem / Redis Cache  | Celery Task Dispatch
       v                           v                       v
+---------------+        +----------------+      +---------------------+
|   Database    |        |  Cache Layer   |      | Celery Worker & Beat|
| - Problem Bank|        | - In-memory dev|      | - Daily digests     |
| - User Progress|       | - Redis (prod) |      | - Deadline audits   |
| - Review Logs |        +----------------+      | - Analytics refresh |
| - Auth/Tokens |                                +---------------------+
+---------------+
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
│   │   ├── settings.py                # Environment-driven settings & dev fallbacks
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
│   │   │   ├── analytics.py           # Heatmap, streaks, readiness
│   │   │   ├── auth_tokens.py         # Token generation & SHA-256 hashing
│   │   │   ├── challenge_service.py   # Challenge validation & progress checks
│   │   │   ├── email_service.py       # Transactional email rendering & delivery
│   │   │   ├── leitner.py             # 5-box spaced repetition state machine
│   │   │   ├── points_service.py      # Server-authoritative point calculation
│   │   │   └── study_plan.py          # Heuristic study schedule generator
│   │   ├── tests/                     # Automated backend test suite
│   │   │   ├── test_n_plus_one.py     # Query budget limits (<=4 queries across endpoints)
│   │   │   ├── test_problems.py       # Problem listing, sorting & filtering tests
│   │   │   ├── test_auth.py           # JWT auth, verification & rotation tests
│   │   │   └── test_core_e2e_features.py # End-to-end integration workflows
│   │   ├── utils/
│   │   │   └── problem_formatter.py   # Problem statement & example normalizer
│   │   ├── authentication.py          # Custom JWTAuthentication class
│   │   ├── email_backends.py          # SendGrid SDK backend with console fallback
│   │   ├── models.py                  # Relational database models
│   │   ├── scraper.py                 # Solution scraper
│   │   ├── serializers.py             # DRF serializers
│   │   ├── tasks.py                   # Celery asynchronous tasks
│   │   └── views.py                   # DRF API endpoints
│   ├── Dockerfile                     # Production backend Docker container
│   ├── manage.py                      # Django CLI
│   └── requirements.txt               # Pinned Python dependencies
├── frontend/
│   ├── public/                        # Static assets & favicons
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js              # Axios client with JWT interceptors
│   │   ├── components/                # Modular React UI components
│   │   │   ├── analytics/             # Heatmaps, difficulty donuts, mastery bars
│   │   │   ├── common/                # Modals, toasts, skeleton cards, error states
│   │   │   ├── dashboard/             # Focus areas, summary widgets
│   │   │   ├── problems/              # Problem table, cards, filters, detail modal
│   │   │   └── spaced_repetition/     # Flashcard reviews, box visualizers
│   │   ├── context/                   # React Contexts (Auth, Theme, Tags)
│   │   ├── pages/                     # Routed page components
│   │   │   ├── auth/                  # Login, Signup, Verify Email, Password Reset
│   │   │   ├── AchievementsPage.jsx   # /achievements
│   │   │   ├── AnalyticsPage.jsx      # /analytics
│   │   │   ├── ChallengesPage.jsx     # /challenges
│   │   │   ├── CompaniesPage.jsx      # /companies
│   │   │   ├── CompanyProblemsPage.jsx# /companies/:companySlug
│   │   │   ├── InterviewModePage.jsx  # /interview-mode
│   │   │   ├── ProblemsPage.jsx       # /problems
│   │   │   ├── SolutionPage.jsx       # /problems/:id/solution
│   │   │   ├── StudyPlanPage.jsx      # /study-plan
│   │   │   └── TodaysReviewPage.jsx   # /today-review
│   │   ├── App.jsx                    # Root component & React Router v7 routes
│   │   ├── main.jsx                   # React DOM entry point
│   │   └── test/                      # Vitest test setup and test files
│   ├── Dockerfile                     # Frontend container definition
│   ├── package.json                   # Pinned Node dependencies
│   ├── tailwind.config.js             # Tailwind CSS styling configuration
│   └── vite.config.js                 # Vite bundler configuration & local dev proxy
├── docker-compose.yml                 # Full-stack multi-container composition
├── .gitignore                         # Git exclusion rules
└── README.md                          # Public repository documentation
```

---

## 🚀 Local Development Setup

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18 or higher (with npm)
- *(Optional)* Docker & Docker Compose

---

### Step-by-Step Local Setup

#### 1. Clone the Repository
```bash
git clone https://github.com/VaraPrasad1800/Dsa-Tracker.git
cd Dsa-Tracker
```

#### 2. Backend Setup (Django + SQLite)
```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
# source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables for local development
# (Defaults to SQLite, in-memory cache, and eager Celery)
cp .env.example .env

# Run database migrations
python manage.py migrate

# Seed sample problems, tags, companies, and demo users (demo_user / password123)
python manage.py seed_data

# Run backend automated tests
python manage.py test tracker

# Start the Django development server on port 8001
python manage.py runserver 8001
```
*Backend API will be running at `http://127.0.0.1:8001/api/` with interactive OpenAPI docs at `http://127.0.0.1:8001/api/docs/`.*

#### 3. Frontend Setup (React + Vite)
In a new terminal window:
```bash
cd frontend

# Install Node dependencies
npm install

# Copy local development environment file
cp .env.example .env.local

# Run frontend unit tests
npm test -- --run

# Start the Vite development server (proxies /api to http://127.0.0.1:8001)
npm run dev
```
*Frontend application will be available at `http://localhost:5173/`.*

---

### Containerized Setup via Docker Compose

To run the entire multi-container stack (PostgreSQL 15, Redis 7, Django, Celery Worker, Celery Beat, and Frontend) in Docker:

```bash
docker-compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/api/`
- API Docs: `http://localhost:8000/api/docs/`

---

## 🔑 Environment Variables

The project reads configuration from environment variables with sensible defaults for local development.

### Backend (`backend/.env`)

| Variable Name | Required | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `DEBUG` | No | `True` | Set to `False` in production to enforce security headers. |
| `DJANGO_SECRET_KEY` | Yes (Prod) | Insecure dev key | Cryptographic secret key. |
| `USE_SQLITE` | No | `True` | Forces SQLite usage regardless of `POSTGRES_DB`. |
| `USE_POSTGRES` | No | `False` | Enables PostgreSQL in development when `DEBUG=True`. |
| `POSTGRES_DB` | No | `""` | PostgreSQL database name (used in production or when `USE_POSTGRES=True`). |
| `POSTGRES_USER` | No | `""` | PostgreSQL username. |
| `POSTGRES_PASSWORD` | No | `""` | PostgreSQL password. |
| `POSTGRES_HOST` | No | `localhost` | PostgreSQL host. |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port. |
| `DB_CONN_MAX_AGE` | No | `600` *(10 min)* | Persistent connection lifetime in seconds. |
| `USE_REDIS` | No | `False` | When `False`, uses in-memory `LocMemCache`. Set to `True` in production. |
| `REDIS_URL` | No | `""` | Redis connection URL (e.g. `redis://localhost:6379/0`). |
| `CELERY_ALWAYS_EAGER`| No | `True` in dev | When `True`, executes Celery tasks synchronously in-process. |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/0` | Celery message broker endpoint. |
| `CELERY_RESULT_BACKEND`| No | `redis://localhost:6379/0` | Celery task result backend. |
| `CORS_ALLOWED_ORIGINS`| Yes (Prod) | Local origins | Comma-separated list of allowed frontend origins. |
| `CSRF_TRUSTED_ORIGINS`| Yes (Prod) | Local origins | Comma-separated list of trusted CSRF origins. |
| `FRONTEND_URL` | No | `http://localhost:5173`| Frontend URL used in email verification and password reset links. |
| `SENDGRID_API_KEY` | Yes (Prod) | `""` | SendGrid API key (falls back to console backend when empty). |
| `DEFAULT_FROM_EMAIL` | No | `DSA Tracker <no-reply@dsatracker.app>` | Sender email header. |
| `JWT_EXPIRATION_HOURS`| No | `1` | Access token lifetime in hours. |
| `JWT_REFRESH_EXPIRATION_HOURS`| No | `168` *(7 days)*| Refresh token lifetime in hours. |

### Frontend (`frontend/.env.local`)

| Variable Name | Required | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | No | `"/api"` | Base API path. In local dev, Vite proxies `/api` to the backend. In production, set to your backend API URL (e.g. `https://api.yourdomain.com/api`). |
| `VITE_API_URL` | No | `http://localhost:8001` | Backend API URL for direct requests in development. |
| `VITE_BACKEND_PORT` | No | `8001` | Port of the local Django development server targeted by Vite proxy. |

---

## 📦 Building for Production

### Frontend Production Build
To create an optimized, minified production build of the React application:

```bash
cd frontend
npm run build
```
The compiled static assets will be output to `frontend/dist/`. These static files can be served using any static web server (Nginx, Caddy, AWS S3/CloudFront, Cloudflare Pages, etc.).

### Backend Production Build
1. Set `DEBUG=False` in your production environment.
2. Collect static files:
   ```bash
   cd backend
   python manage.py collectstatic --noinput
   ```
3. Run database migrations:
   ```bash
   python manage.py migrate --noinput
   ```
4. Start the production WSGI server with Gunicorn:
   ```bash
   gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
   ```

---

## 🧪 Testing & Verification

### Running Backend Tests
```bash
cd backend
python manage.py test tracker
```
To run the N+1 query budget verification suite:
```bash
python manage.py test tracker.tests.test_n_plus_one
```

### Running Frontend Tests
```bash
cd frontend
npm test -- --run
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.