import json
import os
import sys

import psycopg2
from psycopg2.extras import Json, execute_batch

# Add root dir to sys path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from utils import set_cred_environments
except ImportError:
    print("Could not import set_cred_environments from utils")
    sys.exit(1)


def create_table_and_insert_data():
    # Load credentials
    try:
        set_cred_environments()
    except Exception as e:
        print(f"Error loading environments: {e}")
        return

    print("Connecting to database...")
    try:
        db_url = os.getenv("NeonDB_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return

    # Create table
    create_table_query = """
    CREATE TABLE IF NOT EXISTS news_articles (
        id UUID PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        url TEXT,
        publication_date TIMESTAMP,
        source_name VARCHAR(255),
        category JSONB,
        relevance_score FLOAT,
        geolocation GEOGRAPHY(Point, 4326)
    );
    """

    # Create spatial index for fast querying
    create_index_query = """
    CREATE INDEX IF NOT EXISTS news_articles_geo_idx 
    ON news_articles USING GIST (geolocation);
    """

    # create search vector for title, description
    create_search_vector_query = """
    ALTER TABLE news_articles 
    ADD COLUMN search_vector tsvector 
    GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || coalesce(description, ''))) STORED;
    """

    # create inverted index
    create_inverted_index_query = """
    CREATE INDEX IF NOT EXISTS news_articles_inverted_idx 
    ON news_articles USING GIN (search_vector);
    """

    print(
        "Creating table 'news_articles' and spatial index and search vector and inverted index..."
    )
    cur.execute(create_index_query)
    cur.execute(create_search_vector_query)
    cur.execute(create_inverted_index_query)
    conn.commit()
    print("Table and index created successfully.")

    # Read json data
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "resources",
        "news_data.json",
    )
    if not os.path.exists(data_path):
        print(f"Data file not found at {data_path}")
        return

    print(f"Loading data from {data_path}...")
    with open(data_path, "r", encoding="utf-8") as f:
        news_data = json.load(f)

    # Insert data
    insert_query = """
    INSERT INTO news_articles (
        id, title, description, url, publication_date, source_name, category, relevance_score, geolocation
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, 
        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
    ) ON CONFLICT (id) DO NOTHING;
    """

    print("Inserting data in batches...")
    count = 0
    batch_size = 1000
    batch = []

    for item in news_data:
        # Lowercase categories
        raw_cats = item.get("category", [])
        lowered_cats = [c.lower() for c in raw_cats] if raw_cats else []
        category = Json(lowered_cats)

        # Lowercase title
        title = item.get("title")
        if title:
            title = title.lower()

        # Lowercase source_name
        source_name = item.get("source_name")
        if source_name:
            source_name = source_name.lower()

        # Check if coordinates exist
        lat = item.get("latitude")
        lon = item.get("longitude")

        if lat is None or lon is None:
            continue  # Skip inserting spatial data if missing

        batch.append(
            (
                item.get("id"),
                title,
                item.get("description"),
                item.get("url"),
                item.get("publication_date"),
                source_name,
                category,
                item.get("relevance_score"),
                lon,  # ST_MakePoint takes longitude first
                lat,
            )
        )

        # When batch size is reached, insert and commit
        if len(batch) >= batch_size:
            try:
                execute_batch(cur, insert_query, batch)
                conn.commit()
                count += len(batch)
                print(f"Inserted {count} records...")
                batch.clear()
            except Exception as e:
                print(f"Error inserting batch: {e}")
                conn.rollback()
                batch.clear()

    # Insert any remaining records
    if batch:
        try:
            execute_batch(cur, insert_query, batch)
            conn.commit()
            count += len(batch)
        except Exception as e:
            print(f"Error inserting final batch: {e}")
            conn.rollback()

    conn.commit()
    cur.close()
    conn.close()
    print(f"Successfully inserted {count} records into 'news_articles'.")


if __name__ == "__main__":
    create_table_and_insert_data()
