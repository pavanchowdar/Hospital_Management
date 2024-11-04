import sqlite3

def get_db_connection():
    conn = sqlite3.connect('hospital_management.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
    return conn


def query_db(query, args=(), one=False):
    conn = get_db_connection()  # Make sure you're getting the connection here
    cur = conn.execute(query, args)
    rv = [dict(row) for row in cur.fetchall()]
    cur.close()
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=()):
    conn = sqlite3.connect('hospital_management.db')
    try:
        cur = conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()  # Ensure the connection is always closed
