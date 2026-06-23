"""Unified command-line entry point for chan.py."""

import json

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from Chan import CChan
from ChanConfig import CChanConfig
from App.analysis_export import build_document
from App.analysis_summary import format_summary
from App.portfolio_analysis import build_advice
from App.portfolio_store import PortfolioStore
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from DataAPI.CacheAPI import CCache
from DataAPI.CacheStore import CacheStore
from Plot.AnimatePlotDriver import CAnimateDriver
from Plot.PlotDriver import CPlotDriver

app = typer.Typer(help="缠论命令行工具")

DEFAULT_LEVELS = [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M]
DEFAULT_LOOKBACK_DAYS = {
    KL_TYPE.K_WEEK: 2400,
    KL_TYPE.K_DAY: 1200,
    KL_TYPE.K_30M: 180,
    KL_TYPE.K_5M: 20,
}
DATA_SOURCE_MAP = {
    "baostock": DATA_SRC.BAO_STOCK,
    "akshare": DATA_SRC.AKSHARE,
    "ccxt": DATA_SRC.CCXT,
    "csv": DATA_SRC.CSV,
    "sina": DATA_SRC.SINA,
    "cache": DATA_SRC.CACHE,
}
LIVE_TYPES = [KL_TYPE.K_1M, KL_TYPE.K_5M, KL_TYPE.K_15M, KL_TYPE.K_30M, KL_TYPE.K_60M]
EOD_TYPES = [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_60M, KL_TYPE.K_30M, KL_TYPE.K_15M, KL_TYPE.K_5M]
AUTO_TYPES = EOD_TYPES + [KL_TYPE.K_1M]


def _parse_levels(value: str) -> list[KL_TYPE]:
    names = [name.strip() for name in value.split(",") if name.strip()]
    if not names:
        raise typer.BadParameter("K 线级别不能为空")
    try:
        return [KL_TYPE[name] for name in names]
    except KeyError as exc:
        raise typer.BadParameter(f"未知 K 线级别：{exc.args[0]}") from exc


