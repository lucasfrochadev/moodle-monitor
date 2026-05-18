import sqlite3
from datetime import datetime, timezone

base = "C:\\Users\\Admin\\Desktop\\moodle-monitor\\data"
MONITOR = f"{base}\\monitor.db"
STUDY = f"{base}\\study.db"

fixes = {
    # (monitor name, correct due_date)
    "B2 - Site com BACKEND em PHP, conforme instru\u00e7\u00f5es": "2026-06-03 23:59:00",
    "Projeto - Final": "2026-05-22 22:45:00",
    "Controle Financeiro": "2026-05-20 00:00:00",
}

m = sqlite3.connect(MONITOR)

for name, correct_due in fixes.items():
    cur = m.execute("SELECT id FROM activities WHERE name = ?", (name,))
    row = cur.fetchone()
    if not row:
        print(f"NOT FOUND in monitor: {name}")
        continue
    aid = row[0]
    
    # Get latest snapshot
    sn = m.execute("SELECT version, due_date FROM activity_snapshots WHERE activity_id = ? ORDER BY version DESC LIMIT 1", (aid,)).fetchone()
    if sn:
        print(f"{name}: v{sn[0]} due={sn[1]} -> {correct_due}")
        m.execute("""
            UPDATE activity_snapshots 
            SET due_date = ?, full_hash = 'FIXED_' || full_hash
            WHERE activity_id = ? AND version = ?
        """, (correct_due, aid, sn[0]))
    
    # Delete old import in study.db so sync re-imports
    # (will do this in a separate step)

m.commit()
m.close()

# Now delete old study.db tasks for these activities
s = sqlite3.connect(STUDY)
s.execute("PRAGMA foreign_keys = ON")

for name, correct_due in fixes.items():
    # Find by matching title or source activity
    cur = s.execute("""
        SELECT t.id, ai.id FROM tasks t
        JOIN activity_imports ai ON ai.task_id = t.id
        WHERE t.title LIKE ?
    """, (f"%{name[:15]}%",))
    rows = cur.fetchall()
    if rows:
        for task_id, imp_id in rows:
            s.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            print(f"  Deleted task {task_id[:8]} from study.db")
    else:
        print(f"  No study.db entry found for {name}")

s.commit()
s.close()

print("\nDone. Now run sync to re-import with correct dates.")
