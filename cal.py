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

def get_sheet_csv(sheet_url_key, output_filename, url=None):
    """
    Access a publicly available googlesheet tab of match data and save as CSV.
    
    Arguments:
    sheet_url_key -- Key referencing settings.json the individual sheet to
                     export to CSV.
    output_filename -- Save CSV to this filename (str)
    url -- A specially crafted URL that provides a CSV export of a google sheet
           tab. Imports from settings.json if not provided. (str) (optional)
    """
    if not url:
        url = json.loads(open('settings.json').read())[sheet_url_key] 

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
                match[key.lower().replace(' ', '_')] = row[val]
            
            matches.append(match)

    return matches

def parse_teams_csv(csv_filename):
    """
    Parse through a CSV file of teams, convert to a dictionary of team data.

    Arguments:
    csv_filename -- Filename of CSV of matches to import. (str)
    """
    file = open(csv_filename)
    rows = csv.reader(file, delimiter=',')
    
    teams = []
    headers = {
        'Tier': None,
        'Circuit': None,
        'Team': None,
        'Match Wins': None,
        'Matches Played': None,
        'Set Wins': None,
        'Captain': None,
        'Members': []
    }

    for idx, row in enumerate(rows):
    
        # Set Row Header Positions
        if idx == 0:
            for key in headers.keys():
                headers[key] = row.index(key)        

        else:
            team = {}

            for key, val in headers.items():
                if key == 'Members':
                    team['members'] = row[12:19]  
                    
                    # Drop blank member entries
                    team['members'] = [x for x in team['members'] if x]
                else:
                    team[key.lower().replace(' ', '_')] = row[val]

            teams.append(team)

        # Calculate Extra Stats
        for team in teams:
            team['matches_lost'] = str(
                int(team['matches_played']) - int(team['match_wins']))

        # Add lookup-dict
        teams_dict = {}
        teams_dict['all'] = teams

        for team in teams:
            teams_dict[team['team']] = team 


    
    return teams_dict

def generate_calendar(matches, teams):
    """
    Generate a .ics file matches from a dicationary.

    Arguments:
    matches -- A list of dicts containing all matches. (list)
    teams -- A list of dicts containg all teams. (list)
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

            home_team = match['home_team']
            away_team = match['away_team']

            if (
                not home_team or not away_team):
                continue

            event.name = f"{match['tier']}{match['circ']} {away_team} at {home_team}"
            
            match_date = match['date']
            if ('TBD' in match_date
                or not match_date):
                continue

            # Set all TDB times to midnight
            if ('TBD' in match['time_(eastern)']
                or not match['time_(eastern)']):
                match_time = '00:00:00'
            else:
                match_time =  datetime.strptime(
                    match['time_(eastern)'], '%I:%M %p').strftime('%H:%M:%S') 

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

            # Stream Link
            link = ''
            if match['stream_link'] and 'TBD' not in match['stream_link'] :
                link = match['stream_link']

            if link:
                if not link.startswith('http'):
                    link = f'https://{link}'
                                                
                description += f'\n{link}'


            # Add Team Stats
            try:
                if (
                    match['away_team'] in teams.keys()
                    and match['home_team'] in teams.keys()
                ):
                    away_team = teams[match['away_team']]
                    home_team = teams[match['home_team']]

                    # Away Team Stats
                    description += f'\n\n[{match["away_team"]}]'
                    description += f"\n{away_team['match_wins']} Wins, {away_team['matches_lost']} Losses"
                    
                    description += '\n'
                    
                    for member in away_team['members']:
                        description += f'{member}, '
                    
                    description = description.rstrip(', ')

                    # Home Team Stats
                    description += f'\n\n[{match["home_team"]}]'
                    description += f"\n{home_team['match_wins']} Wins, {home_team['matches_lost']} Losses"
                    
                    description += '\n'
                    
                    for member in home_team['members']:
                        description += f'{member}, '
                    
                    description = description.rstrip(', ')

            except:
                pass                    

            # VOD Link            
            if match['vod_link']:
                description += f'\n\nVOD Link:\n{match["vod_link"]}'

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

    get_sheet_csv('match_csv_url', 'matches.csv')
    get_sheet_csv('teams_csv_url', 'teams.csv')
    matches = parse_matches_csv('matches.csv')
    teams = parse_teams_csv('teams.csv')
    generate_calendar(matches, teams)    