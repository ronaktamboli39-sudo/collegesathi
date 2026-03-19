from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "collegesaathi_secret_123"
DB = "carpool.db"

# ─────────────────────────────────────────────
#  DB helpers
# ─────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rides (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id      INTEGER NOT NULL,
            start_location TEXT NOT NULL,
            ride_date      TEXT NOT NULL DEFAULT '',
            ride_day       TEXT NOT NULL DEFAULT '',
            time           TEXT NOT NULL,
            seats          INTEGER NOT NULL,
            active         INTEGER DEFAULT 1,
            FOREIGN KEY(driver_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS route_points (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id      INTEGER NOT NULL,
            location     TEXT NOT NULL,
            order_number INTEGER NOT NULL,
            FOREIGN KEY(ride_id) REFERENCES rides(id)
        );
        CREATE TABLE IF NOT EXISTS requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id      INTEGER NOT NULL,
            passenger_id INTEGER NOT NULL,
            offer_price  REAL NOT NULL,
            status       TEXT DEFAULT 'pending',
            FOREIGN KEY(ride_id)      REFERENCES rides(id),
            FOREIGN KEY(passenger_id) REFERENCES users(id)
        );
    """)
    # Migrate existing DBs that don't yet have ride_date / ride_day columns
    existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(rides)").fetchall()]
    if "ride_date" not in existing_cols:
        conn.execute("ALTER TABLE rides ADD COLUMN ride_date TEXT NOT NULL DEFAULT ''")
    if "ride_day" not in existing_cols:
        conn.execute("ALTER TABLE rides ADD COLUMN ride_day TEXT NOT NULL DEFAULT ''")
    conn.commit()
    conn.close()

def to_ampm(time_24: str) -> str:
    """Convert '14:30' (from HTML time input) to '2:30 PM'."""
    try:
        from datetime import datetime
        return datetime.strptime(time_24, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except Exception:
        return time_24

def to_24h(time_ampm: str) -> str:
    """Convert '2:30 PM' back to '14:30' for HTML time input value."""
    try:
        from datetime import datetime
        for fmt in ("%I:%M %p", "%I:%M%p"):
            try:
                return datetime.strptime(time_ampm.strip(), fmt).strftime("%H:%M")
            except ValueError:
                continue
        return ""
    except Exception:
        return ""

def get_pending_count(uid):
    conn = get_db()
    count = conn.execute("""
        SELECT COUNT(*) FROM requests rq
        JOIN rides r ON r.id = rq.ride_id
        WHERE r.driver_id = ? AND rq.status = 'pending'
    """, (uid,)).fetchone()[0]
    conn.close()
    return count

def get_route_string(conn, ride_id):
    pts = conn.execute(
        "SELECT location FROM route_points WHERE ride_id=? ORDER BY order_number",
        (ride_id,)
    ).fetchall()
    return " → ".join(p["location"] for p in pts)

def save_route_points(conn, ride_id, start, vias):
    conn.execute("DELETE FROM route_points WHERE ride_id=?", (ride_id,))
    conn.execute(
        "INSERT INTO route_points (ride_id, location, order_number) VALUES (?,?,?)",
        (ride_id, start, 0)
    )
    for i, via in enumerate(vias, start=1):
        if via.strip():
            conn.execute(
                "INSERT INTO route_points (ride_id, location, order_number) VALUES (?,?,?)",
                (ride_id, via.strip(), i)
            )
    conn.execute(
        "INSERT INTO route_points (ride_id, location, order_number) VALUES (?,?,?)",
        (ride_id, "College", len(vias) + 1)
    )

def build_ride_list(conn, uid, rides_raw):
    """
    Given a list of ride rows (not created by uid), return a list of dicts with
    ride, route string, and existing request status for this passenger.
    """
    result = []
    for ride in rides_raw:
        route = get_route_string(conn, ride["id"])
        existing = conn.execute(
            "SELECT id, offer_price, status FROM requests WHERE ride_id=? AND passenger_id=?",
            (ride["id"], uid)
        ).fetchone()
        result.append({"ride": ride, "route": route, "existing": existing})
    return result

# ─────────────────────────────────────────────
#  Auth
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form["name"].strip()
        email    = request.form["email"].strip()
        password = request.form["password"]
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?,?,?)",
                (name, email, password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="This email is already registered.")
        conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"].strip()
        password = request.form["password"]
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()
        if user:
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Wrong email or password.")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    uid  = session["user_id"]
    conn = get_db()

    # ── My rides as driver ──
    my_rides_raw = conn.execute("""
        SELECT * FROM rides WHERE driver_id=? AND active=1 ORDER BY time ASC
    """, (uid,)).fetchall()
    my_rides = []
    for ride in my_rides_raw:
        route = get_route_string(conn, ride["id"])
        my_rides.append({"ride": ride, "route": route})

    # ── All available rides from OTHER drivers (passenger view) ──
    all_rides_raw = conn.execute("""
        SELECT r.*, u.name AS driver_name
        FROM rides r
        JOIN users u ON u.id = r.driver_id
        WHERE r.active = 1 AND r.driver_id != ?
        ORDER BY r.time ASC
    """, (uid,)).fetchall()
    all_rides = build_ride_list(conn, uid, all_rides_raw)

    # ── My requests as passenger ──
    my_requests = conn.execute("""
        SELECT rq.*, r.id AS ride_id, r.start_location, r.ride_date, r.ride_day, r.time, u.name AS driver_name
        FROM requests rq
        JOIN rides r ON r.id = rq.ride_id
        JOIN users u ON u.id = r.driver_id
        WHERE rq.passenger_id = ?
        ORDER BY rq.id DESC
    """, (uid,)).fetchall()

    pending_count = get_pending_count(uid)
    conn.close()

    return render_template("dashboard.html",
        my_rides=my_rides,
        all_rides=all_rides,
        my_requests=my_requests,
        pending_count=pending_count
    )

# ─────────────────────────────────────────────
#  Create Ride
# ─────────────────────────────────────────────

@app.route("/create_ride", methods=["GET", "POST"])
def create_ride():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        uid        = session["user_id"]
        start      = request.form["start_location"].strip()
        ride_date  = request.form["ride_date"].strip()       # e.g. "2025-03-20"
        ride_day   = request.form["ride_day"].strip()        # e.g. "Thursday"
        time_raw   = request.form["time"].strip()            # e.g. "08:30" (24h from input)
        time_ampm  = to_ampm(time_raw)                       # e.g. "8:30 AM"
        seats      = int(request.form["seats"])
        vias       = request.form.getlist("via[]")
        conn = get_db()
        cur  = conn.execute(
            "INSERT INTO rides (driver_id, start_location, ride_date, ride_day, time, seats) VALUES (?,?,?,?,?,?)",
            (uid, start, ride_date, ride_day, time_ampm, seats)
        )
        ride_id = cur.lastrowid
        save_route_points(conn, ride_id, start, vias)
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    return render_template("create_ride.html")

# ─────────────────────────────────────────────
#  Update Ride (daily update)
# ─────────────────────────────────────────────

@app.route("/update_ride/<int:ride_id>", methods=["GET", "POST"])
def update_ride(ride_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    uid  = session["user_id"]
    conn = get_db()
    ride = conn.execute(
        "SELECT * FROM rides WHERE id=? AND driver_id=? AND active=1",
        (ride_id, uid)
    ).fetchone()
    if not ride:
        conn.close()
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "cancel":
            conn.execute("UPDATE rides SET active=0 WHERE id=?", (ride_id,))
            conn.commit()
            conn.close()
            return redirect(url_for("dashboard"))
        if action == "keep":
            conn.close()
            return redirect(url_for("dashboard"))
        # update
        start      = request.form["start_location"].strip()
        ride_date  = request.form["ride_date"].strip()
        ride_day   = request.form["ride_day"].strip()
        time_raw   = request.form["time"].strip()
        time_ampm  = to_ampm(time_raw)
        seats      = int(request.form["seats"])
        vias       = request.form.getlist("via[]")
        conn.execute(
            "UPDATE rides SET start_location=?, ride_date=?, ride_day=?, time=?, seats=? WHERE id=?",
            (start, ride_date, ride_day, time_ampm, seats, ride_id)
        )
        save_route_points(conn, ride_id, start, vias)
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    all_points = conn.execute(
        "SELECT location FROM route_points WHERE ride_id=? ORDER BY order_number",
        (ride_id,)
    ).fetchall()
    via_points = [p["location"] for p in all_points[1:-1]]
    conn.close()
    return render_template("update_ride.html", ride=ride, via_points=via_points,
                           time_24=to_24h(ride["time"]))

# ─────────────────────────────────────────────
#  Cancel Ride
# ─────────────────────────────────────────────

@app.route("/cancel_ride/<int:ride_id>", methods=["POST"])
def cancel_ride(ride_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute(
        "UPDATE rides SET active=0 WHERE id=? AND driver_id=?",
        (ride_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

# ─────────────────────────────────────────────
#  Search  (landmark-based, priority sorting)
# ─────────────────────────────────────────────

@app.route("/search", methods=["GET", "POST"])
def search():
    if "user_id" not in session:
        return redirect(url_for("login"))

    matched   = []   # rides where landmark is in start OR via  ← shown first / highlighted
    others    = []   # all other active rides from other drivers
    query     = ""
    uid       = session["user_id"]

    conn = get_db()

    # Always fetch all active rides from other drivers (shown by default on GET too)
    all_rides_raw = conn.execute("""
        SELECT r.*, u.name AS driver_name
        FROM rides r JOIN users u ON u.id = r.driver_id
        WHERE r.active = 1 AND r.driver_id != ?
        ORDER BY r.time ASC
    """, (uid,)).fetchall()

    if request.method == "POST":
        query = request.form["location"].strip()

        for ride in all_rides_raw:
            route = get_route_string(conn, ride["id"])
            existing = conn.execute(
                "SELECT id, offer_price, status FROM requests WHERE ride_id=? AND passenger_id=?",
                (ride["id"], uid)
            ).fetchone()

            # Check if landmark matches start OR any via point (excluding College)
            pts = conn.execute("""
                SELECT location, order_number FROM route_points
                WHERE ride_id=? ORDER BY order_number
            """, (ride["id"],)).fetchall()

            match_type = None
            for pt in pts:
                loc = pt["location"].lower()
                if query.lower() in loc and pt["location"] != "College":
                    match_type = "start" if pt["order_number"] == 0 else "via"
                    break

            item = {"ride": ride, "route": route, "existing": existing, "match_type": match_type}

            if match_type:
                matched.append(item)   # landmark found → show at top
            else:
                others.append(item)    # no match → show below

    else:
        # GET request — show ALL rides (no filter, all go into others)
        for ride in all_rides_raw:
            route = get_route_string(conn, ride["id"])
            existing = conn.execute(
                "SELECT id, offer_price, status FROM requests WHERE ride_id=? AND passenger_id=?",
                (ride["id"], uid)
            ).fetchone()
            others.append({"ride": ride, "route": route, "existing": existing, "match_type": None})

    conn.close()
    pending_count = get_pending_count(uid)
    return render_template("search.html",
        matched=matched,
        others=others,
        query=query,
        pending_count=pending_count
    )

# ─────────────────────────────────────────────
#  Send / Update Request
# ─────────────────────────────────────────────

@app.route("/send_request/<int:ride_id>", methods=["POST"])
def send_request(ride_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    offer = float(request.form["offer_price"])
    uid   = session["user_id"]
    conn  = get_db()
    existing = conn.execute(
        "SELECT id FROM requests WHERE ride_id=? AND passenger_id=?",
        (ride_id, uid)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE requests SET offer_price=?, status='pending' WHERE ride_id=? AND passenger_id=?",
            (offer, ride_id, uid)
        )
    else:
        conn.execute(
            "INSERT INTO requests (ride_id, passenger_id, offer_price) VALUES (?,?,?)",
            (ride_id, uid, offer)
        )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

# ─────────────────────────────────────────────
#  Driver – View & Handle Requests
# ─────────────────────────────────────────────

@app.route("/driver_requests")
def driver_requests():
    if "user_id" not in session:
        return redirect(url_for("login"))
    uid  = session["user_id"]
    conn = get_db()
    reqs = conn.execute("""
        SELECT rq.*, u.name AS passenger_name,
               r.start_location, r.ride_date, r.ride_day, r.time, r.id AS the_ride_id
        FROM requests rq
        JOIN users u ON u.id = rq.passenger_id
        JOIN rides  r ON r.id = rq.ride_id
        WHERE r.driver_id = ? AND rq.status = 'pending'
        ORDER BY rq.id DESC
    """, (uid,)).fetchall()
    requests_with_route = []
    for rq in reqs:
        route = get_route_string(conn, rq["the_ride_id"])
        requests_with_route.append({"req": rq, "route": route})
    pending_count = get_pending_count(uid)
    conn.close()
    return render_template("driver_requests.html",
        requests=requests_with_route,
        pending_count=pending_count
    )

@app.route("/handle_request/<int:req_id>", methods=["POST"])
def handle_request(req_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    action = request.form["action"]
    conn   = get_db()
    conn.execute("UPDATE requests SET status=? WHERE id=?", (action + "ed", req_id))
    conn.commit()
    conn.close()
    return redirect(url_for("driver_requests"))

# ─────────────────────────────────────────────
#  Run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
