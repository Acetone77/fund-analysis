"""数据库层 — SQLite 存储基金信息和净值数据."""

import sqlite3
from pathlib import Path

import pandas as pd

# 数据库文件放在项目根目录的 data/ 下
DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "funds.db"


def get_conn() -> sqlite3.Connection:
    """获取数据库连接."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """初始化数据库表（如果不存在则创建）."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS funds (
            code        TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT DEFAULT '',
            inception   TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS nav (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code   TEXT NOT NULL,
            date        TEXT NOT NULL,
            nav         REAL NOT NULL,
            acc_nav     REAL,
            daily_return REAL,
            FOREIGN KEY (fund_code) REFERENCES funds(code) ON DELETE CASCADE,
            UNIQUE(fund_code, date)
        );

        CREATE INDEX IF NOT EXISTS idx_nav_fund_code ON nav(fund_code);
        CREATE INDEX IF NOT EXISTS idx_nav_date ON nav(date);
    """)
    conn.commit()
    conn.close()


# ── 基金 CRUD ──────────────────────────────────────────────

def save_fund_info(code: str, name: str, fund_type: str = "", inception: str = "") -> None:
    """插入或更新基金基本信息."""
    conn = get_conn()
    conn.execute(
        """INSERT INTO funds (code, name, type, inception)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(code) DO UPDATE SET
               name=excluded.name,
               type=excluded.type,
               inception=excluded.inception""",
        (code, name, fund_type, inception),
    )
    conn.commit()
    conn.close()


def get_fund(code: str) -> dict | None:
    """获取单只基金信息."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM funds WHERE code = ?", (code,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_funds() -> list[dict]:
    """列出所有已保存的基金."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT f.*, MAX(n.date) AS latest_nav_date FROM funds f "
        "LEFT JOIN nav n ON f.code = n.fund_code GROUP BY f.code ORDER BY f.code"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_fund(code: str) -> None:
    """删除基金及其净值数据（CASCADE）."""
    conn = get_conn()
    conn.execute("DELETE FROM funds WHERE code = ?", (code,))
    conn.commit()
    conn.close()


# ── 净值 CRUD ──────────────────────────────────────────────

def save_nav_batch(fund_code: str, records: list[dict]) -> int:
    """批量插入净值数据。records 每项含 date, nav, acc_nav, daily_return.
    返回实际插入行数."""
    conn = get_conn()
    inserted = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO nav (fund_code, date, nav, acc_nav, daily_return)
                   VALUES (?, ?, ?, ?, ?)""",
                (fund_code, r["date"], r["nav"], r.get("acc_nav"), r.get("daily_return")),
            )
            inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted


def get_nav_df(fund_code: str) -> pd.DataFrame:
    """获取基金净值历史，返回 DataFrame（按日期升序）."""
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT date, nav, acc_nav, daily_return FROM nav "
        "WHERE fund_code = ? ORDER BY date ASC",
        conn,
        params=(fund_code,),
    )
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
    return df


def get_latest_nav_date(fund_code: str) -> str | None:
    """获取某基金最新净值日期."""
    conn = get_conn()
    row = conn.execute(
        "SELECT MAX(date) AS d FROM nav WHERE fund_code = ?", (fund_code,)
    ).fetchone()
    conn.close()
    return row["d"] if row else None
