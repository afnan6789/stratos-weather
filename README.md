# Stratos — Multi-City Weather Comparison CLI

Compare real-time weather and 7-day forecasts across multiple cities, side by side in the terminal.  
Built on [Open-Meteo](https://open-meteo.com/) — **no API key required**.

---

## Requirements

- Python 3.9 or higher
- pip

---

## Installation & Run (fresh machine)

```bash
git clone <your-repo-url>
cd stratos-weather
pip install -r requirements.txt
python app.py
```

That's it. No `.env` file, no API key, no account needed.

---

## Usage

### Interactive mode (no arguments)
```bash
python app.py
```
Type city names one at a time. Available commands inside the prompt:

| Command   | What it does                          |
|-----------|---------------------------------------|
| `compare` | Show side-by-side comparison table    |
| `unit`    | Toggle between °C and °F              |
| `clear`   | Remove all cities and start over      |
| `quit`    | Exit                                  |

### Batch mode (cities as arguments)
```bash
python app.py Islamabad Tokyo London
python app.py "New York" Paris Berlin --unit F
```

Displays all cities at once and prints the comparison table automatically when 2+ cities are given.

### Temperature unit flag
```bash
python app.py --unit F Karachi Dubai
```

---

## What it shows

- Current temperature, feels-like, humidity, wind speed, precipitation
- 7-day forecast with daily high/low and precipitation
- Side-by-side comparison table (green = best, red = worst per metric)

---

## Error handling

Stratos handles three failure modes explicitly:
- **Slow API** — 8s geocoding and 10s weather timeouts
- **API errors** — HTTP errors caught per city, others continue
- **Bad input** — validated before any network call is made
