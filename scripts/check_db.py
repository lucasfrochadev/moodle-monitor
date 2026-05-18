import sqlite3, os

conn = sqlite3.connect(os.path.join("data", "monitor.db"))

cur = conn.execute("""
    SELECT c.moodle_course_id, c.fullname, a.name, a.moodle_cmid
    FROM activities a
    JOIN courses c ON c.id = a.course_id
    WHERE c.moodle_course_id = 16016
    ORDER BY a.name
""")
rows = cur.fetchall()
print(f"Activities in course 16016: {len(rows)}")
for r in rows:
    print(f"  {r[2][:55]:55s} cmid={r[3]}")

conn.close()
