def sqlite_leak():
    """SQLite connection opened but never closed."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    cursor = conn.execute("SELECT 1")
    return cursor.fetchall()
