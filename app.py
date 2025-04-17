from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crm.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

@app.before_request
def require_login():
    allowed_routes = ['login', 'login_page', 'static']
    if 'user_id' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SECRET_KEY'] = 'super_secret_key'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120))
    role = db.Column(db.String(20))  # 'admin' or 'rep'

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    tags = db.Column(db.String(250))
    notes = db.Column(db.Text)
    rep = db.Column(db.String(100))
    archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('FollowUpTask', backref='contact', lazy=True, cascade="all, delete-orphan")
    interactions = db.relationship('InteractionLog', backref='contact', lazy=True, cascade="all, delete-orphan")
    orders = db.relationship('OrderLog', backref='contact', lazy=True, cascade="all, delete-orphan")
    pops = db.relationship('POPLog', backref='contact', lazy=True, cascade="all, delete-orphan")

class FollowUpTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    task = db.Column(db.String(250))
    due_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)

class InteractionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    note = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class RepNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rep_name = db.Column(db.String(100), unique=True)
    note = db.Column(db.Text, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OrderLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    order_date = db.Column(db.Date)

class POPLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    material = db.Column(db.String(100))
    sent_date = db.Column(db.Date)

# Utilities
@app.context_processor
def utility_functions():
    def get_task_status(task):
        if task.completed or not task.due_date:
            return "none"
        today = datetime.utcnow().date()
        if task.due_date < today:
            return "overdue"
        elif task.due_date == today:
            return "due_today"
        elif task.due_date <= today + timedelta(days=3):
            return "due_soon"
        return "none"
    return dict(get_task_status=get_task_status)

# Auth
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"🔍 Login attempt: {username} / {password}")

        user = User.query.filter_by(username=username).first()
        print("🔎 DB lookup:", user)

        if user:
            print(f"🟨 Stored password: {user.password} | Role: {user.role}")

        if user and user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            print("✅ Login success")
            return redirect(url_for('index'))
        else:
            print("❌ Login failed")
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


# Dashboard
@app.route('/')
def index():
    today = datetime.utcnow().date()
    three_days = today + timedelta(days=3)
    role = session.get('role')
    current_user = session.get('username')
    show_archived = request.args.get('show_archived') == '1'
    rep_filter = request.args.get('rep')

    query = Contact.query
    if role != 'admin':
        query = query.filter_by(rep=current_user)
    if not show_archived:
        query = query.filter_by(archived=False)
    if rep_filter:
        query = query.filter_by(rep=rep_filter)

    contacts = query.order_by(Contact.created_at.desc()).all()
    reps = sorted(set(c.rep for c in Contact.query if c.rep))

    leaderboard = []
    for rep in reps:
        rep_contacts = Contact.query.filter_by(rep=rep, archived=False).all()
        ids = [c.id for c in rep_contacts]
        leaderboard.append({
            'rep': rep,
            'total_contacts': len(rep_contacts),
            'completed_tasks': FollowUpTask.query.filter(FollowUpTask.contact_id.in_(ids), FollowUpTask.completed == True).count(),
            'overdue_tasks': FollowUpTask.query.filter(FollowUpTask.contact_id.in_(ids), FollowUpTask.completed == False, FollowUpTask.due_date < today).count()
        })

    rep_notes = {}
    for rep in reps:
        note = RepNote.query.filter_by(rep_name=rep).first()
        if not note:
            note = RepNote(rep_name=rep)
            db.session.add(note)
            db.session.commit()
        rep_notes[rep] = {
            "note": note.note,
            "updated_at": note.updated_at.strftime('%b %d, %Y %I:%M %p') if note.updated_at else None
        }

    return render_template("index.html",
        contacts=contacts,
        dashboard={
            'total_contacts': len(contacts),
            'tasks_due_today': FollowUpTask.query.filter_by(due_date=today, completed=False).count(),
            'tasks_due_soon': FollowUpTask.query.filter(FollowUpTask.due_date > today, FollowUpTask.due_date <= three_days, FollowUpTask.completed == False).count(),
            'overdue': FollowUpTask.query.filter(FollowUpTask.due_date < today, FollowUpTask.completed == False).count()
        },
        leaderboard=leaderboard,
        rep_notes=rep_notes,
        all_reps=reps,
        show_archived=show_archived,
        role=role,
        current_user=current_user
    )

# Routes for CRUD
@app.route('/update_contact/<int:id>', methods=['POST'])
def update_contact(id):
    c = Contact.query.get_or_404(id)
    c.name = request.form['name']
    c.email = request.form['email']
    c.phone = request.form['phone']
    c.tags = request.form['tags']
    c.notes = request.form['notes']
    c.rep = request.form['rep']
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_task/<int:contact_id>', methods=['POST'])
def add_task(contact_id):
    t = FollowUpTask(
        contact_id=contact_id,
        task=request.form['task'],
        due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d').date() if request.form['due_date'] else None
    )
    db.session.add(t)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    t = FollowUpTask.query.get_or_404(task_id)
    t.completed = True
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    db.session.delete(FollowUpTask.query.get_or_404(task_id))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_note/<int:contact_id>', methods=['POST'])
def add_note(contact_id):
    note = InteractionLog(contact_id=contact_id, note=request.form['note'])
    db.session.add(note)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_rep_note/<rep_name>', methods=['POST'])
def update_rep_note(rep_name):
    if session.get('role') != 'admin':
        return "Unauthorized"
    note = RepNote.query.filter_by(rep_name=rep_name).first()
    note.note = request.form['note']
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/toggle_archive/<int:id>')
def toggle_archive(id):
    c = Contact.query.get_or_404(id)
    c.archived = not c.archived
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_order/<int:contact_id>', methods=['POST'])
def add_order(contact_id):
    date = datetime.strptime(request.form['order_date'], '%Y-%m-%d').date()
    db.session.add(OrderLog(contact_id=contact_id, order_date=date))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_pop/<int:contact_id>', methods=['POST'])
def add_pop(contact_id):
    db.session.add(POPLog(
        contact_id=contact_id,
        material=request.form['material'],
        sent_date=datetime.strptime(request.form['sent_date'], '%Y-%m-%d').date()
    ))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/export_csv')
def export_csv():
    if session.get('role') != 'admin':
        return "Unauthorized"
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Rep", "Contacts", "Completed Tasks", "Overdue Tasks", "Rep Notes"])
    today = datetime.utcnow().date()
    for rep in sorted(set(c.rep for c in Contact.query if c.rep)):
        rep_contacts = Contact.query.filter_by(rep=rep).all()
        ids = [c.id for c in rep_contacts]
        writer.writerow([
            rep,
            len(rep_contacts),
            FollowUpTask.query.filter(FollowUpTask.contact_id.in_(ids), FollowUpTask.completed == True).count(),
            FollowUpTask.query.filter(FollowUpTask.contact_id.in_(ids), FollowUpTask.completed == False, FollowUpTask.due_date < today).count(),
            RepNote.query.filter_by(rep_name=rep).first().note
        ])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="rep_stats.csv")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
