# My Trust — Progress Tracker

> Updated after every verified task. Status: ⬜ pending · 🔄 in progress · ✅ done · ⛔ blocked · ✂️ dropped (deadline)
> Last updated: 22 Nov 2026 · Phase 1 merged to `main` (`dfa90ea`) · Next task: **P2-T05** · Branch: `feature/p2-skeleton`

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
| P2 | T05 | Create application modules | ⬜ | |
| P2 | T06 | Base layout | ⬜ | |
| P2 | T07 | Landing page | ⬜ | |
| P3 | T01 | Custom User model with roles | ⬜ | |
| P3 | T02 | User admin + superuser | ⬜ | |
| P3 | T03 | Registration | ⬜ | |
| P3 | T04 | Login & logout | ⬜ | |
| P3 | T05 | Profile page | ⬜ | |
| P3 | T06 | (S) Profile edit & password change | ⬜ | |
| P3 | T07 | admin_required decorator | ⬜ | |
| P3 | T08 | Accounts tests | ⬜ | |
| P4 | T01 | FacebookPage + URL normalization | ⬜ | |
| P4 | T02 | ScamReport model | ⬜ | |
| P4 | T03 | Evidence model + validators | ⬜ | |
| P4 | T04 | Feedback/Comment/Vote models | ⬜ | |
| P4 | T05 | TrustEvaluation model | ⬜ | |
| P4 | T06 | AdminAction model | ⬜ | |
| P4 | T07 | Register models in admin | ⬜ | |
| P4 | T08 | Demo seed command | ⬜ | |
| P4 | T09 | Model constraint tests | ⬜ | |
| P5 | T01 | Report form | ⬜ | |
| P5 | T02 | Submission service + view | ⬜ | |
| P5 | T03 | My reports history | ⬜ | |
| P5 | T04 | Report detail | ⬜ | |
| P5 | T05 | Protected evidence serving | ⬜ | |
| P5 | T06 | Add evidence on request | ⬜ | |
| P5 | T07 | Reporting tests | ⬜ | |
| P6 | T01 | Score calculation | ⬜ | |
| P6 | T02 | Persist & recalculate | ⬜ | |
| P6 | T03 | Trust badge component | ⬜ | |
| P7 | T01 | Page list search & filters | ⬜ | |
| P7 | T02 | Page detail | ⬜ | |
| P7 | T03 | Connect landing/navbar search | ⬜ | |
| P7 | T04 | Search tests | ⬜ | |
| P8 | T01 | Feedback create/update | ⬜ | |
| P8 | T02 | Delete own feedback | ⬜ | |
| P8 | T03 | (S) Comments on reports | ⬜ | |
| P8 | T04 | (S) Feedback voting | ⬜ | |
| P8 | T05 | (S) Community activity | ⬜ | |
| P8 | T06 | Feedback tests | ⬜ | |
| P9 | T01 | Dashboard overview stats | ⬜ | |
| P9 | T02 | Report review queue | ⬜ | |
| P9 | T03 | Review decisions | ⬜ | |
| P9 | T04 | User management | ⬜ | |
| P9 | T05 | Reported pages overview | ⬜ | |
| P9 | T06 | (S) Content moderation | ⬜ | |
| P9 | T07 | (S) Activity log | ⬜ | |
| P9 | T08 | Dashboard tests | ⬜ | |
| P10 | T01 | Components & responsive pass | ⬜ | |
| P10 | T02 | About & contact | ⬜ | |
| P10 | T03 | Error pages | ⬜ | |
| P11 | T01 | Security settings | ⬜ | |
| P11 | T02 | Full test run & fixes | ⬜ | |
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
