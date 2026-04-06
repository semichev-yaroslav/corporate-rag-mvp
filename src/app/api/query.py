from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import QueryRequest, QueryResponse
from app.services.query_service import PermissionDeniedError, QueryService
from app.services.runtime import get_query_service

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    payload: QueryRequest,
    service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    try:
        return await service.handle_query(payload)
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
