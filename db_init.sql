CREATE TABLE users (
    username VARCHAR(64),
    password VARCHAR(128),
    email VARCHAR(512),
    created_at VARCHAR(32),
    blog_title VARCHAR(128),
    blog_url VARCHAR(512),
    auth VARCHAR(128),
    pre_auth VARCHAR(8)
);

CREATE TABLE files (
    username VARCHAR(64),
    url VARCHAR(2048),
    uptime INT,
    filesize INT,
    filename VARCHAR(2048)
);
