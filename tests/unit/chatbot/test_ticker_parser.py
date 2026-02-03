"""
Ticker Parser Tests (TDD: RED Phase)
KOSDAQ ELW/덕주 티커 파서 테스트

Phase 1: RED - 실패하는 테스트 먼저 작성
"""

from services.chatbot.ticker_parser import TickerParser, TickerType, get_ticker_parser


class TestTickerParserStandard:
    """표준 6자리 티커 테스트"""

    def test_extract_standard_ticker(self):
        """6자리 숫자 티커 추출"""
        parser = TickerParser()
        query = "삼성전자 005930 뉴스 알려줘"
        result = parser.extract(query)
        assert "005930" in result

    def test_extract_only_digits_ticker(self):
        """티커만 입력된 경우"""
        parser = TickerParser()
        result = parser.extract("005930")
        assert result == ["005930"]

    def test_validate_standard_ticker_valid(self):
        """유효한 6자리 티커 검증"""
        parser = TickerParser()
        assert parser.validate("005930") is True
        assert parser.validate("000660") is True
        assert parser.validate("035420") is True

    def test_validate_standard_ticker_invalid(self):
        """잘못된 형식 검증"""
        parser = TickerParser()
        assert parser.validate("00593") is False  # 5자리
        assert parser.validate("0059300") is False  # 7자리 숫자
        assert parser.validate("ABCDE") is False  # 문자만
        assert parser.validate("") is False  # 빈 문자열

    def test_get_ticker_type_standard(self):
        """표준 티커 타입 분류"""
        parser = TickerParser()
        assert parser.get_ticker_type("005930") == TickerType.STANDARD
        assert parser.get_ticker_type("000660") == TickerType.STANDARD

    def test_is_standard_method(self):
        """표준 티커 확인 메서드"""
        parser = TickerParser()
        assert parser.is_standard("005930") is True
        assert parser.is_standard("005930A") is False
        assert parser.is_elw("005930") is False


class TestTickerParserELW:
    """ELW/덕주 티커 테스트"""

    def test_extract_elw_ticker(self):
        """ELW 티커 추출 (6자리 + 알파벳)"""
        parser = TickerParser()
        query = "0001A0 뉴스 알려줘"
        result = parser.extract(query)
        assert "0001A0" in result

    def test_extract_multiple_elw_tickers(self):
        """여러 ELW 티커 추출"""
        parser = TickerParser()
        query = "0001A0과 005930A 비교"
        result = parser.extract(query)
        assert "0001A0" in result
        assert "005930A" in result

    def test_validate_elw_ticker_valid(self):
        """유효한 ELW 티커 검증"""
        parser = TickerParser()
        assert parser.validate("0001A0") is True
        assert parser.validate("005930A") is True
        assert parser.validate("000660B") is True
        assert parser.validate("035420Z") is True

    def test_get_ticker_type_elw(self):
        """ELW 티커 타입 분류"""
        parser = TickerParser()
        assert parser.get_ticker_type("0001A0") == TickerType.ELW
        assert parser.get_ticker_type("005930A") == TickerType.ELW

    def test_is_elw_method(self):
        """ELW 티커 확인 메서드"""
        parser = TickerParser()
        assert parser.is_elw("0001A0") is True
        assert parser.is_elw("005930") is False
        assert parser.is_standard("0001A0") is False


class TestTickerParserRights:
    """신주인수/권리 티커 테스트"""

    def test_extract_rights_ticker(self):
        """RIGHTS 티커 추출"""
        parser = TickerParser()
        query = "005930A12345 뉴스"
        result = parser.extract(query)
        assert "005930A12345" in result

    def test_validate_rights_ticker_valid(self):
        """유효한 RIGHTS 티커 검증"""
        parser = TickerParser()
        assert parser.validate("005930A12345") is True

    def test_get_ticker_type_rights(self):
        """RIGHTS 티커 타입 분류"""
        parser = TickerParser()
        assert parser.get_ticker_type("005930A12345") == TickerType.RIGHTS


class TestTickerParserEdgeCases:
    """엣지 케이스 테스트"""

    def test_extract_empty_query(self):
        """빈 쿼리 처리"""
        parser = TickerParser()
        assert parser.extract("") == []
        assert parser.extract("뉴스만") == []

    def test_extract_no_ticker(self):
        """티커가 없는 쿼리"""
        parser = TickerParser()
        assert parser.extract("삼성전자 뉴스") == []

    def test_extract_first_ticker(self):
        """첫 번째 티커만 추출"""
        parser = TickerParser()
        assert parser.extract_first("005930 000660") == "005930"
        assert parser.extract_first("뉴스 없음") is None

    def test_validate_invalid_formats(self):
        """잘못된 형식 검증"""
        parser = TickerParser()
        assert parser.validate("00593") is False  # 5자리
        assert parser.validate("A005930") is False  # 알파벳 시작
        assert parser.validate("005-930") is False  # 하이픈 포함
        assert parser.validate("005 930") is False  # 공백 포함

    def test_normalize_ticker(self):
        """티커 정규화"""
        parser = TickerParser()
        assert parser.normalize_ticker("005930") == "005930"
        assert parser.normalize_ticker(" 005930 ") == "005930"
        assert parser.normalize_ticker("005-930") == "005930"
        assert parser.normalize_ticker("005930\n") == "005930"
        assert parser.normalize_ticker("0001a0") == "0001A0"  # 소문자를 대문자로

    def test_get_ticker_type_unknown(self):
        """알 수 없는 티커 타입"""
        parser = TickerParser()
        assert parser.get_ticker_type("invalid") == TickerType.UNKNOWN
        assert parser.get_ticker_type("") == TickerType.UNKNOWN


class TestTickerParserFormatting:
    """표시 포맷팅 테스트"""

    def test_format_for_display_elw(self):
        """ELW 티커 표시 포맷"""
        parser = TickerParser()
        assert parser.format_for_display("0001A0") == "0001A0 (ELW)"
        assert parser.format_for_display("005930A") == "005930A (ELW)"

    def test_format_for_display_standard(self):
        """표준 티커 표시 포맷"""
        parser = TickerParser()
        assert parser.format_for_display("005930") == "005930"
        assert parser.format_for_display("000660") == "000660"

    def test_format_for_display_rights(self):
        """RIGHTS 티커 표시 포맷"""
        parser = TickerParser()
        assert parser.format_for_display("005930A12345") == "005930A12345 (권리)"

    def test_format_for_display_unknown(self):
        """알 수 없는 티커 포맷"""
        parser = TickerParser()
        assert parser.format_for_display("invalid") == "invalid"


class TestTickerParserSingleton:
    """싱글톤 테스트"""

    def test_get_ticker_parser_singleton(self):
        """싱글톤 팩토리 반환"""
        parser1 = get_ticker_parser()
        parser2 = get_ticker_parser()
        assert parser1 is parser2  # 동일 인스턴스
        assert isinstance(parser1, TickerParser)
