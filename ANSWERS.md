# ANSWERS.md

## 1. How to run

On a fresh machine with Python 3.9+:

```bash
git clone <your-repo-url>
cd stratos-weather
pip install -r requirements.txt
python app.py
```

**Interactive mode** (no arguments): launches a prompt where you type city names one at a time, then type `compare` to see the side-by-side table, `unit` to toggle °C/°F, `clear` to reset, `quit` to exit.

**Batch mode** (cities as arguments):
```bash
python app.py Islamabad Tokyo London
python app.py "New York" Paris Berlin --unit F
```

No API key. No `.env`. No account. Open-Meteo is free and keyless.

---

## 2. Stack choice

**Python + httpx + rich**

Python is the natural fit because the task is pure data transformation: fetch JSON from an HTTP API, reshape it, display it. The standard library covers most of it; two small packages close the rest.

- `httpx` over `requests` because it ships with a proper `timeout` parameter as a first-class argument (not an afterthought), and supports both sync and async with the same API. The assessors test slow APIs — `httpx.TimeoutException` is clean and specific.
- `rich` gives a professional terminal UI (panels, tables, colour, spinners, columns) with near-zero boilerplate. The comparison table with green/red highlighting would require significant manual ANSI escape work otherwise.

**A worse choice: JavaScript/Node.js**  
Node is fine for APIs, but the "runnable on a fresh machine via README" requirement gets painful: `node` version differences, `npm install`, the `package-lock.json` sprawl. Python's `pip install -r requirements.txt` is simpler and more universally available. For a CLI that lives in the terminal, Python also has a richer ecosystem of terminal UI libraries.

**An even worse choice: Bash**  
`curl` + `jq` can do one API call, but multi-city parallel fetching, structured error handling per city, and formatted comparison tables become unreadable scripts fast. Bash has no concept of typed exceptions, so the three error modes (timeout, HTTP error, bad input) would require fragile exit-code inspection.

---

## 3. One real edge case

**City names containing digits are rejected before any network call is made.**

**File:** `app.py`  
**Function:** `validate_city_input`  
**Relevant lines:**

```python
if any(ch.isdigit() for ch in stripped):
    return None, f"'{stripped}' doesn't look like a city name (contains digits)."
```

**What it handles:**  
A user typing `Islamabad123`, `123`, or a postal code like `75001` (Paris's arrondissement code) would otherwise reach the geocoding API. Open-Meteo's geocoder handles some of these gracefully but others return an empty result set or an unexpected match — for example `75001` resolves to a location in France with no meaningful name, and the app would silently display weather for the wrong place.

By catching digits before the network call, the user gets an immediate, specific error message (`'75001' doesn't look like a city name (contains digits).`) rather than either a confusing result or a slow round-trip to the API that returns nothing.

**Without this handling:** the geocoder would either return `None` results (showing a generic "city not found" error, which is technically correct but not helpful) or, worse, return a lat/lon for an unrelated numeric match, silently showing weather for the wrong location.

---

## 4. AI usage

**Tool used:** Claude (Anthropic)

### Use 1 — Initial structure
Asked: "Give me a skeleton for a Python CLI that calls two HTTP endpoints and displays results with `rich`."  
Got: A flat script with `requests`, a single `try/except`, and `rich.print` calls. Functional but not structured.  
**What I changed:** Replaced `requests` with `httpx` to get named timeout exceptions (`TimeoutException` vs `requests.exceptions.Timeout`) which produce cleaner, more specific error messages. Also split the monolith into `geocode()`, `fetch_weather()`, and `validate_city_input()` functions so each error mode is isolated and testable independently.

### Use 2 — WMO weather code table
Asked: "Give me a Python dict mapping WMO weather codes to descriptions and emoji."  
Got: A complete mapping with correct WMO codes.  
**What I changed:** The AI included codes like `56`, `57`, `66`, `67` (freezing drizzle/rain) which Open-Meteo does not actually return in its `weathercode` field — it uses a subset. I trimmed the dict to the codes Open-Meteo documents in its API reference to avoid dead entries.

### Use 3 — Comparison table highlighting
Asked: "How do I highlight the best and worst value in a rich Table column?"  
Got: A suggestion using `rich.markup` inline strings with `[green]` and `[red]` tags applied after collecting all values.  
**What I changed:** The AI's version iterated over columns (one pass per city). I restructured it to iterate over metrics (one pass per row), which makes it straightforward to skip highlighting when all values are equal and avoids marking one city both best and worst when there are only two cities with the same value.

---

## 5. Honest gap

**The comparison table ranks metrics independently, not holistically.**

Right now, the table marks the highest temperature green and the lowest red, the lowest wind speed green and the highest red, and so on — but it never combines these into an overall "best weather" score. A user asking "which city has the best weather this week?" has to read the table themselves and mentally weight the metrics.

With another day, I would add a simple composite score — weighting temperature comfort (closeness to 22 °C / 72 °F), low precipitation, and low wind — and add a "Overall Score" row at the bottom of the comparison table with a 1–10 rating per city. The weights would be user-configurable via a `--weights` flag or an interactive prompt. This is the one thing a user cannot do by visiting the Open-Meteo website directly, and it's the most compelling reason to use the tool over the raw API.
