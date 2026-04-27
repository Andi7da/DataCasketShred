# Architecture Notes

## Core modules

- `config`: application settings from environment variables
- `logging`: consistent logger setup for console/file output
- `i18n`: translation helper with locale fallback
- `history`: minimal domain history abstraction

## Growth strategy

Add shared capabilities only when they appear in at least two projects. This keeps the template lean and avoids premature complexity.
