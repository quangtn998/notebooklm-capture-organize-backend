from __future__ import annotations

import json
import sqlite3
from typing import Optional

from .database import row_to_dict
def list_folders(connection: sqlite3.Connection, user_id: int, page: int = 1, limit: int = 2000) -> list[dict]:
    offset = max(page - 1, 0) * max(limit, 1)
    rows = connection.execute(
        """
        SELECT * FROM folders
        WHERE user_id = ?
        ORDER BY title COLLATE NOCASE
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]
def create_folder(connection: sqlite3.Connection, user_id: int, title: str, parent_folder_id: Optional[int]) -> dict:
    cursor = connection.execute(
        "INSERT INTO folders (user_id, title, parent_folder_id) VALUES (?, ?, ?)",
        (user_id, title, parent_folder_id),
    )
    connection.commit()
    return get_folder(connection, user_id, cursor.lastrowid)
def get_folder(connection: sqlite3.Connection, user_id: int, folder_id: int) -> Optional[dict]:
    row = connection.execute(
        "SELECT * FROM folders WHERE id = ? AND user_id = ?",
        (folder_id, user_id),
    ).fetchone()
    return row_to_dict(row)
def update_folder_title(connection: sqlite3.Connection, user_id: int, folder_id: int, title: str) -> Optional[dict]:
    connection.execute(
        "UPDATE folders SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
        (title, folder_id, user_id),
    )
    connection.commit()
    return get_folder(connection, user_id, folder_id)
def update_folder_parent(connection: sqlite3.Connection, user_id: int, folder_id: int, parent_folder_id: Optional[int]) -> Optional[dict]:
    connection.execute(
        """
        UPDATE folders
        SET parent_folder_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (parent_folder_id, folder_id, user_id),
    )
    connection.commit()
    return get_folder(connection, user_id, folder_id)
def delete_folder(connection: sqlite3.Connection, user_id: int, folder_id: int) -> bool:
    connection.execute("UPDATE notebooks SET folder_id = NULL WHERE folder_id = ? AND user_id = ?", (folder_id, user_id))
    cursor = connection.execute("DELETE FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id))
    connection.commit()
    return cursor.rowcount > 0
def list_notebooks(
    connection: sqlite3.Connection,
    user_id: int,
    folder_id: Optional[int] = None,
    page: int = 1,
    limit: int = 2000,
) -> list[dict]:
    offset = max(page - 1, 0) * max(limit, 1)
    if folder_id is None:
        query = """
        SELECT * FROM notebooks
        WHERE user_id = ?
        ORDER BY updated_at DESC, title COLLATE NOCASE
        LIMIT ? OFFSET ?
        """
        params = (user_id, limit, offset)
    else:
        query = """
        SELECT * FROM notebooks
        WHERE user_id = ? AND folder_id = ?
        ORDER BY updated_at DESC, title COLLATE NOCASE
        LIMIT ? OFFSET ?
        """
        params = (user_id, folder_id, limit, offset)
    rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
def get_notebook(connection: sqlite3.Connection, user_id: int, notebook_id: int) -> Optional[dict]:
    row = connection.execute("SELECT * FROM notebooks WHERE id = ? AND user_id = ?", (notebook_id, user_id)).fetchone()
    return row_to_dict(row)
def get_notebook_by_external_id(connection: sqlite3.Connection, user_id: int, external_id: str) -> Optional[dict]:
    row = connection.execute(
        "SELECT * FROM notebooks WHERE external_id = ? AND user_id = ?",
        (external_id, user_id),
    ).fetchone()
    return row_to_dict(row)
def upsert_notebook(connection: sqlite3.Connection, user_id: int, payload: dict) -> dict:
    existing = get_notebook_by_external_id(connection, user_id, payload["external_id"])
    values = (payload["title"], payload.get("folder_id"), payload.get("emoji"), payload.get("source_count", 0), user_id, payload["external_id"])
    if existing:
        connection.execute(
            """
            UPDATE notebooks
            SET title = ?, folder_id = ?, emoji = ?, source_count = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND external_id = ?
            """,
            values,
        )
    else:
        connection.execute(
            """
            INSERT INTO notebooks (title, folder_id, emoji, source_count, user_id, external_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            values,
        )
    connection.commit()
    return get_notebook_by_external_id(connection, user_id, payload["external_id"])
def update_notebook_folder(connection: sqlite3.Connection, user_id: int, external_id: str, folder_id: Optional[int]) -> Optional[dict]:
    connection.execute(
        "UPDATE notebooks SET folder_id = ?, updated_at = CURRENT_TIMESTAMP WHERE external_id = ? AND user_id = ?",
        (folder_id, external_id, user_id),
    )
    connection.commit()
    return get_notebook_by_external_id(connection, user_id, external_id)
def bulk_update_notebook_folder(connection: sqlite3.Connection, user_id: int, external_ids: list[str], folder_id: Optional[int]) -> int:
    if not external_ids:
        return 0
    placeholders = ",".join("?" for _ in external_ids)
    cursor = connection.execute(
        f"UPDATE notebooks SET folder_id = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND external_id IN ({placeholders})",
        [folder_id, user_id, *external_ids],
    )
    connection.commit()
    return cursor.rowcount
def get_existing_notebook_external_ids(connection: sqlite3.Connection, user_id: int, external_ids: list[str]) -> set[str]:
    if not external_ids:
        return set()
    placeholders = ",".join("?" for _ in external_ids)
    rows = connection.execute(
        f"SELECT external_id FROM notebooks WHERE user_id = ? AND external_id IN ({placeholders})",
        [user_id, *external_ids],
    ).fetchall()
    return {row["external_id"] for row in rows}
def delete_notebook_by_id(connection: sqlite3.Connection, user_id: int, notebook_id: int) -> bool:
    cursor = connection.execute("DELETE FROM notebooks WHERE id = ? AND user_id = ?", (notebook_id, user_id))
    connection.commit()
    return cursor.rowcount > 0
def delete_notebook_by_external_id(connection: sqlite3.Connection, user_id: int, external_id: str) -> bool:
    cursor = connection.execute("DELETE FROM notebooks WHERE external_id = ? AND user_id = ?", (external_id, user_id))
    connection.commit()
    return cursor.rowcount > 0
def list_captures(connection: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM captures WHERE user_id = ? ORDER BY created_at DESC, id DESC",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]
def create_capture(connection: sqlite3.Connection, user_id: int, payload: dict) -> dict:
    cursor = connection.execute(
        """
        INSERT INTO captures (user_id, notebook_external_id, title, source_url, source_type, note, raw_payload)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            payload.get("notebook_external_id"),
            payload["title"],
            payload.get("source_url"),
            payload["source_type"],
            payload.get("note"),
            json.dumps(payload.get("raw_payload")) if payload.get("raw_payload") is not None else None,
        ),
    )
    connection.commit()
    row = connection.execute("SELECT * FROM captures WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row)