def _parse_date(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise typer.BadParameter("日期必须采用 YYYY-MM-DD 格式") from exc


def _begin_time(levels: list[KL_TYPE], start: Optional[str], today: date) -> dict[KL_TYPE, Optional[str]]:
    if start:
        return {level: start for level in levels}
    return {
        level: (today - timedelta(days=DEFAULT_LOOKBACK_DAYS[level])).isoformat() if level in DEFAULT_LOOKBACK_DAYS else None
        for level in levels
    }


def _default_chan_config():
    return CChanConfig({
        "bi_strict": True,
        "trigger_step": False,
        "skip_step": 0,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": '1,2,3a,1p,2s,3b',
        "print_warning": True,
        "zs_algo": "normal",
    })


def _default_plot_config():
    return {
        "plot_kline": True,
        "plot_kline_combine": True,
        "plot_bi": True,
        "plot_seg": True,
        "plot_eigen": False,
        "plot_zs": True,
        "plot_macd": False,
        "plot_mean": False,
        "plot_channel": False,
        "plot_bsp": True,
        "plot_extrainfo": False,
        "plot_demark": False,
        "plot_marker": False,
        "plot_rsi": False,
        "plot_kdj": False,
    }


def _default_plot_para():
    return {
        "seg": {},
        "bi": {},
        "figure": {"x_range": 0},
        "marker": {},
    }


@app.command(name="analyze", help="缠论 K 线分析与绘图")
def analyze(
    data_src: Annotated[str, typer.Option("--data-src", help="数据源：cache、baostock、akshare、ccxt、csv、sina")] = "cache",
    code: Annotated[str, typer.Option("--code", help="股票或交易标的代码")] = "sz.000001",
    start: Annotated[Optional[str], typer.Option("--start", help="起始日期，格式 YYYY-MM-DD")] = None,
    end: Annotated[Optional[str], typer.Option("--end", help="结束日期，格式 YYYY-MM-DD")] = None,
    kl_type: Annotated[str, typer.Option("--kl-type", help="逗号分隔的 K 线级别")] = "K_WEEK,K_DAY,K_30M,K_5M",
    output_dir: Annotated[Path, typer.Option("--output-dir", help="图片输出目录")] = Path("output"),
    json_output: Annotated[bool, typer.Option("--json", help="导出格式化的缠论计算结果 JSON")] = False,
    figure: Annotated[bool, typer.Option("--figure", help="生成分析图片")] = False,
):
    if data_src not in DATA_SOURCE_MAP:
        raise typer.BadParameter(f"未知数据源：{data_src}")

    levels = _parse_levels(kl_type)
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    begin_time = _begin_time(levels, start_date, date.today())

    config = _default_chan_config()
    analysis_results = {}
    if data_src == "cache":
        for level in levels:
            cache = CCache(code, level, begin_time[level], end_date, AUTYPE.QFQ, mode="eod")
            list(cache.get_kl_data())
    analysis_level_sets = [[level] for level in levels] if data_src == "cache" else [levels]
    for analysis_levels in analysis_level_sets:
        analysis_begin_time = {level: begin_time[level] for level in analysis_levels}
        chan = CChan(
            code=code,
            begin_time=analysis_begin_time,
            end_time=end_date,
            data_src=DATA_SOURCE_MAP[data_src],
            lv_list=analysis_levels,
            config=config,
            autype=AUTYPE.QFQ,
        )
        for level in analysis_levels:
            analysis_results[level] = chan[level]

        if figure and not config.trigger_step:
            plot_driver = CPlotDriver(
                chan,
                plot_config=_default_plot_config(),
                plot_para=_default_plot_para(),
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            suffix = f"_{analysis_levels[0].name}" if data_src == "cache" else ""
            plot_driver.save2img(str(output_dir / f"{code}{suffix}.png"))
        elif figure:
            CAnimateDriver(
                chan,
                plot_config=_default_plot_config(),
                plot_para=_default_plot_para(),
            )

    if json_output:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{code}_analysis.json"
        output_path.write_text(
            json.dumps(build_document(code, data_src, analysis_results), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    typer.echo(format_summary(code, data_src, analysis_results))


cache_app = typer.Typer(help="离线缓存管理")
app.add_typer(cache_app, name="cache")
portfolio_app = typer.Typer(help="持仓与观察股跟踪")
app.add_typer(portfolio_app, name="portfolio")


@cache_app.command(name="update", help="刷新缓存数据")
def cache_update(
    codes: Annotated[str, typer.Option("--codes", help="逗号分隔的股票代码")],
    mode: Annotated[str, typer.Option("--mode", help="刷新模式：auto、live 或 eod")] = "auto",
    full: Annotated[bool, typer.Option("--full", help="从完整保留窗口重新拉取数据")] = False,
    cache_path: Annotated[Path, typer.Option("--cache-path", help="SQLite 缓存文件路径")] = CCache.DEFAULT_PATH,
):
    if mode not in {"auto", "live", "eod"}:
        raise typer.BadParameter("mode 必须是 auto、live 或 eod")

    types = LIVE_TYPES if mode == "live" else EOD_TYPES if mode == "eod" else AUTO_TYPES
    for code in [c.strip() for c in codes.split(",") if c.strip()]:
        for k_type in types:
            api = CCache(code, k_type, cache_path=cache_path, mode=mode)
            if full:
                refresh_counts = api.refresh(full=True)
            else:
                refresh_counts = api.refresh()
            refresh_counts = refresh_counts or {}
            inserted = sum(stats["inserted"] for stats in refresh_counts.values())
            updated = sum(stats["updated"] for stats in refresh_counts.values())
            source_summary = "，".join(
                f"{source}：新增 {stats['inserted']}，覆盖 {stats['updated']}"
                for source, stats in refresh_counts.items()
            )
            detail = f"（{source_summary}）" if source_summary else ""
            typer.echo(f"{code} {k_type.name}：新增 {inserted} 根，覆盖 {updated} 根{detail}")


@cache_app.command(name="status", help="展示缓存状态")
def cache_status(
    cache_path: Annotated[Path, typer.Option("--cache-path", help="SQLite 缓存文件路径")] = CCache.DEFAULT_PATH,
):
    store = CacheStore(cache_path)
    rows = store.status()
    if not rows:
        typer.echo("缓存为空")
        return

    typer.echo(f"{'symbol':<10} {'k_type':<10} {'first_timestamp':<20} {'last_timestamp':<20} {'bar_count':<10} {'updated_at':<20}")
    for row in rows:
        typer.echo(
            f"{row['symbol']:<10} {row['k_type']:<10} {row['first_timestamp']:<20} "
            f"{row['last_timestamp']:<20} {row['bar_count']:<10} {row['updated_at']:<20}"
        )


@portfolio_app.command(name="init", help="初始化持仓与观察股表")
def portfolio_init(
    cache_path: Annotated[Path, typer.Option("--cache-path", help="SQLite 缓存文件路径")] = CCache.DEFAULT_PATH,
):
    store = PortfolioStore(cache_path)
    store.initialize()
    typer.echo("已初始化跟踪股票表")


@portfolio_app.command(name="set", help="新增或更新观察股、持仓股")
def portfolio_set(
    code: Annotated[str, typer.Option("--code", help="A 股代码")],
    name: Annotated[str, typer.Option("--name", help="股票名称")],
    quantity: Annotated[int, typer.Option("--quantity", help="持仓数量；0 表示观察股")],
    available_quantity: Annotated[Optional[int], typer.Option("--available", help="可用数量")] = None,
    cost_price: Annotated[Optional[float], typer.Option("--cost-price", help="持仓成本价")]=None,
    group_name: Annotated[Optional[str], typer.Option("--group", help="可选分组")]=None,
    note: Annotated[Optional[str], typer.Option("--note", help="备注")]=None,
    cache_path: Annotated[Path, typer.Option("--cache-path", help="SQLite 缓存文件路径")] = CCache.DEFAULT_PATH,
):
    store = PortfolioStore(cache_path)
    store.set_position(code, name, quantity, available_quantity, cost_price, group_name, note)
    typer.echo(f"已更新 {code}")


@portfolio_app.command(name="list", help="列出持仓与观察股")
def portfolio_list(
    cache_path: Annotated[Path, typer.Option("--cache-path", help="SQLite 缓存文件路径")] = CCache.DEFAULT_PATH,
):
    positions = PortfolioStore(cache_path).list_positions()
    if not positions:
        typer.echo("没有跟踪股票")
        return
    typer.echo(f"{'状态':<8} {'代码':<8} {'名称':<12} {'持仓':<8} {'可用':<8} {'成本':<10}")
    for position in positions:
        status = "持仓" if position["status"] == "holding" else "观察"
        cost = "-" if position["cost_price"] is None else f"{position['cost_price']:.3f}"
        typer.echo(
            f"{status:<8} {position['symbol']:<8} {position['name']:<12} {position['quantity']:<8} "
            f"{position['available_quantity']:<8} {cost:<10}"
        )


@portfolio_app.command(name="analyze", help="分析持仓卖点与观察股买点")
def portfolio_analyze(
    refresh: Annotated[bool, typer.Option("--refresh", help="先按 auto 模式刷新缓存")] = False,
    cache_path: Annotated[Path, typer.Option("--cache-path", help="SQLite 缓存文件路径")] = CCache.DEFAULT_PATH,
):
    positions = PortfolioStore(cache_path).list_positions()
    if not positions:
        typer.echo("没有跟踪股票")
        return
    for title, status in (("持仓股", "holding"), ("观察股", "watching")):
        selected = [position for position in positions if position["status"] == status]
        if not selected:
            continue
        typer.echo(f"\n{title}")
        for position in selected:
            levels, latest_price = _portfolio_analysis_levels(position["symbol"], cache_path, refresh)
            advice = build_advice(position, levels, latest_price)
            typer.echo(f"{position['name']} ({position['symbol']})：{advice['priority']}")
            typer.echo(f"  {advice['basis']}")


def _portfolio_analysis_levels(code, cache_path, refresh):
    begin_time = _begin_time(DEFAULT_LEVELS, None, date.today())
    if refresh:
        for level in DEFAULT_LEVELS:
            CCache(code, level, cache_path=cache_path, mode="auto").refresh()

    levels = {}
    latest_price = None
    for level in DEFAULT_LEVELS:
        cache = CCache(code, level, begin_time[level], None, AUTYPE.QFQ, cache_path=cache_path, mode="eod")
        bars = list(cache.get_kl_data())
        if bars and (latest_price is None or level == KL_TYPE.K_5M):
            latest_price = bars[-1].close
        chan = CChan(
            code=code,
            begin_time={level: begin_time[level]},
            end_time=None,
            data_src=DATA_SRC.CACHE,
            lv_list=[level],
            config=_default_chan_config(),
            autype=AUTYPE.QFQ,
        )
        levels[level.name] = build_document(code, "cache", {level: chan[level]})["levels"][level.name]
    return levels, latest_price


if __name__ == "__main__":
    app()
