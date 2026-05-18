import sqlite3
m = sqlite3.connect("data/monitor.db")

# DELETE all snapshots with wrong dates for FRONT-END and BACKEND
# Wrong = due=2026-05-13 (should be 2026-06-03)
m.execute("""
    DELETE FROM activity_snapshots 
    WHERE activity_id IN (
        SELECT id FROM activities 
        WHERE name LIKE '%BACKEND em PHP%' OR name LIKE '%FRONT-END EM REACT%'
    )
    AND (due_date = '2026-05-13 21:00:00' OR due_date IS NULL OR due_date = '')
""")
print("Deleted wrong snapshots for BACKEND and FRONT-END")

# Verify what's left
for name in ["BACKEND em PHP", "FRONT-END EM REACT"]:
    rows = m.execute("""
        SELECT sn.version, sn.due_date FROM activity_snapshots sn
        JOIN activities a ON a.id = sn.activity_id
        WHERE a.name LIKE ?
        ORDER BY sn.version
    """, (f"%{name[:15]}%",)).fetchall()
    if rows:
        for r in rows:
            print(f"  {name}: v{r[0]} due={r[1]}")
    else:
        print(f"  {name}: NO SNAPSHOTS")

m.commit()
m.close()
