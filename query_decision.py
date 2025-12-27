import sqlite3
import json

conn = sqlite3.connect('data/events.sqlite')
cursor = conn.cursor()

# Get latest DECISION_1M event
cursor.execute("""
    SELECT payload_json FROM events 
    WHERE type = 'DECISION_1M' 
    ORDER BY rowid DESC 
    LIMIT 1
""")

row = cursor.fetchone()
if row:
    payload = json.loads(row[0])
    print(json.dumps(payload, indent=2))
else:
    print("No DECISION_1M events found")

conn.close()
