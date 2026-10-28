import csv
import html
import re
import sqlite3
import sys
import tempfile
import textwrap
import tkinter as tk
import webbrowser
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  
from matplotlib.figure import Figure  

#Constants
APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "activity_logger.db"
ICON_PATH = APP_DIR / "activity_logger.ico"
APP_ID = "personal.activity.logger.1"
DATE_FMT = "%Y-%m-%d"
DEFAULT_CATEGORIES = ["Study", "Cycling", "Exercise", "Personal Project", "Reading", "Work", "Other"]
CHART_VIEWS = ["Last 14 days", "Last 8 weeks", "Last 6 months"]
PERIODS = ["Daily", "Weekly", "Monthly"]
REPORT_RANGES = ["This week", "Last week", "This month", "Last month",
                 "Last 7 days", "Last 30 days", "All time", "Custom range"]
PAGES = [("Activities", "\u270E"), ("Summary", "\u03A3"), ("Charts", "\u25A5"), ("Report", "\u25A3")]
QUICK_DURATIONS = ["15m", "30m", "45m", "1h", "1h30m", "2h"]

# "Glacier" palette. Every theme colour is a (light, dark) pair so CustomTkinter can switch live.
TURQUOISE = "#447F98"
PALETTE = ["#447F98", "#629BB5", "#2B5266", "#7BC0C4", "#8E9DB8", "#D9937A", "#A9C7D3", "#5B6F8A"]

BG = ("#D6EBF3", "#111C24")
CARD = ("#FFFFFF", "#1B2B36")
FIELD = ("#FFFFFF", "#142029")
SOFT = ("#EAF5F9", "#223543")
BORDER = ("#B9DBE1", "#2E4656")
GLACIER = ("#B9DBE1", "#2E4656")
PLATINUM = ("#DADEED", "#2A3F4E")
TEXT = ("#1E3340", "#E6F1F5")
MUTED = ("#4A6573", "#9DB6C2")
MUTED_LIGHT = ("#8FAAB5", "#5F7886")
ACCENT = ("#447F98", "#5A9CB8")
ACCENT_HOVER = ("#35677D", "#4A88A3")
DANGER = ("#C2514F", "#CF5F5D")
DANGER_HOVER = ("#A63F3D", "#B54D4B")
SIDEBAR = ("#447F98", "#0D161C")
SIDEBAR_HOVER = ("#629BB5", "#1E313D")
NAV_ACTIVE = ("#D6EBF3", "#25404F")
NAV_ACTIVE_TEXT = ("#35677D", "#E6F1F5")
NAV_TEXT = ("#D6EBF3", "#A9C7D3")


def pick(pair):
    """Resolve a (light, dark) colour pair for widgets that don't understand pairs (ttk, matplotlib)."""
    return pair[0] if ctk.get_appearance_mode() == "Light" else pair[1]


def font(size=10, weight="normal", family="Segoe UI"):
    return ctk.CTkFont(family=family, size=size, weight=weight)


FONT_TK = ("Segoe UI", 10)
FONT_TK_BOLD = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 10)


# App icon
def make_icon_image(size=256):
    """Draw the app icon (rounded glacier tile, progress ring, check mark) with Pillow."""
    from PIL import Image, ImageDraw

    s = 1024
    top, bot = (98, 155, 181), (45, 92, 114)
    grad = Image.new("RGBA", (s, s))
    gd = ImageDraw.Draw(grad)
    for y in range(s):
        t = y / s
        gd.line([(0, y), (s, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.23), fill=255)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    m = int(s * 0.19)
    d.ellipse((m, m, s - m, s - m), outline=(214, 235, 243, 255), width=int(s * 0.055))
    # check mark with rounded ends
    pts = [(s * 0.34, s * 0.52), (s * 0.46, s * 0.64), (s * 0.69, s * 0.37)]
    w = int(s * 0.08)
    d.line(pts, fill="white", width=w, joint="curve")
    r = w / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill="white")
    return img.resize((size, size), Image.LANCZOS)


def ensure_icon_file():
    """Create the .ico next to the script the first time (used by the window and taskbar)."""
    try:
        if not ICON_PATH.exists():
            make_icon_image(256).save(
                ICON_PATH, format="ICO",
                sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return True
    except Exception:
        return False


def set_windows_app_id():
    """Lets Windows show our own icon in the taskbar instead of the Python one."""
    if sys.platform.startswith("win"):
        try:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass


# Helpers: parsing/formatting
def parse_duration(text):
    """Turn '45', '1:30', '1h30m', '2h', '45min' into minutes."""
    t = text.strip().lower().replace(" ", "")
    if not t:
        raise ValueError("Please enter a duration (e.g. 45, 1:30 or 1h30m).")

    minutes = None
    if re.fullmatch(r"\d+", t):
        minutes = int(t)
    else:
        m = re.fullmatch(r"(\d+):(\d{1,2})", t)
        if m:
            minutes = int(m.group(1)) * 60 + int(m.group(2))
        else:
            m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m(?:in)?)?", t)
            if m and (m.group(1) or m.group(2)):
                minutes = int(m.group(1) or 0) * 60 + int(m.group(2) or 0)

    if minutes is None or minutes <= 0:
        raise ValueError("Duration must be a positive time, e.g. 45, 1:30 or 1h30m.")
    if minutes > 24 * 60:
        raise ValueError("A single entry can't be longer than 24 hours.")
    return minutes


def format_minutes(total):
    """Compact form used in tables: '1h 05m' / '45m'."""
    hours, mins = divmod(int(total), 60)
    return f"{hours}h {mins:02d}m" if hours else f"{mins}m"


def human_duration(total):
    """Sentence form used in reports: '1 hour 5 minutes'."""
    hours, mins = divmod(int(total), 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if mins or not hours:
        parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
    return " ".join(parts)


def to_date(text):
    return datetime.strptime(text, DATE_FMT).date()


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def clip(text, width):
    return text if len(text) <= width else text[: width - 1] + "..."


# Helpers: summaries, streaks, buckets
def group_start(d, period):
    if period == "Weekly":
        return d - timedelta(days=d.weekday())  # Monday
    if period == "Monthly":
        return d.replace(day=1)
    return d


def group_label(start, period):
    if period == "Weekly":
        return f"Week of {start.strftime('%d %b %Y')}"
    if period == "Monthly":
        return start.strftime("%B %Y")
    return start.strftime("%a, %d %b %Y")


def summarize(rows, period):
    """Group rows by day/week/month -> list of (label, sessions, total, top_category)."""
    groups = defaultdict(lambda: {"total": 0, "count": 0, "cats": defaultdict(int)})
    for r in rows:
        g = groups[group_start(to_date(r["date"]), period)]
        g["total"] += r["duration"]
        g["count"] += 1
        g["cats"][r["category"]] += r["duration"]

    result = []
    for start in sorted(groups, reverse=True):
        g = groups[start]
        top = max(g["cats"], key=g["cats"].get)
        result.append((group_label(start, period), g["count"], g["total"], top))
    return result


def compute_streaks(dates, today):
    """Return (current_streak, longest_streak) from a set of dates with activity."""
    if not dates:
        return 0, 0
    ordered = sorted(dates)
    longest = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)
    day = today if today in dates else today - timedelta(days=1)
    current = 0
    while day in dates:
        current += 1
        day -= timedelta(days=1)
    return current, longest


