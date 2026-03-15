from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import uuid
from typing import Optional

from .database import row_to_dict


def upsert_google_user(
    connection: sqlite3.Connection,
    *,
    google_sub: str,
    email: str,
    name: Optional[str],
    picture_url: Optional[str],
) -> dict:
    normalized_email = email.strip().lower()
    existing = connection.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
    if existing:
        connection.execute(
            """
            UPDATE users
            SET email = ?, name = ?, picture_url = ?,
                auth_provider = CASE WHEN password_hash IS NOT NULL THEN 'hybrid' ELSE 'google' END,
                updated_at = CURRENT_TIMESTAMP
            WHERE google_sub = ?
            """,
            (normalized_email, name, picture_url, google_sub),
        )
    else:
        existing_email = get_user_by_email(connection, normalized_email)
        if existing_email:
            connection.execute(
                """
                UPDATE users
                SET google_sub = ?, email = ?, name = ?, picture_url = ?,
                    auth_provider = CASE WHEN password_hash IS NOT NULL THEN 'hybrid' ELSE 'google' END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (google_sub, normalized_email, name, picture_url, existing_email["id"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO users (google_sub, email, name, picture_url, auth_provider)
                VALUES (?, ?, ?, ?, 'google')
                """,
                (google_sub, normalized_email, name, picture_url),
            )
    connection.commit()
    return get_user_by_google_sub(connection, google_sub)


def get_user_by_id(connection: sqlite3.Connection, user_id: int) -> Optional[dict]:
    return row_to_dict(connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


def get_user_by_email(connection: sqlite3.Connection, email: str) -> Optional[dict]:
    normalized_email = email.strip().lower()
    row = connection.execute("SELECT * FROM users WHERE email = ?", (normalized_email,)).fetchone()
    return row_to_dict(row)


def get_user_by_google_sub(connection: sqlite3.Connection, google_sub: str) -> dict:
    row = connection.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
    return row_to_dict(row)


def create_password_user(connection: sqlite3.Connection, email: str, password: str) -> tuple[Optional[dict], Optional[str]]:
    normalized_email = email.strip().lower()
    existing = get_user_by_email(connection, normalized_email)
    password_hash = hash_password(password)
    if existing:
        if existing.get("password_hash"):
            return None, "Account already exists for this email."
        auth_provider = "hybrid" if not existing["google_sub"].startswith("local:") else "password"
        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, auth_provider = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (password_hash, auth_provider, existing["id"]),
        )
        connection.commit()
        return get_user_by_id(connection, existing["id"]), None
    cursor = connection.execute(
        """
        INSERT INTO users (google_sub, email, password_hash, auth_provider)
        VALUES (?, ?, ?, 'password')
        """,
        (f"local:{uuid.uuid4().hex}", normalized_email, password_hash),
    )
    connection.commit()
    return get_user_by_id(connection, cursor.lastrowid), None


def authenticate_password_user(connection: sqlite3.Connection, email: str, password: str) -> Optional[dict]:
    user = get_user_by_email(connection, email)
    if not user or not user.get("password_hash"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def update_user_password(connection: sqlite3.Connection, user_id: int, old_password: str, new_password: str) -> bool:
    user = get_user_by_id(connection, user_id)
    if not user:
        return False
    current_hash = user.get("password_hash")
    if current_hash and not verify_password(old_password, current_hash):
        return False
    auth_provider = "hybrid" if not user["google_sub"].startswith("local:") else "password"
    connection.execute(
        """
        UPDATE users
        SET password_hash = ?, auth_provider = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (hash_password(new_password), auth_provider, user_id),
    )
    connection.commit()
    return True


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return "pbkdf2:sha256:600000:{salt}:{digest}".format(salt=salt.hex(), digest=digest.hex())


def verify_password(password: str, encoded_password: str) -> bool:
    try:
        algorithm, hash_name, iterations, salt_hex, digest_hex = encoded_password.split(":")
    except ValueError:
        return False
    if algorithm != "pbkdf2":
        return False
    derived = hashlib.pbkdf2_hmac(
        hash_name,
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
        dklen=len(bytes.fromhex(digest_hex)),
    )
    return hmac.compare_digest(derived.hex(), digest_hex)
