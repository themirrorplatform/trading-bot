#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db_path = 'src/trading_bot/data/events.sqlite'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("=== Tables in database ===")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check events table
    if tables:
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        print(f"\n=== Events Table ===")
        print(f"Total events: {count}")
        
        if count > 0:
            cursor.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
            print("\nEvents by type:")
            for event_type, cnt in cursor.fetchall():
                print(f"  {event_type}: {cnt}")
            
            cursor.execute("SELECT MAX(created_at) FROM events")
            latest = cursor.fetchone()[0]
            print(f"\nLatest event timestamp: {latest}")
            
            # Get last 3 events
            cursor.execute("SELECT event_id, event_type, stream_id, created_at FROM events ORDER BY created_at DESC LIMIT 3")
            print("\nLast 3 events:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} ({row[2]}) - {row[3]}")
        else:
            print("\n⚠️  No events in database - bot may not be running")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
