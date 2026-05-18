import sqlite3
m = sqlite3.connect("data/monitor.db")
# Fix the FRONT-END v14 snapshot
aid = "0db9f817-5afd-5e46-8ae9-cf925c2dd890"
m.execute("""
    UPDATE activity_snapshots 
    SET due_date = '2026-06-03 23:59:00',
        full_hash = 'FIXED_' || full_hash
    WHERE activity_id = ? AND version = 14
""", (aid,))
m.commit()
m.close()

# Also delete the wrong task from study.db so sync re-imports
s = sqlite3.connect("data/study.db")
s.execute("PRAGMA foreign_keys = ON")
r = s.execute("""
    SELECT t.id FROM tasks t
    JOIN activity_imports ai ON ai.task_id = t.id
    WHERE ai.source_activity_id = ?
""", (aid,)).fetchone()
if r:
    s.execute("DELETE FROM tasks WHERE id = ?", (r[0],))
    print(f"Deleted task {r[0][:8]} from study.db")
s.commit()
s.close()
print("Done. Run sync now.")
