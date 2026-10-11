"""
Pydantic v2 schemas for repository management and members (§6.2 & §12).
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RepoSource(BaseModel):
    type: str = Field(description="'github' or 'upload'")
    url: str | None = None
    owner: str | None = None
    name: str | None = None
    ref: str | None = None
    default_branch: str | None = None
    is_private: bool = False
    upload_filename: str | None = None


class RepoStats(BaseModel):
    files_total: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    loc: int = 0
    symbols: int = 0
    chunks: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    redactions: int = 0


class RepoSettings(BaseModel):
    auto_review: bool = False
    extra_ignore_patterns: list[str] = Field(default_factory=list)


class RepoCreateGitHubRequest(BaseModel):
    url: str = Field(
        description="GitHub URL or shorthand 'owner/repo'",
        examples=["https://github.com/fastapi/fastapi", "pallets/flask"],
    )
    ref: str | None = Field(default=None, description="Optional branch, tag, or commit SHA")


class RepoResponse(BaseModel):
    id: str
    owner_id: str
    source: RepoSource
    display_name: str
    description: str
    commit_sha: str | None = None
    status: str
    status_message: str
    stats: RepoStats
    settings: RepoSettings
    last_indexed_at: datetime | str | None = None
    created_at: datetime | str
    updated_at: datetime | str


class RepoListResponse(BaseModel):
    items: list[RepoResponse]
    total: int


class RepoUpdateSettingsRequest(BaseModel):
    auto_review: bool | None = None
    extra_ignore_patterns: list[str] | None = None


class RepoMemberAddRequest(BaseModel):
    email: str
    role: str = Field(default="viewer", description="'viewer' | 'editor' | 'owner'")


class RepoMemberResponse(BaseModel):
    repo_id: str
    user_id: str
    email: str | None = None
    role: str
    added_by: str
    created_at: datetime | str


class SymbolResponse(BaseModel):
    name: str
    qualified_name: str
    kind: str
    signature: str
    docstring: str | None = None
    start_line: int
    end_line: int
    parent: str | None = None
    language: str
    exported: bool = True


class FileDetailResponse(BaseModel):
    path: str
    language: str
    size_bytes: int = 0
    loc: int = 0
    content: str
    symbols: list[SymbolResponse] = Field(default_factory=list)
    card: str = ""
    imports: list[str] = Field(default_factory=list)
    redaction_count: int = 0


class SkippedFileResponse(BaseModel):
    path: str
    reason: str
    size_bytes: int = 0


class RepoSyncRequest(BaseModel):
    ref: str | None = Field(default=None, description="Optional new ref to sync to")


class RepoSyncResponse(BaseModel):
    status: str
    commit_sha: str
    message: str
    added_files: int = 0
    changed_files: int = 0
    removed_files: int = 0
    total_files: int = 0
