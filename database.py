import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port="5432",
        database="HTQL Cong Tac Tin Hoc",
        user="postgres",
        password="1234"
    )