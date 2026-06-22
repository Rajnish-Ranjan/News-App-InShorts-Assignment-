import json
import os
import sys

# Add root dir to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import set_cred_environments, DBConnection


def populate():
    set_cred_environments()

    db_url = os.getenv("NeonDB_URL")
    if not db_url:
        print("Error: NeonDB_URL environment variable is missing.")
        sys.exit(1)

    db = DBConnection()
    db.connect(db_url)

    # Load JSON
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "resources", "users_activities.json")

    print("Loading data from JSON...")
    with open(json_path, "r") as f:
        events = json.load(f)

    print(f"Preparing to insert {len(events)} rows...")
    # Convert dicts to tuples: (article_id, event_type, created_at, lon, lat)
    # ST_MakePoint takes (lon, lat)
    data_tuples = []
    for e in events:
        data_tuples.append(
            (
                e["article_id"],
                e["event_type"],
                e["timestamp"],
                e["location"]["lon"],
                e["location"]["lat"],
            )
        )

    insert_query = """
    INSERT INTO user_events (article_id, event_type, created_at, geolocation) 
    VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
    """

    print("Executing batch insert...")
    with db._conn.cursor() as cur:
        # Clear existing data, so we don't duplicate on re-runs
        cur.execute("TRUNCATE TABLE user_events")
        cur.executemany(insert_query, data_tuples)
        db._conn.commit()

    print("Successfully populated DB with 8,000 synthetic events!")


if __name__ == "__main__":
    populate()
