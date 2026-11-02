# Contributing to ACITIVTY-LOGGER

Thank you for considering a contribution to this project. This guide explains how to prepare your environment, propose improvements, and submit changes for review.

## Project overview

Offline activity logger with summaries, charts, streaks, and reports.

## Getting started

```bash
git clone https://github.com/joshuaarao42-arch/ACITIVTY-LOGGER.git
cd ACITIVTY-LOGGER
python activity_logger_ctk.py
```

Follow the repository README and existing project configuration if setup commands or entry points have changed. Review the current code before introducing new tools or dependencies.

## What you can contribute

- Improve activity CRUD
- Search
- Categories
- Daily/weekly/monthly summaries
- Streaks
- Charts
- CSV exports
- And CustomTkinter usability.

Bug reports, documentation improvements, accessibility fixes, and reproducible tests are also welcome.

## Project-specific requirements

Test date boundaries, empty periods, multiple categories, long notes, totals, streaks, and CSV special characters. Keep records local and never commit personal databases.

## Coding standards

- Follow the language, naming, formatting, and file-organization conventions already used in the repository.
- Keep changes focused and code easy to understand.
- Validate user input and handle errors clearly.
- Avoid unrelated refactoring and unnecessary dependencies.
- Never commit secrets, generated local data, or personal information.

## Testing

Run the application using the documented setup and test every workflow affected by your change. Include edge cases, not only the successful path. State what you tested and the result. Add screenshots for interface changes and sample inputs with expected outputs for logic changes.

## Branch and commit workflow

Create a branch from the default branch. Use descriptive names such as `feature/short-description`, `fix/short-description`, or `docs/short-description`.

Use clear commit prefixes: `feat:` for features, `fix:` for bug fixes, `docs:` for documentation, `style:` for formatting, `refactor:` for restructuring, and `test:` for tests.

## Pull request guidelines

Before submitting, ensure your changes are focused and tested. In the pull request, explain the problem, summarize the changes, link a related issue if available, list tests and results, and add screenshots or sample output when relevant. Mention breaking changes, new dependencies, and known limitations.

## Reporting bugs and requesting features

Search existing issues before opening a new one. For bugs, include reproduction steps, expected and actual behavior, environment details, and sanitized screenshots or logs. For feature requests, explain the use case and expected benefit. Do not publish credentials or private data.

## Code of conduct

Be respectful, patient, and constructive. Critique code and ideas rather than people. Harassment, discrimination, and abusive behavior are not acceptable.
