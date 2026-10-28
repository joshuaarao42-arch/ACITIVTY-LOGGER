# Personal Activity Logger

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-447F98)
![Database](https://img.shields.io/badge/storage-SQLite-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A desktop app for logging what you do each day (study, cycling, exercise, projects and more), then reviewing your time with summaries, charts and printable reports. Built with Python and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), with a light/dark theme and its own app icon. All data stays on your computer in a local SQLite database.

**Author:** Joshua C. Arao, 1st year Computer Science student

<!-- Add a screenshot: save it as screenshot.png in the repo and uncomment the line below -->
<!-- ![Screenshot](screenshot.png) -->

## Features

- **Activities**: add, edit and delete entries with a name, category, duration, date and notes. Search, filter by category, sort by any column, and export the current view to CSV.
- **Summary**: totals for today, this week, this month and all time, plus current and longest streaks, active days and average time per active day. Break your history down by day, week or month, and see time per category.
- **Charts**: stacked bar charts by category for the last 14 days, 8 weeks or 6 months, with a category breakdown alongside.
- **Reports**: a plain-language report for any period (this week, last month, a custom range and more). Preview it in the app, copy it, save it as `.txt`, or open a print-friendly HTML page and use "Save as PDF".
- **Light and dark mode**: switch from the sidebar. Your choice is remembered.
- **Custom app icon**: generated automatically on first run.
- **Private and offline**: no accounts, no network access, no telemetry.

## Requirements

- Python 3.9 or newer, with Tkinter
- `customtkinter`, `pillow`, `matplotlib`

On some Linux distributions Tkinter is a separate package (for example `sudo apt install python3-tk`).

## Installation

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install customtkinter pillow matplotlib
```

## Usage

```bash
python activity_logger_ctk.py
```

On first launch the app creates two files next to the script:

| File | Purpose |
| --- | --- |
| `activity_logger.db` | SQLite database holding your activities and the theme setting |
| `activity_logger.ico` | The generated app icon |

### Logging an activity

1. Open the **Activities** page.
2. Enter a name, pick or type a category, and enter a duration.
3. Adjust the date if needed (the arrows step one day, **Today** resets it).
4. Click **Add**, or press **Enter** in any field.

To edit an entry, select it in the table, change the form and click **Update**. Select one or more rows and click **Delete** (or press the Delete key) to remove them. New categories are created by typing a new name.

### Duration formats

| You type | Meaning |
| --- | --- |
| `45` | 45 minutes |
| `1:30` | 1 hour 30 minutes |
| `1h30m` | 1 hour 30 minutes |
| `2h` | 2 hours |
| `45min` | 45 minutes |

A single entry can be at most 24 hours.

### Reports

Choose a period on the **Report** page, or pick **Custom range** and enter dates as `YYYY-MM-DD`.

- **Copy text** puts the report on the clipboard.
- **Save .txt** writes it to a file.
- **Print / Save as PDF** opens a formatted page in your browser. Pick a printer, or choose "Save as PDF" as the destination.

### Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | Start a new entry |
| `Ctrl+F` | Focus the search box |
| `Ctrl+P` | Open the printable report |
| `Enter` | Add the entry, or update it if one is selected |
| `Delete` | Delete the selected rows |

## Your data

Everything lives in `activity_logger.db`. Copy that file to back it up or move your history to another computer. Delete it to start fresh. The file is created next to the script and should not be committed to Git (see the `.gitignore` suggestion below).

## Project structure

```
.
├── activity_logger_ctk.py   # the whole application
├── README.md
├── requirements.txt         # optional: customtkinter, pillow, matplotlib
└── .gitignore               # keeps your personal data out of the repo
```

Suggested `.gitignore`:

```
activity_logger.db
__pycache__/
*.pyc
```

## Troubleshooting

- **The taskbar icon didn't change (Windows):** delete `activity_logger.ico`, restart the app, and if needed restart Explorer. Windows caches icons.
- **`No module named customtkinter`:** run the install command with the same Python you use to launch the app.
- **Blurry window on a high-DPI screen:** make sure no compatibility setting is overriding DPI scaling for `python.exe`.
- **Tkinter errors on Linux:** install your distribution's Tkinter package.

## Contributing

Issues and pull requests are welcome. For larger changes, please open an issue first to discuss what you would like to change.

## Author

**Joshua C. Arao**
1st year Computer Science student

## License

Copyright (c) 2026 Joshua C. Arao. Released under the [MIT License](LICENSE). Add a `LICENSE` file to the repository (GitHub can generate one for you when you create the repo or from **Add file > Create new file > LICENSE**).
