from models import UserQuery, Location, User
from utils import (
    LLM,
    encode_cursor,
    decode_cursor,
)
import concurrent.futures


from repositories import DBQueryBuilder, DBConnection


class QueryService:
    def __init__(self, llm: LLM, db: DBConnection):
        self.llm = llm
        self.db = db
        self.dbquery_builder = DBQueryBuilder()


    def _inject_single_summary(self, article_detail: dict):
        try:
            summary = self.llm.generate_news_summary(
                categories=article_detail.get("category", []),
                title=article_detail.get("title", ""),
                description=article_detail.get("description", ""),
                url=article_detail.get("url", ""),
                date=str(article_detail.get("publication_date", "")),
            )
        except Exception as e:
            print(
                f"Error in injecting summary for {article_detail.get('title', '')}: {e}"
            )
            return article_detail

        # Create a new dict with the summary at the top, then the rest of the keys
        new_article_detail = {"llm_summary": summary}
        new_article_detail.update(article_detail)
        return new_article_detail

    def _inject_llm_summaries(self, res: list[dict]) -> list[dict]:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            # Add overall timeout of 60 seconds for the entire batch
            enhanced_res = list(
                executor.map(self._inject_single_summary, res, timeout=60)
            )
        except concurrent.futures.TimeoutError:
            print(
                "Timeout Error: LLM summarization took longer than 60 seconds. Returning original results."
            )
            enhanced_res = res
        except Exception as e:
            print("Error in injecting summary:", e)
            enhanced_res = res
        finally:
            # wait=False prevents the main thread from hanging while waiting for stuck LLM threads
            executor.shutdown(wait=False, cancel_futures=True)

        return enhanced_res

    def _extract_next_cursor(
        self, res: list[dict], limit: int, cursor_str: str | None
    ) -> str | None:
        next_cursor = None
        if len(res) > limit:
            # We have more results! Take the (limit)th item (0-indexed limit-1)
            last_item = res[limit - 1]
            sort_val = last_item.get("sort_value", last_item.get("relevance_score"))
            next_cursor = encode_cursor(sort_val, last_item["id"])
            # Remove the extra item
            res.pop()
        return next_cursor

    def process_query(
        self,
        user_query: UserQuery,
        limit: int = 5,
        cursor_str: str = None,
    ) -> tuple[list, str | None, int]:
        """
        Executes a query based on a pre-analyzed UserQuery object.
        """
        cursor_data = decode_cursor(cursor_str) if cursor_str else None

        sql_query, params = self.dbquery_builder.build_query(
            user_query, limit=limit, cursor_data=cursor_data
        )

        print("\nSQL Query:", sql_query)
        print("\nPARAMS:", params)
        res = self.db.query(sql_query, tuple(params))

        total_results = res[0]["total_results"] if res else 0

        next_cursor = self._extract_next_cursor(res, limit, cursor_str)

        for r in res:
            r.pop("total_results", None)
            r.pop("sort_value", None)

        enhanced_res = self._inject_llm_summaries(res)

        return enhanced_res, next_cursor, total_results


if __name__ == "__main__":
    from utils import set_cred_environments

    set_cred_environments()
    query_service = QueryService(LLM(), DBConnection())
    query = "What is happening in the world of AI in 2026?"
    user_query = UserQuery.from_query(query)
    result = query_service.process_query(user_query)
    print(result)
