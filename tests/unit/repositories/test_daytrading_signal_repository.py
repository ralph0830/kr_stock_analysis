"""
Unit Tests for DaytradingSignalRepository
TDD: Red-Green-Refactor Cycle

Phase 4: Database & Repository Tests
- DaytradingSignal 모델
- CRUD operations
- Filtering by min_score, market, status
"""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# =============================================================================
# Test Model Creation
# =============================================================================

class TestDaytradingSignalModel:
    """DaytradingSignal 모델 테스트"""

    @pytest.fixture
    def db_session(self):
        """테스트용 DB 세션"""
        from src.database.session import Base
        from src.database.models.daytrading_signal import DaytradingSignal

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        TestingSessionLocal = sessionmaker(bind=engine)
        session = TestingSessionLocal()

        yield session

        session.close()

    def test_model_create_성공(self, db_session):
        """DaytradingSignal 모델 생성 성공"""
        from src.database.models.daytrading_signal import DaytradingSignal

        signal = DaytradingSignal(
            ticker="005930",
            name="삼성전자",
            market="KOSPI",
            total_score=90,
            grade="S",
            status="OPEN",
            signal_date=date.today(),
        )

        db_session.add(signal)
        db_session.commit()

        assert signal.id is not None
        assert signal.ticker == "005930"
        assert signal.total_score == 90

    def test_model_7개_점수_컬럼_저장(self, db_session):
        """7개 체크리스트 점수 개별 저장"""
        from src.database.models.daytrading_signal import DaytradingSignal

        signal = DaytradingSignal(
            ticker="005930",
            name="삼성전자",
            market="KOSPI",
            total_score=90,
            grade="S",
            volume_score=15,
            momentum_score=15,
            box_score=15,
            ma5_score=15,
            institution_score=15,
            oversold_score=15,
            sector_score=0,
            status="OPEN",
            signal_date=date.today(),
        )

        db_session.add(signal)
        db_session.commit()

        assert signal.volume_score == 15
        assert signal.momentum_score == 15

    def test_model_매매기준가_저장(self, db_session):
        """매매 기준가 저장"""
        from src.database.models.daytrading_signal import DaytradingSignal

        signal = DaytradingSignal(
            ticker="005930",
            name="삼성전자",
            market="KOSPI",
            total_score=75,
            grade="A",
            entry_price=75000,
            target_price=80000,
            stop_loss=72000,
            status="OPEN",
            signal_date=date.today(),
        )

        db_session.add(signal)
        db_session.commit()

        assert signal.entry_price == 75000
        assert signal.target_price == 80000

    def test_model_checks_json_저장(self, db_session):
        """체크리스트 JSON 저장"""
        from src.database.models.daytrading_signal import DaytradingSignal

        checks = [
            {"name": "거래량 폭증", "status": "passed", "points": 15},
            {"name": "모멘텀 돌파", "status": "passed", "points": 15},
        ]

        signal = DaytradingSignal(
            ticker="005930",
            name="삼성전자",
            market="KOSPI",
            total_score=30,
            grade="C",
            checks=checks,
            status="OPEN",
            signal_date=date.today(),
        )

        db_session.add(signal)
        db_session.commit()

        assert len(signal.checks) == 2


# =============================================================================
# Test Repository CRUD Operations
# =============================================================================

