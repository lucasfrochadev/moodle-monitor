import sqlite3
base = "C:\\Users\\Admin\\Desktop\\moodle-monitor\\data"
m = sqlite3.connect(f"{base}\\monitor.db")

# Check Projeto - Final snapshots
tasks = ["Projeto - Final", "Controle Financeiro", "B2 - Site com BACKEND em PHP"]
for name in tasks:
    print(f"\n=== {name} ===")
    cur = m.execute("SELECT id, activity_type, url, course_id FROM activities WHERE name = ?", (name,))
    a = cur.fetchone()
    if not a:
        # try partial match
        cur = m.execute("SELECT id, activity_type, url, course_id FROM activities WHERE name LIKE ?", (f"%{name[:15]}%",))
        a = cur.fetchone()
    if not a:
        print("  NOT FOUND in monitor.db")
        continue
    print(f"  Type: {a[1]}, URL: {a[2]}")
    # All snapshots
    snaps = m.execute("""
        SELECT version, due_date, open_date, taken_at
        FROM activity_snapshots WHERE activity_id = ?
        ORDER BY version
    """, (a[0],)).fetchall()
    print(f"  Snapshots ({len(snaps)}):")
    for s in snaps:
        print(f"    v{s[0]}: due={s[1]}, open={s[2]}, taken={s[3]}")
    # Course
    crs = m.execute("SELECT fullname, moodle_course_id FROM courses WHERE id = ?", (a[3],)).fetchone()
    if crs:
        print(f"  Course: {crs[0]} (id={crs[1]})")

m.close()
