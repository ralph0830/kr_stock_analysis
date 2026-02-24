"""
API Key Management Routes

API Key 발급, 조회, 삭제
"""
import logging
from typing import List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.session import get_db_session
from src.database.models_api_key import APIKey
from src.middleware.api_key_auth import require_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/keys", tags=["admin"])


@router.post(
    "/create",
    summary="API Key 발급",
    description="새로운 API Key를 발급합니다.",
)
async def create_api_key(
    name: str,
    scope: str = "read",
    expires_days: int = 365,
    description: str = None,
    created_by: str = None,
    session: Session = Depends(get_db_session),
):
    """
    API Key 발급

    ## Parameters
    - **name**: 키 식별 이름
    - **scope**: 권한 레벨 (read, write, admin)
    - **expires_days**: 유효기간 (일)
    - **description**: 설명

    ## Example
    ```bash
    curl -X POST "http://localhost:5111/api/admin/keys/create?name=test_key&scope=read"
    ```
    """
    try:
        # 권한 검증
        if scope not in ["read", "write", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid scope. Must be 'read', 'write', or 'admin'",
            )

        # API Key 생성
        api_key = APIKey(
            key=APIKey.generate_key(),
            name=name,
            scope=scope,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
            created_by=created_by,
            description=description,
        )

        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        logger.info(f"API Key created: {api_key.name} ({api_key.scope})")

        return api_key.to_dict(include_key=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Key creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/list",
    summary="API Key 목록 조회",
    description="발급된 모든 API Key 목록을 반환합니다.",
)
async def list_api_keys(
    session: Session = Depends(get_db_session),
):
    """
    API Key 목록 조회

    ## Example
    ```bash
    curl "http://localhost:5111/api/admin/keys/list"
    ```
    """
    try:
        keys = session.query(APIKey).order_by(APIKey.created_at.desc()).all()

        return {
            "total": len(keys),
            "keys": [key.to_dict(include_key=False) for key in keys],
        }

    except Exception as e:
        logger.error(f"API Key list failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/{key_id}",
    summary="API Key 삭제",
    description="지정된 API Key를 삭제합니다.",
)
async def delete_api_key(
    key_id: int,
    session: Session = Depends(get_db_session),
):
    """
    API Key 삭제

    ## Example
    ```bash
    curl -X DELETE "http://localhost:5111/api/admin/keys/1"
    ```
    """
    try:
        api_key = session.query(APIKey).filter(APIKey.id == key_id).first()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key not found",
            )

        key_name = api_key.name
        session.delete(api_key)
        session.commit()

        logger.info(f"API Key deleted: {key_name} (ID: {key_id})")

        return {
            "status": "success",
            "message": f"API Key '{key_name}' deleted",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Key deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/{key_id}/deactivate",
    summary="API Key 비활성화",
    description="API Key를 비활성화합니다 (삭제하지 않음).",
)
async def deactivate_api_key(
    key_id: int,
    session: Session = Depends(get_db_session),
):
    """
    API Key 비활성화

    ## Example
    ```bash
    curl -X POST "http://localhost:5111/api/admin/keys/1/deactivate"
    ```
    """
    try:
        api_key = session.query(APIKey).filter(APIKey.id == key_id).first()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key not found",
            )

        api_key.is_active = False
        session.commit()

        logger.info(f"API Key deactivated: {api_key.name} (ID: {key_id})")

        return {
            "status": "success",
            "message": f"API Key '{api_key.name}' deactivated",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Key deactivation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/{key_id}/activate",
    summary="API Key 활성화",
    description="비활성화된 API Key를 다시 활성화합니다.",
)
async def activate_api_key(
    key_id: int,
    session: Session = Depends(get_db_session),
):
    """
    API Key 활성화

    ## Example
    ```bash
    curl -X POST "http://localhost:5111/api/admin/keys/1/activate"
    ```
    """
    try:
        api_key = session.query(APIKey).filter(APIKey.id == key_id).first()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key not found",
            )

        api_key.is_active = True
        session.commit()

        logger.info(f"API Key activated: {api_key.name} (ID: {key_id})")

        return {
            "status": "success",
            "message": f"API Key '{api_key.name}' activated",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Key activation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
