#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Stock Analysis - CLI Entry Point
한국 주식 분석 시스템 메인 CLI 인터페이스
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint

# API Gateway URL
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:5111")

console = Console()


class APIClient:
    """API Gateway 클라이언트"""

    def __init__(self, base_url: str = API_GATEWAY_URL):
        self.base_url = base_url.rstrip("/")
        self.timeout = 300.0  # 5분 타임아웃

    async def health_check(self) -> bool:
        """API Gateway 상태 확인"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def trigger_vcp_scan(
        self, market: Optional[str] = None, min_score: Optional[float] = None
    ) -> dict:
        """VCP 스캔 트리거"""
        params = {}
        if market:
            params["market"] = market
        if min_score is not None:
            params["min_score"] = min_score

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/kr/scan/vcp",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

    async def trigger_signal_generation(self, tickers: Optional[list[str]] = None) -> dict:
        """시그널 생성 트리거"""
        payload = {"tickers": tickers} if tickers else None

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/kr/scan/signals",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

    async def get_signals(self, limit: int = 20) -> list:
        """시그널 조회"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/kr/signals",
                params={"limit": limit},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def get_market_gate(self) -> dict:
        """Market Gate 상태 조회"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/kr/market-gate",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def get_backtest_kpi(self) -> dict:
        """백테스트 KPI 조회"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/kr/backtest-kpi",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def trigger_ai_analysis(self, ticker: str) -> dict:
        """AI 분석 트리거"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/kr/ai-analyze/{ticker}",
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

    async def get_system_health(self) -> dict:
        """시스템 헬스 체크"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/system/health",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()


