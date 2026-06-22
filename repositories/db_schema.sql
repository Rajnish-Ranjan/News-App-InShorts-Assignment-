
-- Database Schema for InShorts News API


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

-- Index for fast nearby queries
CREATE INDEX IF NOT EXISTS news_articles_geo_idx 
ON news_articles USING GIST (geolocation);

-- Search Vector column
ALTER TABLE news_articles 
ADD COLUMN search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || coalesce(description, ''))) STORED;

-- Inverted index on the search vector
CREATE INDEX IF NOT EXISTS news_articles_inverted_idx 
ON news_articles USING GIN (search_vector);







-- User_events table, For regional trending caching
CREATE TABLE IF NOT EXISTS user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES news_articles(id) ON DELETE CASCADE,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('read', 'share', 'comment', 'like', 'dislike')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    geolocation GEOGRAPHY(Point, 4326)
);

-- Indexes for trending calculations
CREATE INDEX IF NOT EXISTS user_events_article_time_idx 
ON user_events(article_id, created_at);

CREATE INDEX IF NOT EXISTS user_events_geo_idx 
ON user_events USING GIST (geolocation);

-- Cache Trending Calculations
CREATE TABLE IF NOT EXISTS trending_feed_cache (
    bounding_box_id VARCHAR(50) NOT NULL,
    article_id UUID REFERENCES news_articles(id) ON DELETE CASCADE,
    trending_score FLOAT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (bounding_box_id, article_id)
);

-- Index on trending score
CREATE INDEX IF NOT EXISTS trending_feed_score_idx 
ON trending_feed_cache (bounding_box_id, trending_score DESC);

-- Global trending index
CREATE INDEX IF NOT EXISTS trending_feed_article_idx 
ON trending_feed_cache (article_id);
