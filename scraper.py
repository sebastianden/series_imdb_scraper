# Import necessary libraries
import logging
import argparse
import json
from utils import timeit
import requests
from bs4 import BeautifulSoup, SoupStrainer

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style('whitegrid')

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
        ratings = [float(r) for r in ratings]

        data.append({"Season": season, "Episodes": [{"Title": t, "Rating": r} for (t, r) in zip(titles, ratings)]})

    logging.info(json.dumps(data))

    return data


def plot_results(data, plot_mean=False, plot_reg=False):
    """
    Plot results as seaborn lineplot.

    Parameters
    ----------
    data: list of dicts
        List of episodes as dicts with season, title and rating

    plot_mean: bool
        Adds a horizontal line to indicate mean if true

    plot_reg: bool
        Adds a regression to indicate trend if true
    """

    table = []
    for season in data:
        table.extend([{"Season": season["Season"], "Title": episode["Title"], "Rating": episode["Rating"]}
                      for episode in season["Episodes"]])

    print(table)
    df = pd.DataFrame(table)
    # Plot
    plt.figure(figsize=(14, 8))
    sns.pointplot(x='Title', y='Rating', hue='Season', data=df, join=True, legend=False,
                  palette=sns.color_palette("husl", df['Season'][df.index[-1]]))
    if plot_mean:
        mean = df["Rating"].mean()
        plt.axhline(mean)
        plt.annotate("Mean: " + str(round(mean, 1)), (1, mean + 0.1))

    if plot_reg:
        # Polynomial regression
        y = df["Rating"].values
        x = [i for i in range(len(y))]
        model = np.poly1d(np.polyfit(x, y, 4))
        line = np.linspace(0, len(y) - 1, 100 * len(y))
        plt.plot(line, model(line), 'r')

    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    logging.basicConfig(format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
                        level=logging.INFO)

    # Read in command-line parameters
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--title", action="store", required=True, dest="inp", help="Series title")
    parser.add_argument("-p", "--plot", action="store_true", required=False, dest="plot", help="Make plot")
    parser.add_argument("-m", "--mean", action="store_true", required=False, dest="plot_mean", help="Add mean to plot")
    parser.add_argument("-r", "--regression", action="store_true", required=False, dest="plot_reg",
                        help="Add regression to plot")
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

# Plot results
if args.plot:
    plot_results(data, args.plot_mean, args.plot_reg)
