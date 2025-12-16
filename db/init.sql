CREATE TABLE users (
    email VARCHAR(255) NOT NULL PRIMARY KEY,
    username VARCHAR(26) NOT NULL,
    password VARCHAR(255) NOT NULL,
    introduction VARCHAR(511),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- サンプルデータ
INSERT INTO users (email, username, password) VALUES 
('taro.yamada@example.com', 'Taro Yamada', 'taro'),
('saki.abe@example.com', 'Saki Abe', 'saki');

CREATE TABLE items (
                    item_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description VARCHAR(255),
                    cat0 VARCHAR(255),
                    cat1 VARCHAR(255),
                    cat2 VARCHAR(255),
                    price INT NOT NULL,
                    seller_email VARCHAR(255) NOT NULL,
                    seller_username VARCHAR(255) NOT NULL,
                    image_path VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- サンプルデータ
INSERT INTO items (name, description, cat0, cat1, cat2, price, seller_email, seller_username, image_path) VALUES
('dog', 'a small charm of a dog', 'a', 'b', 'c', 10, 'asada@gmail.com', 'asada', '/images/a.jpg'),
('bodysoap','a bottle of body soap of LUSH, grapefruit scented','a', 'b', 'c', 1, 'asuka.dev33@gmail.com', 'asu-bridge93', '/images/b.jpg');

CREATE TABLE purchase_hist (
    purchase_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    cat0 VARCHAR(255),
    cat1 VARCHAR(255),
    cat2 VARCHAR(255),
    price INT NOT NULL,
    seller_email VARCHAR(255) NOT NULL,
    seller_username VARCHAR(255) NOT NULL,
    buyer_email VARCHAR(255) NOT NULL,
    buyer_username VARCHAR(255) NOT NULL,
    image_path VARCHAR(255),
    sold_at DATETIME NOT NULL,
    bought_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
