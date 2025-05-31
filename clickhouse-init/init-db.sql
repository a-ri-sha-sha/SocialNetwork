CREATE DATABASE IF NOT EXISTS stats;

CREATE TABLE IF NOT EXISTS stats.post_views (
    user_id UInt32,
    post_id UInt32,
    view_time DateTime,
    event_time DateTime
) ENGINE = MergeTree()
ORDER BY (post_id, view_time);

CREATE TABLE IF NOT EXISTS stats.post_likes (
    user_id UInt32,
    post_id UInt32,
    is_like UInt8,
    like_time DateTime,
    event_time DateTime
) ENGINE = MergeTree()
ORDER BY (post_id, like_time);

CREATE TABLE IF NOT EXISTS stats.post_comments (
    user_id UInt32,
    post_id UInt32,
    comment_id UInt32,
    comment_time DateTime,
    event_time DateTime
) ENGINE = MergeTree()
ORDER BY (post_id, comment_time);