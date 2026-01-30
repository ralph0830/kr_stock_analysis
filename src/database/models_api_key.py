"""
API Key Model

API 인증을 위한 키 관리
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.orm import relationship

from src.database.models import Base


class APIKey(Base):
    """
    API Key 모델

    ## 속성
    - key: API 키 (UUID 형식)
    - name: 키 식별 이름
    - scope: 권한 레벨 (read, write, admin)
    - is_active: 활성 상태
    - expires_at: 만료일자
    - last_used_at: 마지막 사용 시간
    - created_by: 생성자 정보
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    scope = Column(String(20), nullable=False, default="read")  # read, write, admin
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<APIKey(id={self.id}, key={self.key[:8]}..., scope={self.scope})>"

    def is_valid(self) -> bool:
        """키 유효성 확인"""
        if not self.is_active:
            return False

        if self.expires_at and self.expires_at < datetime.utcnow():
            return False

        return True

    def update_last_used(self) -> None:
        """마지막 사용 시간 업데이트"""
        self.last_used_at = datetime.utcnow()

    @staticmethod
    def generate_key() -> str:
        """새로운 API 키 생성"""
        import secrets
        import string

        # 32자 랜덤 키 생성
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(32))

        # kr_ 접두사 추가
        return f"kr_{random_part}"

    def to_dict(self, include_key: bool = False) -> dict:
        """dict 반환 (키 노출 여부 선택)"""
        result = {
            "id": self.id,
            "name": self.name,
            "scope": self.scope,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
        }

        if include_key:
            result["key"] = self.key

        return result
