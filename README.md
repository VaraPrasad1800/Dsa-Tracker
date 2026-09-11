# DSA Practice Tracker

A production-quality, self-hosted DSA problem tracker that combines problem management, spaced repetition learning (Leitner 5-box system), behavioral analytics with Redis caching, and deterministic rule-based study planning to accelerate technical interview preparation.

---

## Key Features

### Phase 1: Problem Bank & Tracking (Core Foundation)
- **Comprehensive Problem Bank**: Filter by difficulty (Easy, Medium, Hard), topic tags (Array, DP, Graphs, etc.), companies (Google, Meta, Amazon, Microsoft, Apple, etc.), and status.
- **CSV Importer**: Command `python manage.py import_dsa_problems --csv=path/to/problems.csv` with pipe-separated tag/company parsing and idempotent slug upsert.
- **Problem Detail Modal**: View problem information, solution notes, and code solution snippets.
- **Fast Keyboard Shortcuts**: `S` (mark solved), `R` (mark revisit), `?` (shortcuts help guide), `Esc` (close modals).
- **User Isolation**: Complete user data isolation with instant multi-user switching (`demo_user` vs `test_user`).

### Phase 2: Spaced Repetition (Leitner 5-Box Engine)
- **Leitner State Machine**:
  - **Box 1**: Review every 1 day
  - **Box 2**: Review every 3 days
  - **Box 3**: Review every 7 days
  - **Box 4**: Review every 14 days
  - **Box 5**: Review every 30 days (Mastered, capped at 30 days)
- **Progression Logic**:
  - **Correct (Solved)**: Promotes card to next box (`current_box += 1`) and schedules review according to box interval.
  - **Needs Revisit**: Resets card back to Box 1 for review tomorrow.
- **Review History**: Full audit trail of box transitions (`ReviewHistory` model).
- **Today's Review Page**: Distraction-free flashcard interface with review progress bar and Leitner box visualization.

### Phase 3: Analytics Dashboard
- **Activity Heatmap**: 52-week annual GitHub-style heatmap with daily solve counts and tooltips.
- **Topic Mastery & Strength**: Visual mastery bars highlighting weak topics (<50% solved) with quick practice filters.
- **Difficulty Breakdown**: Donut chart tracking Easy / Medium / Hard solved distribution.
- **Streak Tracker**: Tracks current streak (🔥), all-time longest streak (🏆), and last solved date.
- **Redis Caching**: Cached with a 6-hour TTL and invalidated automatically upon any progress update.

### Phase 4: Reminders & Scheduled Tasks
- **Celery & Celery Beat**:
  - `send_daily_review_digest`: Runs at 9:00 AM UTC, caches daily review digest, and notifies user.
  - `refresh_user_analytics`: Runs at 12:00 PM UTC to refresh aggregations.
- **Manual Task Runner**: `python manage.py run_daily_tasks` allows immediate task triggering without daemon overhead.
- **In-App Reminder Banner**: Top notification banner alerting users when review cards are due.

### Phase 5: Rule-Based Study Plan Generator
- **Deterministic Heuristics Engine**:
  - **30% Slots**: Spaced repetition backlog (Box 1-2 + Needs Revisit).
  - **40% Slots**: Weak topics (<50% solved, sorted ascending).
  - **20% Slots**: Medium difficulty (balanced).
  - **10% Slots**: Hard push (focused in the final week).
  - **Dynamic Rules**: Momentum builder (Day 1 starts with Easy problems if streak is 0), crunch-time adjustments, and Box 1 backlog clearing.
- **Day-by-Day Timeline**: Calendar cards with explicit heuristic reasons ("Weak in DP", "Clear Box 1 backlog", "Hard push").
- **Readiness Score**: Quantified interview readiness metric based on topic coverage and plan completion.

---

## Tech Stack

- **Backend**: Python 3.10+, Django 4.2 LTS, Django REST Framework (DRF), Celery 5.6, Redis 8.1, PostgreSQL / SQLite.
- **Frontend**: React 19, Vite 8, Tailwind CSS, Recharts, TanStack Query (React Query), Lucide React.
- **DevOps**: Docker, Docker Compose, Nginx.

---

## Quick Start (Local Development)

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment (if not created)
python -m venv venv
.\venv\Scripts\activate   # Windows
# or: source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed database with ~160 curated problems, demo users, and sample review data
python manage.py seed_data

# Run Django development server
python manage.py runserver 8000
```

### 2. Frontend Setup

```bash
# Navigate to frontend (in a second terminal)
cd frontend

# Install dependencies
npm install

# Start Vite dev server with proxy to backend
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## Running with Docker Compose

To spin up the entire production environment with PostgreSQL, Redis, Django Web, Celery Worker, Celery Beat, and Frontend:

```bash
docker-compose up --build
```
Access the application at:
- **Frontend**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000/api/`

---

## Running Automated Tests

```bash
# Run backend unit and integration test suite
cd backend
.\venv\Scripts\python manage.py test tracker

# Build frontend to verify production assets
cd ../frontend
npm run build
```

---

## API Reference Summary

| Endpoint | Method | Description |
|---|---|---|
| `/api/problems/` | `GET` | List problems with filters (`difficulty`, `topic`, `company`, `status`, `search`) and count pills |
| `/api/problems/<id>/` | `GET` | Retrieve problem detail with requesting user's progress record |
| `/api/problems/tags/` | `GET` | List all tags with problem counts |
| `/api/problems/companies/` | `GET` | List all companies with problem counts |
| `/api/user-progress/` | `POST` | Update user progress (`problem_id`, `status`, `notes`, `code_solution`) |
| `/api/user-progress/stats/` | `GET` | User solve stats, streak, weak topics, and due count |
| `/api/user-progress/due-today/` | `GET` | Problems scheduled for review today by Leitner algorithm |
| `/api/spaced-repetition/stats/` | `GET` | Box distribution (Box 1-5 counts) & due today count |
| `/api/user-progress/<id>/history/` | `GET` | Audit trail of Leitner box transitions |
| `/api/analytics/heatmap/` | `GET` | 52-week activity heatmap (cached in Redis) |
| `/api/analytics/topic-breakdown/` | `GET` | Topic mastery percentages and weak topic flags |
| `/api/analytics/streaks/` | `GET` | Current streak, longest streak, last solved date |
| `/api/analytics/difficulty-breakdown/` | `GET` | Easy, Medium, Hard breakdown |
| `/api/analytics/timeline/` | `GET` | Solved vs attempted volume over time |
| `/api/reminders/digest/` | `GET` | Daily review digest |
| `/api/study-plans/generate/` | `POST` | Generate rule-based study plan (`target_date`, `problems_per_day`) |
| `/api/study-plans/active/` | `GET` | Active study plan with day-by-day problem allocations |
| `/api/study-plans/<id>/progress/` | `GET` | Plan completion, on-pace indicator, and readiness score |
| `/api/auth/me/` | `GET` | Current user profile and available demo users |
