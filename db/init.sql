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

CREATE TABLE items (
                    item_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price INT NOT NULL,
                    seller_email VARCHAR(255) NOT NULL,
                    seller_username VARCHAR(255) NOT NULL,
                    image_path VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- サンプルデータ
INSERT INTO items (name, price, seller_email, seller_username, image_path) VALUES
('dog', 10, 'asada@gmail.com', 'asada', '/images/a.jpg'),
('bodysoap', 1, 'asuka.dev33@gmail.com', 'asu-bridge93', '/images/b.jpg');