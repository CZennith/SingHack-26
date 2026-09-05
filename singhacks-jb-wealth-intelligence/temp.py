import duckdb

con = duckdb.connect("db/wealth.duckdb", read_only=True)

tables = con.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'main'
    ORDER BY table_name
""").fetchall()

for (table,) in tables:
    count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    print(f"{table}: {count}")

con.close()
