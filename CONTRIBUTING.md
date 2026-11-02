# Contributing to Personal Activity Logger

Thanks for contributing to Personal Activity Logger, an offline desktop app for recording activities and reviewing time-use summaries, charts, and reports.

## Set up the project
```bash
git clone https://github.com/joshuaarao42-arch/ACITIVTY-LOGGER.git
cd ACITIVTY-LOGGER
```
Install the dependencies listed in the repository's setup instructions, then run `python activity_logger_ctk.py`.

## Contribution areas
- Activity creation, editing, deletion, search, and category filtering.
- Daily, weekly, monthly, and all-time summaries.
- Streak and active-day calculations.
- Charts, period reports, CSV export, and print-friendly output.
- CustomTkinter usability, themes, and accessibility.

## Data and calculation checks
- Keep activity records local; do not introduce network transmission or telemetry without an explicit project decision.
- Test date boundaries, empty periods, multiple categories, and long notes.
- Verify that totals and streaks match the underlying records.
- Ensure CSV and report exports handle special characters and empty results.
- Do not commit personal activity databases or private user data.

## Pull requests
Use branches such as `feature/category-filter` or `fix/month-boundary-summary`. Include sample test cases and screenshots for visual changes. State whether you tested summaries, charts, exports, or database behavior.
