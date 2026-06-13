import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="DnD",
    user="postgres",
    password="701",
    port="7010"
)

cursor = conn.cursor()

print("Подключение успешно!")