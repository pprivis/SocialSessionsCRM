from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io
import os
import zipfile

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "defaultsecretkey")

db = SQLAlchemy(app)

# -------------------- Models --------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    rep_notes = db.Column(db.Text)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    company = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    rep = db.Column(db.String(120))
    tags = db.Column(db.String(250))
    notes = db.Column(db.Text)
    order_date = db.Column(db.String(120))
    pop_sent = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    title = db.Column(db.String(120))
    due_date = db.Column(db.String(120))
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------- Routes --------------------

@app.route("/")
def root():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    contacts = Contact.query.order_by(Contact.created_at.desc()).all()
    tasks = Task.query.order_by(Task.due_date).all()
    return render_template("dashboard.html", contacts=contacts, tasks=tasks)

@app.route("/add_contact", methods=["POST"])
def add_contact():
    if "user_id" not in session:
        return redirect(url_for("login"))
    contact = Contact(
        name=request.form["name"],
        company=request.form["company"],
        email=request.form["email"],
        phone=request.form["phone"],
        rep=request.form["rep"],
        notes=request.form["notes"],
        tags=request.form["tags"],
        order_date=request.form["order_date"],
        pop_sent=request.form["pop_sent"]
    )
    db.session.add(contact)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/add_task", methods=["POST"])
def add_task():
    task = Task(
        contact_id=request.form["contact_id"],
        title=request.form["title"],
        due_date=request.form["due_date"]
    )
    db.session.add(task)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/update_task_status/<int:task_id>", methods=["POST"])
def update_task_status(task_id):
    task = Task.query.get(task_id)
    task.status = request.form["status"]
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/update_contact/<int:contact_id>", methods=["POST"])
def update_contact(contact_id):
    contact = Contact.query.get(contact_id)
    contact.name = request.form["name"]
    contact.company = request.form["company"]
    contact.email = request.form["email"]
    contact.phone = request.form["phone"]
    contact.rep = request.form["rep"]
    contact.notes = request.form["notes"]
    contact.tags = request.form["tags"]
    contact.order_date = request.form["order_date"]
    contact.pop_sent = request.form["pop_sent"]
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/delete_contact/<int:contact_id>")
def delete_contact(contact_id):
    Contact.query.filter_by(id=contact_id).delete()
    Task.query.filter_by(contact_id=contact_id).delete()
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/rep_notes/<int:user_id>", methods=["POST"])
def rep_notes(user_id):
    user = User.query.get(user_id)
    user.rep_notes = request.form["rep_notes"]
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/export")
def export_data():
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["Name", "Company", "Email", "Phone", "Rep", "Tags", "Notes", "Order Date", "POP Sent", "Created At"])
    for contact in Contact.query.all():
        cw.writerow([contact.name, contact.company, contact.email, contact.phone, contact.rep, contact.tags, contact.notes, contact.order_date, contact.pop_sent, contact.created_at])
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='contacts.csv')

@app.route("/backup")
def backup():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for table, model in {'contacts.csv': Contact, 'tasks.csv': Task, 'users.csv': User}.items():
            si = io.StringIO()
            cw = csv.writer(si)
            if table == 'contacts.csv':
                cw.writerow(["Name", "Company", "Email", "Phone", "Rep", "Tags", "Notes", "Order Date", "POP Sent", "Created At"])
                for c in model.query.all():
                    cw.writerow([c.name, c.company, c.email, c.phone, c.rep, c.tags, c.notes, c.order_date, c.pop_sent, c.created_at])
            elif table == 'tasks.csv':
                cw.writerow(["Title", "Due Date", "Status", "Created At", "Contact ID"])
                for t in model.query.all():
                    cw.writerow([t.title, t.due_date, t.status, t.created_at, t.contact_id])
            elif table == 'users.csv':
                cw.writerow(["Username", "Role", "Rep Notes"])
                for u in model.query.all():
                    cw.writerow([u.username, u.role, u.rep_notes])
            zf.writestr(table, si.getvalue())
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='crm_backup.zip')

# -------------------- Run App --------------------

if __name__ == "__main__":
    app.run(debug=True)