def build_buckets(view, today):
    """Return a list of (label, start_date, end_date) for the chosen chart range."""
    buckets = []
    if view == "Last 8 weeks":
        monday = today - timedelta(days=today.weekday())
        for i in range(7, -1, -1):
            s = monday - timedelta(weeks=i)
            buckets.append((s.strftime("%d %b"), s, s + timedelta(days=6)))
    elif view == "Last 6 months":
        for i in range(5, -1, -1):
            y, m = today.year, today.month - i
            while m <= 0:
                m += 12
                y -= 1
            s = date(y, m, 1)
            nxt = date(y + (m == 12), (m % 12) + 1, 1)
            buckets.append((s.strftime("%b %Y"), s, nxt - timedelta(days=1)))
    else:  
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            buckets.append((d.strftime("%d %b"), d, d))
    return buckets


# Report: data, text and HTML rendering
def resolve_range(name, today, bounds, custom_from="", custom_to=""):
    """Turn a range name into (start_date, end_date)."""
    if name == "This week":
        return today - timedelta(days=today.weekday()), today
    if name == "Last week":
        end = today - timedelta(days=today.weekday() + 1)
        return end - timedelta(days=6), end
    if name == "This month":
        return today.replace(day=1), today
    if name == "Last month":
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    if name == "Last 7 days":
        return today - timedelta(days=6), today
    if name == "Last 30 days":
        return today - timedelta(days=29), today
    if name == "All time":
        lo, hi = bounds
        return (to_date(lo), to_date(hi)) if lo else (today, today)
    try:
        start, end = to_date(custom_from.strip()), to_date(custom_to.strip())
    except ValueError:
        raise ValueError("Enter the custom dates as YYYY-MM-DD.") from None
    if end < start:
        raise ValueError("The 'From' date must be on or before the 'To' date.")
    return start, end


def period_label(start, end):
    if start == end:
        return start.strftime("%d %b %Y")
    return f"{start.strftime('%d %b %Y')} to {end.strftime('%d %b %Y')}"


def build_report(rows, start, end, range_name):
    """Collect everything a report needs, including plain-language sentences."""
    count = len(rows)
    total = sum(r["duration"] for r in rows)
    by_day = defaultdict(list)
    cats = defaultdict(lambda: [0, 0])
    acts = {}
    for r in rows:
        by_day[r["date"]].append(r)
        c = cats[r["category"]]
        c[0] += r["duration"]
        c[1] += 1
        a = acts.setdefault(r["name"].strip().lower(), [r["name"].strip(), 0, 0])
        a[1] += r["duration"]
        a[2] += 1

    active_days = len(by_day)
    span_days = max((end - start).days + 1, 1)
    categories = [(n, v[0], v[1], v[0] / total if total else 0)
                  for n, v in sorted(cats.items(), key=lambda kv: kv[1][0], reverse=True)]
    top_activities = [(a[0], a[1], a[2]) for a in sorted(acts.values(), key=lambda a: a[1], reverse=True)[:5]]
    days = []
    for day in sorted(by_day):
        entries = by_day[day]
        days.append((to_date(day).strftime("%A, %d %B %Y"),
                     sum(r["duration"] for r in entries),
                     [(r["name"], r["category"], r["duration"], r["notes"]) for r in entries]))

    avg_active = total // active_days if active_days else 0
    avg_day = total // span_days

    sentences = []
    if not rows:
        sentences.append("No activities were logged in this period.")
    else:
        sentences.append(
            f"You logged {plural(count, 'activity').replace('activitys', 'activities')} totaling "
            f"{human_duration(total)} across {plural(active_days, 'active day')}.")
        if span_days > 1:
            sentences.append(
                f"That works out to about {human_duration(avg_active)} on each active day and "
                f"{human_duration(avg_day)} per day over the whole period. You were active on "
                f"{active_days} of {span_days} days ({active_days / span_days:.0%}).")
        top = categories[0]
        line = f"Most of your time went to {top[0]} ({human_duration(top[1])}, {top[3]:.0%})"
        if len(categories) > 1:
            second = categories[1]
            line += f", followed by {second[0]} ({human_duration(second[1])}, {second[3]:.0%})"
        sentences.append(line + ".")
        if len(days) > 1:
            busiest = max(days, key=lambda d: d[1])
            sentences.append(f"Your busiest day was {busiest[0]}, with {human_duration(busiest[1])}.")
        longest = max(rows, key=lambda r: r["duration"])
        sentences.append(
            f"Your longest single session was \"{longest['name']}\" on "
            f"{to_date(longest['date']).strftime('%A, %d %B')}, lasting {human_duration(longest['duration'])}.")

    return {
        "title": "Personal Activity Report",
        "range_name": range_name,
        "period": period_label(start, end),
        "generated": datetime.now().strftime("%d %b %Y, %H:%M"),
        "empty": not rows,
        "total": total,
        "count": count,
        "active_days": active_days,
        "span_days": span_days,
        "avg_active": avg_active,
        "categories": categories,
        "top_activities": top_activities,
        "days": days,
        "sentences": sentences,
    }


def report_lines(rep):
    """The report as (text, kind) lines; used by the in-app preview and the .txt export."""
    lines = []

    def add(text, kind="p"):
        lines.append((text, kind))

    add(rep["title"], "title")
    add(f"{rep['range_name']}  ({rep['period']})  -  generated {rep['generated']}", "meta")
    add("Overview", "h")
    for s in rep["sentences"]:
        add(s, "p")
    if rep["categories"]:
        add("Time by category", "h")
        for name, total, count, share in rep["categories"]:
            add(f"{clip(name, 24):<24} {format_minutes(total):>9}  {share:>4.0%}   {plural(count, 'session')}", "mono")
    if rep["top_activities"]:
        add("Top activities", "h")
        for name, total, count in rep["top_activities"]:
            add(f"{clip(name, 24):<24} {format_minutes(total):>9}   {count}x", "mono")
    if rep["days"]:
        add("Day by day", "h")
        for label, total, entries in rep["days"]:
            add(f"{label}  -  {format_minutes(total)}", "day")
            for name, cat, dur, notes in entries:
                add(f"\u2022 {name}  ({cat})  -  {format_minutes(dur)}", "item")
                if notes:
                    add(notes.replace("\n", " "), "note")
    return lines


def report_to_text(rep):
    out = []
    for text, kind in report_lines(rep):
        if kind == "title":
            out += [text.upper(), "=" * len(text), ""]
        elif kind == "meta":
            out += [text, ""]
        elif kind == "h":
            out += ["", text.upper(), "-" * len(text)]
        elif kind == "p":
            out += [textwrap.fill(text, 78), ""]
        elif kind == "day":
            out += ["", text]
        elif kind == "item":
            out.append(textwrap.fill(text, 78, initial_indent="  ", subsequent_indent="    "))
        elif kind == "note":
            out.append(textwrap.fill(text, 78, initial_indent="      ", subsequent_indent="      "))
        else:
            out.append(text)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


