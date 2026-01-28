"""
Base Repository Pattern
공통 CRUD 작업을 처리하는 기본 Repository
"""

from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from src.database.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    베이스 Repository 클래스
    CRUD 작업을 위한 공통 메서드 제공
    """

    def __init__(self, model: Type[ModelType], session: Session):
        """
        Args:
            model: SQLAlchemy 모델 클래스
            session: DB 세션
        """
        self.model = model
        self.session = session

    def create(self, **kwargs) -> ModelType:
        """
        레코드 생성

        Args:
            **kwargs: 모델 필드값

        Returns:
            생성된 모델 인스턴스
        """
        db_obj = self.model(**kwargs)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """ID로 조회"""
        return self.session.get(self.model, id)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """
        전체 목록 조회 (with pagination and filters)

        Args:
            skip: 건너뛸 레코드 수
            limit: 반환할 최대 레코드 수
            **filters: 필터 조건

        Returns:
            모델 인스턴스 리스트
        """
        query = select(self.model)

        # 필터 적용
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        query = query.offset(skip).limit(limit)
        result = self.session.execute(query)
        return list(result.scalars().all())

    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        레코드 업데이트

        Args:
            id: 레코드 ID
            **kwargs: 업데이트할 필드값

        Returns:
            업데이트된 모델 인스턴스
        """
        query = update(self.model).where(self.model.id == id).values(**kwargs)
        self.session.execute(query)
        self.session.commit()
        return self.get_by_id(id)

    def delete(self, id: int) -> bool:
        """
        레코드 삭제

        Args:
            id: 레코드 ID

        Returns:
            삭제 성공 여부
        """
        db_obj = self.get_by_id(id)
        if db_obj:
            self.session.delete(db_obj)
            self.session.commit()
            return True
        return False

    def count(self, **filters) -> int:
        """
        필터 조건에 맞는 레코드 수 카운트

        Args:
            **filters: 필터 조건

        Returns:
            레코드 수
        """
        query = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        result = self.session.execute(query)
        return len(result.all())

    def exists(self, **filters) -> bool:
        """
        레코드 존재 여부 확인

        Args:
            **filters: 필터 조건

        Returns:
            존재 여부
        """
        return self.count(**filters) > 0
