import sqlite3
from datetime import datetime, timezone

base = "C:\\Users\\Admin\\Desktop\\moodle-monitor\\data"
MONITOR = f"{base}\\monitor.db"
STUDY = f"{base}\\study.db"

# 1. FIX monitor.db - update latest snapshot's due_date
m = sqlite3.connect(MONITOR)
activity_id = "0db9f817-5afd-5e46-8ae9-cf925c2dd890"

# Current v13 has wrong due_date=2026-05-13, correct is 2026-06-03
m.execute("""
    UPDATE activity_snapshots 
    SET due_date = '2026-06-03 23:59:00',
        full_hash = 'FIXED_' || full_hash
    WHERE activity_id = ? AND version = 13
""", (activity_id,))
print(f"Fixed monitor.db: updated v13 due_date to 2026-06-03")
m.commit()

# Verify
cur = m.execute("SELECT version, due_date, full_hash FROM activity_snapshots WHERE activity_id = ? ORDER BY version DESC LIMIT 2", (activity_id,))
for r in cur.fetchall():
    print(f"  v{r[0]}: due={r[1]}, hash starts with: {r[2][:20] if r[2] else 'None'}")
m.close()

# 2. FIX study.db - reimport the task (delete old import first, let sync recreate)
s = sqlite3.connect(STUDY)
s.execute("PRAGMA foreign_keys = ON")

# Check if there's already a task or import record
cur = s.execute("SELECT id, task_id FROM activity_imports WHERE source_activity_id = ?", (activity_id,))
row = cur.fetchone()
if row:
    # Delete old task and import (CASCADE will handle activity_imports)
    s.execute("DELETE FROM tasks WHERE id = ?", (row[1],))
    print(f"Deleted existing task {row[1]} from study.db")
else:
    print("No existing import record in study.db")
s.commit()
s.close()

print("\nDone. Now run sync to recreate the task with correct due_date (2026-06-03)")
