import psycopg2
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


@dataclass
class URL:
    name: str
    created_at: Optional[str]
    id: Optional[int] = None


@dataclass
class URLCheck:
    status_code: int
    h1: Optional[str]
    title: Optional[str]
    description: Optional[str]
    created_at: Optional[str] = None
    id: Optional[int] = None
    url_id: Optional[int] = None


def get_connection():
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=DictCursor
    )
    return conn


def commit(conn):
    conn.commit()


def add_url(conn, name):
    with conn.cursor() as cur:
        created_at = datetime.now().strftime('%Y-%m-%d')
        cur.execute(
            'INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id;',
            (name, created_at)
        )
        return cur.fetchone()[0]


def get_url_by_name(conn, name):
    with conn.cursor() as cur:
        cur.execute('SELECT id FROM urls WHERE name = %s;', (name,))
        row = cur.fetchone()
        if row:
            return URL(**row)
        return None


def get_url(conn, id):
    with conn.cursor() as cur:
        cur.execute('SELECT * FROM urls WHERE id = %s;', (id,))
        row = cur.fetchone()
        if row:
            return URL(**row)
        return None


def get_all_urls(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT u.id, u.name, url_checks.created_at, url_checks.status_code
            FROM urls AS u
            LEFT JOIN url_checks ON url_checks.id = (
                SELECT id FROM url_checks
                WHERE url_checks.url_id = u.id
                ORDER BY created_at DESC
                LIMIT 1
            )
            ORDER BY u.id DESC;
        """)
        return cur.fetchall()


def add_check(conn, check):
    with conn.cursor() as cur:
        created_at = datetime.now().strftime('%Y-%m-%d')
        cur.execute("""
            INSERT INTO url_checks
            (url_id, status_code, h1, title, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (
            check.url_id,
            check.status_code,
            check.h1,
            check.title,
            check.description,
            created_at
        )
        )


def get_checks(conn, url_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, status_code, h1, title, description, created_at
            FROM url_checks WHERE url_id = %s
            ORDER BY created_at DESC;
        """, (url_id,)
        )
        checks = [URLCheck(**row) for row in cur.fetchall()]
        return checks
