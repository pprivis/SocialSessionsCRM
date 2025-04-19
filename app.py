from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
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
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    rep_notes = db.Column(db.Text)

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
    allowed = ['login', 'static']
    if 'user_id' not in session and request.endpoint not in allowed:
        return redirect(url_for('login'))

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

# -------------------- DASHBOARD --------------------
@app.route("/dashboard")
def dashboard():
    contacts = Contact.query.all()
    tasks = Task.query.all()
    today = date.today().isoformat()
    overdue = Task.query.filter(Task.status != 'completed', Task.due_date < today).count()
    due_today = Task.query.filter(Task.due_date == today).count()
    due_soon = Task.query.filter(Task.due_date > today).count()
    dashboard = {
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
    return render_template("index.html", contacts=contacts, tasks=tasks, dashboard=dashboard, leaderboard=leaderboard, rep_notes=rep_notes, role=session.get('role'))

# -------------------- CONTACT ROUTES --------------------
@app.route("/add_contact", methods=["POST"])
def add_contact():
    contact = Contact(
        name=request.form["name"],
        email=request.form["email"],
        phone=request.form["phone"],
        tags=request.form["tags"],
        rep=request.form["rep"],
        notes=request.form["notes"]
    )
    db.session.add(contact)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/update_contact/<int:id>", methods=["POST"])
def update_contact(id):
    contact = Contact.query.get_or_404(id)
    contact.name = request.form["name"]
    contact.email = request.form["email"]
    contact.phone = request.form["phone"]
    contact.tags = request.form["tags"]
    contact.rep = request.form["rep"]
    contact.notes = request.form["notes"]
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/toggle_archive/<int:id>")
def toggle_archive(id):
    contact = Contact.query.get_or_404(id)
    contact.archived = not contact.archived
    db.session.commit()
    return redirect(url_for("dashboard"))

# -------------------- TASK ROUTES --------------------
@app.route("/add_task/<int:contact_id>", methods=["POST"])
def add_task(contact_id):
    task = Task(
        contact_id=contact_id,
        task=request.form["task"],
        due_date=request.form["due_date"]
    )
    db.session.add(task)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/complete_task/<int:task_id>")
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = "completed"
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/delete_task/<int:task_id>")
def delete_task(task_id):
    Task.query.filter_by(id=task_id).delete()
    db.session.commit()
    return redirect(url_for("dashboard"))

# -------------------- NOTE ROUTES --------------------
@app.route("/add_note/<int:contact_id>", methods=["POST"])
def add_note(contact_id):
    note = Note(contact_id=contact_id, note=request.form["note"])
    db.session.add(note)
    db.session.commit()
    return redirect(url_for("dashboard"))

# -------------------- ORDER ROUTES --------------------
@app.route("/add_order/<int:contact_id>", methods=["POST"])
def add_order(contact_id):
    order = Order(contact_id=contact_id, order_date=request.form["order_date"])
    db.session.add(order)
    db.session.commit()
    return redirect(url_for("dashboard"))

# -------------------- POP ROUTES --------------------
@app.route("/add_pop/<int:contact_id>", methods=["POST"])
def add_pop(contact_id):
    pop = POP(
        contact_id=contact_id,
        material=request.form["material"],
        sent_date=request.form["sent_date"]
    )
    db.session.add(pop)
    db.session.commit()
    return redirect(url_for("dashboard"))

# -------------------- EXPORT --------------------
@app.route('/export_csv')
def export_csv():
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["Name", "Email", "Phone", "Tags", "Rep", "Notes"])
    for c in Contact.query.all():
        cw.writerow([c.name, c.email, c.phone, c.tags, c.rep, c.notes])
    output = io.BytesIO()
    output.write(si.getvalue().encode())
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='contacts.csv')

@app.route("/backup")
def backup():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for name, model in {'contacts.csv': Contact, 'tasks.csv': Task, 'users.csv': User}.items():
            si = io.StringIO()
            cw = csv.writer(si)
            if model == Contact:
                cw.writerow(["Name", "Email", "Phone", "Rep", "Tags", "Notes"])
                for c in model.query.all():
                    cw.writerow([c.name, c.email, c.phone, c.rep, c.tags, c.notes])
            elif model == Task:
                cw.writerow(["Task", "Due Date", "Status", "Contact ID"])
                for t in model.query.all():
                    cw.writerow([t.task, t.due_date, t.status, t.contact_id])
            elif model == User:
                cw.writerow(["Username", "Role", "Notes"])
                for u in model.query.all():
                    cw.writerow([u.username, u.role, u.rep_notes])
            zf.writestr(name, si.getvalue())
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='crm_backup.zip')

if __name__ == '__main__':
    app.run(debug=True)
