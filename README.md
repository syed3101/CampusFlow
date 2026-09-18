# CampusFlow — Advanced Hackathon Build

CampusFlow is a full-stack campus resource booking platform built with:

- **Frontend:** React 18 + JavaScript + HTML5 + CSS3
- **Frontend tooling:** Vite + ES modules
- **Backend:** Python + Flask
- **Database:** Postgres
- **ORM:** SQLAlchemy

The frontend uses real ES modules:

```html
<script type="module" src="/src/main.jsx"></script>
```

There is no in-browser Babel transformer.

---

## Core hackathon features

- Student and admin authentication
- Password hashing
- Role-based student/admin portals
- Resource search and filtering
- Date/time slot availability checks
- Collision-proof reservation engine
- Alternative slot suggestions
- Maximum booking duration
- Daily booking limits
- Resource CRUD
- Maintenance state management
- Booking history and cancellations
- In-app notifications and emails
- Utilization analytics
- Audit-log model

## Three advanced features added

### 1. Manual approval queue

Admins can mark selected resources as:

```text
Requires manual approval
```

For these resources:

```text
Student requests slot
        ↓
Reservation = PENDING
        ↓
Requested slot is temporarily held
        ↓
Admin opens Approval Queue
        ↓
Approve / Reject
        ↓
Student receives notification
```

Pending reservations also participate in collision detection so two students cannot
request the exact same slot while one request is waiting for approval.

### 2. Email 

Confirmed reservations can receive:

- In-app reminder
- Email reminder through BREVO

Each user can configure:

- phone number
- email reminders

The reminder worker checks upcoming confirmed bookings once per minute.

### 3. Automatic no-show release

Students can check in around the beginning of their booking.

Default window:

```text
Check-in opens:     15 minutes before start
No-show release:    15 minutes after start
```

If the booking is confirmed but no check-in occurs by the grace period:

```text
confirmed
   ↓
NO CHECK-IN
   ↓
no_show
   ↓
slot is released
```

`no_show` reservations are ignored by collision detection, making the remaining
time available again.

---

# Run locally

## Terminal 1 — Flask API

```bash
cd CampusFlow/backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Optional:

```text
Copy .env.example → .env
```

Seed demo data:

```bash
python seed.py
```

Start Flask:

```bash
python app.py
```

Backend:

```text
http://127.0.0.1:5000
```

---

## Terminal 2 — React / Vite

```bash
cd CampusFlow/frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Vite proxies `/api/*` to Flask during development.

---

## Terminal 3 — reminder + no-show worker

The new automation features require the worker:

```bash
cd CampusFlow/backend
.venv\Scripts\activate
python jobs.py
```

Keep this terminal running during the demo.

It checks every 60 seconds for:

```text
Upcoming confirmed booking
        ↓
Send reminder

Confirmed booking past grace period
        ↓
No check-in?
        ↓
Mark NO-SHOW + release slot
```

---

# Demo accounts

After running:

```bash
python seed.py
```

Admin:

```text
admin@campusflow.edu
admin123
```

Student:

```text
student@campusflow.edu
student123
```

Admin registration invite code:

```text
CAMPUS2026
```

---

# Configure email reminders

Add these values to `backend/.env`:

```env
BREVO_API_KEY = your Brevo API key
BREVO_SENDER_EMAIL = the Gmail you verified in Brevo
BREVO_SENDER_NAME = CampusFlow
```

If Brevo is not configured, the worker safely skips real email delivery while
in-app reminders still work.

Do not commit real Brevo keys to GitHub.

---

# Automation settings

In `.env`:

```env
REMINDER_MINUTES=30
CHECKIN_EARLY_MINUTES=15
NO_SHOW_GRACE_MINUTES=15
```

For a demo, you can temporarily use smaller values, for example:

```env
REMINDER_MINUTES=5
CHECKIN_EARLY_MINUTES=5
NO_SHOW_GRACE_MINUTES=2
```

This makes the automated flow easier to demonstrate live.

---

# Important database note

This upgraded version adds new database columns.

If you already ran an older CampusFlow version using SQLite, `db.create_all()`
will not modify the old table structure.

For a fresh demo database, delete:

```text
backend/instance/campusflow.db
```

then run:

```bash
python seed.py
```

For a real long-term project, add Flask-Migrate/Alembic instead of deleting the DB.

---

# Suggested judge demo

## Demo 1 — collision prevention

```text
Existing:
10:00–11:00

Try:
10:30–11:30

Result:
Conflict rejected + alternative slots shown
```

## Demo 2 — manual approval

```text
Student books RTX Workstation
        ↓
Pending approval
        ↓
Admin → Approval Queue
        ↓
Approve
        ↓
Student receives notification
```

## Demo 3 — no-show automation

Temporarily set a short grace period:

```env
NO_SHOW_GRACE_MINUTES=2
```

Create a confirmed booking close to the current time.

Do not check in.

The worker changes:

```text
confirmed → no_show
```

and the slot becomes reusable.

## Demo 4 — reminder channels

With Brevo configured, show an upcoming confirmed booking producing:

- in-app notification
- email

For judging, in-app notification is a safe fallback if external services are
unavailable.

---

# Production note

For local development, run `python jobs.py` as a third
process.

For production, deploy the worker as a separate worker service or scheduled job.
Do not run multiple independent schedulers inside multiple Gunicorn web workers,
because the same reminder could run more than once.

---

# Structure

```text
CampusFlow/
├── backend/
│   ├── app.py
│   ├── models.py
│   ├── mail_services.py
│   ├── jobs.py
│   ├── seed.py
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```
