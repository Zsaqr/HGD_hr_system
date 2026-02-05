import os
import sqlite3
import secrets
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from datetime import datetime

APP_TITLE = "HR System Lite"
HOST = "127.0.0.1"
PORT = 8000
DB_PATH = os.path.join(os.path.dirname(__file__), "hr_lite.db")

# ---- Simple in-memory sessions (dev only) ----
SESSIONS = {}  # sid -> user_id

# ---- Security helpers (basic) ----
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def hash_password(password: str, salt: str) -> str:
    return sha256(salt + password)

def timing_safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))

# ---- DB helpers ----
def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      salt TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      is_admin INTEGER NOT NULL DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      full_name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      job_title TEXT DEFAULT '',
      hire_date TEXT DEFAULT '',
      department_id INTEGER NULL,
      FOREIGN KEY(department_id) REFERENCES departments(id)
    )
    """)

    # seed admin if not exists
    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    row = cur.fetchone()
    if not row:
        salt = secrets.token_hex(16)
        pw_hash = hash_password("admin123", salt)
        cur.execute(
            "INSERT INTO users (username, salt, password_hash, is_admin) VALUES (?, ?, ?, 1)",
            ("admin", salt, pw_hash)
        )

    conn.commit()
    conn.close()

# ---- Fancy UI (Dark NeonGreen) ----
THEME_CSS = """
:root{
  --bg0:#050705;
  --bg1:#070b07;
  --fg:#eaffea;
  --muted:#9bb69b;
  --card: rgba(10, 16, 10, 0.62);
  --border: rgba(57, 255, 20, 0.22);
  --border2: rgba(57, 255, 20, 0.38);
  --accent:#39ff14;
  --accent2:#15ffd6;
  --shadow: 0 14px 55px rgba(0,0,0,.55);
}

*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial;
  background:
    radial-gradient(1200px 700px at 15% 10%, rgba(57,255,20,.10), transparent 55%),
    radial-gradient(1000px 600px at 85% 20%, rgba(21,255,214,.08), transparent 60%),
    radial-gradient(900px 700px at 60% 90%, rgba(57,255,20,.06), transparent 60%),
    linear-gradient(180deg, var(--bg0), var(--bg1));
  color: var(--fg);
  overflow-x:hidden;
}

.wrap{max-width:1120px; margin:0 auto; padding:26px 18px 40px; position:relative; z-index:2}

