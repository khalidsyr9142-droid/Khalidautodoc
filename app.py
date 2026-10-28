import os, sqlite3
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, send_file, abort, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "autodochub.db")
UPLOAD_DIR = os.path.join(APP_DIR, "private_documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE-THIS-TO-A-LONG-RANDOM-SECRET")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# Set these before public deployment:
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
UPI_ID = os.environ.get("UPI_ID", "yourupi@bank")
PAYEE_NAME = os.environ.get("PAYEE_NAME", "AutoDocHub")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, is_admin INTEGER DEFAULT 0)""")
        con.execute("""CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            category TEXT NOT NULL, description TEXT, price INTEGER NOT NULL,
            filename TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        con.execute("""CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            document_id INTEGER NOT NULL, utr TEXT NOT NULL, status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, document_id, utr))""")
        con.execute("""CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            document_id INTEGER NOT NULL, UNIQUE(user_id, document_id))""")
        row = con.execute("SELECT id FROM users WHERE username=?", (ADMIN_USERNAME,)).fetchone()
        if not row:
            con.execute("INSERT INTO users(username,password_hash,is_admin) VALUES(?,?,1)",
                        (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD)))
init_db()

CSS = """
:root{--navy:#0b1422;--blue:#1687f8;--ink:#101a2d;--muted:#5c6a82;--line:#dce5f0}
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:var(--ink);background:#f5f8fc}
a{color:inherit;text-decoration:none}.top{background:var(--navy);color:white;padding:18px 5%;display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap}
.brand{font-size:25px;font-weight:800}.brand span{color:#2597ff}.nav a{margin-left:18px;font-size:14px}
.hero{padding:45px 5%;color:white;background:linear-gradient(115deg,#07111f,#153252);display:flex;justify-content:space-between;gap:30px;align-items:center}
.hero h1{font-size:clamp(30px,5vw,50px);margin:8px 0}.hero h1 span{color:#2799ff}.hero p{line-height:1.7;color:#d8e6f6;max-width:650px}
.wrap{max-width:1200px;margin:30px auto;padding:0 20px}.row{display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px;margin-top:20px}
.card,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:20px;box-shadow:0 5px 18px #152e4b0a}
.card .icon{font-size:35px;background:#e9f3ff;padding:14px;border-radius:10px;display:inline-block}
.muted{color:var(--muted);font-size:14px;line-height:1.5}.price{font-size:22px;color:#0754c5;font-weight:800;margin:15px 0}
.btn{display:inline-block;background:var(--blue);color:white;border:0;padding:11px 16px;border-radius:8px;font-weight:700;cursor:pointer}
.btn.secondary{background:#eaf2fb;color:#17385e}.btn.danger{background:#c83535}
input,select,textarea{width:100%;padding:12px;border:1px solid #cbd7e5;border-radius:8px;margin:6px 0 14px;font:inherit}
label{font-size:14px;font-weight:700}form{max-width:620px}.notice{padding:12px 15px;background:#e9f5ff;border-radius:8px;margin:12px 0}
table{width:100%;border-collapse:collapse;background:white}td,th{text-align:left;padding:12px;border-bottom:1px solid var(--line);font-size:14px}
.footer{margin-top:45px;background:var(--navy);color:#d5dfec;padding:25px 5%;font-size:13px}
"""
BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ title }} | AutoDocHub</title><style>""" + CSS + """</style></head><body>
<header class="top"><a class="brand" href="/">AutoDoc<span>Hub</span></a><nav class="nav"><a href="/">Home</a><a href="/my-purchases">My Purchases</a>{% if session.get('user_id') %}<a href="/logout">Logout</a>{% else %}<a href="/login">Login</a><a href="/signup">Sign Up</a>{% endif %}{% if session.get('is_admin') %}<a href="/admin">Admin</a>{% endif %}</nav></header>
{% with messages=get_flashed_messages() %}{% if messages %}<div class="wrap">{% for m in messages %}<div class="notice">{{m}}</div>{% endfor %}</div>{% endif %}{% endwith %}
{{ body|safe }}<footer class="footer">AutoDocHub · Motorcycle Documents · Secure Access<br><br>Only upload and sell motorcycle documents you own or are authorized to distribute.</footer></body></html>"""

def page(title, body, **context):
    return render_template_string(BASE, title=title, body=render_template_string(body, **context), session=session)

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in or create an account first.")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    with db() as con:
        docs = con.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
    body = """
    <section class="hero"><div><div>WELCOME TO AUTODOCHUB</div><h1>Buy. View. Download.<br><span>Motorcycle Documents.</span></h1>
    <p>Find motorcycle service manuals, bike wiring diagrams, engine repair guides, ECU diagrams and technical references. Documents unlock only after your payment is approved.</p>
    <p>🔒 Secure access &nbsp; · &nbsp; 💳 UPI payment review &nbsp; · &nbsp; 📄 Download after approval</p></div></section>
    <main class="wrap"><div class="row"><div><h2>Motorcycle Documents</h2><p class="muted">Choose a document to see its details and price.</p></div></div>
    {% if docs %}<div class="grid">{% for d in docs %}<article class="card"><div class="icon">📄</div><h3>{{d['title']}}</h3><div class="muted">{{d['category']}}</div><p class="muted">{{d['description'] or 'Motorcycle technical document.'}}</p><div class="price">₹{{d['price']}}</div><a class="btn" href="/document/{{d['id']}}">View Details</a></article>{% endfor %}</div>{% else %}<div class="panel"><h3>Documents coming soon</h3><p class="muted">The administrator can log in and upload the first document.</p></div>{% endif %}</main>"""
    return page("Home", body, docs=docs)

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        if len(username) < 3 or len(password) < 8:
            flash("Use a username of at least 3 characters and password of at least 8 characters.")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",
                                (username, generate_password_hash(password)))
                flash("Account created. Please log in.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username is already taken.")
    return page("Sign Up", """<main class="wrap"><div class="panel"><h2>Create account</h2><form method="post"><label>Username</label><input name="username" required minlength="3"><label>Password (minimum 8 characters)</label><input type="password" name="password" required minlength="8"><button class="btn">Sign Up</button></form></div></main>""")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE username=?", (request.form.get("username","").strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password","")):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            return redirect(url_for("admin" if user["is_admin"] else "home"))
        flash("Incorrect username or password.")
    return page("Login", """<main class="wrap"><div class="panel"><h2>Login</h2><form method="post"><label>Username</label><input name="username" required><label>Password</label><input type="password" name="password" required><button class="btn">Login</button></form></div></main>""")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/document/<int:doc_id>")
def document(doc_id):
    with db() as con:
        d = con.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        owned = False
        if session.get("user_id"):
            owned = con.execute("SELECT 1 FROM purchases WHERE user_id=? AND document_id=?",
                                (session["user_id"], doc_id)).fetchone() is not None
    if not d: abort(404)
    body = """<main class="wrap"><div class="panel"><h2>{{d['title']}}</h2><p class="muted">{{d['category']}}</p><p>{{d['description'] or 'Motorcycle technical document.'}}</p><div class="price">₹{{d['price']}}</div>
    {% if owned %}<div class="notice">Payment approved — you own this document.</div><a class="btn" href="/download/{{d['id']}}">Download Document</a>
    {% else %}<p class="muted">This file stays locked until payment is verified by the administrator.</p><a class="btn" href="/pay/{{d['id']}}">Pay by UPI / QR</a>{% endif %}</div></main>"""
    return page(d["title"], body, d=d, owned=owned)

@app.route("/pay/<int:doc_id>", methods=["GET","POST"])
@login_required
def pay(doc_id):
    with db() as con:
        d = con.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        owned = con.execute("SELECT 1 FROM purchases WHERE user_id=? AND document_id=?",
                            (session["user_id"], doc_id)).fetchone()
    if not d: abort(404)
    if owned: return redirect(url_for("document", doc_id=doc_id))
    if request.method == "POST":
        utr = request.form.get("utr","").strip()
        if len(utr) < 6:
            flash("Enter the UPI transaction reference / UTR after paying.")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO payments(user_id,document_id,utr) VALUES(?,?,?)",
                                (session["user_id"], doc_id, utr))
                flash("Payment reference submitted. Your document unlocks after admin verification.")
                return redirect(url_for("my_purchases"))
            except sqlite3.IntegrityError:
                flash("This transaction reference was already submitted.")
    upi_link = f"upi://pay?pa={UPI_ID}&pn={PAYEE_NAME.replace(' ','%20')}&am={d['price']}&cu=INR&tn=AutoDocHub%20Doc%20{doc_id}"
    body = """<main class="wrap"><div class="panel"><h2>Pay for {{d['title']}}</h2><p>Amount: <b>₹{{d['price']}}</b></p><div class="notice">Pay using your UPI app, then submit the UTR / transaction reference below. Access is granted only after manual verification.</div><p><b>UPI ID:</b> {{upi_id}}</p><a class="btn" href="{{upi_link}}">Open UPI App</a><p class="muted">For QR payments, add your own UPI QR image to this page before publishing.</p><hr><form method="post"><label>UPI Transaction Reference / UTR</label><input name="utr" required minlength="6" placeholder="Enter UTR / transaction ID"><button class="btn">Submit for Verification</button></form></div></main>"""
    return page("Payment", body, d=d, upi_id=UPI_ID, upi_link=upi_link)

@app.route("/my-purchases")
@login_required
def my_purchases():
    with db() as con:
        purchases = con.execute("""SELECT d.* FROM purchases p JOIN documents d ON d.id=p.document_id
                                   WHERE p.user_id=? ORDER BY p.id DESC""", (session["user_id"],)).fetchall()
        payments = con.execute("""SELECT p.*, d.title FROM payments p JOIN documents d ON d.id=p.document_id
                                  WHERE p.user_id=? ORDER BY p.id DESC""", (session["user_id"],)).fetchall()
    body = """<main class="wrap"><h2>My Purchases</h2><div class="grid">{% for d in purchases %}<div class="card"><h3>{{d['title']}}</h3><a class="btn" href="/download/{{d['id']}}">Download</a></div>{% else %}<p class="muted">No unlocked documents yet.</p>{% endfor %}</div><h2>Payment Requests</h2><div class="panel"><table><tr><th>Document</th><th>UTR</th><th>Status</th></tr>{% for p in payments %}<tr><td>{{p['title']}}</td><td>{{p['utr']}}</td><td>{{p['status'].title()}}</td></tr>{% else %}<tr><td colspan="3">No payment requests submitted.</td></tr>{% endfor %}</table></div></main>"""
    return page("My Purchases", body, purchases=purchases, payments=payments)

@app.route("/download/<int:doc_id>")
@login_required
def download(doc_id):
    with db() as con:
        owned = con.execute("SELECT 1 FROM purchases WHERE user_id=? AND document_id=?",
                            (session["user_id"], doc_id)).fetchone()
        d = con.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not d: abort(404)
    if not owned and not session.get("is_admin"): abort(403)
    path = os.path.join(UPLOAD_DIR, d["filename"])
    if not os.path.isfile(path): abort(404)
    return send_file(path, as_attachment=True, download_name=secure_filename(d["title"]) + os.path.splitext(path)[1])

@app.route("/admin", methods=["GET","POST"])
@admin_required
def admin():
    if request.method == "POST" and request.form.get("action") == "upload":
        title = request.form.get("title","").strip()
        category = request.form.get("category","").strip()
        description = request.form.get("description","").strip()
        try: price = int(request.form.get("price","0"))
        except ValueError: price = 0
        f = request.files.get("document")
        if not title or not category or price < 1 or not f or not f.filename:
            flash("Fill all fields and choose a file. Price must be at least ₹1.")
        else:
            original = secure_filename(f.filename)
            stored = f"{os.urandom(8).hex()}_{original}"
            f.save(os.path.join(UPLOAD_DIR, stored))
            with db() as con:
                con.execute("INSERT INTO documents(title,category,description,price,filename) VALUES(?,?,?,?,?)",
                            (title, category, description, price, stored))
            flash("Document uploaded.")
            return redirect(url_for("admin"))
    if request.method == "POST" and request.form.get("action") == "approve":
        payment_id = request.form.get("payment_id")
        with db() as con:
            p = con.execute("SELECT * FROM payments WHERE id=? AND status='pending'", (payment_id,)).fetchone()
            if p:
                con.execute("UPDATE payments SET status='approved' WHERE id=?", (payment_id,))
                con.execute("INSERT OR IGNORE INTO purchases(user_id,document_id) VALUES(?,?)",
                            (p["user_id"], p["document_id"]))
                flash("Payment approved and document unlocked.")
        return redirect(url_for("admin"))
    if request.method == "POST" and request.form.get("action") == "reject":
        with db() as con:
            con.execute("UPDATE payments SET status='rejected' WHERE id=? AND status='pending'",
                        (request.form.get("payment_id"),))
        flash("Payment request rejected.")
        return redirect(url_for("admin"))
    with db() as con:
        docs = con.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
        payments = con.execute("""SELECT p.*, u.username, d.title FROM payments p
                                  JOIN users u ON u.id=p.user_id JOIN documents d ON d.id=p.document_id
                                  ORDER BY p.id DESC""").fetchall()
    body = """<main class="wrap"><h2>Admin Panel</h2><div class="panel"><h3>Upload a document</h3><form method="post" enctype="multipart/form-data"><input type="hidden" name="action" value="upload"><label>Document title</label><input name="title" required><label>Category</label><input name="category" placeholder="Bike Service Manual / Wiring Diagram / ECU Diagram" required><label>Description</label><textarea name="description" rows="3"></textarea><label>Price (INR)</label><input type="number" name="price" min="1" required><label>Document file (PDF recommended)</label><input type="file" name="document" required><button class="btn">Upload Document</button></form></div>
    <h3>Payment verification</h3><div class="panel"><table><tr><th>User</th><th>Document</th><th>UTR</th><th>Status / Action</th></tr>{% for p in payments %}<tr><td>{{p['username']}}</td><td>{{p['title']}}</td><td>{{p['utr']}}</td><td>{{p['status'].title()}} {% if p['status']=='pending' %}<form method="post" style="display:inline"><input type="hidden" name="action" value="approve"><input type="hidden" name="payment_id" value="{{p['id']}}"><button class="btn">Approve</button></form> <form method="post" style="display:inline"><input type="hidden" name="action" value="reject"><input type="hidden" name="payment_id" value="{{p['id']}}"><button class="btn danger">Reject</button></form>{% endif %}</td></tr>{% else %}<tr><td colspan="4">No payments submitted.</td></tr>{% endfor %}</table></div><h3>Uploaded documents</h3><div class="panel"><table><tr><th>Title</th><th>Category</th><th>Price</th></tr>{% for d in docs %}<tr><td>{{d['title']}}</td><td>{{d['category']}}</td><td>₹{{d['price']}}</td></tr>{% else %}<tr><td colspan="3">No documents uploaded yet.</td></tr>{% endfor %}</table></div></main>"""
    return page("Admin", body, docs=docs, payments=payments)

@app.errorhandler(403)
def forbidden(e):
    return page("Access Restricted", """<main class="wrap"><div class="panel"><h2>🔒 Access Restricted</h2><p>You need an approved purchase to download this document.</p><a class="btn" href="/">Back to documents</a></div></main>"""), 403

if __name__ == "__main__":
    app.run(debug=True)
