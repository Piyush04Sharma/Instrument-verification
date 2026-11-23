# Online Verification System for Weighing and Measuring Instruments

A Django web application for the course **INT253: Web Development in Python using Django**.
Shopkeepers register their weighing and measuring instruments and apply for verification online.
Inspection officers review the applications, schedule inspections, record readings and issue digital
certificates. Anyone can check a certificate on a public page, and administrators manage users,
categories and reports.

All data is stored in a database through the Django ORM (SQLite by default, MySQL or PostgreSQL optional).

---

## 1. How to run the project

You need **Python 3.10 or newer**. Check with `python --version` (use `python3` on macOS and Linux).

### Step 1: unzip and open a terminal in the project folder
The folder that contains `manage.py`.

### Step 2: create and activate a virtual environment
Windows (Command Prompt or PowerShell):
```
python -m venv venv
venv\Scripts\activate
```
macOS or Linux:
```
python3 -m venv venv
source venv/bin/activate
```

### Step 3: install the requirements
```
pip install -r requirements.txt
```

### Step 4: create the database tables
The migration files are created from the models, then applied to the database (syllabus Unit V):
```
python manage.py makemigrations accounts instruments verification
python manage.py migrate
```
This creates the file `db.sqlite3`, which is the database.

### Step 5: load demo data (recommended)
```
python manage.py load_demo_data
```
It creates categories, user groups, three demo users, instruments and two sample applications.

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `admin123` |
| Inspection officer | `officer1` | `officer123` |
| Shopkeeper | `shop1` | `shop123` |

To make your own administrator instead, run `python manage.py createsuperuser`.

### Step 6: start the server
```
python manage.py runserver
```
Open **http://127.0.0.1:8000/** in your browser. Stop the server with `Ctrl + C`.

The Django admin site is at **http://127.0.0.1:8000/admin/** (log in as `admin`).

### Run the tests
```
python manage.py test
```

---

## 2. Try the whole workflow (about 5 minutes)

1. **Shopkeeper:** log in as `shop1`. Open *Instruments*, pick the Avery scale or register a new one, then *Apply for verification*. Upload any small PDF, JPG or PNG, then press *Pay* (practice payment, no money is charged).
2. **Officer:** log out, log in as `officer1`. Open the application, *Start review*, *Schedule inspection*, then *Enter inspection results*. Readings within the permissible error can be approved, which issues the certificate. Readings outside the limit can only be rejected.
3. **Shopkeeper:** log back in as `shop1`, open the application, and download the **certificate PDF**. It has a QR code.
4. **Anyone, even logged out:** open *Check a certificate* and type the certificate number (for example the one in the PDF) to see whether it is valid or expired.
5. **Administrator:** log in as `admin` and open *Reports*, including the CSV download.

---

## 3. Features

**Shopkeeper:** register and log in, manage instruments (add, edit, delete, search, filter), apply with documents, pay the fee (simulated), follow the status, resubmit a rejected application, download certificates, see renewals that are due.

**Officer:** secure login, queue of applications, view instrument details and documents, start review, schedule or reschedule an inspection, enter readings, approve (issues the certificate) or reject with a reason.

**Administrator:** dashboard with counts and fees collected, reports (by status, by category, certificates per month) with CSV export, and the Django admin site for users, roles, groups, permissions, categories and all records.

**Extras:** public certificate check page, certificate PDF with QR code, certificate expiry and renewal reminders, in-app notifications and email (printed in the terminal in development), role-based access control, file type and size validation, custom 403, 404 and 500 pages, pagination, unit tests, demo data command.

### Application status flow
Awaiting payment, Submitted, Under review, Inspection scheduled, Inspected, then either Certificate issued or Rejected. A rejected application can be corrected and submitted again without paying again.

---

## 4. Project structure

```
instrument_verification_system/
├── manage.py
├── requirements.txt
├── verification_system/      project settings and root URLs (settings.py, urls.py, wsgi.py)
├── accounts/                 users: Profile with role, registration, login/logout, role decorator
├── instruments/              Category and Instrument models, CRUD views
├── verification/             Application, Document, Payment, Inspection, Certificate, Notification
│   ├── views.py              shopkeeper, officer, admin and public views
│   ├── services.py           notifications and certificate issuing
│   ├── pdf.py                certificate PDF with QR code
│   └── management/commands/load_demo_data.py
├── templates/                base.html and one template per page
└── static/css/style.css
```

