# Use Case Diagram

Mermaid has no native UML use-case notation, so this is drawn as a flowchart: actors on the left, use
cases (rounded) grouped by module. A Registered User can do everything a Visitor can; an Administrator
can do everything a Registered User can (generalization arrows).

```mermaid
flowchart LR
    V(["👤 Visitor"])
    U(["👤 Registered User"])
    A(["👤 Administrator"])
    U -.->|is a| V
    A -.->|is a| U

    subgraph Discovery["Search and discovery"]
        UC1(["Search pages by name or link"])
        UC2(["Filter by category / verification"])
        UC3(["View page detail and trust score"])
        UC4(["View public report"])
    end
    subgraph Account["User management"]
        UC5(["Register"])
        UC6(["Log in / log out"])
        UC7(["Edit profile, change password"])
    end
    subgraph Reporting["Facebook page reporting"]
        UC8(["Submit report with evidence"])
        UC9(["View my reports and status"])
        UC10(["Add requested evidence"])
    end
    subgraph Community["Feedback and community"]
        UC11(["Give / edit / delete feedback"])
        UC12(["Comment on report"])
        UC13(["Like / dislike feedback"])
    end
    subgraph Admin["Admin dashboard"]
        UC14(["View statistics and scam patterns"])
        UC15(["Review report: approve / reject / request evidence"])
        UC16(["Manage users"])
        UC17(["Moderate feedback and comments"])
        UC18(["View audit log"])
    end

    V --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6
    U --- UC7 & UC8 & UC9 & UC10 & UC11 & UC12 & UC13
    A --- UC14 & UC15 & UC16 & UC17 & UC18
```

| Actor | Use cases | Enforced by |
|---|---|---|
| Visitor | UC1–UC6 | public views |
| Registered User | + UC7–UC13 | `@login_required`; owner checks (own feedback, own report evidence) |
| Administrator | + UC14–UC18 | `@admin_required` (role ADMIN or superuser) on every dashboard view |
