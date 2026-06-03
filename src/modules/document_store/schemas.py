from datetime import datetime

from pydantic import Field

from src.shared.enums import ArtifactType
from src.shared.types.common import APIModel


class CreateArtifactRequest(APIModel):
    deal_id: str | None = None
    artifact_type: ArtifactType
    file_name: str = Field(min_length=1)
    mime_type: str | None = None
    storage_uri: str = Field(min_length=1)
    checksum_sha256: str | None = None


class AddArtifactVersionRequest(APIModel):
    storage_uri: str = Field(min_length=1)
    checksum_sha256: str | None = None


class LinkArtifactRequest(APIModel):
    linked_object_type: str = Field(min_length=1)
    linked_object_ref: str = Field(min_length=1)


class ArtifactResponse(APIModel):
    artifact_ref: str
    deal_id: str | None
    artifact_type: ArtifactType
    file_name: str
    mime_type: str | None
    storage_uri: str
    checksum_sha256: str | None
    current_version: int
    created_at: datetime
    updated_at: datetime


class ArtifactVersionResponse(APIModel):
    artifact_ref: str
    version_no: int
    storage_uri: str
    checksum_sha256: str | None
    created_at: datetime


class ArtifactLinkResponse(APIModel):
    artifact_ref: str
    linked_object_type: str
    linked_object_ref: str
    created_at: datetime

