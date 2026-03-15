from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field


def coerce_optional_int(value: Optional[Union[int, str]]) -> Optional[int]:
    if value in (None, "", "0", 0):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class FolderCreatePayload(BaseModel):
    Title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    FolderTitle: Optional[str] = Field(default=None, min_length=1, max_length=255)
    ParentFolderID: Optional[Union[int, str]] = None
    FolderType: Optional[Union[int, str]] = None

    def get_title(self) -> str:
        return (self.Title or self.FolderTitle or "").strip()

    def get_parent_folder_id(self) -> Optional[int]:
        return coerce_optional_int(self.ParentFolderID)


class FolderParentUpdatePayload(BaseModel):
    FolderID: Union[int, str]
    ParentFolderID: Optional[Union[int, str]] = None
    FolderParentID: Optional[Union[int, str]] = None

    def get_folder_id(self) -> Optional[int]:
        return coerce_optional_int(self.FolderID)

    def get_parent_folder_id(self) -> Optional[int]:
        return coerce_optional_int(self.FolderParentID if self.FolderParentID is not None else self.ParentFolderID)


class FolderTitleUpdatePayload(BaseModel):
    FolderID: Union[int, str]
    Title: str = Field(min_length=1, max_length=255)

    def get_folder_id(self) -> Optional[int]:
        return coerce_optional_int(self.FolderID)


class NotebookUpsertPayload(BaseModel):
    NotebookID: Optional[str] = Field(default=None, min_length=1, max_length=255)
    ExternalID: Optional[str] = Field(default=None, min_length=1, max_length=255)
    Title: str = Field(min_length=1, max_length=255)
    FolderID: Optional[Union[int, str]] = None
    Emoji: Optional[str] = None
    SourceCount: int = 0

    def get_external_id(self) -> str:
        return (self.ExternalID or self.NotebookID or "").strip()

    def get_folder_id(self) -> Optional[int]:
        return coerce_optional_int(self.FolderID)


class NotebookFolderUpdatePayload(BaseModel):
    NotebookID: Optional[str] = Field(default=None, min_length=1, max_length=255)
    ExternalID: Optional[str] = Field(default=None, min_length=1, max_length=255)
    FolderID: Optional[Union[int, str]] = None

    def get_external_id(self) -> str:
        return (self.ExternalID or self.NotebookID or "").strip()

    def get_folder_id(self) -> Optional[int]:
        return coerce_optional_int(self.FolderID)


class NotebookBulkFolderUpdatePayload(BaseModel):
    NotebookIDs: Optional[list[str]] = None
    ExternalIDs: Optional[list[str]] = None
    FolderID: Optional[Union[int, str]] = None

    def get_external_ids(self) -> list[str]:
        return [value for value in (self.ExternalIDs or self.NotebookIDs or []) if value]

    def get_folder_id(self) -> Optional[int]:
        return coerce_optional_int(self.FolderID)


class AuthCredentialsPayload(BaseModel):
    Email: str
    Password: str
    LongSession: Optional[int] = 0

    def normalized_email(self) -> str:
        return self.Email.strip().lower()


class PasswordUpdatePayload(BaseModel):
    OldPassword: str
    NewPassword: str


class ForgotPasswordPayload(BaseModel):
    Username: str


class ResetPasswordPayload(BaseModel):
    ResetCode: str
    NewPassword: str


class ProviderLoginPayload(BaseModel):
    Provider: Optional[str] = None
    Code: Optional[str] = None
    Token: Optional[str] = None


class CaptureCreatePayload(BaseModel):
    NotebookID: Optional[str] = None
    Title: str = Field(min_length=1, max_length=255)
    SourceURL: Optional[str] = None
    SourceType: str = Field(min_length=1, max_length=64)
    Note: Optional[str] = None
    RawPayload: Optional[Union[dict[str, Any], list[Any], str]] = None
