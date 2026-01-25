import sqlite3
from datetime import datetime, date

def check_data():
    conn = sqlite3.connect('focus_app.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print('=== Daily Stats (Today) ===')
    today = date.today().strftime("%Y-%m-%d")
    print(f"Querying for: {today}")
    
    c.execute('SELECT * FROM daily_stats WHERE date = ?', (today,))
    rows = c.fetchall()
    for r in rows:
        print(dict(r))
        focus = r['total_focus_time']
        print(f"-> Focus: {focus}s = {round(focus/3600, 2)}h")

    print('\n=== Window Sessions Summary (By Day) ===')
    c.execute('''
        SELECT date(start_time) as day, count(*) as cnt, sum(duration) as dur 
        FROM window_sessions 
        GROUP BY date(start_time) 
        ORDER BY day DESC LIMIT 3
    ''')
    for r in c.fetchall():
        print(f"Day: {r['day']}, Count: {r['cnt']}, Sum: {r['dur']}s ({round(r['dur']/3600, 2)}h)")

    print('\n=== Top 5 Longest Sessions (Today) ===')
    c.execute('SELECT * FROM window_sessions WHERE date(start_time) = ? ORDER BY duration DESC LIMIT 5', (today,))
    for r in c.fetchall():
        print(f"ID: {r['id']}, App: {r['process_name']}, Dur: {r['duration']}s, Start: {r['start_time']}")

if __name__ == "__main__":
    check_data()
