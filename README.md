# Personal Activity Logger

A desktop app for logging what you do each day (study, cycling, exercise, projects and so on), then reviewing your time with summaries, charts and printable reports. Built with Python and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), with a light/dark theme and its own app icon. Data is stored locally in a SQLite database.

## Features

- **Activities**: add, edit and delete entries with a name, category, duration, date and notes. Search, filter by category, sort by any column, and export the current view to CSV.
- **Summary**: totals for today, this week, this month and all time, plus current and longest streaks, active days and average time per active day. Break your history down by day, week or month, and see time per category.
- **Charts**: stacked bar charts by category for the last 14 days, 8 weeks or 6 months, with a category breakdown alongside.
- **Report**: a plain-language report for any period (this week, last month, a custom range and more). Preview it in the app, copy it, save it as `.txt`, or open a print-friendly HTML page and use "Save as PDF".
- **Light and dark mode**: switch from the sidebar. Your choice is remembered.
- **Custom icon**: generated automatically on first run.

## Requirements

- Python 3.9 or newer, with Tkinter
- Packages: `customtkinter`, `pillow`, `matplotlib`

```
pip install customtkinter pillow matplotlib
```

On some Linux distributions Tkinter is a separate package (for example `sudo apt install python3-tk`).

## Running

```
python activity_logger_ctk.py
```

On first launch the app creates two files next to the script:

| File | Purpose |
| --- | --- |
| `activity_logger.db` | SQLite database holding your activities and the theme setting |
| `activity_logger.ico` | The generated app icon |

## Using the app

### Logging an activity

1. Open the **Activities** page.
2. Enter a name, pick or type a category, and enter a duration.
3. Adjust the date if needed (the arrows step one day, **Today** resets it).
4. Click **Add**, or press **Enter** in any field.

To edit an entry, select it in the table, change the form and click **Update**. Select one or more rows and click **Delete** (or press the Delete key) to remove them. **Clear** resets the form.

New categories are created simply by typing a new name.

### Duration formats

| You type | Meaning |
| --- | --- |
| `45` | 45 minutes |
| `1:30` | 1 hour 30 minutes |
| `1h30m` | 1 hour 30 minutes |
| `2h` | 2 hours |
| `45min` | 45 minutes |

The quick buttons (15m, 30m, 45m, 1h, 1h30m, 2h) fill this in for you. A single entry can be at most 24 hours.

### Reports

Choose a period on the **Report** page. Choose **Custom range** to enter your own dates as `YYYY-MM-DD`.

- **Copy text** puts the report on the clipboard.
- **Save .txt** writes it to a file.
- **Print / Save as PDF** opens a formatted page in your browser. Pick a printer, or choose "Save as PDF" as the destination.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | Start a new entry |
| `Ctrl+F` | Focus the search box |
| `Ctrl+P` | Open the printable report |
| `Enter` | Add the entry, or update it if one is selected |
| `Delete` | Delete the selected rows |

## Backing up or moving your data

All your data lives in `activity_logger.db`. Copy that file to back it up, or place it next to the script on another computer to carry your history over. Delete it to start fresh.

## Troubleshooting

- **The taskbar icon didn't change (Windows):** delete `activity_logger.ico`, restart the app, and if needed restart Explorer. Windows caches icons.
- **`No module named customtkinter`:** run the `pip install` command above with the same Python you use to launch the app.
- **The window looks blurry on a high-DPI screen:** CustomTkinter handles scaling itself, so make sure no compatibility setting is overriding DPI scaling for `python.exe`.
- **Tkinter errors on Linux:** install your distribution's Tkinter package (see Requirements).

## Project layout

```
activity_logger_ctk.py   the whole application
activity_logger.db       created on first run
activity_logger.ico      created on first run
README.md
```