/* --- animated background layers --- */
.bg{
  position:fixed; inset:0; z-index:0; pointer-events:none;
}
.bg::before{
  content:"";
  position:absolute; inset:-2px;
  background:
    linear-gradient(rgba(57,255,20,.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(57,255,20,.045) 1px, transparent 1px);
  background-size: 68px 68px;
  opacity:.25;
  filter: blur(.15px);
  transform: perspective(900px) rotateX(58deg) translateY(-180px);
  transform-origin: top;
  animation: gridFloat 10s linear infinite;
}
@keyframes gridFloat{
  0%{ background-position: 0 0, 0 0; }
  100%{ background-position: 0 220px, 220px 0; }
}
.bg::after{
  content:"";
  position:absolute; inset:-30%;
  background:
    radial-gradient(circle at 20% 20%, rgba(57,255,20,.18), transparent 40%),
    radial-gradient(circle at 85% 30%, rgba(21,255,214,.16), transparent 45%),
    radial-gradient(circle at 40% 90%, rgba(57,255,20,.14), transparent 42%);
  filter: blur(55px);
  opacity:.55;
  animation: blob 14s ease-in-out infinite;
}
@keyframes blob{
  0%,100%{ transform: translate3d(0,0,0) scale(1); }
  50%{ transform: translate3d(20px,-10px,0) scale(1.06); }
}

/* --- layout + components --- */
.card{
  border: 1px solid var(--border);
  background: var(--card);
  border-radius: 18px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(12px);
}

.nav{
  display:flex; gap:12px; flex-wrap:wrap; align-items:center; justify-content:space-between;
  margin-bottom:16px;
}

.brand{display:flex; align-items:center; gap:10px}
.dot{
  width:12px;height:12px;border-radius:999px;background:var(--accent);
  box-shadow:0 0 14px rgba(57,255,20,.75), 0 0 46px rgba(57,255,20,.18);
}

.h1{
  font-size:22px; font-weight:850; margin:0 0 12px;
  letter-spacing:.2px;
}
.small{font-size:12px; color:var(--muted); line-height:1.5}
.badge{
  display:inline-flex; align-items:center; gap:8px;
  padding:7px 10px; border-radius:999px;
  border:1px solid rgba(57,255,20,.28);
  background: rgba(57,255,20,.08);
}

.btn{
  position:relative;
  display:inline-flex; align-items:center; justify-content:center; gap:8px;
  padding:10px 14px; border-radius:14px;
  border: 1px solid var(--border2);
  color: var(--fg);
  background: rgba(57,255,20,.07);
  text-decoration:none;
  transition: transform .12s ease, box-shadow .22s ease, background .22s ease, border-color .22s ease;
  overflow:hidden;
  cursor:pointer;
}
.btn::before{
  content:"";
  position:absolute; inset:-40%;
  background: radial-gradient(circle at 30% 30%, rgba(255,255,255,.16), transparent 55%);
  transform: translateX(-30%) translateY(-10%) rotate(10deg);
  opacity:0;
  transition: opacity .22s ease;
}
.btn:hover{
  transform: translateY(-1px);
  box-shadow: 0 0 32px rgba(57,255,20,.10);
  background: rgba(57,255,20,.10);
  border-color: rgba(57,255,20,.60);
}
.btn:hover::before{ opacity:1; }
.btn:active{ transform: translateY(0); }

.btn.danger{
  border-color: rgba(255,60,60,.45);
  background: rgba(255,60,60,.08);
}
.btn.danger:hover{
  border-color: rgba(255,60,60,.70);
  box-shadow: 0 0 32px rgba(255,60,60,.10);
}

.input, select.input{
  width:100%;
  padding:10px 12px;
  border-radius:14px;
  border:1px solid rgba(57,255,20,.18);
  background: rgba(0,0,0,.25);
  color: var(--fg);
  outline:none;
  transition: box-shadow .2s ease, border-color .2s ease;
}
.input:focus, select.input:focus{
  border-color: rgba(57,255,20,.55);
  box-shadow: 0 0 0 3px rgba(57,255,20,.12);
}

.table{width:100%; border-collapse:collapse; overflow:hidden; border-radius:14px}
th,td{padding:11px 10px; border-bottom:1px solid rgba(57,255,20,.12); text-align:right; white-space:nowrap}
th{
  color: var(--muted);
  font-weight:700;
  background: rgba(0,0,0,.12);
}
tbody tr:nth-child(odd){ background: rgba(255,255,255,.02); }
tbody tr:hover{ background: rgba(57,255,20,.06); }

.grid{display:grid; grid-template-columns: 1fr 1fr; gap:12px}
@media (max-width:900px){.grid{grid-template-columns:1fr}}
"""

def page(title: str, body: str, user_logged_in: bool):
    nav = ""
    if user_logged_in:
        nav = f"""
        <div class="nav">
          <div class="brand">
            <div class="dot"></div>
            <div>
              <div style="font-weight:850">{APP_TITLE}</div>
              <div class="small">Lite Mode • Dark NeonGreen</div>
            </div>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap">
            <a class="btn" href="/">Dashboard</a>
            <a class="btn" href="/employees">Employees</a>
            <a class="btn" href="/departments">Departments</a>
            <a class="btn danger" href="/logout">Logout</a>
          </div>
        </div>
        """

    # Main card with subtle top glow (premium feel)
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{title}</title>
<style>{THEME_CSS}</style>
</head>
<body>
  <div class="bg"></div>
  <div class="wrap">
    {nav}

    <div class="card" style="position:relative; overflow:hidden; padding:18px">
      <div style="position:absolute; inset:0; pointer-events:none; opacity:.60;
        background: radial-gradient(900px 220px at 50% 0%, rgba(57,255,20,.10), transparent 65%);">
      </div>
      <div style="position:relative; z-index:1">
        {body}
      </div>
    </div>

    <div class="small" style="margin-top:12px">
      © Prototype • Stdlib + SQLite • {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>
  </div>
</body>
</html>"""

def redirect(handler, location: str):
    handler.send_response(302)
    handler.send_header("Location", location)
    handler.end_headers()

def read_post_form(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    data = handler.rfile.read(length).decode("utf-8")
    return parse_qs(data)

def get_cookie(handler, name: str):
    cookie = handler.headers.get("Cookie", "")
    parts = [p.strip() for p in cookie.split(";") if "=" in p]
    for p in parts:
        k, v = p.split("=", 1)
        if k.strip() == name:
            return v.strip()
    return None

def set_cookie(handler, name: str, value: str):
    handler.send_header("Set-Cookie", f"{name}={value}; Path=/; HttpOnly")

def current_user_id(handler):
    sid = get_cookie(handler, "sid")
    if not sid:
        return None
    return SESSIONS.get(sid)

class HRLiteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        q = parse_qs(parsed.query)

        uid = current_user_id(self)

        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if path == "/login":
            if uid:
                return redirect(self, "/")
            error = q.get("err", [""])[0]
            body = f"""
              <div class="brand" style="margin-bottom:14px">
                <div class="dot"></div>
                <div>
                  <div class="h1">تسجيل الدخول</div>
                  <div class="small">Default: <span style="color:var(--accent)">admin</span> / <span style="color:var(--accent)">admin123</span></div>
                </div>
              </div>

              {"<div class='card' style='border-color:rgba(255,60,60,0.45); background:rgba(255,60,60,0.08); padding:12px; margin-bottom:12px'>"
               + "<div style='font-weight:800; margin-bottom:6px'>خطأ</div><div class='small' style='color:#ffd6d6'>" + error + "</div></div>" if error else ""}

              <form method="post" action="/login">
                <div style="margin-bottom:10px">
                  <label class="small">Username</label>
                  <input class="input" name="username" placeholder="admin" required />
                </div>
                <div style="margin-bottom:12px">
                  <label class="small">Password</label>
                  <input class="input" type="password" name="password" placeholder="admin123" required />
                </div>
                <button class="btn" type="submit" style="width:100%">Login</button>
              </form>
            """
            html = page("Login", body, False)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/logout":
            sid = get_cookie(self, "sid")
            if sid and sid in SESSIONS:
                del SESSIONS[sid]
            self.send_response(302)
            set_cookie(self, "sid", "deleted")
            self.send_header("Location", "/login")
            self.end_headers()
            return

        if not uid:
            return redirect(self, "/login")

        if path == "/":
            body = """
              <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap">
                <div class="h1" style="margin:0">Dashboard</div>
                <div class="badge">MVP Lite</div>
              </div>

              <div class="grid" style="margin-top:14px">
                <div class="card" style="padding:14px">
                  <div style="font-weight:900; margin-bottom:6px">Employees</div>
                  <div class="small" style="margin-bottom:12px">إضافة / حذف الموظفين بسرعة.</div>
                  <a class="btn" href="/employees">Open Employees</a>
                </div>

                <div class="card" style="padding:14px">
                  <div style="font-weight:900; margin-bottom:6px">Departments</div>
                  <div class="small" style="margin-bottom:12px">إدارة الأقسام وربطها.</div>
                  <a class="btn" href="/departments">Open Departments</a>
                </div>
              </div>

              <div class="card" style="padding:14px; margin-top:12px">
                <div style="font-weight:900; margin-bottom:6px">Note</div>
                <div class="small">ده تشغيل فوري بدون pip. لما PostgreSQL يجهز هنرجع FastAPI + PostgreSQL.</div>
              </div>
            """
            html = page("Dashboard", body, True)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/departments":
            conn = db_connect()
            deps = conn.execute("SELECT id, name FROM departments ORDER BY name").fetchall()
            conn.close()

            rows = ""
            for d in deps:
                rows += f"""
                <tr>
                  <td>{d['id']}</td>
                  <td>{d['name']}</td>
                  <td>
                    <form method="post" action="/departments/delete" style="margin:0">
                      <input type="hidden" name="id" value="{d['id']}" />
                      <button class="btn danger" type="submit">Delete</button>
                    </form>
                  </td>
                </tr>
                """
            if not rows:
                rows = "<tr><td colspan='3' class='small'>No departments yet.</td></tr>"

            body = f"""
              <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap">
                <div class="h1" style="margin:0">Departments</div>
              </div>

              <div class="sep"></div>

              <form method="post" action="/departments/new" style="margin:12px 0">
                <div class="grid">
                  <div>
                    <label class="small">Name</label>
                    <input class="input" name="name" placeholder="e.g. Engineering" required />
                  </div>
                  <div style="display:flex; align-items:end">
                    <button class="btn" type="submit" style="width:100%">+ Create Department</button>
                  </div>
                </div>
              </form>

              <div style="overflow:auto">
                <table class="table">
                  <thead><tr><th>ID</th><th>Name</th><th>Actions</th></tr></thead>
                  <tbody>{rows}</tbody>
                </table>
              </div>
            """
            html = page("Departments", body, True)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/employees":
            conn = db_connect()
            emps = conn.execute("""
              SELECT e.id, e.full_name, e.email, e.job_title, e.hire_date, d.name AS dep_name
              FROM employees e
              LEFT JOIN departments d ON d.id = e.department_id
              ORDER BY e.full_name
            """).fetchall()
            deps = conn.execute("SELECT id, name FROM departments ORDER BY name").fetchall()
            conn.close()

            dep_options = "<option value=''>-- None --</option>"
            for d in deps:
                dep_options += f"<option value='{d['id']}'>{d['name']}</option>"

            rows = ""
            for e in emps:
                rows += f"""
                <tr>
                  <td>{e['id']}</td>
                  <td>{e['full_name']}</td>
                  <td>{e['email']}</td>
                  <td>{e['job_title'] or '-'}</td>
                  <td>{e['dep_name'] or '-'}</td>
                  <td>{e['hire_date'] or '-'}</td>
                  <td>
                    <form method="post" action="/employees/delete" style="margin:0">
                      <input type="hidden" name="id" value="{e['id']}" />
                      <button class="btn danger" type="submit">Delete</button>
                    </form>
                  </td>
                </tr>
                """
            if not rows:
                rows = "<tr><td colspan='7' class='small'>No employees yet.</td></tr>"

            body = f"""
              <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap">
                <div class="h1" style="margin:0">Employees</div>
              </div>

              <div class="sep"></div>

              <form method="post" action="/employees/new" style="margin:12px 0">
                <div class="grid">
                  <div>
                    <label class="small">Full Name</label>
                    <input class="input" name="full_name" placeholder="e.g. Ziad Muhammed" required />
                  </div>
                  <div>
                    <label class="small">Email</label>
                    <input class="input" name="email" placeholder="name@company.com" required />
                  </div>
                  <div>
                    <label class="small">Job Title</label>
                    <input class="input" name="job_title" placeholder="e.g. HR Specialist" />
                  </div>
                  <div>
                    <label class="small">Hire Date</label>
                    <input class="input" name="hire_date" placeholder="YYYY-MM-DD" />
                  </div>
                  <div style="grid-column:1 / -1">
                    <label class="small">Department</label>
                    <select class="input" name="department_id">
                      {dep_options}
                    </select>
                    <div class="small" style="margin-top:6px">لو مفيش Departments اعملها الأول.</div>
                  </div>
                  <div style="grid-column:1 / -1">
                    <button class="btn" type="submit" style="width:100%">+ Create Employee</button>
                  </div>
                </div>
              </form>

              <div style="overflow:auto">
                <table class="table">
                  <thead>
                    <tr>
                      <th>ID</th><th>Full Name</th><th>Email</th><th>Job</th><th>Department</th><th>Hire Date</th><th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>{rows}</tbody>
                </table>
              </div>
            """
            html = page("Employees", body, True)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/login":
            form = read_post_form(self)
            username = (form.get("username", [""])[0] or "").strip()
            password = (form.get("password", [""])[0] or "").strip()

            conn = db_connect()
            row = conn.execute(
                "SELECT id, salt, password_hash FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            conn.close()

            if not row:
                return redirect(self, "/login?err=بيانات+غير+صحيحة")

            candidate = hash_password(password, row["salt"])
            if not timing_safe_equals(candidate, row["password_hash"]):
                return redirect(self, "/login?err=بيانات+غير+صحيحة")

            sid = secrets.token_urlsafe(24)
            SESSIONS[sid] = row["id"]

            self.send_response(302)
            set_cookie(self, "sid", sid)
            self.send_header("Location", "/")
            self.end_headers()
            return

        uid = current_user_id(self)
        if not uid:
            return redirect(self, "/login")

        if path == "/departments/new":
            form = read_post_form(self)
            name = (form.get("name", [""])[0] or "").strip()
            if name:
                conn = db_connect()
                try:
                    conn.execute("INSERT INTO departments (name) VALUES (?)", (name,))
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass
                finally:
                    conn.close()
            return redirect(self, "/departments")

        if path == "/departments/delete":
            form = read_post_form(self)
            dep_id = (form.get("id", [""])[0] or "").strip()
            if dep_id.isdigit():
                conn = db_connect()
                conn.execute("UPDATE employees SET department_id = NULL WHERE department_id = ?", (int(dep_id),))
                conn.execute("DELETE FROM departments WHERE id = ?", (int(dep_id),))
                conn.commit()
                conn.close()
            return redirect(self, "/departments")

        if path == "/employees/new":
            form = read_post_form(self)
            full_name = (form.get("full_name", [""])[0] or "").strip()
            email = (form.get("email", [""])[0] or "").strip().lower()
            job_title = (form.get("job_title", [""])[0] or "").strip()
            hire_date = (form.get("hire_date", [""])[0] or "").strip()
            dep_id = (form.get("department_id", [""])[0] or "").strip()

            dep_val = None
            if dep_id.isdigit():
                dep_val = int(dep_id)

            if full_name and email:
                conn = db_connect()
                try:
                    conn.execute("""
                      INSERT INTO employees (full_name, email, job_title, hire_date, department_id)
                      VALUES (?, ?, ?, ?, ?)
                    """, (full_name, email, job_title, hire_date, dep_val))
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass
                finally:
                    conn.close()
            return redirect(self, "/employees")

        if path == "/employees/delete":
            form = read_post_form(self)
            emp_id = (form.get("id", [""])[0] or "").strip()
            if emp_id.isdigit():
                conn = db_connect()
                conn.execute("DELETE FROM employees WHERE id = ?", (int(emp_id),))
                conn.commit()
                conn.close()
            return redirect(self, "/employees")

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not Found")

def main():
    init_db()
    server = HTTPServer((HOST, PORT), HRLiteHandler)
    print(f"[OK] {APP_TITLE} running at: http://{HOST}:{PORT}")
    print("[Login] admin / admin123")
    print(f"[DB] SQLite: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")
        server.server_close()

if __name__ == "__main__":
    main()
