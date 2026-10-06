from database import get_connection

conn = get_connection()

print("Connect successfully!")

conn.close()