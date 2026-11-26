"""Acesso ao PostgreSQL, compartilhado pela API e pelo worker."""
import os
from pathlib import Path


def connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row, connect_timeout=5)


def initialize():
    with connect() as conn:
        conn.execute(Path(__file__).with_name('schema.sql').read_text())


def health():
    with connect() as conn:
        conn.execute('SELECT 1').fetchone()


def list_sites():
    with connect() as conn:
        return conn.execute('''
            SELECT s.id, s.name, s.url, s.created_at,
                   c.online, c.status_code, c.latency_ms, c.checked_at, c.error,
                   stats.total, stats.successes
            FROM sites s
            LEFT JOIN LATERAL (
                SELECT * FROM checks WHERE site_id = s.id
                ORDER BY checked_at DESC, id DESC LIMIT 1
            ) c ON true
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE online) AS successes
                FROM checks WHERE site_id = s.id
            ) stats ON true
            ORDER BY s.id
        ''').fetchall()


def create_site(name, url):
    with connect() as conn:
        return conn.execute('''INSERT INTO sites (name, url) VALUES (%s, %s)
            ON CONFLICT (url) DO NOTHING RETURNING id, name, url''', (name, url)).fetchone()


def delete_site(site_id):
    with connect() as conn:
        return conn.execute('DELETE FROM sites WHERE id = %s', (site_id,)).rowcount > 0


def history(site_id):
    with connect() as conn:
        if not conn.execute('SELECT id FROM sites WHERE id = %s', (site_id,)).fetchone():
            return None
        return conn.execute('''SELECT checked_at, online, status_code, latency_ms, error
            FROM checks WHERE site_id = %s ORDER BY checked_at DESC, id DESC LIMIT 50''',
            (site_id,)).fetchall()


def targets():
    with connect() as conn:
        return conn.execute('SELECT id, url FROM sites ORDER BY id').fetchall()


def save_check(site_id, result):
    # INSERT ... SELECT evita erro caso o monitor tenha sido excluído antes da gravação.
    with connect() as conn:
        conn.execute('''INSERT INTO checks (site_id, online, status_code, latency_ms, error)
            SELECT id, %s, %s, %s, %s FROM sites WHERE id = %s''',
            (result.online, result.status_code, result.latency_ms, result.error, site_id))
