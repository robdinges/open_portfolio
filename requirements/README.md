# Requirements — OpenPortfolio

Datum: 2026-04-06
Status: Geconsolideerde requirementsverzameling

## Structuur

| Document | Onderwerp |
|---|---|
| [REQ-01-weergave-data.md](REQ-01-weergave-data.md) | Generieke regels voor dataweergave in velden, teksten, afronding, vertalingen |
| [REQ-02-weergave-layout.md](REQ-02-weergave-layout.md) | Generieke regels voor schermindeling, veldbreedte, uitlijning, navigatie |
| [REQ-03-schermen.md](REQ-03-schermen.md) | Specifieke requirements per tab/scherm |
| [REQ-04-berekeningen.md](REQ-04-berekeningen.md) | Berekeningen, business rules en validaties |
| [REQ-05-backend.md](REQ-05-backend.md) | Generieke backendfuncties en specifieke afwijkingen |
| [REQ-06-architectuur.md](REQ-06-architectuur.md) | Architectuur, technische requirements en deployment |

## Bronnen

Deze documenten zijn gedestilleerd uit:

- `REQUIREMENTS.md` — oorspronkelijke functionele requirements (FR-01 t/m FR-26, NFR-01 t/m NFR-05)
- `ORDER_ENTRY.md` — normatieve orderinvoerspecificatie
- `ORDER_ENTRY_REQUIREMENTS_STRUCTURED.md` — gestructureerde business rules en domeinmodel
- `ORDER_ENTRY_BACKLOG.md` — gapregistratie met fallback-gedrag en acceptatiecriteria
- `BACKLOG.md` — geprioriteerde backlog (Must/Should/Could)
- `FEATURES.md` — feature- en objectmodeloverzicht
- `SKILLS.md` — best practices en UI-generatieregels
- `.github/instructions.md` — UI- en dataweergave-instructies
- `.github/copilot-instructions.md` — projectconventies
- Chattranscripten met implementatieopdrachten (maart–april 2026)
- Huidige implementatie (templates, `web_app.py`, domeinmodules)

## Conventie

- **[IMPL]** = reeds geïmplementeerd en geverifieerd in de huidige codebase.
- **[SPEC]** = gespecificeerd in requirements-/ontwerpdocumenten maar nog niet (volledig) geïmplementeerd.
- **[GAP]** = expliciet bekend als ontbrekend, geregistreerd in backlog of gaplijst.
- **[IMPLICIET]** = afgeleid uit werking, opdrachten of verwacht gedrag maar niet eerder formeel vastgelegd.