class TestDaytradingSignalRepository:
    """DaytradingSignalRepository CRUD 테스트"""

    @pytest.fixture
    def db_session(self):
        from src.database.session import Base
        from src.database.models.daytrading_signal import DaytradingSignal

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        TestingSessionLocal = sessionmaker(bind=engine)
        session = TestingSessionLocal()

        yield session

        session.close()

    @pytest.fixture
    def repo(self, db_session):
        from src.repositories.daytrading_signal_repository import DaytradingSignalRepository
        return DaytradingSignalRepository(db_session)

    @pytest.fixture
    def sample_signals(self, db_session):
        from src.database.models.daytrading_signal import DaytradingSignal

        signals = [
            DaytradingSignal(
                ticker="005930", name="삼성전자", market="KOSPI",
                total_score=90, grade="S", status="OPEN", signal_date=date.today(),
            ),
            DaytradingSignal(
                ticker="000270", name="기아", market="KOSPI",
                total_score=75, grade="A", status="OPEN", signal_date=date.today(),
            ),
            DaytradingSignal(
                ticker="066570", name="LG전자", market="KOSDAQ",
                total_score=45, grade="C", status="OPEN", signal_date=date.today(),
            ),
        ]

        for signal in signals:
            db_session.add(signal)
        db_session.commit()

        return signals

    def test_create_signal_db에_저장됨(self, repo, db_session):
        from src.database.models.daytrading_signal import DaytradingSignal

        signal = DaytradingSignal(
            ticker="005930", name="삼성전자", market="KOSPI",
            total_score=90, grade="S", status="OPEN", signal_date=date.today(),
        )

        result = repo.create(signal)

        assert result.id is not None
        assert result.ticker == "005930"

        fetched = db_session.query(DaytradingSignal).filter_by(ticker="005930").first()
        assert fetched is not None

    def test_get_by_id_신호_조회(self, repo, sample_signals):
        result = repo.get_by_id(sample_signals[0].id)
        assert result is not None
        assert result.ticker == "005930"

    def test_get_by_ticker_종목별_조회(self, repo, sample_signals):
        result = repo.get_by_ticker("005930")
        assert result is not None
        assert result.ticker == "005930"

    def test_get_active_signals_limit_10(self, repo, sample_signals):
        results = repo.get_active_signals(limit=10)
        assert len(results) == 3

    def test_get_by_min_score_60점이상만(self, repo, sample_signals):
        results = repo.get_by_min_score(60)
        assert len(results) == 2
        assert all(s.total_score >= 60 for s in results)

    def test_get_by_market_kospi만(self, repo, sample_signals):
        results = repo.get_by_market("KOSPI")
        assert len(results) == 2

    def test_get_by_date날짜별_조회(self, repo, sample_signals):
        today = date.today()
        results = repo.get_by_date(today)
        assert len(results) == 3

    def test_update_status_closed_변경(self, repo, sample_signals):
        repo.update_status(sample_signals[0].id, "CLOSED")
        updated = repo.get_by_id(sample_signals[0].id)
        assert updated.status == "CLOSED"

    def test_delete_by_date날짜별_삭제(self, repo, db_session, sample_signals):
        from src.database.models.daytrading_signal import DaytradingSignal

        today = date.today()
        repo.delete_by_date(today)

        count = db_session.query(DaytradingSignal).filter_by(signal_date=today).count()
        assert count == 0

    def test_get_open_signals_by_ticker(self, repo, sample_signals):
        results = repo.get_open_signals_by_ticker("005930")
        assert len(results) == 1


# =============================================================================
# Test Repository Advanced Queries
# =============================================================================

class TestDaytradingSignalRepositoryAdvanced:
    """고급 쿼리 테스트"""

    @pytest.fixture
    def db_session(self):
        from src.database.session import Base
        from src.database.models.daytrading_signal import DaytradingSignal

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        TestingSessionLocal = sessionmaker(bind=engine)
        session = TestingSessionLocal()

        yield session

        session.close()

    @pytest.fixture
    def repo(self, db_session):
        from src.repositories.daytrading_signal_repository import DaytradingSignalRepository
        return DaytradingSignalRepository(db_session)

    def test_get_top_scorers_limit_5(self, repo):
        from src.database.models.daytrading_signal import DaytradingSignal

        for i in range(10):
            signal = DaytradingSignal(
                ticker=f"{i:06d}", name=f"종목{i}",
                market="KOSPI" if i % 2 == 0 else "KOSDAQ",
                total_score=100 - i * 5,
                grade="S" if i < 2 else "A" if i < 5 else "B",
                status="OPEN", signal_date=date.today(),
            )
            repo.session.add(signal)
        repo.session.commit()

        results = repo.get_top_scorers(limit=5)
        assert len(results) == 5

    def test_get_by_grade_s등급만(self, repo):
        from src.database.models.daytrading_signal import DaytradingSignal

        grades_data = [
            ("005930", "S", 95), ("000270", "A", 80),
            ("035420", "S", 90), ("066570", "B", 65),
        ]

        for ticker, grade, score in grades_data:
            signal = DaytradingSignal(
                ticker=ticker, name=f"종목{ticker}", market="KOSPI",
                total_score=score, grade=grade, status="OPEN", signal_date=date.today(),
            )
            repo.session.add(signal)
        repo.session.commit()

        results = repo.get_by_grade("S")
        assert len(results) == 2

    def test_delete_existing_signals_date_갱신(self, repo):
        from src.database.models.daytrading_signal import DaytradingSignal

        today = date.today()

        for i in range(2):
            signal = DaytradingSignal(
                ticker=f"{i:06d}", name=f"종목{i}", market="KOSPI",
                total_score=50, grade="C", status="OPEN", signal_date=today,
            )
            repo.session.add(signal)
        repo.session.commit()

        deleted_count = repo.delete_by_date(today)
        assert deleted_count == 2