---

## 5. Where each syllabus topic is used

| Unit | Topic | Where to look |
|---|---|---|
| I | Project and apps, `manage.py`, app structure | `verification_system/settings.py`, the three apps, `manage.py` commands in this README |
| II | Views, URL mapping, URL parameters | `*/urls.py` (for example `applications/<int:pk>/`, `verify/<str:number>/`), `*/views.py` |
| II | HTTP methods, requests and responses | `@require_POST` views, `request.GET`, `request.POST`, `FileResponse`, CSV and PDF responses |
| II | Error handling | `handler403/404/500` in `verification_system/urls.py`, `error_*` views, `templates/404.html` etc. |
| III | Templates, DTL tags, variables, loops, conditions | everything in `templates/`, for example `{% for %}`, `{% if %}`, `{% url %}`, filters |
| III | Template inheritance | `{% extends 'base.html' %}` in every page |
| III | Debugging and testing | `DEBUG = True` debug page; `tests.py` in every app |
| IV | Forms, GET and POST, validation | `forms.py` in every app (`clean_*` methods, validators), search forms use GET |
| IV | CSRF | `CsrfViewMiddleware` in settings and `{% csrf_token %}` in every POST form |
| IV | POST redirect | every successful POST view ends with `redirect(...)` |
| V | Models, ForeignKey, migrations | `*/models.py`, `makemigrations` and `migrate` |
| V | ORM, shell | `python manage.py shell`, for example `Application.objects.filter(status="submitted")` |
| V | Django Admin, groups, permissions | `*/admin.py`, `load_demo_data` creates the groups and permissions |
| V | Database configuration | `DATABASES` in `settings.py` (SQLite, MySQL example included) |
| VI | Cookies and sessions | `last_visit` cookie and `recent_instruments` session in `owner_dashboard` and `instrument_detail` |
| VI | Users, login, logout | `accounts/` app, `LoginView`, `LogoutView`, `login()` in `register` |
| VI | Securing views | `@login_required`, `role_required` in `accounts/decorators.py` |

Try the ORM in the shell:
```
python manage.py shell
>>> from verification.models import Application
>>> Application.objects.filter(status="submitted").count()
>>> Application.objects.select_related("instrument").first()
```

---

## 6. Using MySQL or PostgreSQL instead of SQLite

Open `verification_system/settings.py`. A ready MySQL block is included as a comment under `DATABASES`.
Create an empty database first (for example `CREATE DATABASE verification_db;`), install the driver
(`pip install mysqlclient` or `pip install psycopg2-binary`), put your credentials in the block, then run
`python manage.py migrate` and `python manage.py load_demo_data` again.

---

## 7. Notes

- **Payment is simulated.** The payment page stores a payment record with a transaction number. A real gateway (for example Razorpay) can replace the `pay` view later.
- **Uploaded documents** are saved in `media/documents/` and are only served through a view that checks that the person is the applicant or an officer.
- **Custom 404 and 500 pages** show when `DEBUG = False`. To preview them, set `DEBUG = False` and `ALLOWED_HOSTS = ["127.0.0.1", "localhost"]` in `settings.py`, then run `python manage.py runserver --insecure` so the stylesheet still loads.
- Before putting the site on a real server, change `SECRET_KEY`, set `DEBUG = False` and configure `ALLOWED_HOSTS`.
- If `makemigrations` says "No changes detected", make sure you included the app names as shown in Step 4.

### Common problems
| Problem | Fix |
|---|---|
| `No module named django` | Activate the virtual environment, then run `pip install -r requirements.txt` |
| `no such table` error | Run `python manage.py migrate` |
| Port already in use | Run `python manage.py runserver 8080` |
| Forgot the demo passwords | Run `python manage.py changepassword admin` |
#   I n s t r u m e n t - v e r i f i c a t i o n  
 