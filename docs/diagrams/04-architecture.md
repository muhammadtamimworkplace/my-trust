# System Architecture

Django MVT (Model–View–Template) as a modular monolith. Views stay thin; business rules live in each
app's `services.py`; validation in forms and model validators; MariaDB enforces integrity constraints.

```mermaid
flowchart TB
    subgraph Client["Browser"]
        B["HTML + Bootstrap 5.3<br/>(CDN, SRI-pinned)"]
    end

    subgraph Django["Django 5.2 application (python manage.py runserver)"]
        MW["Middleware<br/>Security · Session · CSRF · Auth · Messages · Clickjacking"]
        URL["config/urls.py"]
        subgraph Apps["Apps"]
            CORE["core<br/>landing, about, errors,<br/>form helpers, upload validators"]
            ACC["accounts<br/>User (role), auth views,<br/>admin_required"]
            REP["reports<br/>pages, reports, evidence,<br/>search, page detail"]
            FB["feedback<br/>feedback, comments, votes"]
            TS["trustscore<br/>calculate_score, recalculate_trust,<br/>badge"]
            DASH["dashboard<br/>statistics, review, users,<br/>moderation, audit log"]
        end
        TPL["templates/<br/>base + partials + pages"]
        EV["/evidence/ID/<br/>access-checked file view"]
    end

    DB[("MariaDB 10.11<br/>mytrust_db<br/>(mytrust_user)")]
    FS[("media/evidence/<br/>not publicly served")]
    ENV[".env file<br/>SECRET_KEY, DB password"]

    B -- "HTTP GET/POST + CSRF token" --> MW --> URL --> Apps
    Apps --> TPL --> B
    REP & FB & DASH -- "page changed" --> TS
    Apps -- "Django ORM" --> DB
    REP --> EV
    EV --> FS
    ENV -.-> Django
```

| Dependency direction | Reason |
|---|---|
| `dashboard → feedback → reports → accounts` | No import cycles; each app only uses apps below it |
| `trustscore → reports, feedback` | The score reads reports and feedback; callers invoke `recalculate_trust()` explicitly (no hidden signals) |
| every app → `core` | Shared form styling and upload validators |
