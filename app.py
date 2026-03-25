from flask import Flask, render_template, request, redirect, session
import sqlite3, datetime, os
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "akiba_secret_2024")
bcrypt = Bcrypt(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        balance INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        category TEXT,
        date TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS goals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        target INTEGER,
        saved INTEGER
    )""")
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        conn.close()
        if user and bcrypt.check_password_hash(user["password"], p):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")
        error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        hashed = bcrypt.generate_password_hash(p).decode("utf-8")
        try:
            conn = db()
            conn.execute("INSERT INTO users(username,password) VALUES(?,?)", (u, hashed))
            conn.commit()
            conn.close()
            return redirect("/")
        except sqlite3.IntegrityError:
            error = "Username already exists"
    return render_template("register.html", error=error)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    uid = session["user_id"]
    conn = db()
    accounts = conn.execute("SELECT name, balance FROM accounts WHERE user_id=?", (uid,)).fetchall()
    expenses = conn.execute("SELECT amount, category, date FROM expenses WHERE user_id=? ORDER BY date DESC LIMIT 10", (uid,)).fetchall()
    goal = conn.execute("SELECT target, saved FROM goals WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    total = sum([a["balance"] for a in accounts]) if accounts else 0
    dates = [e["date"] for e in expenses]
    amounts = [e["amount"] for e in expenses]
    advice = "Good progress! Keep saving 👍"
    if goal:
        target, saved = goal["target"], goal["saved"]
        pct = (saved / target * 100) if target > 0 else 0
        if pct >= 100:
            advice = "🎉 Goal reached! Set a new target!"
        elif pct >= 75:
            advice = "🔥 Almost there! You're at {}% of your goal!".format(int(pct))
        elif pct >= 50:
            advice = "💪 Halfway there! Keep pushing!"
        else:
            advice = "⚠️ Reduce daily spending to reach your goal faster"
    return render_template("dashboard.html",
        accounts=accounts, total=total, dates=dates,
        amounts=amounts, goal=goal, advice=advice,
        username=session.get("username", "User"), recent_expenses=expenses)

@app.route("/add_account", methods=["POST"])
def add_account():
    if "user_id" not in session:
        return redirect("/")
    uid = session["user_id"]
    conn = db()
    conn.execute("INSERT INTO accounts(user_id,name,balance) VALUES(?,?,?)",
        (uid, request.form["name"], request.form["balance"]))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/")
    uid = session["user_id"]
    conn = db()
    conn.execute("INSERT INTO expenses(user_id,amount,category,date) VALUES(?,?,?,?)",
        (uid, request.form["amount"], request.form["category"], str(datetime.date.today())))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/set_goal", methods=["POST"])
def set_goal():
    if "user_id" not in session:
        return redirect("/")
    uid = session["user_id"]
    conn = db()
    conn.execute("DELETE FROM goals WHERE user_id=?", (uid,))
    conn.execute("INSERT INTO goals(user_id,target,saved) VALUES(?,?,?)",
        (uid, request.form["target"], request.form["saved"]))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(debug=False)
