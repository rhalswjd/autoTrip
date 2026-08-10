from infrastructure.scrapers.timetable.odekake_parser import JROdekakeParser
from collections import Counter

def check_duplicates():
    html = open('/app/backend/timetable.html').read()
    parser = JROdekakeParser()
    deps = parser.parse(html)
    
    # Check for same time + same destination duplicates
    seen = Counter()
    for d in deps:
        key = f"{d['time']}_{d['train_name']}_{d['destination']}"
        seen[key] += 1
        
    dups = {k: v for k, v in seen.items() if v > 1}
    print(f"Duplicates: {dups}")

if __name__ == '__main__':
    check_duplicates()
