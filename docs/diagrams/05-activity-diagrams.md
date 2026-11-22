# Activity Diagrams

## Report submission (`reports.views.report_create` → `reports.services.submit_report`)

```mermaid
flowchart TD
    S([Start]) --> L{Logged in?}
    L -- No --> LG[Redirect to login, then back] --> F
    L -- Yes --> F[Fill in report form:<br/>page name, link, category, title,<br/>description, date, amount, 1–5 screenshots]
    F --> SUB[Submit]
    SUB --> V1{Link is a Facebook page?}
    V1 -- No --> E[Show errors next to fields] --> F
    V1 -- Yes --> V2{Fields valid?<br/>lengths, date not future, amount ≥ 0}
    V2 -- No --> E
    V2 -- Yes --> V3{Each file: JPG/PNG, ≤ 5 MB,<br/>real image? At most 5 files?}
    V3 -- No --> E
    V3 -- Yes --> T[[Begin transaction]]
    T --> P{Page with this canonical URL exists?}
    P -- Yes --> R[Reuse page]
    P -- No --> NP[Create page]
    R & NP --> CR[Create report, status = PENDING]
    CR --> EV[Save each screenshot with a random name]
    EV --> OK{All saved?}
    OK -- No --> RB[Roll back and delete any written files] --> ERR([Error shown])
    OK -- Yes --> TR[Recalculate page trust snapshot<br/>pending count +1, score unchanged]
    TR --> C[[Commit]]
    C --> MSG[Show “under review” message<br/>and the new report page]
    MSG --> END([End])
```

## Administrator review (`dashboard.views.report_review` → `dashboard.services.decide_report`)

```mermaid
flowchart TD
    S([Start]) --> Q[Open review queue<br/>oldest pending first]
    Q --> O[Open report: text, evidence, history]
    O --> D{Decision}
    D -- Approve --> N0[Note optional]
    D -- Reject --> N1{Note written?}
    D -- Request evidence --> N2{Note written?}
    N1 -- No --> ER[Error: note required] --> O
    N2 -- No --> ER
    N1 -- Yes --> RULES
    N2 -- Yes --> MAX{Already 5 files?}
    MAX -- Yes --> ER2[Error: cannot request more] --> O
    MAX -- No --> RULES
    N0 --> RULES{Own report?}
    RULES -- Yes --> ER3[Error: ask another admin] --> O
    RULES -- No --> T[[Begin transaction]]
    T --> U1[Set status, note, reviewed time]
    U1 --> U2[Write audit-log entry]
    U2 --> U3[Recalculate page trust score]
    U3 --> C[[Commit]]
    C --> R[Back to queue with confirmation]
    R --> NE{Status = Needs evidence?}
    NE -- Yes --> REP[Reporter sees note and<br/>“Add evidence” button] --> END([End])
    NE -- No --> END
```
