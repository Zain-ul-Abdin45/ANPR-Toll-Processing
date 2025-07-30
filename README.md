# ANPR-Toll-Processing

# ANPR Toll Processing System - Setup Guide

Steps to set up and run the ANPR-based Toll Processing System using FastAPI and PostgreSQL.

---

## Prerequisites

- Python 3.10 or above
- PostgreSQL (with a user and an `anpr` database)
- Git (for cloning the repository)
- Render or local server for API hosting
- Virtual environment support (optional but recommended)

---

## Project Structure

Working directory looks like this:

```
ANPR-Toll-Processing/
│
├── configs/
│   ├── config.json
│   ├── logger.ini
├── db_scripts/
│   ├── DDL.sql
│   ├── Seeds.py
├── logs/
│   ├── alert_logs
│   │   ├── alert_logs.log
│   ├── general_logs
│   │   ├── general_logs.log
│   ├── plate_logs
│   │   ├── plate_logs.log
│   ├── rfid_logs
│   │   ├── rfid_logs.log
│   ├── trxn_logs
│   │   ├── trxn_logs.log
├── modules/
│   ├── *.py
│
├── api/
│   ├── *.py
│
├── main.py
├── requirements.txt
```

---

## Step 1: Clone the Project

```bash
git clone https://github.com/Zain-ul-Abdin45/ANPR-Toll-Processing.git
cd ANPR-Toll-Processing
```

---

## Step 2: Create Virtual Environment (optional but recommended for an isolated environment)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate   # Windows
```

---

## Step 3: Install Requirements

```bash
pip install -r requirements.txt
```

---

## Step 4: Configure Database Connection

Edit `configs/config.json`:

```json
{
  "username": "your_db_username",
  "password": "your_db_password",
  "host": "localhost",
  "port": 5432,
  "database": "anpr"
}
```

Ensure PostgreSQL is running and you’ve created the database:

```sql
CREATE DATABASE anpr;
```

---

## Step 5: Test DB Connection

Optionally run a test connection script to verify DB config.

---

## Step 6: Run the FastAPI Server

```bash
uvicorn main:app --reload
```

Visit Swagger UI at:

```
http://127.0.0.1:8000/docs
```

---

## Notes

- Ensure `.env` or `config.json` matches your environment.
- Logging and alert logs will be created inside the `logs/` directory.
- Use `render` for cloud deployment if desired.

---