REPORT_CSS = """
@page { size: A4; margin: 14mm; }
* { box-sizing: border-box; }
body { margin: 0; background: #D6EBF3; color: #1E3340; font: 14px/1.55 "Segoe UI", system-ui, Arial, sans-serif;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.toolbar { position: sticky; top: 0; background: #447F98; color: #D6EBF3; padding: 10px 20px; display: flex;
           gap: 14px; align-items: center; font-size: 13px; }
.toolbar button { background: #fff; color: #35677D; border: 0; border-radius: 6px; padding: 8px 16px;
                  font: inherit; font-weight: 600; cursor: pointer; }
.page { max-width: 820px; margin: 24px auto; background: #fff; padding: 40px 48px; border-radius: 12px;
        box-shadow: 0 4px 24px rgba(68,127,152,.18); }
h1 { margin: 0; font: 400 30px/1.2 Georgia, "Times New Roman", serif; text-transform: uppercase;
     letter-spacing: .04em; color: #1E3340; }
.meta { color: #4A6573; margin: 6px 0 24px; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: #447F98; margin: 28px 0 10px;
     border-bottom: 2px solid #B9DBE1; padding-bottom: 6px; break-after: avoid; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat { background: #D6EBF3; border-radius: 10px; padding: 12px 14px; }
.stat:nth-child(even) { background: #B9DBE1; }
.stat b { display: block; font-size: 22px; font-family: Georgia, "Times New Roman", serif; font-weight: 400; }
.stat span { color: #35677D; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }
p { margin: 0 0 8px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid #DADEED; vertical-align: top; }
th { font-size: 11px; color: #4A6573; text-transform: uppercase; letter-spacing: .06em; }
td.num, th.num { text-align: right; white-space: nowrap; }
tr { break-inside: avoid; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
.barwrap { background: #D6EBF3; border-radius: 4px; height: 8px; min-width: 120px; }
.bar { height: 8px; border-radius: 4px; }
tr.day td { background: #EAF5F9; font-weight: 600; border-top: 1px solid #B9DBE1; color: #35677D; }
.notes { color: #4A6573; }
footer { margin-top: 28px; color: #629BB5; font-size: 12px; text-align: center; }
@media print {
  body { background: #fff; }
  .noprint { display: none !important; }
  .page { margin: 0; padding: 0; box-shadow: none; max-width: none; border-radius: 0; }
}
"""


def report_to_html(rep, colors, auto_print=True):
    """A self-contained, print-friendly HTML page (opens in the browser; Ctrl+P / Save as PDF)."""
    esc = html.escape
    default_color = PALETTE[0]
    stats = [
        ("Total time", format_minutes(rep["total"])),
        ("Activities", str(rep["count"])),
        ("Active days", f"{rep['active_days']} of {rep['span_days']}"),
        ("Avg / active day", format_minutes(rep["avg_active"])),
    ]
    body = [
        '<div class="toolbar noprint"><button onclick="window.print()">Print / Save as PDF</button>'
        '<span>Tip: choose "Save as PDF" as the printer to keep a digital copy.</span></div>',
        '<main class="page">',
        f'<h1>{esc(rep["title"])}</h1>',
        f'<p class="meta">{esc(rep["range_name"])} &middot; {esc(rep["period"])}<br>'
        f'Generated {esc(rep["generated"])}</p>',
        '<div class="stats">'
        + "".join(f'<div class="stat"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k, v in stats)
        + "</div>",
        "<h2>Summary</h2>" + "".join(f"<p>{esc(s)}</p>" for s in rep["sentences"]),
    ]

    if rep["categories"]:
        rows = []
        for name, total, count, share in rep["categories"]:
            color = colors.get(name, default_color)
            rows.append(
                f'<tr><td><span class="dot" style="background:{color}"></span>{esc(name)}</td>'
                f'<td class="num">{format_minutes(total)}</td><td class="num">{share:.0%}</td>'
                f'<td class="num">{count}</td>'
                f'<td><div class="barwrap"><div class="bar" style="width:{share * 100:.0f}%;'
                f'background:{color}"></div></div></td></tr>')
        body.append('<h2>Time by category</h2><table><tr><th>Category</th><th class="num">Time</th>'
                    '<th class="num">Share</th><th class="num">Sessions</th><th></th></tr>'
                    + "".join(rows) + "</table>")

    if rep["top_activities"]:
        rows = [f'<tr><td>{esc(n)}</td><td class="num">{format_minutes(t)}</td><td class="num">{c}</td></tr>'
                for n, t, c in rep["top_activities"]]
        body.append('<h2>Top activities</h2><table><tr><th>Activity</th><th class="num">Total time</th>'
                    '<th class="num">Sessions</th></tr>' + "".join(rows) + "</table>")

    if rep["days"]:
        rows = []
        for label, total, entries in rep["days"]:
            rows.append(f'<tr class="day"><td colspan="3">{esc(label)}</td>'
                        f'<td class="num">{format_minutes(total)}</td></tr>')
            for name, cat, dur, notes in entries:
                color = colors.get(cat, default_color)
                rows.append(
                    f'<tr><td>{esc(name)}</td>'
                    f'<td><span class="dot" style="background:{color}"></span>{esc(cat)}</td>'
                    f'<td class="notes">{esc(notes).replace(chr(10), "<br>")}</td>'
                    f'<td class="num">{format_minutes(dur)}</td></tr>')
        body.append('<h2>Day by day</h2><table><tr><th>Activity</th><th>Category</th><th>Notes</th>'
                    '<th class="num">Time</th></tr>' + "".join(rows) + "</table>")

    body.append("<footer>Created with Personal Activity Logger</footer></main>")
    script = ("<script>window.addEventListener('load',function(){setTimeout(function(){window.print();},500);});"
              "</script>") if auto_print else ""
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{esc(rep['title'])} - {esc(rep['period'])}</title><style>{REPORT_CSS}</style></head>"
            f"<body>{''.join(body)}{script}</body></html>")


# Database layer
class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT    NOT NULL,
                category  TEXT    NOT NULL,
                duration  INTEGER NOT NULL CHECK (duration > 0),
                date      TEXT    NOT NULL,
                notes     TEXT    NOT NULL DEFAULT ''
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.conn.commit()

    # settings (remembers light/dark mode)
    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

    def add(self, name, category, duration, day, notes):
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO activities (name, category, duration, date, notes) VALUES (?, ?, ?, ?, ?)",
                (name, category, duration, day, notes),
            )
        return cur.lastrowid

    def update(self, rec_id, name, category, duration, day, notes):
        with self.conn:
            self.conn.execute(
                "UPDATE activities SET name=?, category=?, duration=?, date=?, notes=? WHERE id=?",
                (name, category, duration, day, notes, rec_id),
            )

    def delete(self, ids):
        with self.conn:
            self.conn.executemany("DELETE FROM activities WHERE id=?", [(i,) for i in ids])

    def get(self, rec_id):
        return self.conn.execute("SELECT * FROM activities WHERE id=?", (rec_id,)).fetchone()

    def search(self, text="", category="All"):
        sql = "SELECT * FROM activities WHERE 1=1"
        params = []
        if text:
            like = f"%{text}%"
            sql += " AND (name LIKE ? OR category LIKE ? OR notes LIKE ? OR date LIKE ?)"
            params += [like] * 4
        if category and category != "All":
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY date DESC, id DESC"
        return self.conn.execute(sql, params).fetchall()

    def rows_in_range(self, start, end):
        return self.conn.execute(
            "SELECT * FROM activities WHERE date BETWEEN ? AND ? ORDER BY date ASC, id ASC", (start, end)
        ).fetchall()

    def all_rows(self):
        return self.conn.execute("SELECT date, category, duration FROM activities").fetchall()

    def rows_between(self, start, end):
        return self.conn.execute(
            "SELECT date, category, duration FROM activities WHERE date BETWEEN ? AND ?", (start, end)
        ).fetchall()

    def stats_between(self, start, end):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(duration), 0), COUNT(*) FROM activities WHERE date BETWEEN ? AND ?",
            (start, end),
        ).fetchone()
        return row[0], row[1]

    def date_bounds(self):
        row = self.conn.execute("SELECT MIN(date), MAX(date) FROM activities").fetchone()
        return row[0], row[1]

    def distinct_dates(self):
        return [r[0] for r in self.conn.execute("SELECT DISTINCT date FROM activities")]

    def categories(self):
        rows = self.conn.execute("SELECT DISTINCT category FROM activities ORDER BY category COLLATE NOCASE")
        return [r[0] for r in rows]

    def close(self):
        self.conn.close()


