# Reservation System - Startup Instructions

Below you will find instructions on how to start the project locally.

---

## 1. Create and activate a virtual environment

### On Windows (PowerShell):
```bash
python -m venv venv
.\venv\Scripts\Activate
```
2. Install required packages

```bash
pip install django
```

3. Go to the project directory
```bash
cd system_rezerwacji
```
4. Perform migrations
```bash
python manage.py migrate
```
5. Start the server
```bash
python manage.py runserver
```
6. Open the page http://127.0.0.1:8000/ in your browser

## Login to the admin panel

### login: admin

### password: 1qazXSW@