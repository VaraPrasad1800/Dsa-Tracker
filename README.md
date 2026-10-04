# 🧠 DSA Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Django 4.2](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.2-purple.svg)](https://vitejs.dev/)

A modern, full-stack **Data Structures & Algorithms practice tracking, spaced repetition revision, and technical interview preparation platform** for local development.

---

## 🎯 Overview

Preparing for technical software engineering interviews presents a fundamental challenge: **algorithmic retention and the forgetting curve**. Candidates often solve complex Dynamic Programming, Tree, or Graph problems, only to lose the critical intuitions and edge-case awareness several weeks later.

**DSA Tracker** provides an organized local preparation workflow:
- **Tracks Practice & Progress**: Direct integration with canonical problem sets allows engineers to practice under authentic conditions while logging notes, approach intuitions, problem statements, and code snippets in a single platform.
- **Scientifically Scheduled Revision**: Eliminates manual tracking by scheduling daily reviews through an automated **Leitner 5-box spaced repetition system**.
- **Behavioral Analytics & Readiness**: Translates daily practice into quantified metrics, including a 52-week activity heatmap, topic mastery percentages, streak monitoring, and interview readiness heuristics.
- **Company-Targeted Preparation**: Aggregates questions asked by top tech employers across specific interview recency windows (30 days, 3 months, 6 months, All) with appearance frequencies, server-side pagination, and instant numeric question search.
- **Mock Interview Simulation**: Provides timed technical screen simulations under realistic constraints with direct problem links and score tracking.
- **Declarative Routing**: Full client-side React Router v7 routing with URL deep-linking, query parameter synchronization, and browser history navigation.

---

## ✨ Core Features

### 🔐 Authentication & Account Management
- **JWT Authentication**: Secure access tokens with refresh token rotation and database-backed revocation (RefreshToken store).
- **Email Verification**: Cryptographic token verification delivered via console email backend in local development.
- **Password Reset**: Tokenized, secure forgot-password and reset-password workflow with expiration handling.
- **Pre-seeded Demo Accounts**: Evaluation accounts (demo_user, 	est_user) pre-configured with realistic solve histories and spaced repetition states.

### 📚 Problem Bank & Explorer
- **Curated Algorithmic Catalog**: 3,300+ DSA questions classified by canonical numbering (e.g. #1 Two Sum), difficulty (Easy, Medium, Hard), and topic categories.
- **External Practice Links**: Direct links to canonical problems on LeetCode for authentic online judging.
- **Multi-Faceted Search & Filtering**: Real-time debounced text search, difficulty filters, topic tags, company filters, and solve status (Solved, Unsolved, Needs Revisit, Bookmarked).
- **Deterministic Priority Sorting**: Sort problems by Most Asked, Problem Number (#), or difficulty (Easy, Medium, Hard).
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
  - Solving a problem promotes it to the next box (current_box += 1) and schedules the next review date.
  - Marking a problem as "Needs Revisit" immediately resets it to **Box 1** for next-day review.
- **"Today's Review" Dashboard**: Focused review interface presenting overdue and due-today problems with box distribution metrics.
- **Audit Logging**: Every promotion and reset is recorded in ReviewHistory.

### 📊 Behavioral Analytics & Placement Readiness
- **52-Week Activity Heatmap**: Visual activity grid tracking daily solves and consistency over the past year.
- **Topic Mastery Breakdown**: Visual progress bars mapping solved vs. total problems per tag, automatically flagging weak areas (<50% solve rate).
- **Customizable Focus Areas**: Select priority focus topics or let the platform recommend lowest-mastery topics with one-click practice shortcuts.
- **Placement Readiness Metric**: Weighted heuristic calculating coverage across Easy, Medium, and Hard tiers.
- **Streak Tracker**: Tracks current consecutive solve streak, all-time longest streak, and last active solve dates.

### 🏢 Company-Wise Problem Collections
- **Top Tech Employers**: Curated directories for hundreds of companies (Google, Amazon, Meta, Microsoft, Apple, Uber, etc.).
- **Server-Side Pagination & Caching**: Paginated catalog with user solved-count indicators computed via batched queries.
- **Numeric Search**: Instantly locate questions across company question lists by typing the problem number (e.g. 123 or #123).
- **Recency Windows**: Filter questions asked within specific hiring windows: *Thirty Days*, *Three Months*, *Six Months*, or *All*.
- **Direct Deep Linking**: Dedicated URLs for every employer problem set (/companies/:companySlug).

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
- **Database**: SQLite (db.sqlite3 zero-dependency local dev)
- **Caching**: LocMemCache (in-memory local dev)
- **Background Worker & Scheduler**: Celery 5.3 (eager execution in local dev)
- **Authentication**: Custom JWT Authentication (PyJWT, HS256)
- **Email Delivery**: Console backend for local dev
- **API Documentation**: OpenAPI 3.0 via drf-spectacular (Swagger UI & Redoc)
- **Testing**: Django Test Runner

---

## 🚀 Local Development Setup

### Prerequisites
- **Python 3.10+**
- **Node.js 18+ & npm**

---

### 1. Backend Setup (Django + SQLite on Port 8001)

Open a terminal in the project root:

`ash
cd backend

# Create and activate virtual environment
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
# source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Seed sample problems, tags, companies, and demo users (demo_user / password123)
python manage.py seed_data

# Start the Django development server on port 8001
python manage.py runserver 8001
# (or on Windows: .\run.ps1)
`

*Backend API will run at http://127.0.0.1:8001/api/ with interactive OpenAPI docs at http://127.0.0.1:8001/api/docs/.*

---

### 2. Frontend Setup (React + Vite on Port 5173)

In a second terminal window:

`ash
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
`

*Frontend application will be available at http://localhost:5173/.*

---

## 🔑 Environment Variables

The project uses single-source-of-truth environment configurations for local development:

### Backend (ackend/.env)

`ini
DEBUG=True
DJANGO_SECRET_KEY=local-dev-secret-key
USE_SQLITE=True
USE_REDIS=False
CELERY_ALWAYS_EAGER=True
FRONTEND_URL=http://localhost:5173
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
`

### Frontend (rontend/.env)

`ini
VITE_API_URL=http://127.0.0.1:8001/api
`

---

## 🧪 Testing & Verification

### Running Backend Tests
`ash
cd backend
python manage.py test tracker
`

### Running Frontend Tests
`ash
cd frontend
npm test
`

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
