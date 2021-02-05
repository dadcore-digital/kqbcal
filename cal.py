import csv
import dateutil.parser as dp
from datetime import datetime, timedelta
from ics import Calendar, Event
from ics.parse import ContentLine
import json
import pytz
import requests
import sys


def get_api_data(api_path, params=None):
    """
    Return a list of results from the Buzz API and handle pagination.

    api_path -- Path to query from, e.g. `/matches` or `/events`. Should 
                include leading but NOT trailing slash. (str)
    params -- Querystring parameters to pass to API, e.g.
              `scheduled=true&league=Indy&season=Winter+2021` (str) (optional)
    """
    API_BASE = json.loads(open('settings.json').read())['API_BASE']
    url = f'{API_BASE}{api_path}?{params}'
    
    resp = requests.get(url).json()
    entries = []

    # Handle paginated results
    if resp['next']:

        while len(entries) < resp['count']:
            entries += (resp['results'])
            url = resp['next']
            if url:
                resp = requests.get(url).json()
    
    # Just one page!
    else:
        entries = resp['results']

    return entries

def get_matches(params):
    """
    Return match entries from the Buzz API.
    """
    return get_api_data('/matches', params)


def get_events(params=None):
    """
    Return event entries from the Buzz API.
    """
    return get_api_data('/events')
    

def generate_match_calendar(matches):
    """
    Generate a .ics file of matches from a list of dictionaries.

    Arguments:
    matches -- A list of dicts containing all matches. (list)
    """
    cal = Calendar()
    
    # Set Calendar Metadata
    cal.extra.append(ContentLine(name='X-WR-CALNAME', value='KQB Matches'))  
    cal.extra.append(
        ContentLine(name='X-WR-CALDESC', value='Upcoming matches and events in the Killer Queen Black community.'))  
    cal.extra.append(ContentLine(name='X-PUBLISHED-TTL', value='PT15M'))  

    # Add all events to calendar
    for match in matches:

        event = Event()

        home_team = match['home']
        away_team = match['away']
        
        if match['circuit']['name']:
            circuit_name = match['circuit']['name']
        else:
            circuit_name = match['circuit']['verbose_name']

        circuit_abbrev = f"{match['circuit']['tier']}{match['circuit']['region']}"
        
        # This should not happen anymore, but just to be safe.
        if (not home_team or not away_team): 
            continue
        
        event.name = f"{circuit_abbrev} {away_team['name']} @ {home_team['name']}"            

        event.begin = dp.parse(match['start_time'])
        event.duration = timedelta(minutes=60)     

        # Tier and Circuit
        description = f'🌐 {circuit_name}'

        # Add Caster Details to Description
        if match['primary_caster']:
            description += f'\n\n🎙️ Casted by {match["primary_caster"]["name"]}'

            if match['secondary_casters']:
                description += f'\nCo-Casted by '
                for cocaster in match['secondary_casters']:
                    description += cocaster + ','
                
                # Get rid of trailing comma
                description = description.rstrip(',')

            # Stream Link
            if match['primary_caster']['stream_link']:
                description += f"\n{match['primary_caster']['stream_link']}"
        
        # Away Team Stats
        description += f"\n\n🔷 {away_team['name']} [{away_team['wins']}W/{away_team['losses']}L]"
        
        description += '\n\n'
        
        for member in away_team['members']:
            description += f'{member}, '
        
        description = description.rstrip(', ')

        # Home Team Stats
        description += f"\n\n🔶 {home_team['name']} [{home_team['wins']}W/{home_team['losses']}L]"        
        description += '\n\n'
        
        for member in home_team['members']:
            description += f'{member}, '
        
        description = description.rstrip(', ')

        event.description = description

        # Finalize Event
        cal.events.add(event)
            
    with open('matches.ics', 'w') as cal_file:
        cal_file.writelines(cal) 


def generate_event_calendar(events):
    """
    Generate a .ics file of events from a list of dictionaries.

    Arguments:
    events -- A list of dicts containing all matches. (list)
    """
    cal = Calendar()
    
    # Set Calendar Metadata
    cal.extra.append(ContentLine(name='X-WR-CALNAME', value='KQB Events'))  
    cal.extra.append(
        ContentLine(name='X-WR-CALDESC', value='Upcoming matches and events in the Killer Queen Black community.'))  
    cal.extra.append(ContentLine(name='X-PUBLISHED-TTL', value='PT15M'))  

    # Add all events to calendar
    for entry in events:

        event = Event()

        event.name = entry['name']
        
        event.begin = dp.parse(entry['start_time'])
        if entry['duration']:
            date_obj = datetime.strptime(entry['duration'], '%H:%M:%S')
            delta = timedelta(
                hours=date_obj.hour, minutes=date_obj.minute,
                seconds=date_obj.second
            )
            event.duration = delta
        else:
            event.duration = timedelta(minutes=60)     

        # Tier and Circuit
        description = entry['description']

        if entry['links']:
            description += '\n\n[Event Links]\n'

            for link in entry['links']:
                description += f"\n{link['name']}:\n{link['url']}\n"

        event.description = description

        # Finalize Event
        cal.events.add(event)
            
    with open('events.ics', 'w') as cal_file:
        cal_file.writelines(cal)


if __name__ == '__main__':
    """
    Run from command line.

    Arguments:
    params -- API filter querystring parameters to pass to /matches/ endpoint.
    """
    if 'matches' in sys.argv[1]:
        params = sys.argv[2]
        matches = get_matches(params)      
        generate_match_calendar(matches)

    if 'events'in sys.argv[1]:
        events = get_events()
        generate_event_calendar(events)  

