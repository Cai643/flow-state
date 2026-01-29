import sys
import os
from datetime import date, timedelta

sys.path.append(os.getcwd())
from app.data.web_report.report_generator import ReportGenerator

def main(days=7):
    end_d = date.today()
    start_d = end_d - timedelta(days=days-1)
    print(f"Range: {start_d} ~ {end_d}")

    gen = ReportGenerator()
    data = gen._fetch_data(start_d, end_d)
    fmt = gen._process_data(data, days)

    core_map = data.get('core_events_map', {})
    period_map = data.get('period_summary_map', {})

    for row in fmt['daily_rows_data']:
        d = row['date']
        events = core_map.get(d, [])
        focus = [e for e in events if e['category']=='focus']
        ent = [e for e in events if e['category']=='entertainment']
        print(f"\n== {d} ==")
        print(f"focus_count={len(focus)}, ent_count={len(ent)}")
        print(f"period_summary={period_map.get(d,'')}")
        print(f"raw_core_item={row['raw_core_item']}")

if __name__ == '__main__':
    main(7)

