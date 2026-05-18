import sys, os
sys.path.insert(0, os.path.abspath("."))
from api.database import db
from api.services.sync_service import SyncService
from api.config import config

db.connect()
svc = SyncService(config.monitor_db_path)
result = svc.sync()
print(f"Imported: {result['imported']}")
print(f"Updated: {result['updated']}")
print(f"Errors: {result['errors']}")
print(f"Message: {result['message']}")

# Check if BACKEND is now in study.db
import sqlite3
conn = sqlite3.connect(config.study_db_path)
cur = conn.execute("SELECT title, due_date FROM tasks WHERE title LIKE '%BACKEND%'")
for r in cur.fetchall():
    print(f"  study.db: {r[0]}: due={r[1]}")
conn.close()
