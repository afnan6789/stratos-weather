import sys
import argparse
import httpx
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner
from rich.layout import Layout
import time

console = Console()

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0:  ("Clear Sky",          "☀️"),
    1:  ("Mostly Clear",       "🌤️"),
    2:  ("Partly Cloudy",      "⛅"),
    3:  ("Overcast",           "☁️"),
    45: ("Foggy",              "🌫️"),
    48: ("Icy Fog",            "🌫️"),
    51: ("Light Drizzle",      "🌦️"),
    53: ("Drizzle",            "🌦️"),
    55: ("Heavy Drizzle",      "🌧️"),
    61: ("Light Rain",         "🌧️"),
    63: ("Rain",               "🌧️"),
    65: ("Heavy Rain",         "🌧️"),
    71: ("Light Snow",         "🌨️"),
    73: ("Snow",               "❄️"),
    75: ("Heavy Snow",         "❄️"),
    77: ("Snow Grains",        "🌨️"),
    80: ("Rain Showers",       "🌦️"),
    81: ("Heavy Showers",      "🌧️"),
    82: ("Violent Showers",    "⛈️"),
    85: ("Snow Showers",       "🌨️"),
    86: ("Heavy Snow Showers", "❄️"),
    95: ("Thunderstorm",       "⛈️"),
    96: ("Thunderstorm+Hail",  "⛈️"),
    99: ("Thunderstorm+Hail",  "⛈️"),
}

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def wmo_label(code):
    return WMO_CODES.get(code, ("Unknown", "🌡️"))


def c_to_f(c):
    return round(c * 9 / 5 + 32, 1)


def format_temp(c, unit):
    if unit == "F":
        return f"{c_to_f(c)}°F"
    return f"{c}°C"


