import argparse
import sys
from pathlib import Path

from Common.CEnum import KL_TYPE
from DataAPI.CacheAPI import CCache
from DataAPI.CacheStore import CacheStore


LIVE_TYPES = [KL_TYPE.K_1M, KL_TYPE.K_5M, KL_TYPE.K_15M, KL_TYPE.K_30M, KL_TYPE.K_60M]
EOD_TYPES = [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_60M, KL_TYPE.K_30M, KL_TYPE.K_15M, KL_TYPE.K_5M]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="缠论离线缓存 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_parser = subparsers.add_parser("update", help="刷新缓存数据")
    update_parser.add_argument("--mode", choices=["live", "eod"], required=True)
    update_parser.add_argument("--codes", required=True, help="逗号分隔的股票代码")
    update_parser.add_argument("--cache-path", type=Path, default=CCache.DEFAULT_PATH)

    status_parser = subparsers.add_parser("status", help="展示缓存状态")
    status_parser.add_argument("--cache-path", type=Path, default=CCache.DEFAULT_PATH)

    return parser.parse_args(argv)


def main(argv=None, cache_class=CCache, store_class=CacheStore):
    args = parse_args(argv)
    if args.command == "update":
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        types = LIVE_TYPES if args.mode == "live" else EOD_TYPES
        for code in codes:
            for k_type in types:
                api = cache_class(code, k_type, cache_path=args.cache_path, mode=args.mode)
                api.refresh()
    elif args.command == "status":
        store = store_class(args.cache_path)
        rows = store.status()
        if not rows:
            print("缓存为空")
            return 0
        print(f"{'symbol':<10} {'k_type':<10} {'first_timestamp':<20} {'last_timestamp':<20} {'bar_count':<10} {'updated_at':<20}")
        for row in rows:
            print(
                f"{row['symbol']:<10} {row['k_type']:<10} {row['first_timestamp']:<20} "
                f"{row['last_timestamp']:<20} {row['bar_count']:<10} {row['updated_at']:<20}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
