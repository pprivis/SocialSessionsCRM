from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crm.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Clean reset of user table ---
with app.app_context():
    try:
        db.session.execute('DROP TABLE IF EXISTS "user" CASCADE;')
        db.session.commit()
    except Exception as e:
        print(f"⚠️ Failed to drop table: {e}")

    try:
        db.session.execute('''
            CREATE TABLE "user" (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(128),
                role VARCHAR(20),
                rep_notes TEXT
            );
        ''')
        db.session.commit()
        print("✅ User table recreated.")
    except Exception as e:
        print(f"❌ Failed to create user table: {e}")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20))
    rep_notes = db.Column(db.Text)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@app.route("/")
def root():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.check_password(request.form["password"]):
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return f"Welcome to the dashboard, {session.get('role')}!"

@app.route("/add_test_users")
def add_test_users():
    users = [
        {"username": "polina", "password": "polinapass", "role": "admin"},
        {"username": "tanya", "password": "tanyapass", "role": "creative"},
        {"username": "rory", "password": "rorypass", "role": "sales"},
    ]
    for u in users:
        if not User.query.filter_by(username=u["username"]).first():
            user = User(username=u["username"], role=u["role"])
            user.set_password(u["password"])
            db.session.add(user)
    db.session.commit()
    return "✅ Test users created."

if __name__ == "__main__":
    app.run(debug=True)



