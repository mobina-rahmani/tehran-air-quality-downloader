# Tehran AQCC Archive Downloader

Python + Playwright downloader for the **Tehran Air Quality Control Company** historical archive: https://airnow.tehran.ir/home/DataArchive.aspx

**Status: beta — test against the live archive before relying on results.** This tool is unofficial and not affiliated with AQCC.

## Installation

Requires Python 3.10+, Google Chrome, and access to the AQCC archive.

```bash
python -m pip install -r requirements.txt
```

## Obtain your own follow-up code

Visit the AQCC archive and obtain the follow-up code required by the site. **Each user must provide their own code.** The downloader asks for it interactively, does not print it, and does not include it in the source code or CSV log. Do not put your code in GitHub issues, screenshots, or commits.

## Monitoring Stations

The following 30 monitoring stations and their IDs are listed in the Tehran AQCC historical archive. Use the station ID with the --station option.


| Station ID | Station Name (Persian) |
|---|---|
| 21 | اتوبان محلاتی، منطقه ۱۴ |
| 6 | اقدسیه، منطقه ۱ |
| 23 | بهاران |
| 13 | پارک رز، منطقه ۲۲ |
| 7 | پونک، منطقه ۵ |
| 5 | پیروزی، منطقه ۱۳ |
| 41 | تربیت مدرس، منطقه ۶ |
| 4 | دروس، منطقه ۳ |
| 14 | ستاد بحران، منطقه ۷ |
| 22 | ستاد آباد، منطقه ۱۸ |
| 1 | شریف، منطقه ۲ |
| 12 | شهر ری، منطقه ۲۰ |
| 117 | شهرداری مرکز، منطقه ۱۲ |
| 8 | شهرداری، منطقه ۲ |
| 11 | شهرداری، منطقه ۴ |
| 16 | شهرداری، منطقه ۱۰ |
| 17 | شهرداری، منطقه ۱۱ |
| 15 | شهرداری، منطقه ۱۶ |
| 125 | شهرداری، منطقه ۱۷ |
| 18 | شهرداری، منطقه ۱۹ |
| 19 | شهرداری، منطقه ۲۱ |
| 49 | شهرداری، منطقه ۲۲ |
| 44 | شیخ صفی |
| 45 | صدر، منطقه ۳ |
| 124 | فرهنگسرای خاوران، منطقه ۱۵ |
| 9 | گلبرگ، منطقه ۸ |
| 10 | مسعودیه، منطقه ۱۵ |
| 20 | میدان فتح، منطقه ۹ |
| 118 | وردآورد، منطقه ۲۲ |
| 123 | کتابخانه ملی، منطقه ۳ |

**Note**: Station IDs are identifiers assigned by the AQCC archive, not sequential numbers. Station availability and historical data coverage may vary.


## Usage

List available stations (does not require a follow-up code):

```bash
python airnow_downloader.py --list-stations
```

Download **one station and one winter** (recommended first test):

```bash
python airnow_downloader.py --station 6 --start-year 2023 --end-year 2023 --confirm
```

Download several stations:

```bash
python airnow_downloader.py --station 6 --station 23 --start-year 2022 --end-year 2023 --confirm
```

Without `--station`, all listed stations are selected. Avoid a bulk run until you have checked a successful one-station download. Use `--output PATH` to change the destination. `--pause 8` is the default delay between requests.

**Date definition:** For a `--start-year` of 2023, the requested period is November 1, 2023 to the last day of February 2024 (converted to Jalali dates). This preserves the original research script's date logic; it is **not** an arbitrary-date downloader.

**Report type:** The script preserves the original workflow, which assumes the site's default report is *hourly average*. Confirm that the site actually displays **میانگین ساعتی**, particularly on the first run. It does not currently enforce this option programmatically.

## Output statuses

- `DOWNLOADED_UNVALIDATED`: file saved; inspect its contents before analysis.
- `SKIPPED_EXISTING`: an existing `.xlsx`, `.xls` or `.csv` file over 1 KB was found.
- `NO_RECORDS`: the site visibly reported no records after the query.
- `FAILED`: the download could not be confirmed; inspect the error and the website.

Missing records must **not** be treated as zero pollution. Successful file download does not establish PM2.5 completeness or data validity.

## Notes and limitations

- Requires a working Chrome installation; the site's interface can change.
- Uses the original script's textbox date-entry mechanism. If the date widget changes or is read-only, the script stops rather than silently selecting a different date.
- Do not share downloaded datasets without checking AQCC terms and applicable rights. Respect server load and site usage conditions.
- No guarantee of complete station coverage, accuracy, or uninterrupted availability.

## Provenance

Adapted from a research-oriented Playwright workflow for the Tehran AQCC historical archive. The download interaction and date handling were retained; station selection, CLI configuration, duplicate-file detection, no-record classification, and private follow-up-code input were adapted for general use.
