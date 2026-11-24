import math
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Ganti sesuai nama tabel aktual Anda
ARTICLES_TABLE = "articles"
ATTRITION_TABLE = "raw_attrition_yourname"


def search_articles(
    engine: Engine,
    source: Optional[str] = None,
    title: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
) -> Dict[str, Any]:
    conditions: List[str] = []
    params: Dict[str, Any] = {}

    if source:
        conditions.append("source = :source")
        params["source"] = source.strip()

    if title:
        conditions.append("title ILIKE :title")
        params["title"] = f"%{title.strip()}%"

    if date_from:
        conditions.append("published_at >= :date_from")
        params["date_from"] = date_from.strip()

    if date_to:
        conditions.append("published_at <= :date_to")
        params["date_to"] = date_to.strip()

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_sql = text(f"""
        SELECT COUNT(*) AS total_items
        FROM {ARTICLES_TABLE}
        {where_clause}
    """)

    offset = (page - 1) * per_page
    data_sql = text(f"""
        SELECT *
        FROM {ARTICLES_TABLE}
        {where_clause}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
    """)

    query_params = {**params, "limit": per_page, "offset": offset}

    with engine.connect() as conn:
        total_items = conn.execute(count_sql, params).scalar() or 0
        rows = conn.execute(data_sql, query_params).mappings().all()

    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 0
    data = [dict(row) for row in rows]

    return {
        "data": data,
        "page": page,
        "per_page": per_page,
        "total_items": int(total_items),
        "total_pages": total_pages,
    }


def count_articles_by_source(engine: Engine) -> Dict[str, Any]:
    sql = text(f"""
        SELECT source, COUNT(*) AS cnt
        FROM {ARTICLES_TABLE}
        GROUP BY source
        ORDER BY cnt DESC, source ASC
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    by_source: Dict[str, int] = {}
    total_articles = 0

    for row in rows:
        src = row["source"] if row["source"] is not None else "unknown"
        cnt = int(row["cnt"] or 0)
        by_source[src] = cnt
        total_articles += cnt

    return {
        "total_articles": total_articles,
        "by_source": by_source,
    }


def get_department_attrition_detail(
    engine: Engine, dept_name: str
) -> Optional[Dict[str, Any]]:
    summary_sql = text(f"""
        SELECT
            "Department" AS department,
            COUNT(*) AS total_employees,
            COUNT(*) FILTER (WHERE "Attrition" = 'Yes') AS attrition_count,
            ROUND(
                (COUNT(*) FILTER (WHERE "Attrition" = 'Yes')::numeric / NULLIF(COUNT(*), 0))::numeric,
                4
            ) AS attrition_rate,
            ROUND(AVG("MonthlyIncome")::numeric, 2) AS avg_income,
            MIN("MonthlyIncome") AS min_income,
            MAX("MonthlyIncome") AS max_income
        FROM {ATTRITION_TABLE}
        WHERE LOWER("Department") = LOWER(:dept_name)
        GROUP BY "Department"
    """)

    top_earners_sql = text(f"""
        SELECT "EmployeeNumber", "JobRole", "MonthlyIncome"
        FROM (
            SELECT
                "EmployeeNumber",
                "JobRole",
                "MonthlyIncome",
                RANK() OVER (ORDER BY "MonthlyIncome" DESC) AS rnk
            FROM {ATTRITION_TABLE}
            WHERE LOWER("Department") = LOWER(:dept_name)
        ) ranked
        WHERE rnk <= 3
        ORDER BY "MonthlyIncome" DESC, "EmployeeNumber" ASC
        LIMIT 3
    """)

    with engine.connect() as conn:
        summary_row = conn.execute(summary_sql, {"dept_name": dept_name}).mappings().first()
        if not summary_row:
            return None
        earner_rows = conn.execute(top_earners_sql, {"dept_name": dept_name}).mappings().all()

    return {
        "department": summary_row["department"],
        "total_employees": int(summary_row["total_employees"]),
        "attrition_count": int(summary_row["attrition_count"]),
        "attrition_rate": float(summary_row["attrition_rate"] or 0.0),
        "avg_income": float(summary_row["avg_income"] or 0.0),
        "min_income": int(summary_row["min_income"] or 0),
        "max_income": int(summary_row["max_income"] or 0),
        "top_earners": [
            {
                "EmployeeNumber": int(r["EmployeeNumber"]),
                "JobRole": r["JobRole"],
                "MonthlyIncome": int(r["MonthlyIncome"]),
            }
            for r in earner_rows
        ],
    }


def get_attrition_risk_profile(
    engine: Engine, limit: int = 20
) -> List[Dict[str, Any]]:
    sql = text(f"""
        WITH dept_avg AS (
            SELECT
                "Department",
                AVG("MonthlyIncome") AS avg_income
            FROM {ATTRITION_TABLE}
            GROUP BY "Department"
        )
        SELECT
            e.*,
            ROUND(d.avg_income::numeric, 2) AS dept_avg_income
        FROM {ATTRITION_TABLE} e
        JOIN dept_avg d
            ON e."Department" = d."Department"
        WHERE e."OverTime" = 'Yes'
          AND e."YearsAtCompany" < 3
          AND e."MonthlyIncome" < d.avg_income
        ORDER BY e."MonthlyIncome" ASC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": limit}).mappings().all()

    return [dict(row) for row in rows]