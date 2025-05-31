from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timedelta
import pytz
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from flask_dance.contrib.google import make_google_blueprint, google
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''
app.config['MAIL_DEFAULT_SENDER'] = ''

db = SQLAlchemy(app)
mail = Mail(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False, default='')
    profile_picture = db.Column(db.String(500), nullable=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    priority = db.Column(db.String(10), default='Medium')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notification_sent = db.Column(db.Boolean, default=False)

# Google OAuth configuration
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # For testing only
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

google_bp = make_google_blueprint(
    client_id="",
    client_secret="",
    scope=["openid", "email", "profile"],
    redirect_to="google_login"
)
app.register_blueprint(google_bp, url_prefix="/login")

def send_task_confirmation(user_email, task_title, task_description, start_date, end_date, start_time, end_time, priority):
    """Send email confirmation when a new task is created"""
    try:
        with app.app_context():
            msg = Message(
                subject=f'Task Created Successfully: {task_title}',
                recipients=[user_email],
                html=render_template('confirm.html', 
                                   task_title=task_title,
                                   task_description=task_description,
                                   start_date=start_date,
                                   end_date=end_date,
                                   start_time=start_time,
                                   end_time=end_time,
                                   priority=priority)
            )
            mail.send(msg)
    except Exception as e:
        print(f"Error sending task confirmation email: {str(e)}")

def send_task_reminder(task_id, user_email, task_title, end_datetime):
    """Send email reminder for upcoming task"""
    try:
        with app.app_context():
            msg = Message(
                subject=f'Task Reminder: {task_title}',
                recipients=[user_email],
                html=render_template('email_reminder.html', 
                                   task_title=task_title, 
                                   end_datetime=end_datetime)
            )
            mail.send(msg)
            
            # Mark notification as sent
            task = Task.query.get(task_id)
            if task:
                task.notification_sent = True
                db.session.commit()
                
    except Exception as e:
        print(f"Error sending email: {str(e)}")

def check_upcoming_tasks():
    """Check for tasks ending in the next 20 minutes"""
    try:
        with app.app_context():
            india_tz = pytz.timezone('Asia/Kolkata')
            current_datetime = datetime.now(india_tz)
            reminder_time = current_datetime + timedelta(minutes=20)
            
            tasks = Task.query.join(User).filter(
                Task.end_date.isnot(None),
                Task.end_time.isnot(None),
                Task.notification_sent == False
            ).all()
            
            for task in tasks:
                if task.end_date and task.end_time:
                    task_end_datetime = datetime.combine(task.end_date, task.end_time)
                    task_end_datetime = india_tz.localize(task_end_datetime)
                    
                    time_until_end = task_end_datetime - current_datetime
                    
                    if timedelta(minutes=15) <= time_until_end <= timedelta(minutes=25):
                        user = User.query.get(task.user_id)
                        if user:
                            send_task_reminder(
                                task.id, 
                                user.email, 
                                task.title, 
                                task_end_datetime.strftime('%Y-%m-%d %H:%M')
                            )
    except Exception as e:
        print(f"Error checking upcoming tasks: {str(e)}")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_upcoming_tasks, trigger="interval", minutes=5)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    if 'username' in session:
        username = session['username']
        user_id = session.get('user_id')
        
        profile_picture = None
        if user_id:
            user = User.query.get(user_id)
            if user and user.profile_picture:
                profile_picture = user.profile_picture
        
        india_tz = pytz.timezone('Asia/Kolkata')
        current_hour = datetime.now(india_tz).hour

        if 5 <= current_hour < 12:
            greeting = "Good Morning"
        elif 12 <= current_hour < 17:
            greeting = "Good Afternoon"
        elif 17 <= current_hour < 21:
            greeting = "Good Evening"
        else:
            greeting = "Good Night"

        return render_template('index.html', username=username, greeting=greeting, profile_picture=profile_picture)
    else:
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash('Passwords do not match!')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose a different one.')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email or login.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registered successfully! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/task', methods=['GET', 'POST'])
def task():
    if 'username' not in session or 'user_id' not in session:
        return redirect(url_for('login'))
     
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        priority = request.form.get('priority', 'Medium')
         
        if not title:
            flash('Task title is required.')
            return redirect(url_for('task'))
         
        if start_date:
            start_date = date.fromisoformat(start_date)
        if end_date:
            end_date = date.fromisoformat(end_date)
        if start_time:
            start_time = time.fromisoformat(start_time)
        if end_time:
            end_time = time.fromisoformat(end_time)
         
        # Validation
        today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
        current_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
         
        if start_date and start_date < today:
            flash("Start date cannot be in the past.")
            return redirect(url_for('task'))
         
        if start_date == today and start_time and start_time < current_time:
            flash("Start time cannot be earlier than current time.")
            return redirect(url_for('task'))
         
        if end_date and start_date and end_date < start_date:
            flash("End date cannot be earlier than start date.")
            return redirect(url_for('task'))
         
        if start_date and end_date and end_time and start_time:
            if end_date == start_date and end_time < start_time:
                flash("End time cannot be earlier than start time.")
                return redirect(url_for('task'))
         
        new_task = Task(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            priority=priority,
            user_id=session['user_id'],
            notification_sent=False
        )
        db.session.add(new_task)
        db.session.commit()
        
        # Send confirmation email
        user = User.query.get(session['user_id'])
        if user:
            threading.Thread(target=send_task_confirmation, args=(
                user.email,
                title,
                description,
                start_date.strftime('%Y-%m-%d') if start_date else None,
                end_date.strftime('%Y-%m-%d') if end_date else None,
                start_time.strftime('%H:%M') if start_time else None,
                end_time.strftime('%H:%M') if end_time else None,
                priority
            )).start()
        
        flash('Task added successfully')
        return redirect(url_for('task'))
     
    return render_template('task.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    flash('Logged out successfully.')
    return redirect(url_for('login'))

@app.route('/view_tasks')
def view_tasks():
    if 'user_id' not in session:
        flash('Please login to view your tasks.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    tasks = Task.query.filter_by(user_id=user_id).all()

    india_tz = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(india_tz).replace(tzinfo=None)

    return render_template('view_tasks.html', tasks=tasks, current_time=current_time)

@app.route('/get_task_details/<int:task_id>')
def get_task_details(task_id):
    task = Task.query.get_or_404(task_id)
    task_details = {
        'title': task.title,
        'description': task.description,
        'start_date': task.start_date.strftime('%Y-%m-%d'),
        'end_date': task.end_date.strftime('%Y-%m-%d'),
        'start_time': task.start_time.strftime('%H:%M'),
        'end_time': task.end_time.strftime('%H:%M'),
        'priority': task.priority
    }
    return jsonify(task_details)

@app.route('/update_task', methods=['POST'])
def update_task():
    task_id = request.form['task_id']
    task = Task.query.get_or_404(task_id)

    task.title = request.form['title']
    task.description = request.form['description']
    task.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
    task.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
    task.start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
    task.end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
    task.priority = request.form['priority']

    db.session.commit()
    return jsonify({'success': True})

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first()
    if task:
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted successfully.')
    else:
        flash('Task not found or not authorized.')

    return redirect(url_for('view_tasks'))

@app.template_filter('todatetime')
def to_datetime_filter(value):
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return value

@app.route('/api/tasks')
def get_tasks():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    tasks = Task.query.filter_by(user_id=user_id).all()
    
    tasks_list = [{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'start_date': task.start_date.isoformat() if task.start_date else None,
        'end_date': task.end_date.isoformat() if task.end_date else None,
        'start_time': task.start_time.isoformat() if task.start_time else None,
        'end_time': task.end_time.isoformat() if task.end_time else None,
        'priority': task.priority
    } for task in tasks]
    
    return jsonify(tasks_list)

@app.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    try:
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            flash("Failed to fetch user info from Google")
            return redirect(url_for('login'))

        user_info = resp.json()
        
        if 'email' not in user_info:
            flash("Email not provided by Google. Please try logging in with username/password.")
            return redirect(url_for('login'))
        
        email = user_info["email"]
        name = user_info.get("name", user_info.get("given_name", "GoogleUser"))
        profile_picture = user_info.get("picture")
        
        username = name.replace(" ", "_").lower()
        
        user = User.query.filter_by(email=email).first()
        if not user:
            existing_user = User.query.filter_by(username=username).first()
            counter = 1
            original_username = username
            while existing_user:
                username = f"{original_username}_{counter}"
                existing_user = User.query.filter_by(username=username).first()
                counter += 1
            
            user = User(username=username, email=email, password=generate_password_hash(''), profile_picture=profile_picture)
            db.session.add(user)
            db.session.commit()
            flash(f"Welcome! New account created with username: {username}")
        else:
            if profile_picture and user.profile_picture != profile_picture:
                user.profile_picture = profile_picture
                db.session.commit()

        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session.permanent = True
        
        flash(f"Successfully logged in via Google as {user.username}!")
        return redirect(url_for("index"))
        
    except Exception as e:
        flash("An error occurred during Google login. Please try again or use username/password.")
        return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)