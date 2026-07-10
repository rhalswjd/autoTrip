## Project Goal

This project is a personal railway travel planner for Japan.

The goal is to search railway routes, visualize them on an interactive map, and save the final selected journey into Notion.

This project is intended for local development on macOS and prioritizes maintainability, readability, and clean architecture over premature optimization.

---

# Architecture Principles

Always follow Clean Architecture.

The dependency direction must always be:

Presentation
    ↓
Application
    ↓
Domain

Infrastructure must depend on the Application/Domain layers, never the opposite.

The Domain layer must never know anything about:

- FastAPI
- Notion API
- Scrapers
- SQLite
- Leaflet
- React
- BeautifulSoup
- HTTP
- JSON

Domain objects must remain pure.

---

# SOLID Principles

Always follow SOLID.

Especially:

- Single Responsibility Principle
- Dependency Inversion Principle

Prefer composition over inheritance.

---

# Ports & Adapters

External systems must always be accessed through Ports.

Examples:

- ScraperPort
- CachePort
- NotionPort

Infrastructure provides Adapters.

Never call external libraries directly from Application Services.

---

# Coding Rules

Generate production-quality code.

Never generate placeholder code.

Never generate incomplete implementations.

Never leave TODO comments unless explicitly requested.

Every public function must have a clear responsibility.

Avoid duplicate code.

Prefer readability over cleverness.

Use meaningful names.

---

# Error Handling

Always handle failures.

Never silently ignore exceptions.

Return meaningful error messages.

Log unexpected failures.

---

# Testing

Design everything for testability.

Application Services must be testable without:

- Internet
- Notion
- Scraper
- SQLite

Always support Fake implementations.

Examples:

- FakeScraperAdapter
- FakeNotionAdapter
- InMemoryCacheAdapter

Avoid hard dependencies on external services.

---

# Backend

Framework:

- FastAPI

Validation:

- Pydantic v2

Language:

- Python 3.12+

Architecture:

- Layered Clean Architecture

Use dependency injection.

Never put business logic inside Routers.

---

# Frontend

Framework:

- React
- TypeScript

State:

- Zustand

Map:

- Leaflet

UI should remain responsive.

Map, Route List, Journey Timeline and Detail Panel must always stay synchronized.

---

# Notion

The Domain layer must never contain Notion-specific fields.

Only NotionMapper may transform Movement into Notion properties.

---

# Scraper

Never mix HTML parsing with Domain creation.

Always follow:

Scraper
→ Parser
→ Intermediate Model
→ Builder
→ Domain(Route)

---

# Cache

Use Cache through CachePort only.

Current implementation:

- Memory Cache
- SQLite

Cache implementation should be replaceable.

---

# Refactoring

Do not refactor unrelated files.

Do not change working behavior unless requested.

If architecture changes are necessary,
explain the reason before implementing.

---

# Output Style

When generating code:

1. Explain the approach briefly.
2. Then generate complete code.
3. Keep the implementation production-ready.
4. Do not omit important files.
5. If multiple files are modified, explain why.