def geocode(city_name):
    try:
        r = httpx.get(
            GEOCODE_URL,
            params={"name": city_name, "count": 1, "language": "en", "format": "json"},
            timeout=8.0,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results")
        if not results:
            return None, f"City not found: '{city_name}'"
        loc = results[0]
        return {
            "name":    loc["name"],
            "country": loc.get("country", ""),
            "lat":     loc["latitude"],
            "lon":     loc["longitude"],
            "tz":      loc.get("timezone", "UTC"),
        }, None
    except httpx.TimeoutException:
        return None, f"Geocoding timed out for '{city_name}'. Check your connection."
    except httpx.HTTPStatusError as e:
        return None, f"Geocoding API error {e.response.status_code} for '{city_name}'."
    except httpx.RequestError as e:
        return None, f"Network error during geocoding: {e}"


def fetch_weather(loc):
    params = {
        "latitude":        loc["lat"],
        "longitude":       loc["lon"],
        "current":         "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weathercode,precipitation",
        "daily":           "temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum",
        "wind_speed_unit": "mph",
        "timezone":        loc["tz"],
        "forecast_days":   7,
    }
    try:
        r = httpx.get(WEATHER_URL, params=params, timeout=10.0)
        r.raise_for_status()
        return r.json(), None
    except httpx.TimeoutException:
        return None, f"Weather fetch timed out for {loc['name']}. API may be slow — try again."
    except httpx.HTTPStatusError as e:
        return None, f"Weather API returned {e.response.status_code} for {loc['name']}."
    except httpx.RequestError as e:
        return None, f"Network error fetching weather for {loc['name']}: {e}"


def validate_city_input(raw):
    stripped = raw.strip()
    if not stripped:
        return None, "City name cannot be empty."
    if len(stripped) < 2:
        return None, "City name too short — enter at least 2 characters."
    if len(stripped) > 80:
        return None, "City name too long."
    if any(ch.isdigit() for ch in stripped):
        return None, f"'{stripped}' doesn't look like a city name (contains digits)."
    return stripped, None


def build_city_panel(loc, weather, unit):
    cur = weather["current"]
    daily = weather["daily"]

    temp_c = cur["temperature_2m"]
    feels_c = cur["apparent_temperature"]
    humidity = cur["relative_humidity_2m"]
    wind = cur["wind_speed_10m"]
    precip = cur["precipitation"]
    code = cur["weathercode"]

    desc, icon = wmo_label(code)
    temp_str = format_temp(temp_c, unit)
    feels_str = format_temp(feels_c, unit)

    lines = Text()
    lines.append(f"{icon}  {temp_str}\n", style="bold white")
    lines.append(f"Feels like {feels_str}\n", style="dim")
    lines.append(f"{desc}\n\n", style="italic cyan")
    lines.append(f"💧 Humidity   ", style="dim"); lines.append(f"{humidity}%\n", style="white")
    lines.append(f"💨 Wind       ", style="dim"); lines.append(f"{wind} mph\n", style="white")
    lines.append(f"🌧  Precip now ", style="dim"); lines.append(f"{precip} mm\n\n", style="white")

    lines.append("7-DAY FORECAST\n", style="bold dim")
    for i in range(min(7, len(daily["time"]))):
        hi = daily["temperature_2m_max"][i]
        lo = daily["temperature_2m_min"][i]
        fc_code = daily["weathercode"][i]
        fc_precip = daily["precipitation_sum"][i]
        _, fc_icon = wmo_label(fc_code)
        import datetime
        date_obj = datetime.date.fromisoformat(daily["time"][i])
        day_label = DAYS[date_obj.weekday()]
        hi_str = format_temp(hi, unit)
        lo_str = format_temp(lo, unit)
        lines.append(f"  {day_label}  {fc_icon}  ", style="dim")
        lines.append(f"{hi_str}", style="bold")
        lines.append(f" / {lo_str}", style="dim")
        if fc_precip and fc_precip > 0:
            lines.append(f"  💧{fc_precip}mm", style="blue")
        lines.append("\n")

    title = f"[bold]{loc['name']}[/bold] [dim]{loc['country']}[/dim]"
    return Panel(lines, title=title, border_style="blue", padding=(1, 2))


def build_comparison_table(results, unit):
    table = Table(
        title="Side-by-Side Comparison",
        box=box.SIMPLE_HEAD,
        show_lines=False,
        header_style="bold dim",
        title_style="bold white",
    )

    table.add_column("Metric", style="dim", min_width=18)

    for loc, _ in results:
        table.add_column(loc["name"], justify="right", min_width=12)

    metrics = []
    for loc, weather in results:
        cur = weather["current"]
        daily = weather["daily"]
        metrics.append({
            "temp":     cur["temperature_2m"],
            "feels":    cur["apparent_temperature"],
            "humidity": cur["relative_humidity_2m"],
            "wind":     cur["wind_speed_10m"],
            "precip":   cur["precipitation"],
            "hi":       daily["temperature_2m_max"][0],
            "lo":       daily["temperature_2m_min"][0],
        })

    def row_vals(key, fmt_fn, higher_is_better=None):
        vals = [m[key] for m in metrics]
        if higher_is_better is None:
            return [fmt_fn(v) for v in vals]
        best = max(vals) if higher_is_better else min(vals)
        worst = min(vals) if higher_is_better else max(vals)
        out = []
        for v in vals:
            s = fmt_fn(v)
            if v == best:
                out.append(f"[green]{s}[/green]")
            elif v == worst and len(vals) > 1:
                out.append(f"[red]{s}[/red]")
            else:
                out.append(s)
        return out

    temp_fmt = lambda c: format_temp(c, unit)
    pct_fmt  = lambda v: f"{v}%"
    mph_fmt  = lambda v: f"{v} mph"
    mm_fmt   = lambda v: f"{v} mm"

    table.add_row("🌡  Current Temp",   *row_vals("temp",     temp_fmt, higher_is_better=True))
    table.add_row("🤔 Feels Like",      *row_vals("feels",    temp_fmt, higher_is_better=True))
    table.add_row("📈 Today High",      *row_vals("hi",       temp_fmt, higher_is_better=True))
    table.add_row("📉 Today Low",       *row_vals("lo",       temp_fmt, higher_is_better=False))
    table.add_row("💧 Humidity",        *row_vals("humidity", pct_fmt,  higher_is_better=None))
    table.add_row("💨 Wind Speed",      *row_vals("wind",     mph_fmt,  higher_is_better=False))
    table.add_row("🌧  Precipitation",  *row_vals("precip",   mm_fmt,   higher_is_better=False))

    return table


def spinner_fetch(label, fn):
    result = [None]
    error  = [None]

    with console.status(f"[dim]{label}[/dim]", spinner="dots"):
        result[0], error[0] = fn()

    return result[0], error[0]


def interactive_mode(unit):
    console.print(Panel(
        "[bold]Stratos[/bold] — Multi-City Weather Comparison\n"
        "[dim]Type a city name to add it. Commands: [bold]compare[/bold], [bold]clear[/bold], [bold]unit[/bold], [bold]quit[/bold][/dim]",
        border_style="blue"
    ))

    cities = []
    results = []

    while True:
        try:
            raw = Prompt.ask("\n[blue]>[/blue] City / command")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        cmd = raw.strip().lower()

        if cmd in ("quit", "exit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if cmd == "clear":
            cities.clear()
            results.clear()
            console.print("[dim]Cleared all cities.[/dim]")
            continue

        if cmd == "compare":
            if len(results) < 2:
                console.print("[yellow]Add at least 2 cities to compare.[/yellow]")
                continue
            console.print(build_comparison_table(results, unit))
            continue

        if cmd == "unit":
            unit = "F" if unit == "C" else "C"
            console.print(f"[dim]Switched to °{unit}[/dim]")
            continue

        if cmd == "":
            continue

        city_clean, err = validate_city_input(raw)
        if err:
            console.print(f"[red]✗ {err}[/red]")
            continue

        if city_clean.lower() in [c.lower() for c in cities]:
            console.print(f"[yellow]'{city_clean}' is already in your list.[/yellow]")
            continue

        loc, err = spinner_fetch(f"Locating {city_clean}…", lambda: geocode(city_clean))
        if err:
            console.print(f"[red]✗ {err}[/red]")
            continue

        weather, err = spinner_fetch(f"Fetching weather for {loc['name']}…", lambda: fetch_weather(loc))
        if err:
            console.print(f"[red]✗ {err}[/red]")
            continue

        cities.append(city_clean)
        results.append((loc, weather))

        console.print(build_city_panel(loc, weather, unit))

        if len(results) >= 2:
            console.print(build_comparison_table(results, unit))


def batch_mode(city_names, unit):
    results = []
    errors  = []

    for raw in city_names:
        city_clean, err = validate_city_input(raw)
        if err:
            errors.append(f"{raw}: {err}")
            continue

        loc, err = spinner_fetch(f"Locating {city_clean}…", lambda c=city_clean: geocode(c))
        if err:
            errors.append(err)
            continue

        weather, err = spinner_fetch(f"Fetching weather for {loc['name']}…", lambda l=loc: fetch_weather(l))
        if err:
            errors.append(err)
            continue

        results.append((loc, weather))

    for err in errors:
        console.print(f"[red]✗ {err}[/red]")

    if not results:
        console.print("[red]No valid cities to display.[/red]")
        sys.exit(1)

    panels = [build_city_panel(loc, weather, unit) for loc, weather in results]
    console.print(Columns(panels, equal=True, expand=True))

    if len(results) >= 2:
        console.print(build_comparison_table(results, unit))


def main():
    parser = argparse.ArgumentParser(
        prog="stratos",
        description="Compare weather across multiple cities using Open-Meteo (no API key needed).",
    )
    parser.add_argument(
        "cities",
        nargs="*",
        help="City names to compare (e.g. 'Islamabad' 'Tokyo'). Omit for interactive mode.",
    )
    parser.add_argument(
        "--unit",
        choices=["C", "F"],
        default="C",
        help="Temperature unit (default: C)",
    )

    args = parser.parse_args()

    if args.cities:
        batch_mode(args.cities, args.unit)
    else:
        interactive_mode(args.unit)


if __name__ == "__main__":
    main()
