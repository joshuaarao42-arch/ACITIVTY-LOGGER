# Contributing to Personal Activity Logger

This offline desktop app records daily activities and provides time summaries, charts, streaks, and reports.

## Clone
```bash
git clone https://github.com/joshuaarao42-arch/ACITIVTY-LOGGER.git
cd ACITIVTY-LOGGER
```
Install the dependencies in the README, then run `python activity_logger_ctk.py`.

## Project-specific contributions
- Activity creation, editing, deletion, search, and category filters.
- Daily, weekly, monthly, and all-time summaries and streaks.
- Charts, period reports, CSV export, and print-friendly output.
- CustomTkinter themes, accessibility, and usability.

## Testing and data handling
Test date boundaries, empty periods, multiple categories, and long notes. Verify totals and streaks against saved entries. Check CSV/report exports with special characters and empty results. Keep activity data local and never commit personal databases or private records.

Use branches such as `feature/category-filter` or `fix/month-boundary-summary`. State which calculations, exports, or database workflows you tested.
