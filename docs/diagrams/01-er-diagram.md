# Entity–Relationship Diagram

Generated from the real Django models (22 Nov 2026). Table names are the MariaDB table names.
`accounts_user` also has Django's standard fields (first/last name, is_staff, is_superuser, last_login),
omitted here for readability. All tables use `utf8mb4_unicode_ci`.

```mermaid
erDiagram
    accounts_user ||--o{ reports_facebookpage : "first adds (created_by, SET NULL)"
    accounts_user ||--o{ reports_scamreport : "submits (reporter, PROTECT)"
    accounts_user ||--o{ feedback_feedback : "gives"
    accounts_user ||--o{ feedback_comment : "writes"
    accounts_user ||--o{ feedback_feedbackvote : "casts"
    accounts_user ||--o{ dashboard_adminaction : "performs (admin, PROTECT)"
    accounts_user |o--o{ dashboard_adminaction : "is target of (target_user, SET NULL)"
    reports_facebookpage ||--o{ reports_scamreport : "is reported in (PROTECT)"
    reports_facebookpage ||--o{ feedback_feedback : "receives"
    reports_facebookpage ||--o| trustscore_trustevaluation : "has snapshot"
    reports_scamreport ||--o{ reports_evidence : "supported by (CASCADE)"
    reports_scamreport ||--o{ feedback_comment : "discussed in"
    reports_scamreport |o--o{ dashboard_adminaction : "reviewed in (SET NULL)"
    feedback_feedback ||--o{ feedback_feedbackvote : "voted on"

    accounts_user {
        bigint id PK
        varchar username UK
        varchar email UK "case-insensitive unique"
        varchar password "PBKDF2 hash"
        varchar role "USER or ADMIN"
        bool is_active
        datetime date_joined
    }
    reports_facebookpage {
        bigint id PK
        varchar name "indexed"
        varchar url UK "canonical https://www.facebook.com/..."
        bigint created_by_id FK
        datetime created_at
        datetime updated_at
    }
    reports_scamreport {
        bigint id PK
        bigint page_id FK
        bigint reporter_id FK
        varchar category "6 choices"
        varchar title "10-150 chars"
        text description "30-5000 chars"
        date incident_date "nullable, not future"
        decimal amount_lost "nullable, CHECK >= 0"
        varchar status "PENDING NEEDS_EVIDENCE APPROVED REJECTED"
        text admin_note
        datetime reviewed_at "nullable"
        datetime created_at
        datetime updated_at
    }
    reports_evidence {
        bigint id PK
        bigint report_id FK
        varchar file "evidence/YYYY/MM/uuid.ext"
        varchar original_name
        int size_bytes
        datetime uploaded_at
    }
    feedback_feedback {
        bigint id PK
        bigint page_id FK "UNIQUE with user_id"
        bigint user_id FK
        varchar sentiment "POSITIVE or NEGATIVE"
        text comment "max 1000"
        bool is_hidden
        datetime created_at
        datetime updated_at
    }
    feedback_comment {
        bigint id PK
        bigint report_id FK
        bigint user_id FK
        text body "2-1000 chars"
        bool is_hidden
        datetime created_at
    }
    feedback_feedbackvote {
        bigint id PK
        bigint feedback_id FK "UNIQUE with user_id"
        bigint user_id FK
        smallint value "CHECK IN (1, -1)"
        datetime created_at
    }
    trustscore_trustevaluation {
        bigint id PK
        bigint page_id FK "one-to-one"
        smallint score "0-100, CHECK <= 100"
        varchar label "INSUFFICIENT GOOD MIXED CAUTION"
        int positive_count
        int negative_count
        int verified_report_count
        int pending_report_count
        datetime calculated_at
    }
    dashboard_adminaction {
        bigint id PK
        bigint admin_id FK
        varchar action_type "9 choices"
        bigint report_id FK "nullable"
        bigint target_user_id FK "nullable"
        varchar target_type "FEEDBACK or COMMENT"
        bigint target_id "nullable"
        text note
        datetime created_at "indexed"
    }
```

**Database-level rules** (enforced by MariaDB, not only by forms): unique page URL; unique user email and
username; one feedback per (page, user); one vote per (feedback, user); `amount_lost >= 0`;
vote value in (1, −1); `score <= 100`. Composite indexes: `(page_id, status)` and `(status, created_at)` on reports.

**Normalization:** all tables are in 3NF. `trustscore_trustevaluation` is the one deliberate exception, a
derived snapshot rebuilt only by `recalculate_trust()` so lists can sort and filter by score cheaply.
