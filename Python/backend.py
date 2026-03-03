import os
import psycopg2 as SQL
from dotenv import load_dotenv as env

load_dotenv()

SQLUserPassword = os.getenv("SQLTeamUserPassword")

conn = SQL.connect(
    host="localhost",
    database="CanbetBackend",
    user="SQLTeam",
    password=SQLUserPassword,
    port=5432
)

cursor = conn.cursor()

cursor.execute("SELECT version();")

cursor.execute("""CREATE TABLE  ()""")

conn.commit()

conn.close()