from repositories import DBConnection
from utils import encode_cursor, decode_cursor
from typing import Any
from models import User


class TrendingService:
    def __init__(self, db: DBConnection):
        self.db = db

    def get_trending_news(
        self,
        user_lat: float,
        user_lon: float,
        limit: int = 5,
        cursor_str: str = None,
    ) -> tuple[list[dict[str, Any]], str | None, int]:
        # Hash location to the nearest 100x100km grid matching the batch job
        bounding_box_id = f"{int(round(user_lat, 0))}_{int(round(user_lon, 0))}"

        cursor_data = decode_cursor(cursor_str)

        query = """
            SELECT 
                na.id, na.title, na.description, na.url, 
                na.publication_date, na.source_name, na.category, 
                tfc.trending_score, count(*) OVER() AS total_results
            FROM trending_feed_cache tfc
            JOIN news_articles na ON tfc.article_id = na.id
            WHERE tfc.bounding_box_id = %s
        """
        params = [bounding_box_id]

        if cursor_data:
            query += " AND (tfc.trending_score, na.id) < (%s, %s)"
            params.extend([cursor_data["v"], cursor_data["id"]])

        query += " ORDER BY tfc.trending_score DESC, na.id DESC LIMIT %s;"
        params.extend([limit + 1])

        results = self.db.query(query, tuple(params))
        total_results = results[0]["total_results"] if results else 0

        next_cursor = None
        if len(results) > limit:
            last_item = results[limit - 1]
            next_cursor = encode_cursor(last_item["trending_score"], last_item["id"])
            results.pop()

        for r in results:
            r.pop("total_results", None)
            r.pop("sort_value", None)
            r.pop("trending_score", None)

        return results, next_cursor, total_results
