# ZenSpend Backend — Setup & Deploy Guide

## What's in this folder

| File | What it does |
|---|---|
| `database.py` | Creates all SQLite tables. Run once to set up. |
| `main.py` | The entire FastAPI backend — all API routes. |
| `requirements.txt` | Python packages needed. |
| `render.yaml` | Tells Render.com how to deploy your app. |

---

## Part 1 — Run locally first (test on your machine)

Open CMD and run these commands one by one:

```
cd path\to\this\folder

pip install -r requirements.txt

python database.py

uvicorn main:app --reload --port 8000
```

Then open your browser to:
**http://localhost:8000/docs**

You'll see an interactive page listing every API endpoint.
Try clicking "POST /users" → "Try it out" to create a test user.

---

## Part 2 — Deploy to Render.com (so friends can access it)

### Step 1 — Push to GitHub

```
git init
git add .
git commit -m "ZenSpend backend"
```

Go to github.com → New repository → name it `zenspend-backend` → create it.
Then run what GitHub shows you (the `git remote add origin...` commands).

### Step 2 — Create account on Render

Go to render.com → Sign up (free) → Connect your GitHub account.

### Step 3 — Deploy

1. Click **New** → **Web Service**
2. Select your `zenspend-backend` repo
3. Render will auto-detect `render.yaml` and fill everything in
4. Click **Deploy**

Wait ~2 minutes. Render gives you a URL like:
**https://zenspend-api.onrender.com**

That's your live API. Share it with your friends — or plug it into your React app.

---

## Part 3 — Connect your React app

In your ZenSpend frontend, replace the Firebase calls with fetch calls to your API.

Example — adding a transaction:

```javascript
// Before (Firebase):
await setDoc(doc(db, 'users', uid), { transactions: [...] })

// After (your own API):
await fetch('https://zenspend-api.onrender.com/users/USER_ID/transactions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'Grocery Store',
    amount: 45.50,
    category: 'Essentials',
    txn_date: '2025-03-24'
  })
})
```

---

## Key API endpoints (quick reference)

| Method | URL | What it does |
|---|---|---|
| POST | /users | Register a new user |
| GET | /users/{id} | Get user profile |
| PATCH | /users/{id} | Update budget, streak, settings |
| POST | /users/{id}/transactions | Add a transaction |
| GET | /users/{id}/transactions | Get transactions (filter by category) |
| GET | /users/{id}/transactions/summary | Monthly spend by category |
| POST | /users/{id}/bills | Add a bill |
| GET | /users/{id}/bills?upcoming_only=true | Get upcoming bills |
| POST | /users/{id}/goals | Add a goal |
| PATCH | /users/{id}/goals/{goal_id} | Update goal progress |
| GET | /restaurants?cheap_only=true&healthy_only=true | CravingMode filter |
| GET | /analytics/leaderboard | Top streaks across all users |
| GET | /analytics/spending | Platform-wide spend breakdown |

Full interactive docs always available at: **your-url/docs**

---

## What's NOT overkill (you asked!)

Everything in the database is genuinely used by your app:
- **Restaurants** — same 8 from your constants.ts, pre-seeded automatically
- **Cross-user analytics** — leaderboard + spending endpoints exist because you said you need cross-user queries
- **Personality + streak** — stored on the user row, updated via PATCH /users/{id}

The only thing removed vs the Hive version is partitioning — SQLite doesn't need it at your scale.
