import json
import random
import os
from datetime import datetime, timedelta


def generate_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_file = os.path.join(base_dir, "resources", "news_data.json")
    out_file = os.path.join(base_dir, "resources", "users_activities.json")

    print("Loading news articles...")
    with open(news_file, "r") as f:
        news_data = json.load(f)

    article_ids = [article["id"] for article in news_data if "id" in article]
    if not article_ids:
        print("No articles found!")
        return

    # Select a small subset of articles to be "viral" so they get more hits
    viral_articles = random.sample(article_ids, min(50, len(article_ids)))

    event_types = ["read", "share", "comment", "like", "dislike"]
    # Weighted probabilities to simulate real user behavior
    event_weights = [0.60, 0.05, 0.10, 0.20, 0.05]

    # Centers of population (simulating clusters)
    locations = [
        {"lat": 28.6139, "lon": 77.2090},  # Delhi
        {"lat": 19.0760, "lon": 72.8777},  # Mumbai
        {"lat": 12.9716, "lon": 77.5946},  # Bangalore
        {"lat": 25.1223, "lon": 85.4562},  # User location
    ]

    now = datetime.utcnow()
    activities = []

    print("Generating 8,000 synthetic events...")
    for _ in range(8000):
        # 30% chance to be a viral article, 70% chance any random article
        if random.random() < 0.3:
            art_id = random.choice(viral_articles)
        else:
            art_id = random.choice(article_ids)

        event = random.choices(event_types, weights=event_weights, k=1)[0]

        # Time distribution: more events closer to now
        # Random offset between 0 and 24 hours (86400 seconds)
        # We square the random number to skew towards recent events
        seconds_ago = (random.random() ** 2) * 86400
        event_time = now - timedelta(seconds=seconds_ago)

        base_loc = random.choice(locations)
        # Add slight jitter to location
        lat = base_loc["lat"] + random.uniform(-0.1, 0.1)
        lon = base_loc["lon"] + random.uniform(-0.1, 0.1)

        activities.append(
            {
                "article_id": art_id,
                "event_type": event,
                "timestamp": event_time.isoformat()
                + "Z",  # Explicitly mark as UTC ISO format
                "location": {"lat": round(lat, 4), "lon": round(lon, 4)},
            }
        )

    # Sort chronologically
    activities.sort(key=lambda x: x["timestamp"])

    with open(out_file, "w") as f:
        json.dump(activities, f, indent=2)

    print(f"Successfully wrote {len(activities)} events to {out_file}")


if __name__ == "__main__":
    generate_data()
