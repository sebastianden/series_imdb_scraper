# Import necessary libraries
from bs4 import BeautifulSoup
import requests
import numpy as np
import pandas as pd
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style('whitegrid')

# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--title", action="store", required=True, dest="inp", help="Series Title")
args = parser.parse_args()
inp = args.inp

# Get IMDb ID
# Turn input into IMDb search url
inp = inp.replace(' ', '+')
search_url = "https://www.imdb.com/find?q={0}&ref_=nv_sr_sm".format(inp)

# Scrape search url for the IMDb ID of first search result
resp = requests.get(search_url)
soup = BeautifulSoup(resp.text,features="lxml")

st = str(soup.find('td',{'class':'result_text'}).find('a',href=True))
st = st[st.find('tt'):]
imdbid = st[:st.find('/')]

print('Found IMDb ID:', imdbid)

titles = []
ratings = []
s_data = []
s = 0
true_season = 0

while len(ratings)==len(titles) :
    # Go to new season
    s += 1
    
    url = 'https://www.imdb.com/title/{}/episodes?season={}'.format(imdbid, s)
    
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text,features="lxml")
    
    # Get the actual season from soup (to compare with season nmber in loop)
    true_season = soup.find('h3',{'id':'episode_top',  'itemprop':'name'})
    true_season = int(true_season.text[6:])
    if true_season != s:
        break
    
    print("Scraping Season {}".format(s))
    
    # Get titles from soup
    title_list = soup.find_all('a',{'itemprop':'name'})
    # Get ratings from soup
    rating_list = soup.find_all('span',{'class':'ipl-rating-star__rating'})

    # Concatenate all titles 
    for x in title_list:
        titles.append(x.text)
        s_data.append(s)

    # Concatenate all respective ratings
    for x in rating_list:
        #print(x.text)
        if len(x.text)==3:
            ratings.append(float(x.text))
 

# Check if number of ratings and names are the same
if len(ratings)!=len(titles):
    titles = titles[:len(ratings)]
    s_data = s_data[:len(ratings)]

# Put everything into pandas dataframe
d = {'Title':titles,'Season':s_data,'Rating':ratings}
df = pd.DataFrame(d)

# If duplicates in title add season number
dup = df['Title'].duplicated(keep=False)
if not df[dup].empty:
    df['Title'].loc[dup] = df[dup].apply(lambda x: str(x.Title)+' (S'+str(x.Season)+')',axis=1)
    
# Plot
plt.figure(figsize=(14,8))
g = sns.pointplot(x='Title', y='Rating', 
                 hue='Season', data=df,
                 join=True,
                 legend=False,
                 palette=sns.color_palette("husl",df['Season'][df.index[-1]]))
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()
