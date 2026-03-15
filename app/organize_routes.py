from __future__ import annotations

from fastapi import APIRouter, Request

from .http_helpers import data_response, require_user
from .legacy_api_compat import read_optional_folder_id, read_positive_int, serialize_folder, serialize_notebook
from .organize_storage import (
    bulk_update_notebook_folder,
    create_capture,
    create_folder,
    delete_notebook_by_external_id,
    delete_notebook_by_id,
    delete_folder,
    get_existing_notebook_external_ids,
    get_notebook,
    get_notebook_by_external_id,
    list_captures,
    list_folders,
    list_notebooks,
    update_folder_parent,
    update_folder_title,
    update_notebook_folder,
    upsert_notebook,
)
from .schemas import (
    CaptureCreatePayload,
    FolderCreatePayload,
    FolderParentUpdatePayload,
    FolderTitleUpdatePayload,
    NotebookBulkFolderUpdatePayload,
    NotebookFolderUpdatePayload,
    NotebookUpsertPayload,
)


router = APIRouter(prefix="/rest/v1")


@router.get("/folders")
async def folders_index(request: Request) -> dict:
    user = require_user(request)
    page = read_positive_int(request, "Page", 1)
    limit = read_positive_int(request, "Limit", 2000)
    folders = list_folders(request.app.state.db, user["id"], page=page, limit=limit)
    return data_response({"Success": True, "Folders": [serialize_folder(folder) for folder in folders]})


@router.post("/folders")
async def folders_create(request: Request, payload: FolderCreatePayload) -> dict:
    user = require_user(request)
    title = payload.get_title()
    if not title:
        return data_response({"Success": False, "MsgCode": 1039})
    folder = create_folder(request.app.state.db, user["id"], title, payload.get_parent_folder_id())
    return data_response({"Success": True, "FolderID": str(folder["id"]), "Folder": serialize_folder(folder)})


@router.put("/folders/update-parent-id")
async def folders_update_parent(request: Request, payload: FolderParentUpdatePayload) -> dict:
    user = require_user(request)
    folder_id = payload.get_folder_id()
    parent_folder_id = payload.get_parent_folder_id()
    if folder_id is None:
        return data_response({"Success": False, "MsgCode": 1035})
    if folder_id == parent_folder_id:
        return data_response({"Success": False, "MsgCode": 1038})
    folder = update_folder_parent(request.app.state.db, user["id"], folder_id, parent_folder_id)
    return data_response({"Success": bool(folder), "Folder": serialize_folder(folder) if folder else None})


@router.put("/folders/update-title")
async def folders_update_title(request: Request, payload: FolderTitleUpdatePayload) -> dict:
    user = require_user(request)
    folder_id = payload.get_folder_id()
    if folder_id is None:
        return data_response({"Success": False, "MsgCode": 1035})
    folder = update_folder_title(request.app.state.db, user["id"], folder_id, payload.Title.strip())
    return data_response({"Success": bool(folder), "Folder": serialize_folder(folder) if folder else None})


@router.delete("/folders/by-id/{folder_id}")
async def folders_delete(request: Request, folder_id: int) -> dict:
    user = require_user(request)
    return data_response({"Success": delete_folder(request.app.state.db, user["id"], folder_id)})


@router.get("/notebooks")
async def notebooks_index(request: Request) -> dict:
    user = require_user(request)
    page = read_positive_int(request, "Page", 1)
    limit = read_positive_int(request, "Limit", 2000)
    folder_id = read_optional_folder_id(request)
    notebooks = list_notebooks(request.app.state.db, user["id"], folder_id=folder_id, page=page, limit=limit)
    return data_response({"Success": True, "Notebooks": [serialize_notebook(notebook) for notebook in notebooks]})


@router.get("/notebooks/by-id/{notebook_id}")
async def notebooks_show(request: Request, notebook_id: int) -> dict:
    user = require_user(request)
    notebook = get_notebook(request.app.state.db, user["id"], notebook_id)
    return data_response({"Success": True, "Notebook": serialize_notebook(notebook) if notebook else None})


@router.get("/notebooks/by-external-id/{external_id}")
async def notebooks_show_by_external_id(request: Request, external_id: str) -> dict:
    user = require_user(request)
    notebook = get_notebook_by_external_id(request.app.state.db, user["id"], external_id)
    return data_response({"Success": True, "Notebook": serialize_notebook(notebook) if notebook else None})


@router.post("/notebooks")
async def notebooks_upsert(request: Request, payload: NotebookUpsertPayload) -> dict:
    user = require_user(request)
    external_id = payload.get_external_id()
    if not external_id:
        return data_response({"Success": False, "MsgCode": 1041})
    notebook = upsert_notebook(
        request.app.state.db,
        user["id"],
        {
            "external_id": external_id,
            "title": payload.Title,
            "folder_id": payload.get_folder_id(),
            "emoji": payload.Emoji,
            "source_count": payload.SourceCount,
        },
    )
    return data_response({"Success": True, "Notebook": serialize_notebook(notebook), "NotebookID": str(notebook["id"])})


@router.put("/notebooks/update-folder")
async def notebooks_update_folder(request: Request, payload: NotebookFolderUpdatePayload) -> dict:
    user = require_user(request)
    external_id = payload.get_external_id()
    if not external_id:
        return data_response({"Success": False, "MsgCode": 1041})
    notebook = update_notebook_folder(request.app.state.db, user["id"], external_id, payload.get_folder_id())
    return data_response({"Success": bool(notebook), "Notebook": serialize_notebook(notebook) if notebook else None})


@router.put("/notebooks/bulk-update-folder")
@router.patch("/notebooks/bulk-update-folder")
async def notebooks_bulk_update_folder(request: Request, payload: NotebookBulkFolderUpdatePayload) -> dict:
    user = require_user(request)
    external_ids = payload.get_external_ids()
    existing_ids = get_existing_notebook_external_ids(request.app.state.db, user["id"], external_ids)
    affected = bulk_update_notebook_folder(request.app.state.db, user["id"], external_ids, payload.get_folder_id())
    results = [{"Success": external_id in existing_ids, "ExternalID": external_id} for external_id in external_ids]
    return data_response(
        {
            "Success": True,
            "UpdatedCount": affected,
            "FailedCount": max(len(external_ids) - affected, 0),
            "Results": results,
        }
    )


@router.delete("/notebooks/by-id/{notebook_id}")
async def notebooks_delete(request: Request, notebook_id: int) -> dict:
    user = require_user(request)
    return data_response({"Success": delete_notebook_by_id(request.app.state.db, user["id"], notebook_id)})


@router.delete("/notebooks/by-external-id/{external_id}")
async def notebooks_delete_by_external(request: Request, external_id: str) -> dict:
    user = require_user(request)
    return data_response({"Success": delete_notebook_by_external_id(request.app.state.db, user["id"], external_id)})


@router.get("/captures")
async def captures_index(request: Request) -> dict:
    user = require_user(request)
    return data_response({"Success": True, "Captures": list_captures(request.app.state.db, user["id"])})


@router.post("/captures")
async def captures_create(request: Request, payload: CaptureCreatePayload) -> dict:
    user = require_user(request)
    capture = create_capture(
        request.app.state.db,
        user["id"],
        {
            "notebook_external_id": payload.NotebookID,
            "title": payload.Title,
            "source_url": payload.SourceURL,
            "source_type": payload.SourceType,
            "note": payload.Note,
            "raw_payload": payload.RawPayload,
        },
    )
    return data_response({"Success": True, "Capture": capture})
