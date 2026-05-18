import sqlite3
m = sqlite3.connect("data/monitor.db")

# Check latest snapshots for all activities
cur = m.execute("""
    SELECT a.name, a.activity_type, sn.due_date, sn.version
    FROM activities a
    LEFT JOIN activity_snapshots sn ON sn.activity_id = a.id
    AND sn.version = (SELECT MAX(version) FROM activity_snapshots WHERE activity_id = a.id)
    ORDER BY a.name
""")
print("Latest snapshot per activity:")
for r in cur.fetchall():
    print(f"  [{r[1]:8s}] {r[0][:45]:45s} due={str(r[2]):25s} v{r[3]}")

m.close()
