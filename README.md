# 📝 TO-DO List Web Application

A feature-rich Flask-based To-Do list application that allows users to manage their tasks with ease. It supports user registration, login, task creation with priority and deadline settings, email reminders, and more.

## 🚀 Features

- 🧑‍💻 **User Authentication**
  - Register, login, and logout securely
  - Passwords are stored securely using hashing

- 📅 **Task Management**
  - Create, edit, and delete tasks
  - Set task start/end date and time
  - Set task priority (High, Medium, Low)

- 📧 **Email Reminders**
  - Automatic email reminders for upcoming tasks

- 🌐 **Google OAuth Login**
  - Users can log in using their Google account

- 🗂️ **User Dashboard**
  - View tasks by priority and date
  - Task filtering and display

## 🛠️ Built With

- [Flask](https://flask.palletsprojects.com/)
- [Flask-Mail](https://pythonhosted.org/Flask-Mail/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- [Flask-Dance (Google OAuth)](https://flask-dance.readthedocs.io/)
- [SQLite](https://www.sqlite.org/index.html)
- [APScheduler](https://apscheduler.readthedocs.io/)

## 📂 Project Structure

```
TO-DO/
│
├── app.py                  # Main application logic
├── instance/users.db       # SQLite database file
├── static/                 # Static files (CSS, JS, Images)
├── templates/              # HTML templates (Jinja2)
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── task.html
│   ├── view_tasks.html
│   └── ...
├── Todo/                   # Virtual environment (optional)
└── __pycache__/            # Python bytecode
```
