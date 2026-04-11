"""
Portfolio Analytics — Modular MVP for portfolio analysis.

A scalable, modular Python package for portfolio analysis, mock data generation,
and clean API/UI separation. Designed for extensibility toward real pricing feeds,
additional asset classes, and multi-user support.

Package structure:
    domain/        Pure domain models and enums (no DB or I/O logic)
    db/            Database schema and connection management
    repositories/  Data-access abstractions and SQLite implementations
    services/      Business logic: pricing, FX, analytics, transactions
    mock/          Deterministic mock data generation
    api/           FastAPI REST endpoints
    ui/            Streamlit dashboard pages
    app/           Application bootstrap, config, dependency injection
    utils/         Shared helpers (date, currency formatting)
"""

__version__ = "0.1.0"