# Widget factories
def make_button(parent, text, command, kind="soft", **kw):
    styles = {
        "accent": dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="white"),
        "danger": dict(fg_color=DANGER, hover_color=DANGER_HOVER, text_color="white"),
        "soft": dict(fg_color=PLATINUM, hover_color=GLACIER, text_color=TEXT),
        "chip": dict(fg_color=SOFT, hover_color=GLACIER, text_color=ACCENT_HOVER,
                     height=26, corner_radius=13, font=font(9)),
    }
    opts = dict(height=36, corner_radius=10, text_color_disabled=MUTED_LIGHT,
                font=font(10, "bold" if kind in ("accent", "danger") else "normal"))
    opts.update(styles[kind])
    opts.update(kw)
    return ctk.CTkButton(parent, text=text, command=command, **opts)


def make_entry(parent, **kw):
    return ctk.CTkEntry(parent, height=36, corner_radius=8, border_width=1, border_color=BORDER,
                        fg_color=FIELD, text_color=TEXT, font=font(10), **kw)


def make_combo(parent, **kw):
    return ctk.CTkComboBox(parent, height=36, corner_radius=8, border_width=1, border_color=BORDER,
                           fg_color=FIELD, button_color=PLATINUM, button_hover_color=GLACIER,
                           text_color=TEXT, dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                           dropdown_hover_color=SOFT, font=font(10), dropdown_font=font(10), **kw)


def make_menu(parent, **kw):
    return ctk.CTkOptionMenu(parent, height=36, corner_radius=8, fg_color=FIELD, button_color=PLATINUM,
                             button_hover_color=GLACIER, text_color=TEXT, dropdown_fg_color=CARD,
                             dropdown_text_color=TEXT, dropdown_hover_color=SOFT, font=font(10),
                             dropdown_font=font(10), **kw)


def make_label(parent, text="", size=10, weight="normal", color=TEXT, **kw):
    return ctk.CTkLabel(parent, text=text, text_color=color, font=font(size, weight), **kw)


def card(parent, **kw):
    return ctk.CTkFrame(parent, corner_radius=16, fg_color=CARD, border_width=1, border_color=BORDER, **kw)


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master, corner_radius=14, fg_color=CARD, border_width=1, border_color=BORDER)
        make_label(self, title.upper(), 8, "bold", MUTED).pack(anchor="w", padx=16, pady=(12, 0))
        self.value = make_label(self, "0m", 20, "bold", TEXT)
        self.value.pack(anchor="w", padx=16)
        self.sub = make_label(self, "", 9, "normal", MUTED)
        self.sub.pack(anchor="w", padx=16, pady=(0, 12))

    def set(self, value, sub=""):
        self.value.configure(text=value)
        self.sub.configure(text=sub)


