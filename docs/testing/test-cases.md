# My Trust — Test Cases and Results

Prepared 22 Nov 2026 (task P11-T03) for thesis Chapter 5 "Testing and Results".

> **Integrity rule:** the *Actual result* and *Status* of a manual test are filled in **only after the
> test has really been performed**. Until then they stay blank / "Not run". Automated results in §2
> are copied from real test-runner output.

## 1. Test environment

| Item | Version / value |
|---|---|
| OS | Windows 10 Pro 10.0.19045 |
| Python | 3.13.17 |
| Django | 5.2.19 |
| Database | MariaDB 10.11.20 (XAMPP 8.2.12), database `mytrust_db`, test database `test_mytrust_db` |
| Browser (manual tests) | Google Chrome (record the version when testing) |
| Server | `python manage.py runserver 127.0.0.1:8001` |
| Test data | `python manage.py seed_demo` (fictional "(Demo)" pages; accounts `demo_admin`, `demo_rina`, `demo_karim`, `demo_sadia`, `demo_tanvir`, `demo_nabila`; password = `DEMO_USER_PASSWORD` in `.env`) |

## 2. Automated tests (unit, integration, functional, security)

Run with:

```powershell
python manage.py test                       # all tests
python -m coverage run manage.py test       # with coverage (pip install -r requirements-dev.txt)
python -m coverage report
```

**Result recorded 22 Nov 2026:** `Ran 370 tests … OK` (≈12 s). Line + branch coverage **99.5 %**
(1 312 statements, 3 missed; 47 of 53 measured files at 100 %).

| App | Tests | What the tests cover |
|---|---:|---|
| accounts | 56 | Custom user model, password hashing (PBKDF2), registration validation (duplicate/weak/mismatched, role injection), login/logout (session rotation, open redirect, POST-only logout, inactive users), profile, profile edit, password change, `admin_required` |
| core | 50 | Landing page, recent activity, about/contact, upload validators, Django-admin configuration, error pages (403/404/500/CSRF), security headers and cookies, upload limits, template audit (9 rules) |
| reports | 109 | URL normalization (20+ variants), models and DB constraints, report form, atomic submission incl. file clean-up on failure, history, report visibility rules, private evidence serving, adding requested evidence, page search and filters, page detail, demo-data command |
| feedback | 42 | Feedback create/edit/delete, one-per-user rule, comments, like/dislike voting rules |
| trustscore | 29 | Score formula (worked example, every label boundary, penalty cap, rounding), recalculation, badge display |
| dashboard | 84 | Overview statistics, review queue, review decisions (rules, audit log, rollback), user management, page overview, moderation, activity log, **access-control matrix over every dashboard route** |
| **Total** | **370** | |

Test types covered (source document §10): unit ✔ · integration ✔ · functional ✔ · authentication ✔ · form validation ✔ · file upload ✔ · database ✔ · access control ✔ · usability → manual tests in §3 (UI-*).

## 3. Manual test cases

**Status:** Pass · Fail · Not run. Record the date and tester for each run in §4.

### 3.1 Authentication (AUTH)

| ID | Test scenario | Input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| AUTH-01 | Register a new account | Username `tester1`, a new email, strong password twice | Account created, user logged in, "Welcome to My Trust" message, navbar shows username | | Not run |
| AUTH-02 | Register with an email already in use | Same email as AUTH-01 in different letter case | Error "An account with this email address already exists."; no account created | | Not run |
| AUTH-03 | Register with a weak password | Password `12345678` | Error "This password is too common."; no account created | | Not run |
| AUTH-04 | Log in with correct credentials | `demo_rina` + demo password | Logged in, redirected to home, username in navbar | | Not run |
| AUTH-05 | Log in with a wrong password | `demo_rina` + wrong password | Error "Please enter a correct username and password"; not logged in | | Not run |
| AUTH-06 | Log out | Click **Log out** | Logged out, navbar shows Log in / Register | | Not run |
| AUTH-07 | Change password | Profile → Change password, correct old + new password | "Your password has been changed."; still logged in; new password works next login | | Not run |
| AUTH-08 | Deactivated user cannot log in | Admin deactivates `tester1`, then log in as `tester1` | Login refused | | Not run |

