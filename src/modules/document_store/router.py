from fastapi import APIRouter, status

from src.modules.document_store.schemas import (
    AddArtifactVersionRequest,
    ArtifactLinkResponse,
    ArtifactResponse,
    ArtifactVersionResponse,
    CreateArtifactRequest,
    LinkArtifactRequest,
)
from src.modules.document_store.service import (
    add_artifact_version,
    create_artifact,
    get_artifact,
    link_artifact,
    list_artifact_versions,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["artifacts"])


@router.post("/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
def create_artifact_route(payload: CreateArtifactRequest, session: DBSession) -> ArtifactResponse:
    return ArtifactResponse.model_validate(create_artifact(session, payload))


@router.post("/artifacts/{artifact_ref}/versions", response_model=ArtifactVersionResponse, status_code=status.HTTP_201_CREATED)
def add_artifact_version_route(
    artifact_ref: str,
    payload: AddArtifactVersionRequest,
    session: DBSession,
) -> ArtifactVersionResponse:
    return ArtifactVersionResponse.model_validate(add_artifact_version(session, artifact_ref, payload))


@router.get("/artifacts/{artifact_ref}", response_model=ArtifactResponse)
def get_artifact_route(artifact_ref: str, session: DBSession) -> ArtifactResponse:
    return ArtifactResponse.model_validate(get_artifact(session, artifact_ref))


@router.get("/artifacts/{artifact_ref}/versions", response_model=list[ArtifactVersionResponse])
def get_artifact_versions_route(artifact_ref: str, session: DBSession) -> list[ArtifactVersionResponse]:
    return [ArtifactVersionResponse.model_validate(item) for item in list_artifact_versions(session, artifact_ref)]


@router.post("/artifacts/{artifact_ref}/links", response_model=ArtifactLinkResponse, status_code=status.HTTP_201_CREATED)
def link_artifact_route(artifact_ref: str, payload: LinkArtifactRequest, session: DBSession) -> ArtifactLinkResponse:
    return ArtifactLinkResponse.model_validate(link_artifact(session, artifact_ref, payload))

