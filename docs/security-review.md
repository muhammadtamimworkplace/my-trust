# My Trust — Security Review

Review date: 22 Nov 2026 · Django 5.2.19 · MariaDB 10.11.20 · task P11-T01

This document maps each security requirement of the project (source document §8, guide §12.2)
to how it is implemented and which automated tests prove it. It also records the output of
Django's deployment check and the warnings accepted for the local demonstration.

## 1. Requirements → controls → evidence

| Requirement | Implementation | Verified by (tests) |
|---|---|---|
| Passwords hashed, never plain text | Django auth with PBKDF2-SHA256 (`PRODUCTION_PASSWORD_HASHERS`); password strength validators on sign-up and change | `accounts/tests/test_models.py`, `test_registration.py` (pinned to PBKDF2), `core/tests/test_security.py` |
| CSRF protection | `CsrfViewMiddleware`; `{% csrf_token %}` in every POST form; logout is POST-only | CSRF-enforcing client tests in accounts, reports, feedback and dashboard; template audit rule "every POST form has a CSRF token" |
| Input validation | Django forms + model validators (length, dates not in future, amount ≥ 0, allowed categories); DB `CHECK` and `UNIQUE` constraints as a second layer | `reports/tests/test_forms.py`, `test_models.py`, `feedback/tests/test_models.py` |
| File upload validation | Extension whitelist (JPG/PNG), 5 MB limit, Pillow content check (rejects renamed scripts/GIFs, truncated and "decompression bomb" images), max 5 files per report, random UUID file names | `core/tests/test_validators.py`, `reports/tests/test_forms.py`, `test_evidence_add.py` |
| File size/type limits at request level | `DATA_UPLOAD_MAX_NUMBER_FILES = 10` (hard refusal beyond the friendly 5-file form error), 2 MB in-memory limits | `core/tests/test_security.py::UploadLimitTests` |
| Evidence handled appropriately | Never served from public `/media/`; only via `/evidence/<id>/`, which checks reporter-or-admin and sends `Cache-Control: private, no-store` | `reports/tests/test_evidence_access.py` |
| SQL injection | Django ORM only; no raw SQL anywhere in the project | Code search for `.raw(` / `connection.cursor` across all apps and tests: no matches (22 Nov 2026) |
| XSS | Template autoescaping; `|safe` and `autoescape off` are banned | Template audit test; tests that post `<script>` and check it is escaped (reports, comments) |
| Unauthorized access / role-based permissions | `@login_required`; `@admin_required` (role ADMIN or superuser) on every dashboard view; owner checks for evidence, feedback deletion, adding evidence | `dashboard/tests/test_access_control.py` (auto-discovers **every** dashboard route; mutation-checked: removing one decorator makes it fail), plus per-feature access tests |
| Secure sessions | HttpOnly + SameSite=Lax session and CSRF cookies; session key rotated at login; 1-week lifetime; deactivated users' sessions stop working | `core/tests/test_security.py::CookieTests`, `accounts/tests/test_login_logout.py`, `dashboard/tests/test_users.py` |
| No exposure of sensitive data | Public pages show usernames only (never emails); rejected reports and pages with no public information return 404; error pages show no technical details | `reports/tests/test_report_detail.py`, `test_page_detail.py`, `core/tests/test_error_pages.py` |
| Open-redirect protection | `?next=` values checked with `url_has_allowed_host_and_scheme` (login, dashboard actions) | `accounts/tests/test_login_logout.py`, `dashboard/tests/test_users.py`, `test_moderation.py` |
| Clickjacking / MIME sniffing / referrer leaks | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin` | `core/tests/test_security.py::SecurityHeaderTests` |
| Secrets kept out of the code | `SECRET_KEY`, DB password and demo password only in `.env` (git-ignored); app refuses to start without `SECRET_KEY` | Every commit scanned for the real secrets; `.env` never committed (verified in git history) |
| Least-privilege database account | Django connects as `mytrust_user`, which has rights only on `mytrust_db` / `test_mytrust_db` (cannot read other databases or create users) | 11-check verification in `docs/PROGRESS.md` |
| Audit trail | Every admin decision, moderation action and account change is written to `AdminAction`; the log is read-only in the UI and in Django admin | `dashboard/tests/test_*`, `core/tests/test_admin_site.py` |

## 2. `python manage.py check --deploy`

### Local demonstration (DEBUG=False, HTTPS=False): 4 warnings, all accepted

```
?: (security.W004) You have not set a value for the SECURE_HSTS_SECONDS setting. ...
?: (security.W008) Your SECURE_SSL_REDIRECT setting is not set to True. ...
?: (security.W012) SESSION_COOKIE_SECURE is not set to True. ...
?: (security.W016) ... you have not set CSRF_COOKIE_SECURE to True. ...
System check identified 4 issues (0 silenced).
```

**Why they are accepted:** the thesis demonstration runs on the developer's own computer over plain
HTTP at `127.0.0.1`. All four settings require HTTPS; enabling them on HTTP would break login
(secure cookies are never sent over HTTP) or redirect to an HTTPS address that does not exist.

### Simulated HTTPS deployment (DEBUG=False, HTTPS=True): 1 warning, accepted

```
?: (security.W021) You have not set the SECURE_HSTS_PRELOAD setting to True. ...
System check identified 1 issue (0 silenced).
```

Setting `HTTPS=True` in `.env` turns on secure cookies, the HTTPS redirect and 30-day HSTS together.
HSTS *preload* is deliberately left off: being added to browsers' preload list is difficult to undo
and is only appropriate for a permanent production domain.

## 3. Known limitations (for the thesis "Limitations" section)

- **No brute-force / rate limiting** on login. Mitigation would need an extra package (e.g. django-axes) or a reverse proxy; left as future work.
- **No email verification or password reset by email**: there is no mail server in the local setup.
- **Local HTTP only**: HTTPS settings are prepared (one `HTTPS=True` switch) but not exercised, because there is no deployment.
- **Total upload size** per request is not capped by Django itself (files stream to disk); a web server would normally enforce this in production.
- **Admin verification** reviews the evidence supplied; it is not a legal judgement about a business.
