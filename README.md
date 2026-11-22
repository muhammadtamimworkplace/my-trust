# My Trust

**Community reports and trust ratings for Facebook-based online sellers.**

My Trust is a web application where buyers report suspicious Facebook sales pages with screenshot
evidence, administrators verify the reports, and every page receives a transparent trust score that keeps
**admin-verified findings**, **unverified allegations** and **community feedback** clearly separate.

> Undergraduate Software Engineering thesis project:
> *Identification of Scam Patterns in Facebook-Based Online Sales Pages*.

---

## Features

**Visitors**
- Search reported pages by name or by Facebook link in any form (mobile links, `fb.com`, tracking codes are normalized)
- Filter by scam category and verification status
- Page detail with trust badge and separate sections for verified reports, unverified allegations and feedback

**Registered users**
- Register, log in/out, edit profile, change password
- Report a page with 1–5 screenshots (JPG/PNG, max 5 MB each, content-verified)
- Track own reports and admin notes; add evidence when an administrator requests it
- Give one positive/negative feedback per page, comment on reports, like/dislike others' feedback

**Administrators**
- Dashboard with totals and **reports by status and by scam category** (scam-pattern analysis)
- Review queue; approve / reject / request evidence with a note to the reporter
- User management (activate/deactivate), reported-pages overview, content moderation
- Read-only audit log of every administrator action

**Trust score** (0–100): community feedback sets the base; only admin-verified reports lower it;
unverified reports never change it, and no label ever says "fraud". Formula: `docs/IMPLEMENTATION_GUIDE.md` §9.

## Technology

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Django 5.2 LTS |
| Database | MariaDB 10.11 (via XAMPP) with `mysqlclient` |
| Frontend | HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, minimal JavaScript |
| Images | Pillow (upload content verification) |
| Configuration | python-dotenv (`.env` file) |
| Testing | Django test runner (373 tests), coverage.py |

## Requirements

- Windows 10/11 (the project was developed and tested on Windows 10)
- Python **3.13** (64-bit) from python.org, with "Add python.exe to PATH" ticked
- XAMPP with **MariaDB 10.5 or newer** (10.11 used). XAMPP 8.2.12 ships MariaDB 10.4, which Django 5.2
  does not support; upgrade its MariaDB, or use a separate MySQL 8.0+/MariaDB 10.5+ server
- Git

Check: `python --version`, `git --version`, `C:\xampp\mysql\bin\mysql.exe --version`.

## Installation

All commands are for **PowerShell**, run in the project folder.

### 1. Get the code

```powershell
git clone https://github.com/muhammadtamimworkplace/my-trust.git
cd my-trust
```

### 2. Create the database and a dedicated user

Start **MySQL** in the XAMPP Control Panel, then open the database client as root:

```powershell
C:\xampp\mysql\bin\mysql.exe -u root -p
```

Run (choose your own strong password):

```sql
CREATE DATABASE mytrust_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mytrust_user'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON `mytrust\_db`.* TO 'mytrust_user'@'localhost';
GRANT ALL PRIVILEGES ON `test\_mytrust\_db`.* TO 'mytrust_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

The `\_` escapes matter: in `GRANT`, `_` is a wildcard. The second grant lets Django create and delete
its temporary test database. The application never connects as root.

### 3. Create the virtual environment and install dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activation script, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4. Configure `.env`

```powershell
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Open `.env` and set:

| Variable | Value |
|---|---|
| `SECRET_KEY` | the generated key, in single quotes: `SECRET_KEY='…'` |
| `DB_PASSWORD` | the password chosen in step 2 |
| `DEMO_USER_PASSWORD` | leave empty: `seed_demo` generates a random password and fills it in |
| `CONTACT_EMAIL` | optional public contact address for the Contact page |

The site refuses to start while any required value is still the `change-me` placeholder.
`.env` contains secrets and is ignored by Git. Never commit it.

### 5. Create the tables, an administrator and demo data

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
```

`seed_demo` creates clearly fictional demo data: pages named "… (Demo)" with `facebook.com/demo.…` links,
reports in every status, feedback and comments, plus the accounts `demo_admin`, `demo_rina`, `demo_karim`,
`demo_sadia`, `demo_tanvir` and `demo_nabila`. Their password is `DEMO_USER_PASSWORD` in `.env`.
It is safe to run repeatedly; `python manage.py seed_demo --reset` removes only demo data.

### 6. Run

```powershell
python manage.py runserver 127.0.0.1:8001
```

Open **http://127.0.0.1:8001/**. The dashboard is at `/dashboard/` (administrators only); Django admin is at `/admin/`.
Port 8001 is used because 8000 may already be taken by another local project.

## Testing

```powershell
python manage.py test                        # 373 tests, about 15 seconds
pip install -r requirements-dev.txt          # once, for coverage
python -m coverage run manage.py test
python -m coverage report                    # 99.5 % line + branch coverage
```

Manual test cases and recorded results: [`docs/testing/test-cases.md`](docs/testing/test-cases.md).

## Useful commands

| Command | Purpose |
|---|---|
| `python manage.py seed_demo` / `--reset` | Create / remove demo data |
| `python manage.py recalculate_trust` | Rebuild every page's trust score |
| `python manage.py check --deploy` | Django security check (reviewed in `docs/security-review.md`) |
| `python manage.py createsuperuser` | Create an administrator |

## Project structure

```
config/        settings, root URLs
core/          landing, about/contact, error pages, shared form helpers and upload validators
accounts/      custom user model with roles, registration, login, profile, admin_required
reports/       Facebook pages, scam reports, evidence, search, page detail, demo-data command
feedback/      page feedback, comments, votes
trustscore/    trust score formula, snapshots, badge, recalculation command
dashboard/     admin dashboard, review decisions, moderation, user management, audit log
templates/     base layouts, partials and page templates
static/        css/main.css, js/main.js
docs/          implementation guide, progress tracker, security review, test cases, diagrams
```

## Documentation

| Document | Contents |
|---|---|
| [`docs/IMPLEMENTATION_GUIDE.md`](docs/IMPLEMENTATION_GUIDE.md) | Requirements, architecture, database design, trust formula, routes, task plan |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Environment, decisions and task-by-task progress |
| [`docs/security-review.md`](docs/security-review.md) | Security requirements → controls → tests; `check --deploy` review |
| [`docs/testing/test-cases.md`](docs/testing/test-cases.md) | Automated test summary and manual test cases |
| [`docs/diagrams/`](docs/diagrams/) | ER, use case, DFD, architecture, activity and sequence diagrams |

## Limitations

- All data is user-submitted; My Trust does not collect data from Facebook.
- Administrator verification reviews the evidence provided; it is not a legal judgement.
- Runs locally over HTTP for demonstration; HTTPS settings are prepared (`HTTPS=True`) but not deployed.
- No email verification, password reset by email, or login rate limiting.

See `docs/security-review.md` §3 for details.
