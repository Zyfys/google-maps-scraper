import sqlite3
import json
import csv
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "results.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                name TEXT,
                rating REAL,
                reviews_count INTEGER,
                address TEXT,
                phone TEXT,
                website TEXT,
                latitude REAL,
                longitude REAL,
                categories TEXT,
                google_maps_url TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrape_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queries TEXT,
                status TEXT DEFAULT 'pending',
                total_found INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                finished_at TEXT
            )
        """)
        conn.commit()
    logger.info(f"DB initialized: {DB_PATH}")


def save_places(places: list):
    if not places:
        return 0
    with get_conn() as conn:
        for p in places:
            conn.execute("""
                INSERT INTO places (query, name, rating, reviews_count, address, phone, website,
                                    latitude, longitude, categories, google_maps_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.get("query"),
                p.get("name"),
                p.get("rating"),
                p.get("reviews_count"),
                p.get("address"),
                p.get("phone"),
                p.get("website"),
                p.get("latitude"),
                p.get("longitude"),
                json.dumps(p.get("categories"), ensure_ascii=False) if p.get("categories") else None,
                p.get("google_maps_url"),
            ))
        conn.commit()
    return len(places)


def get_all_places(limit: int = 1000, offset: int = 0):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM places ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    return [dict(r) for r in rows]


def export_csv(filepath: str = "results.csv"):
    places = get_all_places(limit=100000)
    if not places:
        return 0
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=places[0].keys())
        writer.writeheader()
        writer.writerows(places)
    return len(places)


def create_job(queries: list) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO scrape_jobs (queries, status) VALUES (?, 'running')",
            (json.dumps(queries, ensure_ascii=False),)
        )
        conn.commit()
        return cur.lastrowid


def finish_job(job_id: int, total: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE scrape_jobs SET status='done', total_found=?, finished_at=datetime('now') WHERE id=?",
            (total, job_id)
        )
        conn.commit()


def get_jobs():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM scrape_jobs ORDER BY created_at DESC LIMIT 20").fetchall()
    return [dict(r) for r in rows]
