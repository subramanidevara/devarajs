from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3, os, csv
import qrcode
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "svyasa_secret"

DB = "students.db"
QR_DIR = "static/qrcodes"
UPLOAD_DIR = "static/uploads"
ATTENDANCE_FILE = "attendance.csv"

os.makedirs(QR_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect(DB)

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        usn TEXT UNIQUE,
        dept TEXT,
        year TEXT,
        photo TEXT
    )
    """)
    con.commit()
    con.close()

init_db()

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin":
            session["admin"] = True
            return redirect("/")
        flash("Invalid Login", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def admin_required():
    return "admin" in session

# ---------------- HOME ----------------
@app.route("/")
def index():
    if not admin_required():
        return redirect("/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    con.close()
    return render_template("index.html", students=students)

# ---------------- ADD STUDENT ----------------
@app.route("/add", methods=["GET","POST"])
def add_student():
    if not admin_required():
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        usn = request.form["usn"]
        dept = request.form["dept"]
        year = request.form["year"]

        photo_file = request.files.get("photo")
        photo_name = ""
        if photo_file and photo_file.filename:
            photo_name = f"{usn}.jpg"
            photo_file.save(os.path.join(UPLOAD_DIR, photo_name))

        con = get_db()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO students(name,usn,dept,year,photo) VALUES(?,?,?,?,?)",
            (name, usn, dept, year, photo_name)
        )
        con.commit()
        con.close()

        qrcode.make(f"http://127.0.0.1:5000/verify/{usn}") \
            .save(os.path.join(QR_DIR, f"{usn}.png"))

        flash("Student Added Successfully", "success")
        return redirect("/")

    return render_template("add_student.html")

# ---------------- CSV UPLOAD ----------------
@app.route("/upload_csv", methods=["GET","POST"])
def upload_csv():
    if not admin_required():
        return redirect("/login")

    if request.method == "POST":
        file = request.files["csv_file"]
        data = file.read().decode("latin-1").splitlines()
        reader = csv.reader(data)

        con = get_db()
        cur = con.cursor()

        for row in reader:
            if len(row) < 4:
                continue
            name, usn, dept, year = row[:4]
            cur.execute(
                "INSERT OR IGNORE INTO students(name,usn,dept,year,photo) VALUES(?,?,?,?,?)",
                (name, usn, dept, year, "")
            )
            qrcode.make(f"http://127.0.0.1:5000/verify/{usn}") \
                .save(os.path.join(QR_DIR, f"{usn}.png"))

        con.commit()
        con.close()
        flash("CSV Uploaded Successfully", "success")
        return redirect("/")

    return render_template("upload_csv.html")

# ---------------- VIEW STUDENT ----------------
@app.route("/student/<usn>")
def view_student(usn):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM students WHERE usn=?", (usn,))
    s = cur.fetchone()
    con.close()
    return render_template("view_student.html", s=s)

# ---------------- EDIT STUDENT ----------------
@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit_student(id):
    con = get_db()
    cur = con.cursor()

    if request.method == "POST":
        name = request.form["name"]
        dept = request.form["dept"]
        year = request.form["year"]

        photo_file = request.files.get("photo")
        if photo_file and photo_file.filename:
            photo_name = f"{id}.jpg"
            photo_file.save(os.path.join(UPLOAD_DIR, photo_name))
            cur.execute(
                "UPDATE students SET name=?, dept=?, year=?, photo=? WHERE id=?",
                (name, dept, year, photo_name, id)
            )
        else:
            cur.execute(
                "UPDATE students SET name=?, dept=?, year=? WHERE id=?",
                (name, dept, year, id)
            )

        con.commit()
        con.close()
        flash("Updated Successfully", "success")
        return redirect("/")

    cur.execute("SELECT * FROM students WHERE id=?", (id,))
    s = cur.fetchone()
    con.close()
    return render_template("edit_student.html", s=s)

# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete_student(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM students WHERE id=?", (id,))
    con.commit()
    con.close()
    flash("Deleted Successfully", "success")
    return redirect("/")

# ---------------- PDF ----------------
@app.route("/pdf/<usn>")
def pdf_id(usn):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM students WHERE usn=?", (usn,))
    s = cur.fetchone()
    con.close()

    path = f"static/{usn}.pdf"
    c = canvas.Canvas(path, pagesize=A4)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 800, "S-VYASA DEEMED TO BE UNIVERSITY")

    c.setFont("Helvetica", 12)
    c.drawString(100, 740, f"Name: {s[1]}")
    c.drawString(100, 710, f"USN : {s[2]}")
    c.drawString(100, 680, f"Dept: {s[3]}")
    c.drawString(100, 650, f"Year: {s[4]}")

    if s[5]:
        c.drawImage(f"{UPLOAD_DIR}/{s[5]}", 350, 650, 150, 150)

    c.drawImage(f"{QR_DIR}/{s[2]}.png", 350, 450, 150, 150)
    c.save()

    return redirect("/" + path)

# ---------------- VERIFY QR (TIME RULES IMPLEMENTED) ----------------
@app.route("/verify/<usn>")
def verify_qr(usn):
    now = datetime.now()
    today = date.today().isoformat()

    current_time = now.hour * 60 + now.minute

    morning_end = 9 * 60 + 30        # 9:30 AM
    lunch_start = 12 * 60 + 30       # 12:30 PM
    lunch_end = 13 * 60 + 30         # 1:30 PM
    evening_start = 15 * 60          # 3:00 PM

    if current_time < morning_end:
        session_type = "MORNING"
    elif lunch_start <= current_time <= lunch_end:
        return jsonify({"status":"error","msg":"🍽 Lunch break"})
    elif current_time >= evening_start:
        session_type = "EVENING"
    else:
        return jsonify({"status":"error","msg":"⏰ Attendance not allowed"})

    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE,"w",newline="") as f:
            csv.writer(f).writerow(["date","usn","session"])

    with open(ATTENDANCE_FILE,"r") as f:
        for r in csv.reader(f):
            if len(r)==3 and r[0]==today and r[1]==usn and r[2]==session_type:
                return jsonify({"status":"error","msg":"Already marked"})

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT name FROM students WHERE usn=?", (usn,))
    s = cur.fetchone()
    con.close()

    if not s:
        return jsonify({"status":"error","msg":"Invalid QR"})

    with open(ATTENDANCE_FILE,"a",newline="") as f:
        csv.writer(f).writerow([today, usn, session_type])

    return jsonify({"status":"success","name":s[0],"session":session_type})

# ---------------- SCANNER ----------------
@app.route("/scanner")
def scanner():
    return render_template("scanner.html")

# ---------------- DAILY ATTENDANCE SUMMARY ----------------
@app.route("/attendance/summary")
def attendance_summary():
    data = {}
    if not os.path.exists(ATTENDANCE_FILE):
        return jsonify(data)

    with open(ATTENDANCE_FILE,"r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = row["date"]
            data[d] = data.get(d, 0) + 1

    return jsonify(data)

# ---------------- ATTENDANCE GRAPH ----------------
@app.route("/attendance/graph")
def attendance_graph():
    return render_template("attendance_graph.html")

# ---------------- ML ROUTES ----------------
@app.route("/ml/anomalies")
def ml_anomalies():
    from ml_anomaly import detect_anomalies
    return jsonify(detect_anomalies())

@app.route("/ml/proxy")
def ml_proxy():
    from ml_proxy import detect_proxy
    return jsonify(detect_proxy())

@app.route("/ml/predict")
def ml_predict():
    from ml_predict import predict_absentee
    return jsonify(predict_absentee())

@app.route("/ml")
def ml_dashboard_page():
    return render_template("ml_dashboard.html")

@app.route("/ml/anomalies/page")
def ml_anomalies_page():
    return render_template("ml_anomalies.html")

@app.route("/ml/proxy/page")
def ml_proxy_page():
    return render_template("ml_proxy.html")

@app.route("/ml/predict/page")
def ml_predict_page():
    return render_template("ml_predict.html")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