def show_header():
    """헤더 표시"""
    header = Panel(
        "[bold cyan]KR Stock Analysis System[/bold cyan]\n"
        "[dim]한국 주식 분석 시스템 - CLI 인터페이스[/dim]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(header)


def show_menu():
    """메뉴 표시"""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Option", style="cyan", width=3)
    table.add_column("Description")

    table.add_row("1", "[bold green]수급 스크리닝[/bold green] - VCP 패턴 스캔 실행")
    table.add_row("2", "[bold blue]종가베팅 V2[/bold blue] - 시그널 생성 실행")
    table.add_row("3", "[bold yellow]시그널 조회[/bold yellow] - 활성 시그널 확인")
    table.add_row("4", "[bold magenta]Market Gate[/bold magenta] - 시장 상태 확인")
    table.add_row("5", "[bold red]AI 분석[/bold red] - 종목 AI 분석 실행")
    table.add_row("6", "[bold purple]시스템 상태[/bold purple] - 헬스 체크")
    table.add_row("7", "[bold white]백테스트 KPI[/bold white] - 전략 성과 확인")
    table.add_row("0", "[dim]종료[/dim]")
    console.print(table)


async def menu_vcp_scan(client: APIClient):
    """VCP 스캔 메뉴"""
    console.print("\n[bold cyan]VCP 패턴 스캔[/bold cyan]")

    market = Prompt.ask(
        "시장 선택",
        choices=["all", "KOSPI", "KOSDAQ"],
        default="all"
    )

    min_score_input = Prompt.ask("최소 점수 (0-100, Enter=기본값)", default="")
    min_score = float(min_score_input) if min_score_input else None

    with console.status("[bold yellow]VCP 스캔 실행 중...", spinner="dots"):
        try:
            result = await client.trigger_vcp_scan(market=market if market != "all" else None, min_score=min_score)
            console.print(f"[green]✓ 스캔 완료![/green]")
            console.print(f"  - 스캔된 종목: {result.get('scanned_count', 0)}개")
            console.print(f"  - 발견된 시그널: {result.get('found_signals', 0)}개")
            if result.get("signals"):
                console.print("\n[bold]발견된 시그널:[/bold]")
                for signal in result["signals"][:10]:
                    console.print(f"  • {signal.get('name')} ({signal.get('ticker')}) - 점수: {signal.get('score')}, 등급: {signal.get('grade')}")
        except Exception as e:
            console.print(f"[red]✗ 스캔 실패: {e}[/red]")


async def menu_signal_generation(client: APIClient):
    """시그널 생성 메뉴"""
    console.print("\n[bold cyan]종가베팅 V2 시그널 생성[/bold cyan]")

    tickers_input = Prompt.ask("대상 종목 티커 (쉼표 구분, Enter=전체)", default="")
    tickers = [t.strip() for t in tickers_input.split(",")] if tickers_input else None

    with console.status("[bold yellow]시그널 생성 중...", spinner="dots"):
        try:
            result = await client.trigger_signal_generation(tickers=tickers)
            console.print(f"[green]✓ 시그널 생성 완료![/green]")
            console.print(f"  - 생성된 시그널: {result.get('generated_count', 0)}개")
        except Exception as e:
            console.print(f"[red]✗ 시그널 생성 실패: {e}[/red]")


async def menu_view_signals(client: APIClient):
    """시그널 조회 메뉴"""
    console.print("\n[bold cyan]활성 시그널 조회[/bold cyan]")

    try:
        signals = await client.get_signals(limit=50)

        if not signals:
            console.print("[yellow]활성 시그널이 없습니다.[/yellow]")
            return

        table = Table(title="활성 VCP 시그널")
        table.add_column("티커", style="cyan")
        table.add_column("종목명", style="white")
        table.add_column("등급", style="bold")
        table.add_column("점수", justify="right")
        table.add_column("진입가", justify="right")
        table.add_column("목표가", justify="right")
        table.add_column("생성일", style="dim")

        for sig in signals[:20]:
            score = sig.get("score")
            score_value = score.get("total") if isinstance(score, dict) else score

            # 등급별 색상
            grade = sig.get("grade", "")
            grade_style = {
                "S": "bold red",
                "A": "bold yellow",
                "B": "green",
                "C": "blue",
            }.get(grade, "white")

            table.add_row(
                sig.get("ticker", ""),
                sig.get("name", ""),
                f"[{grade_style}]{grade}[/{grade_style}]",
                f"{score_value}" if score_value else "-",
                f"{sig.get('entry_price', 0):,.0f}" if sig.get("entry_price") else "-",
                f"{sig.get('target_price', 0):,.0f}" if sig.get("target_price") else "-",
                sig.get("created_at", "")[:10],
            )

        console.print(table)
        console.print(f"\n[dim]총 {len(signals)}개 시그널 중 상위 20개 표시[/dim]")

    except Exception as e:
        console.print(f"[red]✗ 조회 실패: {e}[/red]")


async def menu_market_gate(client: APIClient):
    """Market Gate 메뉴"""
    console.print("\n[bold cyan]Market Gate 상태[/bold cyan]")

    try:
        gate = await client.get_market_gate()

        # 상태 색상
        status = gate.get("status", "UNKNOWN")
        status_style = {
            "GREEN": "bold green",
            "YELLOW": "bold yellow",
            "RED": "bold red",
        }.get(status, "white")

        # 패널 표시
        # KOSPI/KOSDAQ 값이 None인 경우 처리
        kospi_close = gate.get('kospi_close')
        kospi_change = gate.get('kospi_change_pct')
        kosdaq_close = gate.get('kosdaq_close')
        kosdaq_change = gate.get('kosdaq_change_pct')

        kospi_line = f"KOSPI 종가: {kospi_close:,.0f} ({kospi_change:+.2f}%)" if kospi_close else "KOSPI: 데이터 없음"
        kosdaq_line = f"KOSDAQ 종가: {kosdaq_close:,.0f} ({kosdaq_change:+.2f}%)" if kosdaq_close else "KOSDAQ: 데이터 없음"

        panel = Panel(
            f"[{status_style}]상태: {status}[/{status_style}]\n"
            f"[dim]레벨: {gate.get('level', 0)}[/dim]\n\n"
            f"KOSPI: {gate.get('kospi_status', 'N/A')}\n"
            f"KOSDAQ: {gate.get('kosdaq_status', 'N/A')}\n"
            f"{kospi_line}\n"
            f"{kosdaq_line}",
            title="[bold]Market Gate[/bold]",
            border_style=status_style.lower() if status != "UNKNOWN" else "white",
        )
        console.print(panel)

        # 섹터별 현황
        sectors = gate.get("sectors", [])
        if sectors:
            console.print("\n[bold]섹터별 현황:[/bold]")
            sector_table = Table(show_header=True, box=None)
            sector_table.add_column("섹터", style="cyan")
            sector_table.add_column("신호", justify="center")
            sector_table.add_column("등락률", justify="right")
            sector_table.add_column("점수", justify="right")

            for sector in sectors:
                signal = sector.get("signal", "neutral")
                signal_style = {
                    "bullish": "green",
                    "bearish": "red",
                    "neutral": "yellow",
                }.get(signal, "white")

                sector_table.add_row(
                    sector.get("name", ""),
                    f"[{signal_style}]{signal}[/{signal_style}]",
                    f"{sector.get('change_pct', 0):+.2f}%",
                    f"{sector.get('score', 0):.1f}" if sector.get("score") else "-",
                )
            console.print(sector_table)

    except Exception as e:
        console.print(f"[red]✗ 조회 실패: {e}[/red]")


async def menu_ai_analysis(client: APIClient):
    """AI 분석 메뉴"""
    console.print("\n[bold cyan]AI 종목 분석[/bold cyan]")

    ticker = Prompt.ask("종목 티커 (예: 005930)", default="005930").strip()

    with console.status("[bold yellow]AI 분석 실행 중...", spinner="dots"):
        try:
            result = await client.trigger_ai_analysis(ticker)
            console.print(f"[green]✓ 분석 완료![/green]")
            console.print(f"  - 종목: {result.get('name', ticker)}")
            console.print(f"  - 감성: {result.get('sentiment', 'N/A')}")
            console.print(f"  - 점수: {result.get('score', 'N/A')}")
            console.print(f"  - 추천: {result.get('recommendation', 'N/A')}")
        except Exception as e:
            console.print(f"[red]✗ 분석 실패: {e}[/red]")


async def menu_system_health(client: APIClient):
    """시스템 헬스 체크 메뉴"""
    console.print("\n[bold cyan]시스템 상태[/bold cyan]")

    try:
        health = await client.get_system_health()

        # 전체 상태
        status = health.get("status", "unknown")
        status_style = {
            "healthy": "bold green",
            "degraded": "bold yellow",
            "unhealthy": "bold red",
        }.get(status, "white")

        panel = Panel(
            f"[{status_style}]상태: {status.upper()}[/{status_style}]\n"
            f"[dim]업타임: {health.get('uptime_seconds', 0) // 3600}시간[/dim]",
            title="[bold]시스템 헬스[/bold]",
            border_style="green" if status == "healthy" else "yellow" if status == "degraded" else "red",
        )
        console.print(panel)

        # 서비스 상태
        services = health.get("services", {})
        if services:
            console.print("\n[bold]서비스 상태:[/bold]")
            service_table = Table(show_header=True, box=None)
            service_table.add_column("서비스", style="cyan")
            service_table.add_column("상태", justify="center")

            for svc_name, svc_status in services.items():
                svc_style = "green" if svc_status == "up" else "red"
                service_table.add_row(svc_name, f"[{svc_style}]{svc_status}[/{svc_style}]")

            console.print(service_table)

        # 데이터베이스/Redis 상태
        db_status = health.get("database_status", "unknown")
        redis_status = health.get("redis_status", "unknown")

        console.print(f"\nDatabase: [{ 'green' if db_status == 'healthy' else 'red' }]{db_status}[/{ 'green' if db_status == 'healthy' else 'red' }]")
        console.print(f"Redis: [{ 'green' if redis_status == 'healthy' else 'red' }]{redis_status}[/{ 'green' if redis_status == 'healthy' else 'red' }]")

    except Exception as e:
        console.print(f"[red]✗ 조회 실패: {e}[/red]")


async def menu_backtest_kpi(client: APIClient):
    """백테스트 KPI 메뉴"""
    console.print("\n[bold cyan]백테스트 KPI[/bold cyan]")

    try:
        kpi = await client.get_backtest_kpi()

        table = Table(title="전략별 백테스트 성과")
        table.add_column("전략", style="cyan")
        table.add_column("상태", justify="center")
        table.add_column("건수", justify="right")
        table.add_column("승률", justify="right")
        table.add_column("수익률", justify="right")
        table.add_column("Profit Factor", justify="right")

        for strategy_name, stats in kpi.items():
            status = stats.get("status", "N/A")
            status_style = {
                "OK": "green",
                "Accumulating": "yellow",
                "No Data": "dim",
            }.get(status, "white")

            count = stats.get("count", 0)
            win_rate = stats.get("win_rate")
            avg_return = stats.get("avg_return")
            profit_factor = stats.get("profit_factor")

            table.add_row(
                strategy_name.upper(),
                f"[{status_style}]{status}[/{status_style}]",
                f"{count}",
                f"{win_rate:.1f}%" if win_rate else "-",
                f"{avg_return:.2f}%" if avg_return else "-",
                f"{profit_factor:.2f}" if profit_factor else "-",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ 조회 실패: {e}[/red]")


async def main():
    """메인 함수"""
    show_header()

    # API Gateway 상태 확인
    client = APIClient()
    is_healthy = await client.health_check()

    if not is_healthy:
        console.print(
            f"\n[red]✗ API Gateway에 연결할 수 없습니다.[/red]"
            f"\n[dim]URL: {API_GATEWAY_URL}[/dim]"
            f"\n[yellow]서비스를 시작하려면:[/yellow]"
            f"\n  .venv/bin/python -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 5111 --reload"
        )
        if not Confirm.ask("\n계속 진행하시겠습니까? (서비스 연결 없음)", default=False):
            return

    while True:
        show_menu()
        choice = Prompt.ask(
            "\n[cyan]선택[/cyan]",
            choices=["0", "1", "2", "3", "4", "5", "6", "7"],
            default="0"
        )

        if choice == "0":
            console.print("\n[green]프로그램을 종료합니다.[/green]\n")
            break
        elif choice == "1":
            await menu_vcp_scan(client)
        elif choice == "2":
            await menu_signal_generation(client)
        elif choice == "3":
            await menu_view_signals(client)
        elif choice == "4":
            await menu_market_gate(client)
        elif choice == "5":
            await menu_ai_analysis(client)
        elif choice == "6":
            await menu_system_health(client)
        elif choice == "7":
            await menu_backtest_kpi(client)

        # 메뉴로 돌아가기 전 대기
        if choice != "0":
            input("\n엔터 키를 누르면 메뉴로 돌아갑니다...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]프로그램이 중단되었습니다.[/yellow]")
        sys.exit(0)