# Main application
class ActivityLoggerApp(ctk.CTk):
    COLUMNS = (
        ("date", "Date", 100, "w"),
        ("name", "Activity", 190, "w"),
        ("category", "Category", 130, "w"),
        ("duration", "Duration", 80, "e"),
        ("notes", "Notes", 260, "w"),
    )

    def __init__(self, db):
        super().__init__(fg_color=BG)
        self.db = db
        self.title("Personal Activity Logger")
        try:
            self._scale = self._get_window_scaling()
        except Exception:
            self._scale = 1.0
        width = min(1280, int(self.winfo_screenwidth() / self._scale) - 80)
        height = min(800, int(self.winfo_screenheight() / self._scale) - 100)
        self.geometry(f"{width}x{height}+30+20")
        self.minsize(min(1100, width), min(680, height))

        self.selected_id = None
        self.cat_colors = {}
        self._rows = {}
        self._sort_col = None
        self._sort_rev = False
        self._toast_job = None
        self._search_job = None
        self._report = None
        self.current_page = None
        self._icon_photo = None

        self._build_icon()
        self._build_ttk_style()
        self._build_layout()
        self._style_trees()
        self._apply_report_tags()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_all()

    # icon --
    def _build_icon(self):
        try:
            from PIL import ImageTk
            self._icon_photo = ImageTk.PhotoImage(make_icon_image(64))
            self.iconphoto(True, self._icon_photo)
        except Exception:
            pass
        if sys.platform.startswith("win") and ensure_icon_file():
            self.after(250, lambda: self._safe_iconbitmap())

    def _safe_iconbitmap(self):
        try:
            self.iconbitmap(str(ICON_PATH))
        except Exception:
            pass

    # Styling --
    def _build_ttk_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # no outer border

    def _style_trees(self):
        """Re-colour the ttk tables for the current light/dark mode."""
        s = ttk.Style(self)
        bg, fg = pick(CARD), pick(TEXT)
        row_h = int(30 * self._scale)
        s.configure("Treeview", rowheight=row_h, background=bg, fieldbackground=bg, foreground=fg,
                    borderwidth=0, font=FONT_TK)
        s.map("Treeview", background=[("selected", pick(ACCENT))], foreground=[("selected", "white")])
        s.configure("Treeview.Heading", background=pick(PLATINUM), foreground=fg, font=FONT_TK_BOLD,
                    padding=(8, 7), relief="flat", borderwidth=0)
        s.map("Treeview.Heading", background=[("active", pick(GLACIER))])
        for tree in (self.tree, self.tree_sum, self.tree_cat):
            tree.tag_configure("odd", background=pick(CARD))
            tree.tag_configure("even", background=pick(SOFT))
        self.canvas.get_tk_widget().configure(bg=pick(CARD))

    # Layout --
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=SIDEBAR)
        side.grid(row=0, column=0, sticky="nsew")
        side.pack_propagate(False)

        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(anchor="w", padx=20, pady=(26, 22))
        try:
            logo = make_icon_image(96)
            self._logo = ctk.CTkImage(light_image=logo, dark_image=logo, size=(40, 40))
            ctk.CTkLabel(brand, image=self._logo, text="").pack(side="left", padx=(0, 10))
        except Exception:
            pass
        ctk.CTkLabel(brand, text="ACTIVITY\nLOGGER", justify="left", text_color="white",
                     font=font(15, "normal", "Georgia")).pack(side="left")

        self.nav_buttons = {}
        for name, glyph in PAGES:
            btn = ctk.CTkButton(side, text=f"  {glyph}   {name}", anchor="w", height=42, corner_radius=10,
                                font=font(12), fg_color="transparent", text_color=NAV_TEXT,
                                hover_color=SIDEBAR_HOVER, command=lambda n=name: self.show_page(n))
            btn.pack(fill="x", padx=14, pady=2)
            self.nav_buttons[name] = btn

        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=20, pady=20)
        self.sw_theme = ctk.CTkSwitch(bottom, text="Dark mode", command=self.on_theme_toggle,
                                      text_color=NAV_TEXT, progress_color=SIDEBAR_HOVER,
                                      button_color="white", button_hover_color=PLATINUM,
                                      fg_color=("#35677D", "#2A3F4E"), font=font(10))
        if ctk.get_appearance_mode() == "Dark":
            self.sw_theme.select()
        self.sw_theme.pack(anchor="w", pady=(0, 14))
        ctk.CTkLabel(bottom, text=date.today().strftime("%A\n%d %B %Y"), justify="left",
                     text_color=NAV_TEXT, font=font(9)).pack(anchor="w")

        self.content = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.pages = {}
        for name, _g in PAGES:
            frame = ctk.CTkFrame(self.content, fg_color="transparent", corner_radius=0)
            frame.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = frame

        self._build_activities_page(self.pages["Activities"])
        self._build_summary_page(self.pages["Summary"])
        self._build_charts_page(self.pages["Charts"])
        self._build_report_page(self.pages["Report"])

        self.toast = ctk.CTkLabel(self, text="", fg_color=SIDEBAR, text_color="white", corner_radius=10,
                                  font=font(10), padx=16, pady=10)
        self.show_page("Activities")

    def show_page(self, name):
        self.current_page = name
        self.pages[name].tkraise()
        for key, btn in self.nav_buttons.items():
            active = key == name
            btn.configure(fg_color=NAV_ACTIVE if active else "transparent",
                          text_color=NAV_ACTIVE_TEXT if active else NAV_TEXT,
                          hover_color=NAV_ACTIVE if active else SIDEBAR_HOVER)
        if name == "Summary":
            self.refresh_summary()
        elif name == "Charts":
            self.refresh_chart()
        elif name == "Report":
            self.refresh_report()

    def _page_header(self, parent, title, subtitle, action=None):
        head = ctk.CTkFrame(parent, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        head.grid_columnconfigure(0, weight=1)
        make_label(head, title.upper(), 24, "normal", TEXT).grid(row=0, column=0, sticky="w")
        sub = make_label(head, "", 10, "normal", MUTED)
        if isinstance(subtitle, tk.StringVar):
            sub.configure(textvariable=subtitle)
        else:
            sub.configure(text=subtitle)
        sub.grid(row=1, column=0, sticky="w")
        sub.configure(font=font(10))
        for lbl in head.winfo_children()[:1]:
            lbl.configure(font=font(24, "normal", "Georgia"))
        if action:
            make_button(head, action[0], action[1], "accent").grid(row=0, column=1, rowspan=2, sticky="e")

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda _e: self._new_entry())
        self.bind("<Control-f>", lambda _e: self._focus_search())
        self.bind("<Control-p>", lambda _e: self.on_print_report())

    def _toast_msg(self, text):
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self.toast.configure(text=text)
        self.toast.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        self.toast.lift()
        self._toast_job = self.after(3500, self.toast.place_forget)

    def on_theme_toggle(self):
        mode = "Dark" if self.sw_theme.get() else "Light"
        ctk.set_appearance_mode(mode)
        self.db.set_setting("appearance", mode)
        self.after(30, self._after_theme_change)

    def _after_theme_change(self):
        self._style_trees()
        self._apply_report_tags()
        self.refresh_chart()

    # Activities page --
    def _build_activities_page(self, parent):
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        self.var_activity_sub = tk.StringVar()
        self._page_header(parent, "Activities", self.var_activity_sub)

        # --- form card
        form = card(parent)
        form.grid(row=1, column=0, sticky="ns", padx=(0, 14))
        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        inner.grid_columnconfigure(0, weight=1)

        self.var_name = tk.StringVar()
        self.var_category = tk.StringVar(value=DEFAULT_CATEGORIES[0])
        self.var_duration = tk.StringVar()
        self.var_date = tk.StringVar(value=date.today().strftime(DATE_FMT))

        make_label(inner, "Log an activity", 14, "bold").grid(row=0, column=0, sticky="w", pady=(0, 10))

        make_label(inner, "Activity name", 10, "normal", MUTED).grid(row=1, column=0, sticky="w")
        self.ent_name = make_entry(inner, textvariable=self.var_name, width=300)
        self.ent_name.grid(row=2, column=0, sticky="ew", pady=(2, 8))

        make_label(inner, "Category", 10, "normal", MUTED).grid(row=3, column=0, sticky="w")
        self.cb_category = make_combo(inner, variable=self.var_category, values=DEFAULT_CATEGORIES)
        self.cb_category.grid(row=4, column=0, sticky="ew", pady=(2, 8))

        make_label(inner, "Duration", 10, "normal", MUTED).grid(row=5, column=0, sticky="w")
        self.ent_duration = make_entry(inner, textvariable=self.var_duration)
        self.ent_duration.grid(row=6, column=0, sticky="ew", pady=(2, 6))
        chips = ctk.CTkFrame(inner, fg_color="transparent")
        chips.grid(row=7, column=0, sticky="w", pady=(0, 8))
        for label in QUICK_DURATIONS:
            make_button(chips, label, lambda v=label: self.var_duration.set(v), "chip", width=44).pack(
                side="left", padx=(0, 4))

        make_label(inner, "Date (YYYY-MM-DD)", 10, "normal", MUTED).grid(row=8, column=0, sticky="w")
        date_row = ctk.CTkFrame(inner, fg_color="transparent")
        date_row.grid(row=9, column=0, sticky="ew", pady=(2, 8))
        date_row.grid_columnconfigure(1, weight=1)
        make_button(date_row, "\u2039", lambda: self._shift_date(-1), width=34).grid(row=0, column=0, padx=(0, 4))
        self.ent_date = make_entry(date_row, textvariable=self.var_date)
        self.ent_date.grid(row=0, column=1, sticky="ew")
        make_button(date_row, "\u203A", lambda: self._shift_date(1), width=34).grid(row=0, column=2, padx=4)
        make_button(date_row, "Today", self._set_today, width=58).grid(row=0, column=3)

        make_label(inner, "Notes", 10, "normal", MUTED).grid(row=10, column=0, sticky="w")
        self.txt_notes = ctk.CTkTextbox(inner, height=90, corner_radius=8, border_width=1, border_color=BORDER,
                                        fg_color=FIELD, text_color=TEXT, font=font(10), wrap="word")
        self.txt_notes.grid(row=11, column=0, sticky="ew", pady=(2, 14))

        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.grid(row=12, column=0, sticky="ew")
        btns.grid_columnconfigure((0, 1), weight=1)
        self.btn_add = make_button(btns, "Add", self.on_add, "accent")
        self.btn_update = make_button(btns, "Update", self.on_update, state="disabled")
        self.btn_delete = make_button(btns, "Delete", self.on_delete, "danger", state="disabled")
        self.btn_clear = make_button(btns, "Clear", self.clear_form)
        self.btn_add.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 8))
        self.btn_update.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=(0, 8))
        self.btn_delete.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.btn_clear.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        for entry in (self.ent_name, self.ent_duration, self.ent_date):
            entry.bind("<Return>", self.on_save)

        # history card
        right = card(parent)
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(right, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 10))
        toolbar.grid_columnconfigure(1, weight=1)
        make_label(toolbar, "Search", 10, "normal", MUTED).grid(row=0, column=0, padx=(0, 8))
        self.var_search = tk.StringVar()
        self.ent_search = make_entry(toolbar, textvariable=self.var_search)
        self.ent_search.grid(row=0, column=1, sticky="ew")
        self.var_search.trace_add("write", self._on_search_change)

        self.var_filter = tk.StringVar(value="All")
        self.cb_filter = make_combo(toolbar, variable=self.var_filter, state="readonly", width=150,
                                    values=["All"] + DEFAULT_CATEGORIES,
                                    command=lambda _v: self.refresh_table())
        self.cb_filter.grid(row=0, column=2, padx=8)
        make_button(toolbar, "Reset", self._reset_filters, width=64).grid(row=0, column=3, padx=(0, 8))
        make_button(toolbar, "Export CSV", self.on_export, width=96).grid(row=0, column=4)

        wrap = ctk.CTkFrame(right, fg_color="transparent")
        wrap.grid(row=1, column=0, sticky="nsew", padx=(14, 8), pady=0)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        cols = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="extended")
        for key, label, width, anchor in self.COLUMNS:
            self.tree.heading(key, text=label, command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=int(width * self._scale), anchor=anchor, stretch=(key == "notes"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ctk.CTkScrollbar(wrap, orientation="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Delete>", lambda _e: self.on_delete())
        self.empty_lbl = make_label(wrap, "", 12, "normal", MUTED, justify="center")

        self.status_var = tk.StringVar()
        ctk.CTkLabel(right, textvariable=self.status_var, text_color=MUTED, font=font(9)).grid(
            row=2, column=0, sticky="w", padx=16, pady=(8, 12))

    # Summary page --
    def _build_summary_page(self, parent):
        parent.grid_columnconfigure(0, weight=3)
        parent.grid_columnconfigure(1, weight=2)
        parent.grid_rowconfigure(3, weight=1)
        self._page_header(parent, "Summary", "Your totals, streaks and where your time goes.",
                          action=("Print report...", lambda: self.show_page("Report")))

        self.cards = {}
        rows = (
            (("today", "Today"), ("week", "This week"), ("month", "This month"), ("all", "All time")),
            (("streak", "Current streak"), ("longest", "Longest streak"), ("days", "Active days"),
             ("avg", "Avg / active day")),
        )
        for r, items in enumerate(rows, start=1):
            strip = ctk.CTkFrame(parent, fg_color="transparent")
            strip.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            for i, (key, title) in enumerate(items):
                sc = StatCard(strip, title)
                sc.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 10, 0))
                strip.grid_columnconfigure(i, weight=1, uniform=f"stat{r}")
                self.cards[key] = sc

        left = card(parent)
        left.grid(row=3, column=0, sticky="nsew", padx=(0, 14))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        head = ctk.CTkFrame(left, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(14, 10))
        make_label(head, "Breakdown", 14, "bold").pack(side="left")
        self.var_period = tk.StringVar(value="Daily")
        ctk.CTkSegmentedButton(head, values=PERIODS, variable=self.var_period, font=font(10),
                               selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                               unselected_color=PLATINUM, unselected_hover_color=GLACIER,
                               text_color=("white", "white"), fg_color=PLATINUM,
                               command=lambda _v: self.refresh_summary()).pack(side="right")

        sum_wrap = ctk.CTkFrame(left, fg_color="transparent")
        sum_wrap.grid(row=1, column=0, sticky="nsew", padx=(14, 8), pady=(0, 14))
        sum_wrap.grid_columnconfigure(0, weight=1)
        sum_wrap.grid_rowconfigure(0, weight=1)
        self.tree_sum = ttk.Treeview(sum_wrap, columns=("period", "sessions", "total", "top"),
                                     show="headings", selectmode="browse")
        for key, label, width, anchor in (("period", "Period", 190, "w"), ("sessions", "Sessions", 80, "e"),
                                          ("total", "Total time", 100, "e"), ("top", "Top category", 140, "w")):
            self.tree_sum.heading(key, text=label)
            self.tree_sum.column(key, width=int(width * self._scale), anchor=anchor, stretch=(key == "top"))
        self.tree_sum.grid(row=0, column=0, sticky="nsew")
        sb = ctk.CTkScrollbar(sum_wrap, orientation="vertical", command=self.tree_sum.yview)
        sb.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self.tree_sum.configure(yscrollcommand=sb.set)

        right = card(parent)
        right.grid(row=3, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        make_label(right, "Time by category (all time)", 14, "bold").grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 10))
        cat_wrap = ctk.CTkFrame(right, fg_color="transparent")
        cat_wrap.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        cat_wrap.grid_columnconfigure(0, weight=1)
        cat_wrap.grid_rowconfigure(0, weight=1)
        self.tree_cat = ttk.Treeview(cat_wrap, columns=("category", "total", "share"), show="headings",
                                     selectmode="browse")
        for key, label, width, anchor in (("category", "Category", 140, "w"), ("total", "Total time", 100, "e"),
                                          ("share", "Share", 70, "e")):
            self.tree_cat.heading(key, text=label)
            self.tree_cat.column(key, width=int(width * self._scale), anchor=anchor, stretch=(key == "category"))
        self.tree_cat.grid(row=0, column=0, sticky="nsew")

    # Charts page --
    def _build_charts_page(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        self._page_header(parent, "Charts", "See your progress over time, stacked by category.")

        box = card(parent)
        box.grid(row=1, column=0, columnspan=2, sticky="nsew")
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(box, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        make_label(top, "Range", 10, "normal", MUTED).pack(side="left", padx=(0, 10))
        self.var_range = tk.StringVar(value=CHART_VIEWS[0])
        ctk.CTkSegmentedButton(top, values=CHART_VIEWS, variable=self.var_range, font=font(10),
                               selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                               unselected_color=PLATINUM, unselected_hover_color=GLACIER,
                               text_color=("white", "white"), fg_color=PLATINUM,
                               command=lambda _v: self.refresh_chart()).pack(side="left")

        self.fig = Figure(figsize=(9, 5), dpi=100, facecolor=pick(CARD))
        self.canvas = FigureCanvasTkAgg(self.fig, master=box)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    # Report page --
    def _build_report_page(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        self._page_header(parent, "Report", "A printable, easy-to-read summary of your activities.")

        ctrl = card(parent)
        ctrl.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        row = ctk.CTkFrame(ctrl, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        row.grid_columnconfigure(5, weight=1)

        self.var_report_range = tk.StringVar(value="This week")
        today = date.today()
        self.var_from = tk.StringVar(value=(today - timedelta(days=6)).strftime(DATE_FMT))
        self.var_to = tk.StringVar(value=today.strftime(DATE_FMT))

        make_label(row, "Period", 10, "normal", MUTED).grid(row=0, column=0, padx=(0, 8))
        make_menu(row, variable=self.var_report_range, values=REPORT_RANGES, width=140,
                  command=lambda _v: self.refresh_report()).grid(row=0, column=1, padx=(0, 16))
        make_label(row, "From", 10, "normal", MUTED).grid(row=0, column=2, padx=(0, 8))
        self.ent_from = make_entry(row, textvariable=self.var_from, width=110)
        self.ent_from.grid(row=0, column=3, padx=(0, 12))
        make_label(row, "To", 10, "normal", MUTED).grid(row=0, column=4, padx=(0, 8), sticky="w")
        self.ent_to = make_entry(row, textvariable=self.var_to, width=110)
        self.ent_to.grid(row=0, column=5, sticky="w")
        for entry in (self.ent_from, self.ent_to):
            entry.bind("<Return>", lambda _e: self.refresh_report())
            entry.bind("<FocusOut>", lambda _e: self.refresh_report())

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.grid(row=0, column=6, sticky="e")
        make_button(actions, "Copy text", self.on_copy_report, width=90).pack(side="left", padx=4)
        make_button(actions, "Save .txt", self.on_save_report_txt, width=90).pack(side="left", padx=4)
        make_button(actions, "Print / Save as PDF", self.on_print_report, "accent", width=160).pack(
            side="left", padx=(4, 0))

        self.txt_report = ctk.CTkTextbox(parent, corner_radius=16, fg_color=CARD, text_color=TEXT,
                                         border_width=1, border_color=BORDER, wrap="word",
                                         font=font(11), state="disabled")
        self.txt_report.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self._rt = self.txt_report._textbox
        self._rt.configure(padx=28, pady=20, cursor="arrow")

    def _apply_report_tags(self):
        t = self._rt
        t.tag_configure("title", font=("Georgia", 20), foreground=pick(TEXT), spacing3=2)
        t.tag_configure("meta", font=FONT_TK, foreground=pick(MUTED), spacing3=8)
        t.tag_configure("h", font=("Segoe UI", 12, "bold"), foreground=pick(ACCENT), spacing1=16, spacing3=6)
        t.tag_configure("p", font=("Segoe UI", 11), foreground=pick(TEXT), spacing3=6)
        t.tag_configure("mono", font=FONT_MONO, foreground=pick(TEXT))
        t.tag_configure("day", font=FONT_TK_BOLD, foreground=pick(TEXT), spacing1=10, spacing3=2)
        t.tag_configure("item", font=FONT_TK, foreground=pick(TEXT), lmargin1=16, lmargin2=30)
        t.tag_configure("note", font=("Segoe UI", 9, "italic"), foreground=pick(MUTED), lmargin1=30, lmargin2=30)

    # Refreshing --
    def refresh_all(self):
        self.refresh_categories()
        self.refresh_stats()
        self.refresh_table()
        self.refresh_summary()
        self.refresh_chart()
        self.refresh_report()

    def refresh_categories(self):
        cats = list(dict.fromkeys(DEFAULT_CATEGORIES + self.db.categories()))
        self.cat_colors = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(cats)}
        self.cb_category.configure(values=cats)
        self.cb_filter.configure(values=["All"] + cats)
        if self.var_filter.get() not in ["All"] + cats:
            self.var_filter.set("All")

    def color_of(self, category):
        return self.cat_colors.get(category, PALETTE[0])

    def refresh_stats(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        spans = {
            "today": (today, today),
            "week": (week_start, week_start + timedelta(days=6)),
            "month": (month_start, today),
            "all": (date(1900, 1, 1), date(9999, 12, 31)),
        }
        totals = {}
        for key, (s, e) in spans.items():
            total, count = self.db.stats_between(s.isoformat(), e.isoformat())
            totals[key] = total
            self.cards[key].set(format_minutes(total), plural(count, "session"))

        dates = {to_date(d) for d in self.db.distinct_dates()}
        current, longest = compute_streaks(dates, today)
        if today in dates:
            hint = "Logged today"
        elif current:
            hint = "Log today to keep it going"
        else:
            hint = "Log today to start one"
        self.cards["streak"].set(plural(current, "day"), hint)
        self.cards["longest"].set(plural(longest, "day"), "best run so far")
        self.cards["days"].set(str(len(dates)), "days with activity")
        avg = totals["all"] // len(dates) if dates else 0
        self.cards["avg"].set(format_minutes(avg), "across active days")

        self.var_activity_sub.set(
            f"Today {format_minutes(totals['today'])}   \u00B7   This week {format_minutes(totals['week'])}"
            f"   \u00B7   Streak {plural(current, 'day')}")

    def refresh_table(self):
        keep = self.selected_id
        rows = self.db.search(self.var_search.get().strip(), self.var_filter.get())
        self._rows = {r["id"]: r for r in rows}
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            self.tree.insert("", "end", iid=str(r["id"]), tags=("even" if i % 2 else "odd",),
                             values=(r["date"], r["name"], r["category"], format_minutes(r["duration"]),
                                     r["notes"].replace("\n", " ")))
        if self._sort_col:
            self._apply_sort(self._sort_col, self._sort_rev)
        if keep is not None and keep in self._rows:
            self.tree.selection_set(str(keep))
            self.tree.see(str(keep))

        if rows:
            self.empty_lbl.place_forget()
        else:
            filtered = bool(self.var_search.get().strip()) or self.var_filter.get() != "All"
            self.empty_lbl.configure(text="No matching activities." if filtered else
                                     "No activities yet.\nFill in the form on the left and click Add.")
            self.empty_lbl.place(relx=0.5, rely=0.4, anchor="center")
        total = sum(r["duration"] for r in rows)
        self.status_var.set(f"{plural(len(rows), 'record')}   \u00B7   {format_minutes(total)} total")

    def refresh_summary(self):
        rows = self.db.all_rows()
        self.tree_sum.delete(*self.tree_sum.get_children())
        for i, (label, count, total, top) in enumerate(summarize(rows, self.var_period.get())):
            self.tree_sum.insert("", "end", tags=("even" if i % 2 else "odd",),
                                 values=(label, count, format_minutes(total), top))

        cats = defaultdict(int)
        for r in rows:
            cats[r["category"]] += r["duration"]
        grand = sum(cats.values()) or 1
        self.tree_cat.delete(*self.tree_cat.get_children())
        for i, (name, total) in enumerate(sorted(cats.items(), key=lambda kv: kv[1], reverse=True)):
            self.tree_cat.insert("", "end", tags=("even" if i % 2 else "odd",),
                                 values=(name, format_minutes(total), f"{total / grand:.0%}"))

    def refresh_chart(self):
        card_c, text_c, muted_c, border_c = pick(CARD), pick(TEXT), pick(MUTED), pick(BORDER)
        view = self.var_range.get()
        buckets = build_buckets(view, date.today())
        n = len(buckets)
        rows = self.db.rows_between(buckets[0][1].isoformat(), buckets[-1][2].isoformat())

        per_bucket = [defaultdict(int) for _ in buckets]
        cats = defaultdict(int)
        for r in rows:
            d = to_date(r["date"])
            for i, (_label, s, e) in enumerate(buckets):
                if s <= d <= e:
                    per_bucket[i][r["category"]] += r["duration"]
                    break
            cats[r["category"]] += r["duration"]
        total = sum(cats.values())

        self.fig.clear()
        self.fig.set_facecolor(card_c)
        gs = self.fig.add_gridspec(1, 2, width_ratios=[3, 2])
        ax1 = self.fig.add_subplot(gs[0])
        ax2 = self.fig.add_subplot(gs[1])
        for ax in (ax1, ax2):
            ax.set_facecolor(card_c)

        labels = [b[0] for b in buckets]
        xs = list(range(n))
        bottoms = [0.0] * n
        order = [c for c, _ in sorted(cats.items(), key=lambda kv: kv[1], reverse=True)]
        for c in order:
            vals = [per_bucket[i].get(c, 0) / 60 for i in range(n)]
            ax1.bar(xs, vals, bottom=bottoms, color=self.color_of(c), width=0.65, label=c,
                    edgecolor=card_c, linewidth=0.8)
            bottoms = [b + v for b, v in zip(bottoms, vals)]
        for x, h in zip(xs, bottoms):
            if h > 0:
                ax1.text(x, h, f"{h:.1f}", ha="center", va="bottom", fontsize=8, color=muted_c)
        ax1.set_xticks(xs)
        rotate = n > 8
        ax1.set_xticklabels(labels, rotation=45 if rotate else 0, ha="right" if rotate else "center", fontsize=8)
        ax1.set_ylabel("Hours", color=muted_c)
        ax1.set_title(f"{view}  -  {format_minutes(total)} logged", fontsize=11, loc="left", color=text_c)
        ax1.grid(axis="y", color=border_c)
        ax1.set_axisbelow(True)
        peak = max(bottoms) if bottoms else 0
        if peak > 0:
            ax1.set_ylim(0, peak * 1.32)
            leg = ax1.legend(loc="upper left", ncol=min(len(order), 4), fontsize=8, frameon=False)
            for txt in leg.get_texts():
                txt.set_color(text_c)
        else:
            ax1.text(0.5, 0.5, "No activities in this range", transform=ax1.transAxes, ha="center",
                     va="center", color=muted_c)

        if cats:
            items = sorted(cats.items(), key=lambda kv: kv[1])
            names = [k for k, _ in items]
            vals = [v / 60 for _, v in items]
            ax2.barh(names, vals, color=[self.color_of(nm) for nm in names], height=0.6)
            top = max(vals)
            for y, v in enumerate(vals):
                ax2.text(v + top * 0.02, y, f"{v:.1f}h", va="center", fontsize=8, color=muted_c)
            ax2.set_xlim(0, top * 1.2)
            ax2.set_title("By category", fontsize=11, loc="left", color=text_c)
            ax2.tick_params(axis="y", labelsize=9)
            ax2.grid(axis="x", color=border_c)
            ax2.set_axisbelow(True)
        else:
            ax2.text(0.5, 0.5, "No data", transform=ax2.transAxes, ha="center", va="center", color=muted_c)
            ax2.set_axis_off()

        for ax in (ax1, ax2):
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(border_c)
            ax.tick_params(colors=muted_c)

        self.fig.tight_layout()
        self.canvas.draw_idle()

    def refresh_report(self):
        name = self.var_report_range.get()
        custom = name == "Custom range"
        for entry in (self.ent_from, self.ent_to):
            entry.configure(state="normal" if custom else "disabled")
        try:
            start, end = resolve_range(name, date.today(), self.db.date_bounds(),
                                       self.var_from.get(), self.var_to.get())
        except ValueError as exc:
            self._report = None
            self._show_preview([(str(exc), "p")])
            return
        rows = self.db.rows_in_range(start.isoformat(), end.isoformat())
        self._report = build_report(rows, start, end, name)
        self._show_preview(report_lines(self._report))

    def _show_preview(self, lines):
        self.txt_report.configure(state="normal")
        self._rt.delete("1.0", "end")
        for text, kind in lines:
            self._rt.insert("end", text + "\n", kind)
        self.txt_report.configure(state="disabled")
        self._rt.yview_moveto(0)

    # Form logic --
    def _on_search_change(self, *_):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(180, self.refresh_table)  # debounce so typing stays smooth

    def _set_today(self):
        self.var_date.set(date.today().strftime(DATE_FMT))

    def _shift_date(self, days):
        try:
            current = to_date(self.var_date.get().strip())
        except ValueError:
            current = date.today()
        self.var_date.set((current + timedelta(days=days)).strftime(DATE_FMT))

    def _reset_filters(self):
        self.var_search.set("")
        self.var_filter.set("All")
        self.refresh_table()

    def _new_entry(self):
        self.show_page("Activities")
        self.clear_form()
        self.ent_name.focus_set()

    def _focus_search(self):
        self.show_page("Activities")
        self.ent_search.focus_set()
        self.ent_search.select_range(0, "end")

    def _read_form(self):
        name = self.var_name.get().strip()
        if not name:
            raise ValueError("Please enter an activity name.")
        category = self.var_category.get().strip() or "Other"
        duration = parse_duration(self.var_duration.get())
        day = self.var_date.get().strip()
        try:
            to_date(day)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format, e.g. 2026-10-28.") from None
        notes = self.txt_notes.get("1.0", "end").strip()
        return name, category, duration, day, notes

    def _try_read_form(self):
        try:
            return self._read_form()
        except ValueError as exc:
            messagebox.showwarning("Check your entry", str(exc))
            return None

    def _load_form(self, rec_id):
        row = self.db.get(rec_id)
        if not row:
            return
        self.var_name.set(row["name"])
        self.var_category.set(row["category"])
        self.var_duration.set(str(row["duration"]))
        self.var_date.set(row["date"])
        self.txt_notes.delete("1.0", "end")
        self.txt_notes.insert("1.0", row["notes"])

    def clear_form(self):
        self.selected_id = None
        self.var_name.set("")
        self.var_duration.set("")
        self._set_today()
        self.txt_notes.delete("1.0", "end")
        self.tree.selection_remove(*self.tree.selection())
        self._update_buttons()

    def _update_buttons(self):
        count = len(self.tree.selection())
        self.btn_update.configure(state="normal" if count == 1 else "disabled")
        self.btn_delete.configure(state="normal" if count >= 1 else "disabled")

    # Actions --
    def on_select(self, _event=None):
        sel = self.tree.selection()
        if len(sel) == 1:
            rec_id = int(sel[0])
            if rec_id != self.selected_id:
                self.selected_id = rec_id
                self._load_form(rec_id)
        else:
            self.selected_id = None
        self._update_buttons()

    def on_save(self, _event=None):
        """Enter key: update the selected record, or add a new one."""
        if self.selected_id is not None:
            self.on_update()
        else:
            self.on_add()

    def on_add(self):
        data = self._try_read_form()
        if not data:
            return
        self.db.add(*data)
        self.var_name.set("")
        self.var_duration.set("")
        self.txt_notes.delete("1.0", "end")
        self.selected_id = None
        self.tree.selection_remove(*self.tree.selection())
        self.refresh_all()
        self._update_buttons()
        self._toast_msg(f"Added '{data[0]}' ({format_minutes(data[2])}).")
        self.ent_name.focus_set()

    def on_update(self):
        if self.selected_id is None:
            return
        data = self._try_read_form()
        if not data:
            return
        self.db.update(self.selected_id, *data)
        self.refresh_all()
        self._toast_msg("Record updated.")

    def on_delete(self):
        ids = [int(i) for i in self.tree.selection()]
        if not ids:
            return
        if not messagebox.askyesno("Delete records", f"Delete {len(ids)} selected record(s)?\nThis cannot be undone."):
            return
        self.db.delete(ids)
        self.clear_form()
        self.refresh_all()
        self._toast_msg(f"Deleted {plural(len(ids), 'record')}.")

    def on_export(self):
        ids = [int(i) for i in self.tree.get_children()]
        if not ids:
            messagebox.showinfo("Export CSV", "There are no records to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export records to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"activities_{date.today().strftime(DATE_FMT)}.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig opens cleanly in Excel
                writer = csv.writer(f)
                writer.writerow(["Date", "Activity", "Category", "Duration (minutes)", "Notes"])
                for rec_id in ids:
                    r = self._rows[rec_id]
                    writer.writerow([r["date"], r["name"], r["category"], r["duration"], r["notes"]])
        except OSError as exc:
            messagebox.showerror("Export failed", f"Could not write the file:\n{exc}")
            return
        messagebox.showinfo("Export CSV", f"Exported {plural(len(ids), 'record')} (as currently shown) to:\n{path}")

    # report actions 
    def _report_or_warn(self):
        self.refresh_report()
        if not self._report:
            messagebox.showwarning("Report", "Please fix the dates first (use YYYY-MM-DD).")
            return None
        return self._report

    def on_print_report(self):
        self.show_page("Report")
        rep = self._report_or_warn()
        if not rep:
            return
        path = Path(tempfile.gettempdir()) / f"activity_report_{datetime.now():%Y%m%d_%H%M%S}.html"
        try:
            path.write_text(report_to_html(rep, self.cat_colors, auto_print=True), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Report", f"Could not create the report:\n{exc}")
            return
        webbrowser.open(path.as_uri())
        self._toast_msg("Report opened in your browser. Choose a printer, or 'Save as PDF'.")

    def on_copy_report(self):
        rep = self._report_or_warn()
        if not rep:
            return
        self.clipboard_clear()
        self.clipboard_append(report_to_text(rep))
        self._toast_msg("Report copied to the clipboard.")

    def on_save_report_txt(self):
        rep = self._report_or_warn()
        if not rep:
            return
        path = filedialog.asksaveasfilename(
            title="Save report as text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"activity_report_{date.today().strftime(DATE_FMT)}.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(report_to_text(rep))
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not write the file:\n{exc}")
            return
        self._toast_msg("Report saved.")

    # Sorting --
    def sort_by(self, col):
        reverse = (not self._sort_rev) if self._sort_col == col else False
        self._apply_sort(col, reverse)

    def _apply_sort(self, col, reverse):
        def key(iid):
            r = self._rows[int(iid)]
            if col == "duration":
                return r["duration"]
            if col == "date":
                return (r["date"], r["id"])
            return str(r[col]).lower()

        items = sorted(self.tree.get_children(), key=key, reverse=reverse)
        for i, iid in enumerate(items):
            self.tree.move(iid, "", i)
            self.tree.item(iid, tags=("even" if i % 2 else "odd",))
        self._sort_col, self._sort_rev = col, reverse
        for k, label, _w, _a in self.COLUMNS:
            arrow = (" \u25BC" if reverse else " \u25B2") if k == col else ""
            self.tree.heading(k, text=label + arrow)

    # Close --
    def on_close(self):
        self.db.close()
        self.destroy()


def main():
    set_windows_app_id()
    ensure_icon_file()
    db = Database(DB_PATH)
    ctk.set_appearance_mode(db.get_setting("appearance", "Light"))
    ctk.set_default_color_theme("blue")
    app = ActivityLoggerApp(db)
    app.mainloop()


if __name__ == "__main__":
    main()
