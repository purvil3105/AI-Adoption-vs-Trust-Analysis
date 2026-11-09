"""Download the Stack Overflow Developer Survey 2023-2025 files.

Source: https://survey.stackoverflow.co/ -> GitHub archive StackExchange/Survey (packages/archive/<year>).
The CSVs are stored with Git LFS, so they are fetched from media.githubusercontent.com.
Data licence: Open Database License (ODbL) 1.0.

Usage:  python -m src.download
"""
import time
import urllib.error
import urllib.request

from src.config import RAW, YEARS

LFS = "https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive/{year}/{file}"
RAW_GH = "https://raw.githubusercontent.com/StackExchange/Survey/main/packages/archive/{year}/json/{file}"

FILES = ["results.csv", "schema.csv", "survey.pdf"]
OFFICIAL_JSON = ["ai.json", "methodology.json"]


def fetch(url: str, dest, retries: int = 3) -> None:
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  skip (exists) {dest.relative_to(RAW)}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  get  {url}")
    part = dest.with_name(dest.name + ".part")     # write to a temp file so an interrupted download is never "complete"
    for attempt in range(1, retries + 1):
        try:
            urllib.request.urlretrieve(url, part)
            if part.stat().st_size <= 1000:          # Git LFS pointer / error page instead of the real file
                raise IOError(f"downloaded file is only {part.stat().st_size} bytes")
            part.replace(dest)
            return
        except (OSError, urllib.error.URLError) as e:
            part.unlink(missing_ok=True)
            if attempt == retries:
                raise RuntimeError(f"failed to download {url}: {e}") from e
            print(f"  retry {attempt}/{retries - 1} after error: {e}")
            time.sleep(5 * attempt)


def main() -> None:
    for year in YEARS:
        print(f"== {year}")
        for f in FILES:
            fetch(LFS.format(year=year, file=f), RAW / str(year) / f)
        for f in OFFICIAL_JSON:
            fetch(RAW_GH.format(year=year, file=f), RAW / str(year) / "official_json" / f)


if __name__ == "__main__":
    main()
