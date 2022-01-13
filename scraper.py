# Import necessary libraries
import logging
import argparse
import json
from utils import timeit
import requests
from bs4 import BeautifulSoup, SoupStrainer


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

        # Scrape search url for the IMDb ID of first search result
        strainer = SoupStrainer('td', {'class': 'result_text'})
        resp = requests.get(search_url)
        soup = BeautifulSoup(resp.text, features='lxml', parse_only=strainer)

        imdbid = soup.find('a', href=True)
        imdbid = str(imdbid).split("/")[2]

        logging.info(f'Found IMDb ID: {imdbid}')
        return imdbid
    except AttributeError:
        logging.error("No valid IMDb ID found")


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
    while True:
        season += 1
        url = f'https://www.imdb.com/title/{imdbid}/episodes?season={season}'

        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, features='lxml')

        # Get the actual season from soup (to compare with season nmber in loop)
        true_season = soup.find('h3', {'id': 'episode_top', 'itemprop': 'name'})
        true_season = int(true_season.text.split()[1])
        if season != true_season:
            break

        logging.info(f"Scraping Season {season}")
        # Get titles from soup
        titles = [t.text for t in soup.find_all('a', {'itemprop': 'name'})]
        # Get ratings from soup
        ratings = [r.text for r in soup.find_all('span', {'class': 'ipl-rating-star__rating'})][::23]

        data.append({"Season": season, "Episodes": [{"Title": t, "Rating": r} for (t, r) in zip(titles, ratings)]})

    logging.info(json.dumps(data))

    return data


if __name__ == "__main__":
    logging.basicConfig(format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
                        level=logging.INFO)

    # Read in command-line parameters
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--title", action="store", required=True, dest="inp", help="Series title")
    args = parser.parse_args()

    try:
        # Get IMDb ID
        imdbid = get_id(args.inp)

        # Scrape IMDb
        data = scrape(imdbid)
    except requests.exceptions.SSLError:
        logging.error("SSL certificate error")
    except requests.exceptions.ConnectionError:
        logging.error("No network connection")
