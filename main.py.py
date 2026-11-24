from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, Path, Query

# Sesuaikan import engine & auth dependency dengan struktur proyek Session 9/10 Anda
from database import engine  # atau dari db.py jika engine didefinisikan di sana
import db

app = FastAPI(title="Mini Project 2 API")


# Contoh dependency auth jika proyek Anda memakai API Key / Bearer token
# def verify_auth(...):
#     ...


@app.get("/articles/search")
def articles_search(
    source: Optional[str] = Query(default=None, description="Filter by source (e.g. bbc, nytimes)"),
    title: Optional[str] = Query(default=None, description="Case-insensitive partial match on title"),
    date_from: Optional[str] = Query(default=None, description="Format YYYY-MM-DD (published_at >=)"),
    date_to: Optional[str] = Query(default=None, description="Format YYYY-MM-DD (published_at <=)"),
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(default=10, ge=1, le=50, description="Items per page (max 50)"),
):
    return db.search_articles(
        engine=engine,
        source=source,
        title=title,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )


@app.get("/articles/stats")
def articles_stats():
    return db.count_articles_by_source(engine=engine)


@app.get("/attrition/department/{dept_name}")
def attrition_department_detail(
    dept_name: str = Path(..., min_length=1, description="Department name, e.g. Sales"),
):
    result = db.get_department_attrition_detail(engine=engine, dept_name=dept_name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Department '{dept_name}' not found")
    return result


@app.get("/attrition/risk-profile")
def attrition_risk_profile(
    limit: int = Query(default=20, ge=1, le=100, description="Max rows returned (1-100)"),
):
    return db.get_attrition_risk_profile(engine=engine, limit=limit)