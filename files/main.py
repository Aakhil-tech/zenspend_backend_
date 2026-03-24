"""
main.py
=======
ZenSpend FastAPI backend — all routes for users, transactions, bills, goals, restaurants.

Run locally:
    pip install -r requirements.txt
    python database.py        # create tables once
    uvicorn main:app --reload --port 8000

Then visit: http://localhost:8000/docs  (interactive API explorer)
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import sqlite3
import uuid
from datetime import datetime, date

from database import get_db, init_db

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ZenSpend API",
    description="Local-first backend for ZenSpend personal finance app",
    version="1.0.0"
)

# Allow your React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this to your frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

# ── Pydantic models (request/response shapes) ─────────────────────────────────

class UserCreate(BaseModel):
    email: str
    display_name: str = "ZenSpender"
    current_budget: float = 2500.0
    saving_allowance: float = 345.0

class UserUpdate(BaseModel):
    display_name:     Optional[str]   = None
    current_budget:   Optional[float] = None
    saving_allowance: Optional[float] = None
    personality_score:Optional[int]   = None
    personality_type: Optional[str]   = None
    streak_count:     Optional[int]   = None
    high_legibility:  Optional[bool]  = None
    exam_mode_active: Optional[bool]  = None
    onboarding_done:  Optional[bool]  = None

class TransactionCreate(BaseModel):
    title:    str
    amount:   float = Field(gt=0)
    category: str   = Field(pattern="^(Essentials|Savings|Wants)$")
    txn_date: str   = Field(default_factory=lambda: date.today().isoformat())

class BillCreate(BaseModel):
    title:    str
    amount:   float = Field(gt=0)
    due_date: str

class GoalCreate(BaseModel):
    title:         str
    target_amount: float = Field(gt=0)
    deadline:      Optional[str] = None

class GoalProgressUpdate(BaseModel):
    current_amount: float = Field(ge=0)

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "app": "ZenSpend API", "version": "1.0.0"}

# ── Users ─────────────────────────────────────────────────────────────────────

@app.post("/users", status_code=201)
def create_user(data: UserCreate, db: sqlite3.Connection = Depends(get_db)):
    user_id = str(uuid.uuid4())
    try:
        db.execute(
            """INSERT INTO users (user_id, email, display_name, current_budget, saving_allowance)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, data.email, data.display_name, data.current_budget, data.saving_allowance)
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Email already registered")
    return {"user_id": user_id, "email": data.email, "display_name": data.display_name}


@app.get("/users/{user_id}")
def get_user(user_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return dict(row)


@app.patch("/users/{user_id}")
def update_user(user_id: str, data: UserUpdate, db: sqlite3.Connection = Depends(get_db)):
    fields = {k: v for k, v in data.dict().items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields to update")
    fields["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    db.execute(
        f"UPDATE users SET {set_clause} WHERE user_id = ?",
        (*fields.values(), user_id)
    )
    db.commit()
    return {"updated": True, "fields": list(fields.keys())}


@app.get("/users")
def list_users(db: sqlite3.Connection = Depends(get_db)):
    """Admin: list all users (useful for cross-user analytics)."""
    rows = db.execute(
        "SELECT user_id, email, display_name, personality_type, streak_count FROM users"
    ).fetchall()
    return [dict(r) for r in rows]

# ── Transactions ──────────────────────────────────────────────────────────────

@app.post("/users/{user_id}/transactions", status_code=201)
def add_transaction(user_id: str, data: TransactionCreate, db: sqlite3.Connection = Depends(get_db)):
    txn_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
        (txn_id, user_id, data.title, data.amount, data.category, data.txn_date)
    )
    db.commit()
    return {"transaction_id": txn_id, **data.dict()}


@app.get("/users/{user_id}/transactions")
def get_transactions(
    user_id: str,
    category: Optional[str] = None,
    limit: int = 50,
    db: sqlite3.Connection = Depends(get_db)
):
    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY txn_date DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/users/{user_id}/transactions/summary")
def transaction_summary(user_id: str, db: sqlite3.Connection = Depends(get_db)):
    """Monthly spend breakdown by category — used by the dashboard."""
    rows = db.execute("""
        SELECT
            category,
            COUNT(*)        AS count,
            ROUND(SUM(amount), 2) AS total,
            strftime('%Y-%m', txn_date) AS month
        FROM transactions
        WHERE user_id = ?
          AND txn_date >= date('now', '-30 days')
        GROUP BY category, month
        ORDER BY month DESC
    """, (user_id,)).fetchall()
    return [dict(r) for r in rows]


@app.delete("/users/{user_id}/transactions/{txn_id}")
def delete_transaction(user_id: str, txn_id: str, db: sqlite3.Connection = Depends(get_db)):
    db.execute(
        "DELETE FROM transactions WHERE transaction_id = ? AND user_id = ?",
        (txn_id, user_id)
    )
    db.commit()
    return {"deleted": True}

# ── Bills ─────────────────────────────────────────────────────────────────────

@app.post("/users/{user_id}/bills", status_code=201)
def add_bill(user_id: str, data: BillCreate, db: sqlite3.Connection = Depends(get_db)):
    bill_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO bills VALUES (?, ?, ?, ?, ?)",
        (bill_id, user_id, data.title, data.amount, data.due_date)
    )
    db.commit()
    return {"bill_id": bill_id, **data.dict()}