### 3.2 Reporting and evidence (REP)

| ID | Test scenario | Input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| REP-01 | Submit a report with evidence | Logged in; page name, link `https://m.facebook.com/Some.Shop/?ref=x`, category, title, description, 1 PNG | Redirect to report page, "under review" message, link stored as `https://www.facebook.com/some.shop` | | Not run |
| REP-02 | Same page reported with a different link form | Report again with `fb.com/some.shop/` | Second report attaches to the **same** page (no duplicate in Browse) | | Not run |
| REP-03 | Non-Facebook link rejected | Link `https://www.instagram.com/some.shop` | Error "Enter a facebook.com link …"; nothing saved | | Not run |
| REP-04 | Report without a screenshot | No file selected | Error "Attach at least one screenshot." | | Not run |
| REP-05 | Fake image rejected | A `.txt` file renamed to `photo.png` | Error naming the file: "not a valid JPG or PNG image" | | Not run |
| REP-06 | File larger than 5 MB rejected | A real JPG > 5 MB | Error stating the file size and the 5 MB limit | | Not run |
| REP-07 | More than 5 files rejected | 6 valid images | Error "You can attach at most 5 files per report." | | Not run |
| REP-08 | Future incident date rejected | Incident date tomorrow | Error "The incident date cannot be in the future." | | Not run |
| REP-09 | My reports shows status and admin note | `demo_sadia` → My reports | Reports listed newest first with status badges; admin note visible on reviewed ones | | Not run |
| REP-10 | Add evidence when requested | `demo_sadia` → report "Paid but parcel marked as returned" → Add evidence → 1 image | Message "back under review"; status becomes Under review | | Not run |

### 3.3 Privacy and visibility (PRIV)

| ID | Test scenario | Input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| PRIV-01 | Evidence visible to the reporter | `demo_rina` opens her verified report | Screenshot thumbnails shown in the private section | | Not run |
| PRIV-02 | Evidence hidden from other users | Log in as `demo_karim`, open the same report URL | No private section, no thumbnails | | Not run |
| PRIV-03 | Evidence URL blocked for other users | As `demo_karim`, open the `/evidence/<id>/` URL copied in PRIV-01 | 403 "You don't have access to this page" | | Not run |
| PRIV-04 | Rejected report hidden from public | Logged out, open a rejected report's URL | 404 "Page not found" | | Not run |
| PRIV-05 | Unverified report clearly labelled | Logged out, open a pending report | Yellow "Unverified allegation" notice | | Not run |
| PRIV-06 | No emails shown publicly | Browse page detail and report pages as a visitor | Only usernames appear, never email addresses | | Not run |

### 3.4 Search and trust score (SRCH, TRUST)

| ID | Test scenario | Input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| SRCH-01 | Search by name from landing page | Type `closet` in the hero search | Results list shows "Trendy Closet (Demo)" | | Not run |
| SRCH-02 | Search by any form of link | `https://m.facebook.com/demo.luxe.watches/?ref=x` | Exactly "Luxe Watches (Demo)" | | Not run |
| SRCH-03 | Filter by category + verification | Category "Fake product", "Has verified reports" | Only pages with a verified/public fake-product report | | Not run |
| SRCH-04 | No results message | Search `zzzz` | "No reported pages match …" + warning that no reports doesn't mean safe | | Not run |
| TRUST-01 | Page detail sections are separate | Open Trendy Closet (Demo) | Separate "Verified reports", "Unverified allegations", "Community feedback" sections + disclaimer | | Not run |
| TRUST-02 | Unverified report does not change score | Note Beauty Hub's badge, submit a new report about it | Badge still "Not enough data"; unverified count +1 | | Not run |
| TRUST-03 | Approval lowers the score | Admin approves a pending report on a page | That page's score drops by 15 (verified count +1) | | Not run |

