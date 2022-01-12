# Import necessary libraries
import logging
import argparse
from utils import timeit
import requests
from bs4 import BeautifulSoup
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
        resp = requests.get(search_url)
        soup = BeautifulSoup(resp.text, features="lxml")

        st = str(soup.find('td', {'class': 'result_text'}).find('a', href=True))
        st = st[st.find('tt'):]
        imdbid = st[:st.find('/')]

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
    titles = []
    ratings = []
    s_data = []
    s = 0
    true_season = 0

    while len(ratings) == len(titles):
        # Go to new season
        s += 1

        url = 'https://www.imdb.com/title/{}/episodes?season={}'.format(imdbid, s)

        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, features="lxml")

        # Get the actual season from soup (to compare with season number in loop)
        true_season = soup.find('h3', {'id': 'episode_top', 'itemprop': 'name'})
        true_season = int(true_season.text[6:])
        if true_season != s:
            break

        logging.info("Scraping Season {}".format(s))

        # Get titles from soup
        title_list = soup.find_all('a', {'itemprop': 'name'})
        # Get ratings from soup
        rating_list = soup.find_all('span', {'class': 'ipl-rating-star__rating'})

        # Concatenate all titles
        for x in title_list:
            titles.append(x.text)
            s_data.append(s)

        # Concatenate all respective ratings
        new_ratings = []
        for x in rating_list:
            new_ratings.append(x.text)

        ratings.extend(new_ratings[::23])

    # Convert all ratings to float
    ratings = [float(i) for i in ratings]

    # Check if number of ratings and names are the same
    if len(ratings) != len(titles):
        titles = titles[:len(ratings)]
        s_data = s_data[:len(ratings)]

    # Put everything into pandas dataframe
    d = {'Title': titles, 'Season': s_data, 'Rating': ratings}
    df = pd.DataFrame(d)

    # If duplicates in title add season number
    dup = df['Title'].duplicated(keep=False)
    if not df[dup].empty:
        df.loc[dup, "Title"] = df[dup].apply(lambda x: str(x.Title) + ' (S' + str(x.Season) + ')', axis=1)

    return df


def plot_results(df, plot_mean=False, plot_reg=False):
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
        df = scrape(imdbid)
    except requests.exceptions.SSLError:
        logging.error("SSL certificate error")
    except requests.exceptions.ConnectionError:
        logging.error("No network connection")

    # Plot results
    if args.plot:
        plot_results(df, args.plot_mean, args.plot_reg)
