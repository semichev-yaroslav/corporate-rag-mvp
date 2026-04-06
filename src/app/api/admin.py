from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.schemas import DocumentSummary, HealthResponse, ReindexRequest, ReindexResponse
from app.services.admin_service import AdminService
from app.services.runtime import get_admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_operator(
    x_operator_id: str | None = Header(default=None, alias="X-Operator-Id"),
    settings: Settings = Depends(get_settings),
) -> str:
    if x_operator_id and x_operator_id in set(settings.operator_telegram_user_ids):
        return x_operator_id
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Оператор не авторизован.",
    )


@router.post("/reindex", response_model=ReindexResponse, dependencies=[Depends(require_operator)])
async def reindex_documents(
    payload: ReindexRequest,
    service: AdminService = Depends(get_admin_service),
) -> ReindexResponse:
    try:
        return await service.reindex_documents(payload)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.get("/documents", response_model=list[DocumentSummary], dependencies=[Depends(require_operator)])
async def list_documents(service: AdminService = Depends(get_admin_service)) -> list[DocumentSummary]:
    return await service.list_documents()


@router.get("/health", response_model=HealthResponse, dependencies=[Depends(require_operator)])
async def health(service: AdminService = Depends(get_admin_service)) -> HealthResponse:
    return await service.health()
