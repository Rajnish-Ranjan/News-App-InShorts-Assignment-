import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import set_cred_environments, DBConnection


from datetime import datetime


def run_trending_mapreduce():
    set_cred_environments()

    db = DBConnection()
    conn_str = f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}?sslmode={os.environ['DB_SSLMODE']}"
    db.connect(conn_str)


    # Compute 'now' once
    current_time = datetime.now()

    # We use 0 decimal places for ~111km grid
    upsert_query = """
    INSERT INTO trending_feed_cache (bounding_box_id, article_id, trending_score, last_updated)
    SELECT
        CONCAT(ROUND(ST_Y(geolocation::geometry)::numeric, 0), '_', ROUND(ST_X(geolocation::geometry)::numeric, 0)) as bounding_box_id,
        article_id,
        SUM(
            (CASE event_type
                WHEN 'read' THEN 1.0
                WHEN 'like' THEN 2.0
                WHEN 'share' THEN 3.0
                WHEN 'comment' THEN 2.0
                WHEN 'dislike' THEN -1.0
                ELSE 0.0
            END) * EXP(-0.05 * (EXTRACT(EPOCH FROM (%s - created_at))/3600.0))
        ) as trending_score,
        %s
    FROM user_events
    GROUP BY bounding_box_id, article_id
    ON CONFLICT (bounding_box_id, article_id)
    DO UPDATE SET 
        trending_score = EXCLUDED.trending_score,
        last_updated = EXCLUDED.last_updated;
    """

    try:
        db.execute(upsert_query, (current_time, current_time))
        print("Cached trending feeds!")

        # Verify counts
        counts = db.query("SELECT COUNT(*) as cnt FROM trending_feed_cache;")
        print(
            f"Total unique (bounding_box, article) entries created: {counts[0]['cnt']}"
        )

    except Exception as e:
        print(f"Failed to calculate trending cache: {e}")


if __name__ == "__main__":
    run_trending_mapreduce()  # -- Call it via Cronjob every 30 minute
