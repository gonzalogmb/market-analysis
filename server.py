"""Servidor Flask: expone los datos de Yahoo Finance como JSON para la UI en static/ y templates/."""

import functools
import math
import os
import secrets

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import db
from fetch_yahoo_data import (
    BASE_CURRENCY,
    TICKERS,
    fetch_full_close_in_base,
    fetch_history,
    fetch_summary,
    fetch_top_gainers,
    search_symbols,
)
from indicators import correlation_matrix, stats_summary
from portfolio import compute_portfolio

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key")
app.config["TEMPLATES_AUTO_RELOAD"] = True


def asset_url(filename):
    """URL de un archivo estático con ?v=<fecha de modificación>, para que el navegador
    descargue la versión nueva en cada despliegue en vez de servir una copia en caché."""
    path = os.path.join(app.static_folder, filename)
    try:
        version = int(os.path.getmtime(path))
    except OSError:
        version = 0
    return f"{url_for('static', filename=filename)}?v={version}"


app.jinja_env.globals["asset_url"] = asset_url

APP_PASSWORD = os.environ.get("APP_PASSWORD")

RANGES = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"]
INTERVALS = ["1d", "1wk", "1mo"]
BENCHMARK_SYMBOL = "^GSPC"
BENCHMARK_NAME = "S&P 500"

try:
    db.init_db()
except Exception as exc:  # noqa: BLE001
    print(f"Aviso: no se pudo inicializar la base de datos de la cartera: {exc}")


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if APP_PASSWORD and not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "No has iniciado sesión."}), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "unknown")


def _lockout_message(remaining_seconds):
    minutes = max(1, remaining_seconds // 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"Demasiados intentos fallidos. Inténtalo de nuevo en {hours}h {minutes}min."
    return f"Demasiados intentos fallidos. Inténtalo de nuevo en {minutes} min."


@app.route("/login", methods=["GET", "POST"])
def login():
    ip = _client_ip()
    error = None
    locked, remaining = db.is_locked_out(ip)

    if request.method == "POST":
        if locked:
            error = _lockout_message(remaining)
        else:
            password = request.form.get("password", "")
            if APP_PASSWORD and secrets.compare_digest(password, APP_PASSWORD):
                db.clear_failed_logins(ip)
                session["authenticated"] = True
                return redirect(request.args.get("next") or url_for("index"))
            db.record_failed_login(ip)
            locked, remaining = db.is_locked_out(ip)
            error = _lockout_message(remaining) if locked else "Contraseña incorrecta."
    elif locked:
        error = _lockout_message(remaining)

    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


def _clean(value):
    """Convierte NaN/Inf (no válidos en JSON) y tipos numpy a valores serializables."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        return _clean(value.item())
    return value


def _clean_deep(value):
    if isinstance(value, dict):
        return {k: _clean_deep(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_deep(v) for v in value]
    return _clean(value)


def _records(df):
    rows = df.reset_index().to_dict("records")
    return [{k: _clean(v) for k, v in row.items()} for row in rows]


def _history_records(df):
    df = df.reset_index()
    df["Date"] = df["Date"].apply(lambda d: d.isoformat())
    rows = df.to_dict("records")
    return [{k: _clean(v) for k, v in row.items()} for row in rows]


@app.route("/")
def index():
    return render_template(
        "index.html",
        defaults=TICKERS,
        ranges=RANGES,
        intervals=INTERVALS,
        login_enabled=bool(APP_PASSWORD),
        authenticated=bool(session.get("authenticated")),
    )


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    return jsonify(search_symbols(query))


@app.route("/api/top-gainers")
def api_top_gainers():
    count = request.args.get("count", 10, type=int)
    gainers = fetch_top_gainers(count=count)
    return jsonify([{k: _clean(v) for k, v in row.items()} for row in gainers])


@app.route("/api/generate", methods=["POST"])
def api_generate():
    payload = request.get_json(silent=True) or {}
    tickers = payload.get("tickers") or {}
    range_ = payload.get("range", "6mo")
    interval = payload.get("interval", "1d")

    if not tickers:
        return jsonify({"error": "Selecciona al menos un instrumento."}), 400
    if range_ not in RANGES or interval not in INTERVALS:
        return jsonify({"error": "Rango o intervalo no válido."}), 400

    try:
        summary = fetch_summary(tickers)
        histories = fetch_history(tickers, range_=range_, interval=interval)
        stats = stats_summary(histories)
        corr = correlation_matrix(histories) if len(histories) > 1 else None
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Error al descargar datos: {exc}"}), 502

    corr_payload = None
    if corr is not None:
        corr_payload = {
            "labels": list(corr.columns),
            "matrix": [[_clean(v) for v in row] for row in corr.values.tolist()],
        }

    return jsonify(
        {
            "summary": _records(summary),
            "stats": _records(stats),
            "corr": corr_payload,
            "histories": {name: _history_records(df) for name, df in histories.items()},
        }
    )


@app.route("/api/portfolio", methods=["POST"])
@login_required
def api_portfolio():
    payload = request.get_json(silent=True) or {}
    holdings_input = payload.get("holdings") or []

    if not holdings_input:
        return jsonify({"error": "Añade al menos una posición con importe invertido y fecha."}), 400

    symbols = {h.get("symbol") for h in holdings_input if h.get("symbol")}
    symbols.add(BENCHMARK_SYMBOL)

    closes = {}
    unconverted = []
    try:
        for symbol in symbols:
            close, converted = fetch_full_close_in_base(symbol)
            closes[symbol] = close
            if not converted:
                unconverted.append(symbol)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Error al descargar datos: {exc}"}), 502

    benchmark_close = closes.get(BENCHMARK_SYMBOL)
    result = compute_portfolio(holdings_input, closes, benchmark_close, BENCHMARK_NAME)

    if result is None:
        return jsonify({"error": "No se pudo calcular ninguna posición (revisa importes y fechas)."}), 400

    result["base_currency"] = BASE_CURRENCY
    result["currency_warnings"] = unconverted
    return jsonify(_clean_deep(result))


@app.route("/api/portfolio/holdings", methods=["GET"])
@login_required
def api_get_holdings():
    try:
        return jsonify(db.load_holdings())
    except db.DatabaseNotConfigured:
        return jsonify({"error": "El servidor no tiene configurada la base de datos (DATABASE_URL)."}), 503


@app.route("/api/portfolio/holdings", methods=["PUT"])
@login_required
def api_save_holdings():
    payload = request.get_json(silent=True) or {}
    holdings = payload.get("holdings")
    if not isinstance(holdings, list):
        return jsonify({"error": "Formato inválido: se esperaba una lista de posiciones."}), 400

    for h in holdings:
        if not h.get("name") or not h.get("symbol") or not h.get("date"):
            return jsonify({"error": "Cada posición necesita nombre, símbolo y fecha."}), 400
        try:
            h["invested"] = float(h.get("invested"))
        except (TypeError, ValueError):
            return jsonify({"error": "El importe invertido debe ser numérico."}), 400
        if h["invested"] <= 0:
            return jsonify({"error": "El importe invertido debe ser mayor que 0."}), 400

    try:
        db.save_holdings(holdings)
    except db.DatabaseNotConfigured:
        return jsonify({"error": "El servidor no tiene configurada la base de datos (DATABASE_URL)."}), 503

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=not os.environ.get("PORT"), host="0.0.0.0", port=port)
