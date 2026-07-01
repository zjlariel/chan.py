ETF_SH_PREFIXES = ("51", "56", "58")
ETF_SZ_PREFIXES = ("15",)


def normalize_cn_symbol(code, dotted=False):
    symbol = str(code).lower().replace(".", "")
    exchange = symbol[:2] if symbol[:2] in {"sh", "sz"} else ""
    digits = symbol[2:] if exchange else symbol
    if len(digits) != 6 or not digits.isdigit():
        raise ValueError(f"unsupported A-share or ETF symbol: {code}")

    if exchange:
        separator = "." if dotted else ""
        return f"{exchange}{separator}{digits}"

    expected_exchange = _expected_exchange(digits)
    if expected_exchange is None:
        raise ValueError(f"unsupported A-share or ETF symbol: {code}")
    if exchange and exchange != expected_exchange:
        raise ValueError(f"A-share or ETF symbol exchange does not match code: {code}")

    separator = "." if dotted else ""
    return f"{expected_exchange}{separator}{digits}"


def is_etf_symbol(code):
    symbol = str(code).lower().replace(".", "")
    digits = symbol[2:] if symbol[:2] in {"sh", "sz"} else symbol
    return len(digits) == 6 and digits.isdigit() and digits.startswith(ETF_SH_PREFIXES + ETF_SZ_PREFIXES)


def _expected_exchange(digits):
    if digits.startswith("6") or digits.startswith(ETF_SH_PREFIXES):
        return "sh"
    if digits.startswith(("0", "2", "3")) or digits.startswith(ETF_SZ_PREFIXES):
        return "sz"
    return None
