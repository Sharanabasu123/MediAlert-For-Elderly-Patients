import os
import sqlite3

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'medialert.db')

if not os.path.exists(DB):
    print(f"Database not found at: {DB}")
    raise SystemExit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print(f"Inspecting DB: {DB}\n")

# list tables
cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name")
rows = cur.fetchall()
print("Objects in DB:")
for r in rows:
    n = r['name']
    t = r['type']
    print(f"- {t}: {n}")

# print schema for tables
print('\nTable schemas:')
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
for r in cur.fetchall():
    print('\n--', r['name'])
    print(r['sql'])

# print counts for tables
print('\nRow counts:')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r['name'] for r in cur.fetchall()]
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) as c FROM {t}")
        c = cur.fetchone()['c']
    except Exception as e:
        c = f"error: {e}"
    print(f"{t}: {c}")

# sample rows from important tables
sample_tables = ['patients','caretakers','medicines','medicine_logs','reports','full_screen_alerts']
print('\nSample rows (up to 5)')
for t in sample_tables:
    if t in tables:
        print(f"\n-- {t}")
        try:
            cur.execute(f"SELECT * FROM {t} LIMIT 5")
            rows = cur.fetchall()
            if not rows:
                print("(no rows)")
            else:
                for r in rows:
                    print(dict(r))
        except Exception as e:
            print(f"(could not read {t}: {e})")

conn.close()
print('\nInspection complete.')