@app.get("/users/{user_id}/bills")
def get_bills(user_id: str, upcoming_only: bool = False, db: sqlite3.Connection = Depends(get_db)):
    query = "SELECT * FROM bills WHERE user_id = ?"
    params = [user_id]
    if upcoming_only:
        query += " AND due_date >= date('now') AND due_date <= date('now', '+30 days')"
    query += " ORDER BY due_date ASC"
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.delete("/users/{user_id}/bills/{bill_id}")
def delete_bill(user_id: str, bill_id: str, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM bills WHERE bill_id = ? AND user_id = ?", (bill_id, user_id))
    db.commit()
    return {"deleted": True}

# ── Goals ─────────────────────────────────────────────────────────────────────

@app.post("/users/{user_id}/goals", status_code=201)
def add_goal(user_id: str, data: GoalCreate, db: sqlite3.Connection = Depends(get_db)):
    goal_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO goals (goal_id, user_id, title, target_amount, deadline) VALUES (?,?,?,?,?)",
        (goal_id, user_id, data.title, data.target_amount, data.deadline)
    )
    db.commit()
    return {"goal_id": goal_id, **data.dict()}


@app.get("/users/{user_id}/goals")
def get_goals(user_id: str, db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        "SELECT *, ROUND(current_amount * 100.0 / target_amount, 1) AS progress_pct FROM goals WHERE user_id = ? ORDER BY is_complete, created_at DESC",
        (user_id,)
    ).fetchall()
    return [dict(r) for r in rows]


@app.patch("/users/{user_id}/goals/{goal_id}")
def update_goal_progress(
    user_id: str, goal_id: str,
    data: GoalProgressUpdate,
    db: sqlite3.Connection = Depends(get_db)
):
    row = db.execute(
        "SELECT target_amount FROM goals WHERE goal_id = ? AND user_id = ?",
        (goal_id, user_id)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Goal not found")
    is_complete = 1 if data.current_amount >= row["target_amount"] else 0
    db.execute(
        "UPDATE goals SET current_amount = ?, is_complete = ? WHERE goal_id = ? AND user_id = ?",
        (data.current_amount, is_complete, goal_id, user_id)
    )
    db.commit()
    return {"updated": True, "is_complete": bool(is_complete)}


@app.delete("/users/{user_id}/goals/{goal_id}")
def delete_goal(user_id: str, goal_id: str, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM goals WHERE goal_id = ? AND user_id = ?", (goal_id, user_id))
    db.commit()
    return {"deleted": True}

# ── Restaurants (CravingMode) ─────────────────────────────────────────────────

@app.get("/restaurants")
def get_restaurants(
    cheap_only:   bool = False,
    healthy_only: bool = False,
    category:     Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    query = "SELECT * FROM restaurants WHERE 1=1"
    params = []
    if cheap_only:   query += " AND is_cheap = 1"
    if healthy_only: query += " AND is_healthy = 1"
    if category:     query += " AND category = ?"; params.append(category)
    query += " ORDER BY rating DESC"
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]

# ── Cross-user analytics ───────────────────────────────────────────────────────

@app.get("/analytics/leaderboard")
def streak_leaderboard(db: sqlite3.Connection = Depends(get_db)):
    """Top users by streak — cross-user query."""
    rows = db.execute("""
        SELECT display_name, streak_count, personality_type
        FROM users
        ORDER BY streak_count DESC
        LIMIT 10
    """).fetchall()
    return [dict(r) for r in rows]


@app.get("/analytics/spending")
def platform_spending(db: sqlite3.Connection = Depends(get_db)):
    """Aggregate spend by category across all users."""
    rows = db.execute("""
        SELECT
            category,
            COUNT(DISTINCT user_id) AS user_count,
            ROUND(AVG(amount), 2)   AS avg_transaction,
            ROUND(SUM(amount), 2)   AS total_platform_spend
        FROM transactions
        WHERE txn_date >= date('now', '-30 days')
        GROUP BY category
    """).fetchall()
    return [dict(r) for r in rows]
