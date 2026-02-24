import os
import sqlite3

BASE = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(BASE, 'medialert.db')

if not os.path.exists(DB):
    print(f"Database not found at: {DB}")
    raise SystemExit(1)

conn = sqlite3.connect(DB)
cur = conn.cursor()

print('Checking `feedback` table columns...')
cur.execute("PRAGMA table_info(feedback)")
cols = [row[1] for row in cur.fetchall()]
print('Columns:', cols)

if 'email' in cols:
    print('`email` column already exists — nothing to do.')
else:
    print('Adding `email` column to `feedback` table...')
    try:
        cur.execute("ALTER TABLE feedback ADD COLUMN email TEXT")
        conn.commit()
        print('Added `email` column successfully.')
    except Exception as e:
        print('Failed to add column:', e)

# show final schema
cur.execute("PRAGMA table_info(feedback)")
print('\nFinal feedback columns:')
for row in cur.fetchall():
    print(row)

conn.close()
print('\nMigration complete.')
