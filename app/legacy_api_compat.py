from __future__ import annotations

from typing import Optional

from fastapi import Request


def serialize_folder(folder: Optional[dict]) -> Optional[dict]:
    if not folder:
        return None
    return {
        "ID": str(folder["id"]),
        "Title": folder["title"],
        "ParentFolderID": "" if folder["parent_folder_id"] is None else str(folder["parent_folder_id"]),
        "CreatedAt": folder["created_at"],
        "UpdatedAt": folder["updated_at"],
    }


def serialize_notebook(notebook: Optional[dict]) -> Optional[dict]:
    if not notebook:
        return None
    return {
        "ID": str(notebook["id"]),
        "ExternalID": notebook["external_id"],
        "Title": notebook["title"],
        "FolderID": "" if notebook["folder_id"] is None else str(notebook["folder_id"]),
        "Emoji": notebook["emoji"] or "",
        "SourceCount": notebook["source_count"] or 0,
        "CreatedAt": notebook["created_at"],
        "UpdatedAt": notebook["updated_at"],
    }


def read_positive_int(request: Request, key: str, default: int) -> int:
    raw_value = request.query_params.get(key)
    if raw_value in (None, ""):
        return default
    try:
        return max(1, int(raw_value))
    except ValueError:
        return default


def read_optional_folder_id(request: Request, key: str = "FolderID") -> Optional[int]:
    raw_value = request.query_params.get(key)
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None
