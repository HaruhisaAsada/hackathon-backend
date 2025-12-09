CREATE TABLE users (
    email VARCHAR(255) NOT NULL PRIMARY KEY,
    username VARCHAR(26) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- サンプルデータ
INSERT INTO users (email, username, password) VALUES 
('taro.yamada@example.com', 'Taro Yamada', 'taro'),
('saki.abe@example.com', 'Saki Abe', 'saki');