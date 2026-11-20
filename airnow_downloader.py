"""Tehran AQCC historical hourly archive downloader.

Adapted from the working station/season Playwright workflow. No credentials
or follow-up codes are stored in this source file.
"""
from __future__ import annotations

import argparse
import csv
import getpass
import re
import time
from datetime import date, timedelta
from pathlib import Path

import jdatetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://airnow.tehran.ir/home/DataArchive.aspx"
STATION = "#ContentPlaceHolder1_ddlStation"
FROM_DATE = "#ContentPlaceHolder1_pddFrom"
TO_DATE = "#ContentPlaceHolder1_pddTo"
CODE = "#ContentPlaceHolder1_txtFollowUpCode"
FIELDS = ["season", "station", "station_id", "from_jalali", "to_jalali", "status", "filename", "message"]


def norm(s: str) -> str:
    s = str(s).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return re.sub(r"\s+", "", s).strip()


def gregorian_to_jalali(d: date) -> str:
    j = jdatetime.date.fromgregorian(date=d)
    return f"{j.year:04d}/{j.month:02d}/{j.day:02d}"


def season_dates(year: int) -> tuple[str, str]:
    # Preserves the original project's November 1–last day of February window.
    return (gregorian_to_jalali(date(year, 11, 1)),
            gregorian_to_jalali(date(year + 1, 3, 1) - timedelta(days=1)))


def select_date(page, selector: str, jalali: str) -> None:
    # Preserved from original script; do not silently choose datepicker dates.
    field = page.locator(selector)
    field.wait_for(state="visible", timeout=30000)
    try:
        field.fill(jalali, timeout=5000)
        field.dispatch_event("input")
        field.dispatch_event("change")
        actual = field.input_value().strip()
        if norm(actual).replace("/", "") != norm(jalali).replace("/", ""):
            raise RuntimeError(f"Date mismatch: expected {jalali}, got {actual!r}")
    except Exception as exc:
        raise RuntimeError(f"Cannot reliably set {selector} to {jalali}: {exc}") from exc


def get_stations(page) -> list[dict]:
    options = page.locator(f"{STATION} option").evaluate_all(
        "els => els.map(e => ({value:e.value, text:e.textContent.trim()}))"
    )
    return [o for o in options if o["value"].strip() and norm(o["text"]) != norm("تست")]


def safe_filename(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")


def log_result(log_file: Path, row: dict) -> None:
    new = not log_file.exists() or log_file.stat().st_size == 0
    with log_file.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def no_records_visible(page) -> bool:
    # Only treat a clearly displayed archive message as NO_RECORDS.
    return page.get_by_text("رکوردی برای نمایش موجود نیست", exact=False).count() > 0 and \
        page.get_by_text("رکوردی برای نمایش موجود نیست", exact=False).first.is_visible()


def download_one(page, station: dict, year: int, code: str, output: Path,
                 log_file: Path, confirm: bool) -> dict:
    from_j, to_j = season_dates(year)
    stem = safe_filename(f"AQCC_{station['value']}_{station['text']}_{year}-{year + 1}")
    row = dict(season=f"{year}-{year + 1}", station=station["text"],
               station_id=station["value"], from_jalali=from_j, to_jalali=to_j,
               status="", filename="", message="")
    existing = [output / (stem + ext) for ext in (".xlsx", ".xls", ".csv")]
    for path in existing:
        if path.is_file() and path.stat().st_size > 1024:
            row.update(status="SKIPPED_EXISTING", filename=str(path))
            log_result(log_file, row)
            print(f"{row['season']} | {row['station']} | SKIPPED_EXISTING")
            return row
    try:
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.locator(STATION).select_option(value=station["value"])
        # Original script uses the website's default report type; verify hourly in browser.
        select_date(page, FROM_DATE, from_j)
        select_date(page, TO_DATE, to_j)
        page.locator(CODE).fill(code)
        if confirm:
            print(f"Verify station={station['text']}, HOURLY report, {from_j} to {to_j}.")
            input("Press ENTER to click نمایش, or Ctrl+C to stop: ")
        page.get_by_role("button", name="نمایش").click()
        # Keep the original download-button workflow, with an explicit no-record check.
        try:
            page.get_by_role("button", name="دانلود").wait_for(state="visible", timeout=15000)
        except PlaywrightTimeoutError:
            if no_records_visible(page):
                row.update(status="NO_RECORDS", message="Archive displayed no records")
                return row
            raise RuntimeError("Download button not visible; verify report, code and site response")
        with page.expect_download(timeout=120000) as event:
            page.get_by_role("button", name="دانلود").click()
        download = event.value
        ext = Path(download.suggested_filename).suffix.lower()
        if ext not in (".xlsx", ".xls", ".csv"):
            raise RuntimeError(f"Unexpected downloaded extension: {ext!r}")
        target = output / (stem + ext)
        download.save_as(str(target))
        if target.stat().st_size < 1024:
            target.unlink(missing_ok=True)
            raise RuntimeError("Downloaded file unexpectedly small")
        row.update(status="DOWNLOADED_UNVALIDATED", filename=str(target),
                   message="Inspect spreadsheet rows, pollutant values, station and dates")
        return row
    except Exception as exc:
        row.update(status="FAILED", message=str(exc)[:500])
        return row
    finally:
        # Return from try/except still executes finally.
        log_result(log_file, row)
        print(f"{row['season']} | {row['station']} | {row['status']}"
              + (f" | {row['message']}" if row['message'] else ""))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Tehran AQCC hourly winter archives")
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--station", action="append", help="Station ID or exact name; repeatable")
    parser.add_argument("--list-stations", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("downloads"))
    parser.add_argument("--pause", type=float, default=8.0)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--confirm", action="store_true", help="Verify each request in browser")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_year > args.end_year:
        raise SystemExit("--start-year must not exceed --end-year")
    if args.pause < 0:
        raise SystemExit("--pause must be nonnegative")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=args.headless)
        context = browser.new_context(accept_downloads=True, locale="fa-IR")
        page = context.new_page()
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            stations = get_stations(page)
            if args.list_stations:
                for station in stations:
                    print(f"{station['value']}: {station['text']}")
                return
            if args.station:
                wanted = {norm(x) for x in args.station}
                selected = [s for s in stations if norm(s["value"]) in wanted or norm(s["text"]) in wanted]
                matched = {norm(s["value"]) for s in selected} | {norm(s["text"]) for s in selected}
                if not selected or any(x not in matched for x in wanted):
                    raise SystemExit("Some station IDs/names were not found; use --list-stations")
                stations = selected
            print(f"Selected {len(stations)} stations, {args.end_year - args.start_year + 1} seasons")
            # Never embed or log the follow-up code. Input is hidden where supported.
            code = input("Enter YOUR follow-up code from the AQCC website: ").strip()
            if not code:
                raise SystemExit("A follow-up code is required")
            output = args.output.resolve()
            output.mkdir(parents=True, exist_ok=True)
            log_file = output / "download_log.csv"
            for year in range(args.start_year, args.end_year + 1):
                for station in stations:
                    download_one(page, station, year, code, output, log_file, args.confirm)
                    time.sleep(args.pause)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
