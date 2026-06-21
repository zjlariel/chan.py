import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from Common.CEnum import DATA_SRC, KL_TYPE


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
}


@dataclass(frozen=True)
class CliOptions:
    data_src: DATA_SRC
    code: str
    begin_time: dict[KL_TYPE, str | None]
    end_time: Optional[str]
    lv_list: list[KL_TYPE]
    output_dir: Path

    @property
    def output_path(self) -> Path:
        return self.output_dir / f"{self.code}.png"


def _parse_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise argparse.ArgumentTypeError("日期必须采用 YYYY-MM-DD 格式") from error


def _parse_levels(value: str) -> list[KL_TYPE]:
    names = [name.strip() for name in value.split(",") if name.strip()]
    if not names:
        raise argparse.ArgumentTypeError("K 线级别不能为空")
    try:
        return [KL_TYPE[name] for name in names]
    except KeyError as error:
        raise argparse.ArgumentTypeError(f"未知 K 线级别：{error.args[0]}") from error


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="缠论 K 线分析与绘图")
    parser.add_argument("--data-src", choices=DATA_SOURCE_MAP, default="baostock", help="数据源，默认 baostock")
    parser.add_argument("--code", default="sz.000001", help="股票或交易标的代码")
    parser.add_argument("--start", type=_parse_date, help="起始日期，格式 YYYY-MM-DD")
    parser.add_argument("--end", type=_parse_date, help="结束日期，格式 YYYY-MM-DD")
    parser.add_argument(
        "--kl-type",
        type=_parse_levels,
        default=DEFAULT_LEVELS,
        help="逗号分隔的 K 线级别，默认 K_WEEK,K_DAY,K_30M,K_5M",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="图片输出目录，默认 output")
    return parser


def parse_args(argv: Optional[list[str]] = None, today: Optional[date] = None) -> CliOptions:
    args = _create_parser().parse_args(argv)
    today = today or date.today()
    begin_time = (
        {level: args.start for level in args.kl_type}
        if args.start
        else {
            level: (today - timedelta(days=DEFAULT_LOOKBACK_DAYS[level])).isoformat() if level in DEFAULT_LOOKBACK_DAYS else None
            for level in args.kl_type
        }
    )
    return CliOptions(
        data_src=DATA_SOURCE_MAP[args.data_src],
        code=args.code,
        begin_time=begin_time,
        end_time=args.end,
        lv_list=args.kl_type,
        output_dir=args.output_dir,
    )
