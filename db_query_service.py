import sqlite3
import pandas as pd

def execute_sql_query(db_path, sql_query):
    """Executes a SQL query against a SQLite database and returns a Pandas DataFrame."""
    try:
        conn = sqlite3.connect(db_path)
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        print(f"Database Error: {e}")
        return pd.DataFrame({"Error": [str(e)]})