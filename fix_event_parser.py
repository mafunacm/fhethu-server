import re
import json
from datetime import datetime


def parse_event_text(text):
    """
    Parse concatenated event text to extract title, location, date, and time.
    Example input: "Jesus Loves South AfricaThe Chosen Convention & Expo CentreSaturday, May 9, 202609:00"
    """
    # Common date patterns
    date_patterns = [
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})',
        r'(\d{1,2})\s+(\w+)\s+(\d{4})',
        r'(\w+)\s+(\d{1,2}),?\s+(\d{4})'
    ]
    
    # Time pattern
    time_pattern = r'(\d{1,2}:\d{2})'
    
    # Initialize results
    title = text
    location = ""
    date = ""
    time = "00:00"
    
    # Try to find time
    time_match = re.search(time_pattern, text)
    if time_match:
        time = time_match.group(1)
        # Remove time from text
        text = text[:time_match.start()] + text[time_match.end():]
    
    # Try to find date
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            date = date_match.group(0)
            # Split text at date position
            before_date = text[:date_match.start()].strip()
            after_date = text[date_match.end():].strip()
            
            # Usually: title + location before date, remaining location after date
            # Try to identify location by looking for venue-like keywords
            venue_keywords = ['Centre', 'Center', 'Stadium', 'Hall', 'Arena', 'Theatre', 
                            'Theater', 'Club', 'Venue', 'Park', 'ICC', 'Expo']
            
            # Check if there's a clear venue name
            for keyword in venue_keywords:
                if keyword in before_date:
                    # Find where the venue name likely starts
                    keyword_pos = before_date.rfind(keyword)
                    # Go back to find the start of the venue name
                    venue_start = keyword_pos
                    for i in range(keyword_pos - 1, -1, -1):
                        if i == 0 or (before_date[i].isupper() and before_date[i-1].islower()):
                            venue_start = i
                            break
                    
                    title = before_date[:venue_start].strip()
                    location = before_date[venue_start:].strip()
                    if after_date:
                        location += " " + after_date
                    break
            
            if not location and before_date:
                # Fallback: assume last capitalized phrase is location
                words = before_date.split()
                for i in range(len(words) - 1, -1, -1):
                    if words[i][0].isupper():
                        title = ' '.join(words[:i])
                        location = ' '.join(words[i:])
                        if after_date:
                            location += " " + after_date
                        break
            
            break
    
    # Clean up
    title = title.strip()
    location = location.strip()
    
    # If no date found but there's a time, the entire text might be malformed
    if not date and time != "00:00":
        # Just use the text before time as title
        title = text.strip()
    
    return {
        "title": title,
        "date": date,
        "time": time,
        "location": location
    }


def fix_events_file(input_file, output_file):
    """Fix the events in the given file by parsing the concatenated titles."""
    with open(input_file, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    fixed_events = []
    
    for event in events:
        if event.get('date') == '' and event.get('location') == '':
            # This event needs parsing
            parsed = parse_event_text(event['title'])
            event['title'] = parsed['title']
            event['date'] = parsed['date']
            event['time'] = parsed['time']
            event['location'] = parsed['location']
        
        fixed_events.append(event)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fixed_events, f, indent=2)
    
    return len(fixed_events)


if __name__ == "__main__":
    # Test with a few examples
    examples = [
        "Jesus Loves South AfricaThe Chosen Convention & Expo CentreSaturday, May 9, 202609:00",
        "Laerskool Park Koorfees 2026N.G.Moedergemeente MosselbaaiRuns fromTuesday, May 5, 202618:00",
        "East Coast Radio House + Garden ShowDurban ICCSaturday, June 27, 202610:00",
        "Once Upon A Time In JoburgRosefield Equestrian (Polo) ClubSaturday, May 23, 202612:00"
    ]
    
    print("Testing parser with examples:\n")
    for ex in examples:
        result = parse_event_text(ex)
        print(f"Original: {ex}")
        print(f"Parsed:")
        print(f"  Title: {result['title']}")
        print(f"  Location: {result['location']}")
        print(f"  Date: {result['date']}")
        print(f"  Time: {result['time']}")
        print()
    
    # Fix the actual files
    print("\nFixing sa_events.json...")
    count = fix_events_file('sa_events.json', 'sa_events_fixed.json')
    print(f"Fixed {count} events and saved to sa_events_fixed.json")
    
    print("\nFixing cache_events.json...")
    count = fix_events_file('cache_events.json', 'cache_events_fixed.json')
    print(f"Fixed {count} events and saved to cache_events_fixed.json")