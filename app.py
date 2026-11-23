import os, sqlite3, secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(APP_DIR, "qaida.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE-ME-before-deployment")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1")

LESSONS = [
    ("Les lettres isolées", ["ا","ب","ت","ث","ج","ح","خ","د","ذ","ر"]),
    ("La Fatha", ["بَ","تَ","ثَ","جَ","حَ","خَ","دَ","رَ","سَ","مَ"]),
    ("La Kasra", ["بِ","تِ","ثِ","جِ","حِ","خِ","دِ","رِ","سِ","مِ"]),
    ("La Damma", ["بُ","تُ","ثُ","جُ","حُ","خُ","دُ","رُ","سُ","مُ"]),
    ("Combiner les voyelles", ["بَتَ","سَمَ","كَتَبَ","جَلَسَ","سُمِعَ","عَلِمَ","حَسُنَ","مَنَعَ"]),
    ("Les tanwîn", ["بً","بٍ","بٌ","تً","تٍ","تٌ","كِتَابٌ","قَلَمٌ"]),
    ("Les prolongations", ["بَا","بِي","بُو","تَا","تِي","تُو","قَالَ","نُورٌ"]),
    ("Le Sukûn", ["أَبْ","أَتْ","بَتْ","مِنْ","عَنْ","هَلْ","يَكْتُبُ"]),
    ("La Chadda", ["بَّ","تَّ","رَّ","مُحَمَّدٌ","رَبِّ","ثُمَّ","إِنَّ"]),
    ("Mélange et consolidation", ["بَتَ","سُمِعَ","مُحَمَّدٌ","كَتَبَ","قَالَ","مِنْ","ثُمَّ","كِتَابٌ"])
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher','student')),
            must_change_password INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS progress(
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL,
            lesson_index INTEGER NOT NULL, exercise_index INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0, successes INTEGER NOT NULL DEFAULT 0,
            last_result INTEGER NOT NULL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, lesson_index, exercise_index),
            FOREIGN KEY(student_id) REFERENCES users(id))""")
        teacher_user = os.environ.get("TEACHER_USERNAME", "professeur")
        teacher_pass = os.environ.get("TEACHER_PASSWORD")
        if teacher_pass and not c.execute("SELECT id FROM users WHERE username=?", (teacher_user,)).fetchone():
            c.execute("INSERT INTO users(username,display_name,password_hash,role) VALUES(?,?,?,'teacher')",
                      (teacher_user, "Professeur", generate_password_hash(teacher_pass)))

def current_user():
    if "user_id" not in session: return None
    with db() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not current_user(): return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapped

def teacher_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        u=current_user()
        if not u: return redirect(url_for("login"))
        if u["role"] != "teacher": abort(403)
        return fn(*a, **kw)
    return wrapped

@app.before_request
def csrf_guard():
    if request.method == "POST":
        token = session.get("csrf_token")
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not token or not sent or not secrets.compare_digest(token, sent):
            abort(400, "Jeton de sécurité invalide. Rechargez la page.")

@app.context_processor
def inject():
    if "csrf_token" not in session: session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"], "user": current_user()}

@app.route("/")
def home():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))

@app.route("/connexion", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form.get("username","").strip().lower()
        password=request.form.get("password","")
        with db() as c: u=c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if u and check_password_hash(u["password_hash"], password):
            session.clear(); session["user_id"]=u["id"]; session["csrf_token"]=secrets.token_urlsafe(32)
            return redirect(url_for("change_password") if u["must_change_password"] else url_for("dashboard"))
        flash("Identifiant ou mot de passe incorrect.", "error")
    return render_template("login.html")

@app.route("/deconnexion", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/tableau-de-bord")
@login_required
def dashboard():
    u=current_user()
    if u["must_change_password"]: return redirect(url_for("change_password"))
    if u["role"]=="teacher": return redirect(url_for("teacher_dashboard"))
    with db() as c:
        rows=c.execute("SELECT * FROM progress WHERE student_id=? ORDER BY lesson_index,exercise_index", (u["id"],)).fetchall()
    summary={}
    for r in rows:
        s=summary.setdefault(r["lesson_index"], {"attempts":0,"successes":0})
        s["attempts"]+=r["attempts"]; s["successes"]+=r["successes"]
    return render_template("student.html", lessons=LESSONS, summary=summary)

@app.route("/professeur")
@teacher_required
def teacher_dashboard():
    with db() as c:
        students=c.execute("SELECT id,username,display_name,created_at FROM users WHERE role='student' ORDER BY display_name").fetchall()
        rows=c.execute("""SELECT p.student_id, SUM(p.attempts) attempts, SUM(p.successes) successes,
                          COUNT(DISTINCT p.lesson_index) lessons_touched, MAX(p.updated_at) updated
                          FROM progress p GROUP BY p.student_id""").fetchall()
    stats={r["student_id"]:r for r in rows}
    return render_template("teacher.html", students=students, stats=stats)

@app.route("/eleves/creer", methods=["POST"])
@teacher_required
def create_student():
    username=request.form.get("username","").strip().lower()
    display=request.form.get("display_name","").strip()
    if not username or not display or len(username)>40 or len(display)>80:
        flash("Renseignez un identifiant et un nom (formats courts).", "error")
        return redirect(url_for("teacher_dashboard"))
    temp=secrets.token_urlsafe(9)
    try:
        with db() as c:
            c.execute("INSERT INTO users(username,display_name,password_hash,role,must_change_password) VALUES(?,?,?,'student',1)",
                      (username, display, generate_password_hash(temp)))
        session["new_student_credentials"]={"username":username,"password":temp}
        flash("Compte élève créé. Communiquez le mot de passe temporaire en privé.", "success")
    except sqlite3.IntegrityError:
        flash("Cet identifiant existe déjà. Choisissez-en un autre.", "error")
    return redirect(url_for("teacher_dashboard"))

@app.route("/eleves/<int:student_id>")
@teacher_required
def student_detail(student_id):
    with db() as c:
        student=c.execute("SELECT id,username,display_name FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
        rows=c.execute("SELECT * FROM progress WHERE student_id=? ORDER BY lesson_index,exercise_index", (student_id,)).fetchall()
    if not student: abort(404)
    return render_template("detail.html", student=student, rows=rows, lessons=LESSONS)

@app.route("/mot-de-passe", methods=["GET","POST"])
@login_required
def change_password():
    if request.method=="POST":
        old=request.form.get("old_password","")
        new=request.form.get("new_password","")
        u=current_user()
        if not check_password_hash(u["password_hash"], old):
            flash("Mot de passe actuel incorrect.", "error")
        elif len(new)<12:
            flash("Choisissez un mot de passe d'au moins 12 caractères.", "error")
        else:
            with db() as c:
                c.execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?",
                          (generate_password_hash(new),u["id"]))
            flash("Mot de passe modifié.", "success")
            return redirect(url_for("dashboard"))
    return render_template("change_password.html")

@app.route("/api/progression", methods=["POST"])
@login_required
def save_progress():
    u=current_user()
    if u["role"]!="student": abort(403)
    data=request.get_json(silent=True) or {}
    li=data.get("lesson_index"); ei=data.get("exercise_index"); ok=data.get("success")
    if not isinstance(li,int) or not isinstance(ei,int) or not isinstance(ok,bool): return jsonify(error="Données invalides"),400
    if not (0<=li<len(LESSONS)) or not (0<=ei<len(LESSONS[li][1])): return jsonify(error="Exercice inconnu"),400
    with db() as c:
        c.execute("""INSERT INTO progress(student_id,lesson_index,exercise_index,attempts,successes,last_result,updated_at)
          VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)
          ON CONFLICT(student_id,lesson_index,exercise_index) DO UPDATE SET
          attempts=attempts+1,successes=successes+excluded.successes,last_result=excluded.last_result,updated_at=CURRENT_TIMESTAMP""",
          (u["id"],li,ei,1,1 if ok else 0,1 if ok else 0))
    return jsonify(saved=True)

@app.route("/sante")
def health(): return {"status":"ok"}

init_db()


if __name__=="__main__":
    app.run(host="127.0.0.1",port=int(os.environ.get("PORT",5000)),debug=False)
