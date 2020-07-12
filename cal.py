import csv
from datetime import datetime, timedelta
from ics import Calendar, Event
from ics.parse import ContentLine
import json
import pytz
import requests
import sys

def convert_et_to_utc(date_obj):
    """Convert a datetime object from Eastern to UTC."""
    tz = pytz.timezone('US/Eastern')
    now = pytz.utc.localize(datetime.utcnow())
    is_edt =now.astimezone(tz).dst() != timedelta(0)

    if is_edt:
        return date_obj + timedelta(hours=4) 
    else:
        return date_obj + timedelta(hours=5) 

def get_match_csv(output_filename, url=None):
    """
    Access a publicly available googlesheet tab of match data and save as CSV.
    
    Arguments:
    output_filename -- Save CSV to this filename (str)
    url -- A specially crafted URL that provides a CSV export of a google sheet
           tab. Imports from settings.json if not provided. (str) (optional)
    """
    if not url:
        url = json.loads(open('settings.json').read())['match_csv_url'] 

    resp = requests.get(url)
    
    with open(output_filename, 'wb') as fd:
        for chunk in resp.iter_content(chunk_size=128):
            fd.write(chunk)

    return output_filename

def parse_matches_csv(csv_filename):
    """
    Parse through a CSV file of matches, convert to a dictionary of matches.

    Arguments:
    csv_filename -- Filename of CSV of matches to import. (str)
    """
    file = open(csv_filename)
    rows = csv.reader(file, delimiter=',')
    
    matches = []
    headers = {
        'Tier': None,
        'Circ': None,
        'Away Team': None,
        'Home Team': None,
        'Time (Eastern)': None,
        'Date': None,
        'Caster': None,
        'Co-casters': None,
        'Stream Link': None,
        'VOD Link': None,
        'Concatenate': None 
    }

    for idx, row in enumerate(rows):
    
        # Set Row Header Positions
        if idx == 0:
            for key in headers.keys():
                headers[key] = row.index(key)        

        else:
            match = {}

            for key, val in headers.items():
                match[key.lower()] = row[val]
            
            matches.append(match)

    return matches

def generate_calendar(matches):
    """
    Generate a .ics file matches from a dicationary.

    Arguments:
    matches -- A dictionary of matches.
    """
    cal = Calendar()
    
    # Set Calendar Metadata
    cal.extra.append(ContentLine(name='X-WR-CALNAME', value='KQB Matches'))  
    cal.extra.append(
        ContentLine(name='X-WR-CALDESC', value='Upcoming matches and events in the Killer Queen Black community.'))  
    cal.extra.append(ContentLine(name='X-PUBLISHED-TTL', value='PT15M'))  

    # Add all events to calendar
    for match in matches:

        try:
            event = Event()

            home_team = match['home team']
            away_team = match['away team']

            if (
                not home_team or not away_team):
                continue

            event.name = f"{match['tier']}{match['circ']} {away_team} at {home_team}"
            
            match_date = match['date']
            if ('TBD' in match_date
                or not match_date):
                continue

            # Set all TDB times to midnight
            if ('TBD' in match['time (eastern)']
                or not match['time (eastern)']):
                match_time = '00:00:00'
            else:
                match_time =  datetime.strptime(
                    match['time (eastern)'], '%I:%M %p').strftime('%H:%M:%S') 

            # Convert match time from ET to UTC
            et_match_dt = datetime.strptime(f'{match_date} {match_time}', '%Y-%m-%d %H:%M:%S')
            utc_match_dt = convert_et_to_utc(et_match_dt)

            event.begin = utc_match_dt.strftime('%Y-%m-%d %H:%M:%S')
            event.duration = timedelta(minutes=60)     

            description = ''

            # Tier and Circuit
            if match['tier'] and match['circ']:
                tier = f'Tier {match["tier"]}'

                circuit = ''
                circ_abbr = match['circ']

                if circ_abbr == 'W':
                    circuit = 'West'
                elif circ_abbr == 'E':
                    circuit = 'East'
                elif circ_abbr == 'Wa':
                    circuit = 'West Conference A'
                elif circ_abbr == 'Wb':
                    circuit = 'West Conference B'

                description += f'{tier} {circuit}'                

            # Add Caster Details to Description
            if match['caster']:
                description += f'\nCasted by {match["caster"]}'
            else:
                description += f'\nNo caster yet'
            
            if match['co-casters']:
                description += f'\nCo-Casted by {match["co-casters"]}'

            # Add Stream and VOD Links
            if match['stream link'] and 'TBD' not in match['stream link'] :
                link = match['stream link']

                if not link.startswith('http'):
                    link = f'https://{link}'
                                                
                description += f'\n{link}'
            
            if match['vod link']:
                description += f'\n\nVOD Link:\n{match["vod link"]}'

            event.description = description

            # Finalize Event
            cal.events.add(event)
        
        except ValueError:    
            pass
    
    with open('matches.ics', 'w') as cal_file:
        cal_file.writelines(cal)    

if __name__ == '__main__':
    """
    Run from command line

    Arguments:
    filename -- Filename to give where CSV of match data will be written.        
    """
    try:
        filename = sys.argv[1]  
    except IndexError:
        filename = 'matches.csv'

    get_match_csv(filename)
    matches = parse_matches_csv(filename)
    generate_calendar(matches)    