"""数据采集层 — 通过 akshare 拉取公募基金数据."""

from datetime import datetime, timedelta

import akshare as ak
import pandas as pd


def fetch_fund_info(code: str) -> dict | None:
    """拉取基金基本信息.

    Returns:
        dict: {"code": str, "name": str, "type": str, "inception": str}
        失败返回 None
    """
    try:
        df = ak.fund_individual_basic_info_xq(symbol=code, timeout=15)
        if df.empty:
            return None

        info = {}
        for _, row in df.iterrows():
            key = str(row.iloc[0]).strip()
            val = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
            info[key] = val

        return {
            "code": code,
            "name": info.get("基金全称", info.get("基金简称", "")),
            "type": info.get("基金类型", ""),
            "inception": info.get("成立日期", ""),
        }
    except Exception as e:
        print(f"[fetcher] 拉取基金信息失败 {code}: {e}")
        return None


def fetch_nav_history(code: str, start_date: str = "2010-01-01") -> list[dict] | None:
    """拉取基金历史净值，计算日收益率.

    Args:
        code: 6 位基金代码
        start_date: 起始日期 YYYY-MM-DD

    Returns:
        list[dict]: [{date, nav, acc_nav, daily_return}, ...]
        失败返回 None
    """
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df.empty:
            return None

        col_map = {
            "净值日期": "date",
            "单位净值": "nav",
            "累计净值": "acc_nav",
        }
        df.rename(columns=col_map, inplace=True)

        if "date" not in df.columns or "nav" not in df.columns:
            return None

        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df = df[df["date"] >= start_date].copy()
        df.sort_values("date", inplace=True)

        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        df["acc_nav"] = pd.to_numeric(
            df.get("acc_nav", df["nav"]), errors="coerce"
        ).fillna(df["nav"])

        # 日收益率 = (今日净值 - 昨日净值) / 昨日净值
        df["daily_return"] = df["nav"].pct_change()

        result = []
        for _, row in df.iterrows():
            result.append({
                "date": row["date"],
                "nav": round(float(row["nav"]), 4),
                "acc_nav": round(float(row["acc_nav"]), 4)
                if pd.notna(row.get("acc_nav"))
                else None,
                "daily_return": round(float(row["daily_return"]), 6)
                if pd.notna(row["daily_return"])
                else None,
            })
        return result if result else None

    except Exception as e:
        print(f"[fetcher] 拉取净值失败 {code}: {e}")
        return None


def fetch_and_save(code: str, db_module=None) -> dict | None:
    """一站式：拉取基金信息 + 净值，存入数据库.

    Returns:
        dict: {"code", "name", "type", "inception", "nav_count": int}
    """
    if db_module is None:
        from fund_analysis import db as db_module

    info = fetch_fund_info(code)
    if info is None:
        return None

    db_module.save_fund_info(
        info["code"], info["name"], info["type"], info["inception"]
    )

    start = "2010-01-01"
    if info["inception"]:
        try:
            start = max(start, info["inception"])
        except Exception:
            pass

    records = fetch_nav_history(code, start_date=start)
    if records:
        db_module.save_nav_batch(code, records)

    info["nav_count"] = len(records) if records else 0
    return info
