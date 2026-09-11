"""Persistencia de la cartera en Postgres (Neon/Supabase u otro proveedor compatible), a través
de la variable de entorno DATABASE_URL. Al ser una app de un único usuario no hay tabla de
usuarios: la tabla `portfolio_holdings` reemplaza por completo su contenido en cada guardado."""

import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

MAX_LOGIN_ATTEMPTS = 3
LOGIN_LOCKOUT_WINDOW = timedelta(hours=5)


class DatabaseNotConfigured(RuntimeError):
    pass


@contextmanager
def _cursor(commit=False):
    if not DATABASE_URL:
        raise DatabaseNotConfigured("Falta la variable de entorno DATABASE_URL.")
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db():
    """Crea la tabla si no existe. No hace nada (ni falla) si DATABASE_URL no está configurada,
    para que el resto de la app (datos de mercado) siga funcionando sin persistencia de cartera."""
    if not DATABASE_URL:
        return
    with _cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                name TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                invested DOUBLE PRECISION NOT NULL,
                purchase_date DATE NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS login_attempts (
                ip TEXT PRIMARY KEY,
                failed_count INTEGER NOT NULL,
                first_failed_at TIMESTAMPTZ NOT NULL
            )
            """
        )


def load_holdings() -> list[dict]:
    with _cursor() as cur:
        cur.execute("SELECT name, symbol, invested, purchase_date FROM portfolio_holdings ORDER BY name")
        rows = cur.fetchall()
    return [
        {
            "name": row["name"],
            "symbol": row["symbol"],
            "invested": float(row["invested"]),
            "date": row["purchase_date"].isoformat(),
        }
        for row in rows
    ]


def save_holdings(holdings: list[dict]) -> None:
    """Reemplaza el contenido completo de la tabla por `holdings` (name, symbol, invested, date)."""
    with _cursor(commit=True) as cur:
        cur.execute("DELETE FROM portfolio_holdings")
        for h in holdings:
            cur.execute(
                "INSERT INTO portfolio_holdings (name, symbol, invested, purchase_date) VALUES (%s, %s, %s, %s)",
                (h["name"], h["symbol"], h["invested"], h["date"]),
            )


def is_locked_out(ip: str) -> tuple[bool, int]:
    """(bloqueado, segundos_restantes). Si DATABASE_URL no está configurada, nunca bloquea."""
    if not DATABASE_URL:
        return False, 0
    with _cursor() as cur:
        cur.execute("SELECT failed_count, first_failed_at FROM login_attempts WHERE ip = %s", (ip,))
        row = cur.fetchone()
    if not row or row["failed_count"] < MAX_LOGIN_ATTEMPTS:
        return False, 0
    elapsed = datetime.now(timezone.utc) - row["first_failed_at"]
    if elapsed >= LOGIN_LOCKOUT_WINDOW:
        return False, 0
    return True, int((LOGIN_LOCKOUT_WINDOW - elapsed).total_seconds())


def record_failed_login(ip: str) -> None:
    if not DATABASE_URL:
        return
    now = datetime.now(timezone.utc)
    with _cursor(commit=True) as cur:
        cur.execute("SELECT first_failed_at FROM login_attempts WHERE ip = %s", (ip,))
        row = cur.fetchone()
        if not row or (now - row["first_failed_at"]) >= LOGIN_LOCKOUT_WINDOW:
            cur.execute(
                """
                INSERT INTO login_attempts (ip, failed_count, first_failed_at) VALUES (%s, 1, %s)
                ON CONFLICT (ip) DO UPDATE SET failed_count = 1, first_failed_at = EXCLUDED.first_failed_at
                """,
                (ip, now),
            )
        else:
            cur.execute("UPDATE login_attempts SET failed_count = failed_count + 1 WHERE ip = %s", (ip,))


def clear_failed_logins(ip: str) -> None:
    if not DATABASE_URL:
        return
    with _cursor(commit=True) as cur:
        cur.execute("DELETE FROM login_attempts WHERE ip = %s", (ip,))
