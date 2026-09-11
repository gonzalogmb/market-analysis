"""Persistencia de la cartera en Postgres (Neon/Supabase u otro proveedor compatible), a través
de la variable de entorno DATABASE_URL. Al ser una app de un único usuario no hay tabla de
usuarios. La cartera se guarda como un historial de movimientos (aportaciones y retiradas) por
instrumento en `portfolio_transactions`, no como una única compra por fondo. Cada movimiento se
guarda en participaciones (`units`), no en euros: `amount` se conserva solo como euros históricos
de movimientos antiguos que ya no se usan para el cálculo."""

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
    """Crea las tablas si no existen. No hace nada (ni falla) si DATABASE_URL no está
    configurada, para que el resto de la app siga funcionando sin cartera.

    (La migración one-off del modelo antiguo —una compra por fondo, tabla `portfolio_holdings`—
    al histórico de movimientos actual ya se ejecutó y esa tabla ya no existe. Se quitó el código
    de migración de aquí a propósito: no aporta nada una vez hecha, y cada arranque que lo
    ejecutaba innecesariamente era la única sospechosa razonable de un vaciado de datos que no
    pudimos explicar de otro modo.)"""
    if not DATABASE_URL:
        return
    with _cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_transactions (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                amount DOUBLE PRECISION,
                units DOUBLE PRECISION,
                transaction_date DATE NOT NULL
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


def load_transactions() -> list[dict]:
    with _cursor() as cur:
        cur.execute(
            "SELECT id, name, symbol, units, amount, transaction_date FROM portfolio_transactions "
            "ORDER BY name, transaction_date"
        )
        rows = cur.fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "symbol": row["symbol"],
            "units": float(row["units"]) if row["units"] is not None else None,
            "amount": float(row["amount"]) if row["amount"] is not None else None,
            "date": row["transaction_date"].isoformat(),
        }
        for row in rows
    ]


def add_transaction(name: str, symbol: str, units: float, date: str) -> dict:
    with _cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO portfolio_transactions (name, symbol, units, transaction_date) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (name, symbol, units, date),
        )
        new_id = cur.fetchone()["id"]
    return {"id": new_id, "name": name, "symbol": symbol, "units": units, "amount": None, "date": date}


def delete_transaction(transaction_id: int) -> None:
    with _cursor(commit=True) as cur:
        cur.execute("DELETE FROM portfolio_transactions WHERE id = %s", (transaction_id,))


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