### 3.5 Community feedback (FB)

| ID | Test scenario | Input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| FB-01 | Give feedback | Logged in, page detail → 👎 + comment → Submit | "Thank you, your feedback was saved."; counts and score updated | | Not run |
| FB-02 | Edit instead of duplicate | Submit again with 👍 | "Your feedback was updated."; still only one feedback from this user | | Not run |
| FB-03 | Delete own feedback | Click "Delete my feedback" | "Your feedback was deleted."; counts updated | | Not run |
| FB-04 | Comment on a report | Report page → write a comment → Post | Comment appears under the report with your username | | Not run |
| FB-05 | Like / dislike others' feedback | Click 👍 on someone else's feedback, then 👍 again | Count +1, then back to previous (toggle) | | Not run |
| FB-06 | Cannot vote on own feedback | Look at your own feedback | No vote buttons, only counts | | Not run |

### 3.6 Administration (ADM)

| ID | Test scenario | Input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| ADM-01 | Dashboard statistics | `demo_admin` → Dashboard | Totals, reports by status, **reports by scam category**, most reported pages | | Not run |
| ADM-02 | Review queue order | Dashboard → Review queue | "Under review" tab, oldest report first, counts on each tab | | Not run |
| ADM-03 | Approve a report | Open a pending report → Approve → Save | "Decision saved: Verified by admin."; entry in Activity log; page score updated | | Not run |
| ADM-04 | Reject requires a note | Choose Reject with empty note | Error "Write a note for the reporter …"; status unchanged | | Not run |
| ADM-05 | Request evidence | Request more evidence with a note | Status "Needs more evidence"; reporter sees the note and an Add evidence button | | Not run |
| ADM-06 | Admin cannot review own report | `demo_admin` reports a page, then tries to approve it | Error "You cannot review your own report." | | Not run |
| ADM-07 | Deactivate and reactivate a user | Users → Deactivate `tester1` → Activate | Messages confirm each change; both appear in Activity log | | Not run |
| ADM-08 | Hide inappropriate feedback | Moderation → Hide a feedback | Disappears from the public page detail; trust counts updated; logged | | Not run |
| ADM-09 | Non-admin blocked from dashboard | Log in as `demo_rina`, open `/dashboard/` | 403 "You don't have access to this page" | | Not run |

### 3.7 Usability and responsiveness (UI)

| ID | Test scenario | Input | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| UI-01 | Phone layout | Chrome DevTools device toolbar, width 375 px: home, browse, page detail, report form, dashboard | No horizontal page scrolling; menu collapses to ☰; cards stack; dashboard menu scrolls sideways | | Not run |
| UI-02 | Desktop layout | Window 1366 px wide, same pages | Content readable, sidebar on dashboard, no overlap | | Not run |
| UI-03 | No browser console errors | DevTools → Console while visiting the main pages | No red errors | | Not run |
| UI-04 | Keyboard navigation | Use Tab / Enter only to log in and submit feedback | All controls reachable, visible focus outline, "Skip to main content" link appears on first Tab | | Not run |
| UI-05 | Friendly error pages | Visit `/does-not-exist/` | Styled "Page not found" page with links home and to Browse | | Not run |

## 4. Test run log

| Date | Tester | Cases run | Passed | Failed | Notes |
|---|---|---|---|---|---|
| | | | | | |

## 5. Summary (fill in after running §3)

| Category | Cases | Passed | Failed | Not run |
|---|---:|---:|---:|---:|
| Authentication (AUTH) | 8 | | | |
| Reporting and evidence (REP) | 10 | | | |
| Privacy and visibility (PRIV) | 6 | | | |
| Search and trust (SRCH, TRUST) | 7 | | | |
| Community feedback (FB) | 6 | | | |
| Administration (ADM) | 9 | | | |
| Usability (UI) | 5 | | | |
| **Total** | **51** | | | |
