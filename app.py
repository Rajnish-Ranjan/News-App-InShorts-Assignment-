from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import json
import psycopg
import sys
import os

from utils import set_cred_environments, LLM
from repositories import DBConnection
from services import QueryService, TrendingService
from models import (
    User,
    UserQuery,
    CategoryParams,
    ScoreParams,
    SourceParams,
    NearbyParams,
    SearchParams,
    SmartSearchParams,
    PaginationParams,
)
import uvicorn

app = FastAPI(title="News App Backend API")

@app.exception_handler(psycopg.Error)
async def psycopg_error_handler(request: Request, exc: psycopg.Error):
    return JSONResponse(
        status_code=503,
        content={"detail": "database unavailable"},
    )



@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(json.JSONDecodeError)
async def json_decode_error_handler(request: Request, exc: json.JSONDecodeError):
    return JSONResponse(
        status_code=422,
        content={"detail": "failed to parse query"},
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "invalid query parameters",
            "errors": exc.errors(include_url=False),
        },
    )


# Initialize environments and services
try:
    set_cred_environments()

    # Initialize DB connection
    db = DBConnection()
    conn_str = f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}?sslmode={os.environ['DB_SSLMODE']}"
    db.connect(conn_str)

    llm = LLM()

    query_service = QueryService(db=db, llm=llm)
    trending_service = TrendingService(db=db)
except Exception as e:
    print(f"Failed to initialize services: {e}")
    sys.exit(1)


def _build_user_input(
    params: PaginationParams, lat: float = None, lon: float = None
) -> dict:
    user_input = {}
    for key, value in params.model_dump(exclude_none=True).items():
        if key != "cursor":
            user_input[key] = value
    if lat is not None:
        user_input["lat"] = lat
    if lon is not None:
        user_input["lon"] = lon
    return user_input


@app.get("/news/api/v1/category")
def get_by_category(
    params: CategoryParams = Depends(),
    x_user_lat: float = Header(
        None, description="Latitude"
    ),
    x_user_lon: float = Header(
        None, description="Longitude"
    ),
):
    try:
        user = (
            User(x_user_lat, x_user_lon)
            if x_user_lat is not None and x_user_lon is not None
            else None
        )
        user_query = UserQuery(
            intents=["category"], entities=[], category=params.category, user=user
        )
        results, next_cursor, total_results = query_service.process_query(
            user_query,
            limit=params.limit,
            cursor_str=params.cursor,
        )
        user_input = _build_user_input(params, x_user_lat, x_user_lon)

        return {
            "status": "success",
            "total_results": total_results,
            "results_count": len(results),
            "user_input": user_input,
            "next_cursor": next_cursor,
            "articles": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/news/api/v1/score")
def get_by_score(
    params: ScoreParams = Depends(),
    x_user_lat: float = Header(
        None, description="Latitude"
    ),
    x_user_lon: float = Header(
        None, description="Longitude"
    ),
):
    try:
        user = (
            User(x_user_lat, x_user_lon)
            if x_user_lat is not None and x_user_lon is not None
            else None
        )
        user_query = UserQuery(
            intents=["score"], entities=[], score_threshold=params.threshold, user=user
        )
        results, next_cursor, total_results = query_service.process_query(
            user_query,
            limit=params.limit,
            cursor_str=params.cursor,
        )
        user_input = _build_user_input(params, x_user_lat, x_user_lon)

        return {
            "status": "success",
            "total_results": total_results,
            "results_count": len(results),
            "user_input": user_input,
            "next_cursor": next_cursor,
            "articles": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/news/api/v1/source")
def get_by_source(
    params: SourceParams = Depends(),
    x_user_lat: float = Header(
        None, description="Latitude"
    ),
    x_user_lon: float = Header(
        None, description="Longitude"
    ),
):
    try:
        user = (
            User(x_user_lat, x_user_lon)
            if x_user_lat is not None and x_user_lon is not None
            else None
        )
        user_query = UserQuery(
            intents=["source"], entities=[], source=params.source, user=user
        )
        results, next_cursor, total_results = query_service.process_query(
            user_query,
            limit=params.limit,
            cursor_str=params.cursor,
        )
        user_input = _build_user_input(params, x_user_lat, x_user_lon)

        return {
            "status": "success",
            "total_results": total_results,
            "results_count": len(results),
            "user_input": user_input,
            "next_cursor": next_cursor,
            "articles": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/news/api/v1/nearby")
def get_nearby(
    params: NearbyParams = Depends(),
    x_user_lat: float = Header(..., description="Latitude"),
    x_user_lon: float = Header(
        ..., description="Longitude"
    ),
):
    try:
        user = User(x_user_lat, x_user_lon)
        user_query = UserQuery(
            intents=["nearby"], entities=[], radius=params.radius, user=user
        )
        results, next_cursor, total_results = query_service.process_query(
            user_query,
            limit=params.limit,
            cursor_str=params.cursor,
        )
        user_input = _build_user_input(params, x_user_lat, x_user_lon)

        return {
            "status": "success",
            "total_results": total_results,
            "results_count": len(results),
            "user_input": user_input,
            "next_cursor": next_cursor,
            "articles": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/news/api/v1/search")
def get_by_keyword(params: SearchParams = Depends()):
    try:
        user_query = UserQuery(
            intents=["search"], entities=[], search_query=params.query
        )
        results, next_cursor, total_results = query_service.process_query(
            user_query, limit=params.limit, cursor_str=params.cursor
        )
        user_input = _build_user_input(params)

        return {
            "status": "success",
            "total_results": total_results,
            "results_count": len(results),
            "user_input": user_input,
            "next_cursor": next_cursor,
            "articles": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/news/api/v1/smart-search")
def smart_search_news(
    params: SmartSearchParams = Depends(),
    x_user_lat: float = Header(
        None, description="Latitude"
    ),
    x_user_lon: float = Header(
        None, description="Longitude"
    ),
):
    try:
        user = (
            User(x_user_lat, x_user_lon)
            if x_user_lat is not None and x_user_lon is not None
            else None
        )
        user_query = UserQuery.from_query(params.query, llm=query_service.llm)
        user_query.user = user
        results, next_cursor, total_results = query_service.process_query(
            user_query, limit=params.limit, cursor_str=params.cursor
        )
        user_input = _build_user_input(params, x_user_lat, x_user_lon)

        return {
            "status": "success",
            "total_results": total_results,
            "results_count": len(results),
            "user_input": user_input,
            "next_cursor": next_cursor,
            "articles": results,
        }
    except Exception as e:
        print(f"Error during smart search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/news/api/v1/trending")
def get_trending_news(
    params: PaginationParams = Depends(),
    x_user_lat: float = Header(
        ..., description="Latitude"
    ),
    x_user_lon: float = Header(
        ..., description="Longitude"
    ),
):
    try:
        results, next_cursor, total_results = trending_service.get_trending_news(
            user_lat=x_user_lat,
            user_lon=x_user_lon,
            limit=params.limit,
            cursor_str=params.cursor,
        )
        user_input = _build_user_input(params, x_user_lat, x_user_lon)

        return {
            "status": "success",
            "total_results": total_results,
            "results_count": len(results),
            "user_input": user_input,
            "next_cursor": next_cursor,
            "articles": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
