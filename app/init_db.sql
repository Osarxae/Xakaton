-- Создание таблицы (если её нет)
CREATE TABLE IF NOT EXISTS courts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,
    electronic_form_url TEXT
);

-- Вставка тестовых данных
INSERT INTO courts (name, type)
VALUES ('Мировой суд №1 Москвы', 'мировой');

-- Проверка данных
SELECT * FROM courts;