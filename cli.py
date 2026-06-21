"""Unified command-line entry point for chan.py."""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from Chan import CChan
from ChanConfig import CChanConfig
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
    KL_TYPE.K_30M: 300,
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
        "figure": {"x_range": 200},
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
):
    if data_src not in DATA_SOURCE_MAP:
        raise typer.BadParameter(f"未知数据源：{data_src}")

    levels = _parse_levels(kl_type)
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    begin_time = _begin_time(levels, start_date, date.today())

    config = _default_chan_config()
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

        if not config.trigger_step:
            plot_driver = CPlotDriver(
                chan,
                plot_config=_default_plot_config(),
                plot_para=_default_plot_para(),
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            suffix = f"_{analysis_levels[0].name}" if data_src == "cache" else ""
            plot_driver.save2img(str(output_dir / f"{code}{suffix}.png"))
        else:
            CAnimateDriver(
                chan,
                plot_config=_default_plot_config(),
                plot_para=_default_plot_para(),
            )


cache_app = typer.Typer(help="离线缓存管理")
app.add_typer(cache_app, name="cache")


@cache_app.command(name="update", help="刷新缓存数据")
def cache_update(
    codes: Annotated[str, typer.Option("--codes", help="逗号分隔的股票代码")],
    mode: Annotated[str, typer.Option("--mode", help="刷新模式：auto、live 或 eod")] = "auto",
    cache_path: Annotated[Path, typer.Option("--cache-path", help="SQLite 缓存文件路径")] = CCache.DEFAULT_PATH,
):
    if mode not in {"auto", "live", "eod"}:
        raise typer.BadParameter("mode 必须是 auto、live 或 eod")

    types = LIVE_TYPES if mode == "live" else EOD_TYPES if mode == "eod" else AUTO_TYPES
    for code in [c.strip() for c in codes.split(",") if c.strip()]:
        for k_type in types:
            api = CCache(code, k_type, cache_path=cache_path, mode=mode)
            api.refresh()


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


if __name__ == "__main__":
    app()
