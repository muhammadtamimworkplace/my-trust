# System Diagrams

All diagrams are written in [Mermaid](https://mermaid.js.org/) and are displayed automatically when these
files are viewed on GitHub. They were drawn from the actual code (models, services and views as of
22 Nov 2026), so they match the implementation.

| # | Diagram | File | Thesis chapter |
|---|---|---|---|
| 1 | Entity–Relationship diagram | [01-er-diagram.md](01-er-diagram.md) | 3 (database design) |
| 2 | Use case diagram | [02-use-case-diagram.md](02-use-case-diagram.md) | 3 (requirements) |
| 3 | Data flow diagrams (context + level 1) | [03-data-flow-diagrams.md](03-data-flow-diagrams.md) | 3 (system design) |
| 4 | System architecture | [04-architecture.md](04-architecture.md) | 3 / 4 |
| 5 | Activity diagrams (report submission, admin review) | [05-activity-diagrams.md](05-activity-diagrams.md) | 3 |
| 6 | Sequence diagrams (admin approval, evidence access) | [06-sequence-diagrams.md](06-sequence-diagrams.md) | 3 / 4 |

## Exporting images for the printed thesis

1. Open https://mermaid.live
2. Copy the code between the ```` ```mermaid ```` and ```` ``` ```` lines of one diagram into the left panel.
3. Check it renders, then use **Actions → PNG** (or SVG for sharper printing).
4. Save as `docs/diagrams/png/<number>-<name>.png` and insert into the thesis with a figure caption.

Repeat for each diagram (some files contain two).
