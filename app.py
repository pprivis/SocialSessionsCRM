from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
import os, io, csv, zipfile

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crm.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# -------------------- MODELS --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    rep_notes = db.Column(db.Text)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    tags = db.Column(db.String(250))
    rep = db.Column(db.String(120))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    archived = db.Column(db.Boolean, default=False)
    tasks = db.relationship('Task', backref='contact', lazy=True)
    orders = db.relationship('Order', backref='contact', lazy=True)
    pops = db.relationship('POP', backref='contact', lazy=True)
    interactions = db.relationship('Note', backref='contact', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    task = db.Column(db.String(255))
    due_date = db.Column(db.String(120))
    status = db.Column(db.String(50), default='pending')

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    note = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    order_date = db.Column(db.String(120))

class POP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    material = db.Column(db.String(120))
    sent_date = db.Column(db.String(120))

# -------------------- AUTH --------------------
@app.before_request
def require_login():
    allowed = ['login', 'static', 'add_test_users']
    if 'user_id' not in session and request.endpoint not in allowed:
        return redirect(url_for('login'))

@app.route("/")
def root():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.check_password(request.form["password"]):
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

@app.route("/add_test_users")
def add_test_users():
    if User.query.filter_by(username="polina").first():
        return "Test users already exist."

    u1 = User(username="polina", role="admin")
    u1.set_password("polinapass")

    u2 = User(username="tanya", role="creative")
    u2.set_password("tanyapass")

    u3 = User(username="rory", role="sales")
    u3.set_password("rorypass")

    db.session.add_all([u1, u2, u3])
    db.session.commit()
    return "✅ Test users created with hashed passwords."

# -------------------- DASHBOARD --------------------
@app.route("/dashboard")
def dashboard():
    contacts = Contact.query.all()
    tasks = Task.query.all()
    today = date.today().isoformat()
    overdue = Task.query.filter(Task.status != 'completed', Task.due_date < today).count()
    due_today = Task.query.filter(Task.due_date == today).count()
    due_soon = Task.query.filter(Task.due_date > today).count()
    metrics = {
        'total_contacts': len(contacts),
        'tasks_due_today': due_today,
        'tasks_due_soon': due_soon,
        'overdue': overdue
    }
    reps = [u.username for u in User.query.filter_by(role='sales').all()]
    leaderboard = []
    rep_notes = {}
    for rep in reps:
        total = Contact.query.filter_by(rep=rep).count()
        completed = Task.query.join(Contact).filter(Contact.rep==rep, Task.status=='completed').count()
        overdue = Task.query.join(Contact).filter(Contact.rep==rep, Task.status!='completed', Task.due_date < today).count()
        note = User.query.filter_by(username=rep).first().rep_notes or ''
        leaderboard.append({
            'rep': rep,
            'total_contacts': total,
            'completed_tasks': completed,
            'overdue_tasks': overdue
        })
        rep_notes[rep] = {'note': note, 'updated_at': 'Just now'}
    return render_template("index.html", contacts=contacts, tasks=tasks, metrics=metrics, leaderboard=leaderboard, rep_notes=rep_notes, role=session.get('role'))

@app.route("/patch_rep_notes")
def patch_rep_notes_column():
    try:
        db.session.execute('ALTER TABLE "user" ADD COLUMN rep_notes TEXT;')
        db.session.commit()
        return "✅ rep_notes column added!"
    except Exception as e:
        return f"⚠️ Error: {e}"

@app.route("/patch_rep_notes")
def patch_rep_notes_column():
    try:
        db.session.execute('ALTER TABLE "user" ADD COLUMN rep_notes TEXT;')
        db.session.commit()
        return "✅ rep_notes column added!"
    except Exception as e:
        return f"⚠️ Error: {e}"

@app.route("/reset_users_table")
def reset_users_table():
    try:
        User.__table__.drop(db.engine)
        User.__table__.create(db.engine)
        return "✅ User table dropped and recreated successfully."
    except Exception as e:
        return f"⚠️ Error resetting user table: {e}"

# ... (your contact/task/note/order/pop/export/backup routes stay unchanged) ...

if __name__ == '__main__':
    app.run(debug=True)

