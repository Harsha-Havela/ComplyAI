# ComplyAI — Tax Compliance Management Platform

A professional web application for managing tax compliance deadlines, clients, tasks, and team workflows — built with Flask and Firebase Firestore.

---

## Features

- **Dashboard** — Overview of clients, tasks, and compliance deadlines
- **Client Management** — Add and manage client profiles with PAN/GSTIN details
- **Task Management** — Create, assign, and track tasks across your team
- **Compliance Tracking** — Monitor tax deadlines with calendar, overdue, and upcoming views
- **Reports & Exports** — Export data as CSV for tasks, clients, and compliance
- **User Management** — Role-based access control (Admin, Manager, Employee)
- **Authentication** — Secure login with session management

---

## Tech Stack

- **Backend** — Python, Flask
- **Database** — Firebase Firestore
- **Frontend** — Jinja2 templates, Bootstrap 5, Bootstrap Icons
- **Auth** — Firebase Admin SDK

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/complyai.git
cd complyai
```

### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your `SECRET_KEY`.

### 5. Set up Firebase

- Go to [Firebase Console](https://console.firebase.google.com)
- Create a project and enable **Firestore**
- Generate a service account key and save it as `firebase-service-account.json`
- Add the path to your `.env`:

```
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json
```

### 6. Run the application

```bash
python app.py
```

Visit `http://127.0.0.1:5000`

---

## Default Login

| Username | Password |
|----------|----------|
| admin    | Admin123 |

> Change the password after first login.

---

## Environment Variables

See `.env.example` for all available configuration options.

---

## License

MIT
