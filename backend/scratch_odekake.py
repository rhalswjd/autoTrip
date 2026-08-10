from bs4 import BeautifulSoup

def main():
    with open('timetable.html', 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    
    # Let's find the rows or timetable cells
    # The timetable is typically grouped by hour
    hours = soup.select('.time-box') # Guessing class name
    print(f"Hours found: {len(hours)}")
    
    # Or just search for the trains
    trains = soup.select('.train-info')
    print(f"Trains found: {len(trains)}")
    
    for i, train in enumerate(trains[:3]):
        print(f"--- Train {i} Context ---")
        parent = train.parent
        # Go up a few levels to see the container
        print(parent.parent.prettify())

if __name__ == '__main__':
    main()
