CREATE TABLE users (
       username CHARACTER VARYING PRIMARY KEY,
       is_admin BOOLEAN DEFAULT FALSE NOT NULL,
       secret CHARACTER(32) NOT NULL
);
