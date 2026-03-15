from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS backend_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  google_sub TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  auth_provider TEXT NOT NULL DEFAULT 'google',
  name TEXT,
  picture_url TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS folders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  parent_folder_id INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(parent_folder_id) REFERENCES folders(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notebooks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  external_id TEXT NOT NULL,
  title TEXT NOT NULL,
  folder_id INTEGER,
  emoji TEXT,
  source_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, external_id),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS captures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  notebook_external_id TEXT,
  title TEXT NOT NULL,
  source_url TEXT,
  source_type TEXT NOT NULL,
  note TEXT,
  raw_payload TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS support_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  subject TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL DEFAULT 'open'
);

CREATE INDEX IF NOT EXISTS idx_folders_user_id_title ON folders(user_id, title);
CREATE INDEX IF NOT EXISTS idx_notebooks_user_id_updated_at ON notebooks(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_notebooks_user_id_folder_id ON notebooks(user_id, folder_id);
CREATE INDEX IF NOT EXISTS idx_captures_user_id_created_at ON captures(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_requests_created_at ON support_requests(created_at DESC);
"""


USER_SCHEMA_COLUMNS = {
    "google_sub": "TEXT UNIQUE NOT NULL",
    "email": "TEXT UNIQUE NOT NULL",
    "password_hash": "TEXT",
    "auth_provider": "TEXT NOT NULL DEFAULT 'google'",
    "name": "TEXT",
    "picture_url": "TEXT",
    "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
}


def open_connection(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    connection = open_connection(database_path)
    try:
        connection.executescript(SCHEMA)
        _migrate_users_table(connection)
        connection.execute(
            """
            INSERT INTO backend_meta (key, value)
            VALUES ('schema_version', '3')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """
        )
        connection.commit()
    finally:
        connection.close()


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(row) if row is not None else None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> dict:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"]: dict(row) for row in rows}


def _migrate_users_table(connection: sqlite3.Connection) -> None:
    columns = _table_columns(connection, "users")
    if not columns:
        return
    for column_name, definition in USER_SCHEMA_COLUMNS.items():
        if column_name in columns:
            continue
        connection.execute(f"ALTER TABLE users ADD COLUMN {column_name} {definition}")
    connection.execute(
        """
        UPDATE users
        SET auth_provider = CASE
            WHEN password_hash IS NOT NULL AND google_sub NOT LIKE 'local:%' THEN 'hybrid'
            WHEN password_hash IS NOT NULL THEN 'password'
            ELSE 'google'
        END
        WHERE auth_provider IS NULL OR auth_provider = ''
        """
    )
