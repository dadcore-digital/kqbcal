import csv
import json
import requests
import sys


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
            row_data = []

            for key, val in headers.items():
                match = {}
                match[key] = row[val]
                row_data.append(match)
            
            matches.append(row_data)

    return matches

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
