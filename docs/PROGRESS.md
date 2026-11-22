# My Trust — Progress Tracker

> Updated after every verified task. Status: ⬜ pending · 🔄 in progress · ✅ done · ⛔ blocked · ✂️ dropped (deadline)
> Last updated: 22 Nov 2026 · Phases 1–2 merged to `main` (`dfa90ea`, `86f1ae3`) · Next task: **P11-T02** · Branch: `feature/p11-security` (Phases 3–10 merged, latest `aa50501`)

## Development environment (verified in P1-T01, 22 Nov 2026)

| Tool | Version | Notes |
|------|---------|-------|
| OS | Windows 10 Pro 10.0.19045 | console code page cp949 (affects terminal output of non-ASCII text only) |
| Python | 3.13.17 (64-bit) | installed from python.org (latest 3.13 with a Windows installer; 3.13.18 is source-only). Authenticode signature valid (Python Software Foundation). Per-user, on PATH, `py` launcher. |
| pip | 26.2.2 | |
| Git | 2.55.0.windows.2 | |
| VS Code | 1.127.0 (x64) | |
| XAMPP | 8.2.12 (PHP 8.2.12, phpMyAdmin 5.2.1) | |
| **MariaDB (XAMPP)** | **10.11.20 LTS, port 3306** | upgraded from 10.4.32; used by My Trust |
| MySQL (service `MySQL84`) | 8.4.9, 127.0.0.1:3307 | another project's server (`bomnal*`). **Not used, not modified.** |
| Django (chosen) | 5.2 LTS | supports MariaDB 10.5+ |
| **Virtual env** (P1-T05) | `venv\` (Python 3.13.17) | Django 5.2.19, mysqlclient 2.3.2, Pillow 13.0.0, python-dotenv 1.2.4 (+ asgiref 3.13.0, sqlparse 0.6.1, tzdata 2026.6); all prebuilt cp313 wheels; `pip check` clean; live DB connection as `mytrust_user` verified |

### My Trust database (P1-T04)

| Item | Value |
|------|-------|
| Database | `mytrust_db`, utf8mb4 / utf8mb4_unicode_ci |
| Test database | `test_mytrust_db`, created and dropped by Django automatically (lifecycle verified) |
| Account | `mytrust_user@localhost`, ALL on `mytrust\_db`.* and `test\_mytrust\_db`.* only |
| Credentials | `C:\projects\MY-TRUST\.env` (32-char random password; ignored by `.gitignore`) |
| Verification | 11/11 checks passed: login, encoding, read/write (incl. Bangla text), test-DB create/drop; denied on other DBs, other DB names, CREATE USER |

## MariaDB 10.4 → 10.11 upgrade record (22 Nov 2026)

| Step | Result |
|------|--------|
| Download | official `mariadb-10.11.20-winx64.zip`, SHA-256 `aad30008…82c3` matches archive.mariadb.org |
| Dry run | separate 10.11 instance (port 3310, `C:\mariadb_staging`): old `my.ini` valid; backup restored; 172/172 row counts match |
| Final backup | `C:\xampp_backup_preupgrade_20261122\`: fresh SQL dump, grants, row counts, checksums, and a byte-identical copy of the stopped 10.4 data dir (449 files). Restore-tested: 172/172 checksums identical. |
| Config | `my.ini` = old file with `key_buffer` → `key_buffer_size` (deprecated short name). All other settings unchanged. |
| Server settings | sql_mode, charset, collation, max_allowed_packet, lower_case_table_names identical to 10.4 |
| Data | 6 project DBs + phpmyadmin: **172/172 row counts match baseline, 172/172 table checksums identical** |
| Users | root@localhost / 127.0.0.1 / ::1 and pma@localhost: grants identical to 10.4 (extra default `root@hostname` account and two extra PROXY rows removed) |
| Stop/start | clean shutdown + restart OK; root login via localhost, 127.0.0.1, ::1 OK; pma OK and restricted to `phpmyadmin` |
| phpMyAdmin | HTTP 200, shows 10.11.20; no configuration-storage or control-user warnings |
| Rollback | old install kept at `C:\xampp\mysql_10.4_backup` (stop MySQL, rename folders back) |

**Known differences / follow-ups**
* New 10.11 default: the `PUBLIC` role has access to databases named `test` / `test_*`, so every account (incl. `mytrust_user`) can see the empty `test` DB. This is the stock MariaDB setup and doesn't affect the 6 project DBs or `mytrust_db`. Left as is unless you want it revoked.
* ✅ 22 Nov: manual checks passed (reported by you): XAMPP Control Panel Stop/Start, phpMyAdmin, and the existing apps on 10.11.
* `C:\xampp\mysql_10.4_backup\resetroot.bat` is 10.4-only. Do not use it on 10.11.
* MariaDB time-zone tables are empty (`CONVERT_TZ()` returns NULL), so Django features that convert dates inside the DB fail (admin `date_hierarchy`, `TruncDate`/`TruncMonth` with USE_TZ). **Rule:** group dates in Python. Loading the tables would change the shared server, so ask first.

## Open questions

| # | Question | Status |
|---|----------|--------|
| Q1 | University thesis formatting guideline | ⬜ awaiting |
| Q2 | What exactly is due on 30 Nov (printed/bound, defense, soft copy)? | ⬜ awaiting |
| Q3 | Completed proposal document available? | ⬜ awaiting |

## Tasks

| Phase | Task | Name | Status | Commit |
|-------|------|------|--------|--------|
| P1 | T01 | Verify development toolchain | ✅ 22 Nov | — (no file changes) |
| P1 | T02 | Commit project documentation | ✅ 22 Nov | `docs: add implementation guide and progress tracker` |
| P1 | T03 | Add .gitignore | ✅ 22 Nov | `chore: add gitignore for Python and Django` |
| P1 | T04 | Create MySQL database and user | ✅ 22 Nov (done early, with the upgrade) | — (no repo files) |
| P1 | T05 | Virtual env + pinned dependencies | ✅ 22 Nov | `chore: add pinned project dependencies` |
| P2 | T01 | Initialize Django project | ✅ 22 Nov | `chore: initialize Django project` |
| P2 | T02 | Settings from environment | ✅ 22 Nov | `chore: load settings from environment variables` |
| P2 | T03 | MySQL connection | ✅ 22 Nov | `chore: configure MySQL database connection` |
| P2 | T04 | Templates/static/media config | ✅ 22 Nov (TIME_ZONE Asia/Dhaka) | `chore: configure templates, static and media settings` |
| P2 | T05 | Create application modules | ✅ 22 Nov | `chore: create application modules` |
| P2 | T06 | Base layout | ✅ 22 Nov (Bootstrap 5.3.9, Icons 1.13.2, SRI) | `feat: add base layout with navbar and footer` |
| P2 | T07 | Landing page | ✅ 22 Nov (6 tests; served on :8001; your browser/mobile check not yet reported) | `feat: add landing page` |
| P3 | T01 | Custom User model with roles | ✅ 22 Nov (first migrate; 7 model tests) | `feat: add custom user model with roles` |
| P3 | T02 | User admin + superuser | ✅ code 22 Nov (4 admin tests) · ⬜ superuser: you run `createsuperuser` | `feat: register user model in admin` |
| P3 | T03 | Registration | ✅ 22 Nov (12 tests incl. role injection + CSRF) | `feat: add user registration` |
| P3 | T04 | Login & logout | ✅ 22 Nov (12 tests: session rotation, open-redirect, POST-only logout) | `feat: add login and logout` |
| P3 | T05 | Profile page | ✅ 22 Nov (5 tests) | `feat: add user profile page` |
| P3 | T06 | (S) Profile edit & password change | ✅ 22 Nov (10 tests) | `feat: add profile editing and password change` |
| P3 | T07 | admin_required decorator | ✅ 22 Nov (6 tests) | `feat: add admin_required access decorator` |
| P3 | T08 | Accounts tests | ✅ 22 Nov: covered by tests written in T01–T07 (56 accounts tests); no separate commit | — |
| P4 | T01 | FacebookPage + URL normalization | ✅ 22 Nov (9 tests, 20+ URL cases) | `feat: add Facebook page model with URL normalization` |
| P4 | T02 | ScamReport model | ✅ 22 Nov (8 tests; DB CHECK amount ≥ 0) | `feat: add scam report model` |
| P4 | T03 | Evidence model + validators | ✅ 22 Nov (14 tests: ext, size, Pillow content, UUID names) | `feat: add evidence model with upload validation` |
| P4 | T04 | Feedback/Comment/Vote models | ✅ 22 Nov (8 tests; 2 UNIQUE + 1 CHECK in DB) | `feat: add feedback, comment and vote models` |
| P4 | T05 | TrustEvaluation model | ✅ 22 Nov (5 tests) | `feat: add trust evaluation model` |
| P4 | T06 | AdminAction model | ✅ 22 Nov (5 tests) | `feat: add admin action audit log model` |
| P4 | T07 | Register models in admin | ✅ 22 Nov (5 tests; trust + audit log read-only) | `feat: register domain models in admin` |
| P4 | T08 | Demo seed command | ✅ 22 Nov (6 tests; seeded mytrust_db: 6 users, 8 pages, 15 reports) | `feat: add demo data seeding command` |
| P4 | T09 | Model constraint tests | ✅ 22 Nov: covered by tests written in T01–T08; no separate commit | — |
| P5 | T01 | Report form | ✅ 22 Nov (9 tests; multi-file upload, 1–5 files) | `feat: add scam report form with validation` |
| P5 | T02 | Submission service + view | ✅ 22 Nov (10 tests; atomic incl. file cleanup) | `feat: implement report submission` |
| P5 | T03 | My reports history | ✅ 22 Nov (8 tests; constant query count) | `feat: add user report history` |
| P5 | T04 | Report detail | ✅ 22 Nov (11 tests; rejected = 404 for public; evidence/note private) | `feat: add report detail page` |
| P5 | T05 | Protected evidence serving | ✅ 22 Nov (7 tests; owner/admin only, no-store, /media/ not served) | `feat: serve evidence through access-controlled view` |
| P5 | T06 | Add evidence on request | ✅ 22 Nov (9 tests; reporter only, back to review) | `feat: allow adding evidence when requested` |
| P5 | T07 | Reporting tests | ✅ 22 Nov: covered by tests written in T01–T06; no separate commit | — |
| P6 | T01 | Score calculation | ✅ 22 Nov (10 tests; pure function, half-up rounding) | `feat: implement trust score calculation` |
| P6 | T02 | Persist & recalculate | ✅ 22 Nov (7 tests; wired into submission, evidence, seed; `recalculate_trust` command) | `feat: persist trust evaluations and add recalculation command` |
| P6 | T03 | Trust badge component | ✅ 22 Nov (7 tests; full + compact; disclaimer; no number for "Not enough data") | `feat: add trust score badge component` |
| P7 | T01 | Page list search & filters | ✅ 22 Nov (13 tests; name or any-form link; category + verification filters) | `feat: add page search and filters` |
| P7 | T02 | Page detail | ✅ 22 Nov (9 tests; 3 separate sections; prefilled "Report this page") | `feat: add Facebook page detail view` |
| P7 | T03 | Connect landing/navbar search | ✅ 22 Nov (4 tests) | `feat: connect landing and navbar search to page results` |
| P7 | T04 | Search tests | ✅ 22 Nov: covered by tests written in T01–T03; no separate commit | — |
| P8 | T01 | Feedback create/update | ✅ 22 Nov (11 tests; one per user per page; recalculates score; moderator hide kept) | `feat: add page feedback submission` |
| P8 | T02 | Delete own feedback | ✅ 22 Nov (6 tests; owner only, others get 404) | `feat: allow users to delete their feedback` |
| P8 | T03 | (S) Comments on reports | ✅ 22 Nov (7 tests; public reports only; hidden excluded) | `feat: add comments on reports` |
| P8 | T04 | (S) Feedback voting | ✅ 22 Nov (10 tests; toggle; no own/hidden votes; no score effect) | `feat: add feedback voting` |
| P8 | T05 | (S) Community activity | ✅ 22 Nov (4 tests; verified reports + visible feedback only) | `feat: show recent community activity` |
| P8 | T06 | Feedback tests | ✅ 22 Nov: covered by tests written in T01–T05; no separate commit | — |
| P9 | T01 | Dashboard overview stats | ✅ 22 Nov (12 tests; by status + by category; no date grouping in DB) | `feat: add admin dashboard overview` |
| P9 | T02 | Report review queue | ✅ 22 Nov (8 tests; tabs with counts; oldest pending first) | `feat: add report review queue` |
| P9 | T03 | Review decisions | ✅ 22 Nov (17 tests; atomic; audit log; score refresh; own-report + evidence-cap rules) | `feat: implement report moderation decisions` |
| P9 | T04 | User management | ✅ 22 Nov (13 tests; not self/superuser; audit log; sessions invalidated) | `feat: add user management` |
| P9 | T05 | Reported pages overview | ✅ 22 Nov (7 tests; includes pages hidden from public; correct joined counts) | `feat: add reported pages overview` |
| P9 | T06 | (S) Content moderation | ✅ 22 Nov (10 tests; hide/restore; audit log; trust recalculated) | `feat: add content moderation` |
| P9 | T07 | (S) Activity log | ✅ 22 Nov (5 tests; read-only; filter by action) | `feat: add admin activity log` |
| P9 | T08 | Dashboard tests | ✅ 22 Nov (7 tests; auto-discovered route matrix; mutation-checked) | `test: add dashboard access and moderation tests` |
| P10 | T01 | Components & responsive pass | ✅ 22 Nov (9-rule template audit test; dashboard menu scrolls on phones; visual check by you pending) | `style: unify components and improve responsive layout` |
| P10 | T02 | About & contact | ✅ 22 Nov (4 tests; optional CONTACT_EMAIL, no invented address) | `feat: add about and contact pages` |
| P10 | T03 | Error pages | ✅ 22 Nov (5 tests; 403, 404, 500, CSRF; no technical details) | `feat: add custom error pages` |
| P11 | T01 | Security settings | ✅ 22 Nov (7 tests; check --deploy reviewed in docs/security-review.md; test suite 130s → 11s) | `chore: harden security settings` |
| P11 | T02 | Full test run & fixes | 🔄 coverage 98.8% (branch); fixes in progress | |
| P11 | T03 | Manual test case document | ⬜ | |
| P12 | T01 | README | ⬜ | |
| P12 | T02 | System diagrams | ⬜ | |
| P12 | T03 | Screenshots | ⬜ | |
| P12 | T04 | Fresh-install rehearsal + v1.0.0 | ⬜ | |

## Thesis track

| ID | Output | Status |
|----|--------|--------|
| T1 | Collect proposal & guidelines | ⬜ |
| T2 | Chapter 1 | ⬜ |
| T3 | Chapter 2 | ⬜ |
| T4 | Chapter 3 + diagrams | ⬜ |
| T5 | Chapter 4 | ⬜ |
| T6 | Chapter 5 | ⬜ |
| T7 | Chapter 6 + front/back matter | ⬜ |
| T8 | Proofread, print, bind | ⬜ |

## Dropped scope / decisions log

| Date | Decision |
|------|----------|
| 22 Nov 2026 | Local-only deployment, no email features, no Facebook scraping, no ML (guide §1.5) |
| 22 Nov 2026 | Python 3.13.17 installed (3.13.18 has no Windows installer). |
| 22 Nov 2026 | XAMPP MariaDB upgraded 10.4.32 → 10.11.20 so Django 5.2 LTS can be used; all existing data and users preserved and verified. MySQL 8.4 (port 3307) left untouched. |
| 22 Nov 2026 | Dedicated `mytrust_user`; Django never connects as root. |
| 22 Nov 2026 | Dev server runs on **port 8001** (`manage.py runserver 127.0.0.1:8001`); port 8000 is used by the Aura Studio Laravel dev server. |
