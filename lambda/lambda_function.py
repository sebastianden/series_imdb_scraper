import logging
import argparse
import json
from utils import timeit
import requests
from bs4 import BeautifulSoup, SoupStrainer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

requests_session = requests.Session()

class ScrapingError(Exception): 
    def __init__(self, value): 
        self.value = value
    def __str__(self): 
        return "Error: %s" % self.value


@timeit
def get_id(inp):
    """
    Find the IMDb ID of the of the series provided as input.

    Parameters
    ----------
    inp: str
        Title of series

    Returns
    -------
    imdbid: str
        ID of series as string
    """
    try:
        # Get IMDb ID
        # Turn input into IMDb search url
        inp = inp.replace(' ', '+')
        
        search_url = "https://www.imdb.com/find?q={0}&ref_=nv_sr_sm".format(inp)

        print(search_url)
        
        # Scrape search url for the IMDb ID of first search result
        strainer = SoupStrainer('div', {'class': 'ipc-metadata-list-summary-item__tc'})
        #strainer = SoupStrainer('td', {'class': 'result_text'})
        
        headers = {
            'User-Agent': 'Custom'
        }
        
        resp = requests_session.get(search_url, headers=headers)
        #print(f"Response {resp.text}")

        soup = BeautifulSoup(resp.text, 'lxml', parse_only=strainer)
        print(soup)

        imdbid = soup.find('a', href=True)
        print(imdbid)
        imdbid = str(imdbid).split("/")[2]

        logger.info(f'Found IMDb ID: {imdbid}')
        return imdbid
    except (AttributeError, IndexError):
        raise ScrapingError("No valid IMDb ID found")
    except requests.exceptions.SSLError:
        raise ScrapingError("SSL certificate error")
    except requests.exceptions.ConnectionError:
        raise ScrapingError("No network connection")


@timeit
def scrape(imdbid):
    """
    Scrapes IMDb for the series episode rating.

    Parameters
    ----------
    imdbid: str
        ID of series as string

    Returns
    -------
    df: pandas.DataFrame
        Dataframe with Title, Season and Rating columns
    """
    season = 0
    data = []
    
    try:
        while True:
            season += 1
            url = f'https://www.imdb.com/title/{imdbid}/episodes?season={season}'
    
            resp = requests_session.get(url)
            strainer = SoupStrainer('div', {'class': 'clear', 'itemscope': ''})
            soup = BeautifulSoup(resp.text, 'lxml', parse_only=strainer)
    
            # Get the actual season from soup (to compare with season nmber in loop)
            true_season = soup.find('h3', {'id': 'episode_top', 'itemprop': 'name'})
            true_season = int(true_season.text.split()[1])
            if season != true_season:
                break
    
            logger.info(f"Scraping Season {season}")
            # Get titles from soup
            titles = [t.text for t in soup.find_all('a', {'itemprop': 'name'})]
            # Get ratings from soup
            ratings = [r.text for r in soup.find_all('span', {'class': 'ipl-rating-star__rating'})][::23]
            ratings = [float(r) for r in ratings]
            
            if ratings:
                data.append({"Season": season, 
                             "Episodes": [{"Title": t, "Rating": r} for (t, r) in zip(titles, ratings)]})
        return data
    except Exception:
        raise ScrapingError("Error occurred during scraping of episodes")
        


def lambda_handler(event, context):
    logger.info(event)
    if event["httpMethod"] == "POST":
        req = json.loads(event['body'])
    elif event["httpMethod"] == "GET":
        req = event["queryStringParameters"]
    elif event["httpMethod"] == "OPTIONS":
        return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
        }

    try:
        # Get IMDb ID
        imdbid = get_id(req["title"])

        # Scrape IMDb
        data = scrape(imdbid)
        logger.info(json.dumps(data))
        
        return {
            'statusCode': 200,
            'body': json.dumps(data),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            }
        }
    except ScrapingError as e:
        return {
            'statusCode': 400,
            'body': json.dumps(str(e)),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            }
        }
        
        

