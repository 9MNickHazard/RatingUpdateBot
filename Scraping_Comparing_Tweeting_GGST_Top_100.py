import sys
import subprocess
import pkg_resources

def install_requirements():
    required = {'tweepy', 'python-dotenv', 'pandas', 'requests','beautifulsoup4'}
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = required - installed

    if missing:
        print("Installing missing packages.")
        python = sys.executable
        subprocess.check_call([python, '-m', 'pip', 'install', *missing], stdout=subprocess.DEVNULL)
        print("Required packages installed successfully.")
    else:
        print("All required packages are already installed.")

install_requirements()

import os
import tweepy
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import re
from bs4 import BeautifulSoup
import requests

load_dotenv()

api_key = os.getenv('TWITTER_API_KEY')
api_secret = os.getenv('TWITTER_API_SECRET')
access_token = os.getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

client = tweepy.Client(
    consumer_key=api_key, 
    consumer_secret=api_secret,
    access_token=access_token, 
    access_token_secret=access_token_secret
)    

def scrape_rating_update():
    url = "https://puddle.farm/top/all"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to retrieve data from website")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")

    data = []

    headers = ['Rank', 'Name', 'Character', 'Rating', 'Games Played']

    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        
        rank = cols[0].text.strip()
        name = cols[1].text.strip()
        character = cols[2].text.strip()
        rating = cols[3].text.strip()
        games_played = cols[4].text.strip()

        data.append([rank, name, character, rating, games_played])

    df = pd.DataFrame(data, columns=headers)

    df['Name'] = df['Name'].apply(lambda x: re.split(r'\n', x)[0])
    df['Rating'] = df['Rating'].apply(lambda x: re.match(r'\d{4}', x).group() if re.match(r'\d{4}', x) else '')
    return df


def get_latest_csv(output_folder='output', current_csv=None):
    csv_files = [f for f in os.listdir(output_folder) if f.endswith('.csv') and f != current_csv]
    if not csv_files:
        return None
    latest_file = max(csv_files, key=lambda x: os.path.getctime(os.path.join(output_folder, x)))
    print(f"Latest CSV file found: {latest_file}")
    return os.path.join(output_folder, latest_file)


def process_rank_changes(rank_changes):
    processed_ranks = []
    
    for rank in rank_changes:
        if rank[0] == 0:
            processed_ranks.append(['No Change', rank[1], rank[2]])
        elif rank[0] < 0:
            processed_ranks.append([f"Up {abs(rank[0])}", rank[1], rank[2]])
        elif rank[0] > 0 and rank[0] < 100000:
            processed_ranks.append([f"Down {rank[0]}", rank[1], rank[2]])
        else:
            processed_ranks.append(['New', rank[1], rank[2]]) # changed to new
    
    return processed_ranks

def process_rating_changes(rating_changes):
    processed_ratings = []
    
    for rating in rating_changes:
        if rating[0] == 0:
            processed_ratings.append(['No Change', rating[1], rating[2]])
        elif rating[0] < 0:
            processed_ratings.append([rating[0], rating[1], rating[2]])
        elif rating[0] > 0 and rating[0] < 100000:
            processed_ratings.append([f"+{rating[0]}", rating[1], rating[2]])
        else:
            processed_ratings.append(['New', rating[1], rating[2]]) # changed to new from ''
    
    return processed_ratings

def tweet_changes(changes):
    tweets = []
    current_tweet = ""
    
    for change in changes:
        if len(current_tweet) + len(change) <= 280:
            current_tweet += change
        else:
            if current_tweet:
                tweets.append(current_tweet.strip())
            current_tweet = change
    
    if current_tweet:
        tweets.append(current_tweet.strip())
    
    first_tweet = client.create_tweet(text=tweets[0])
    last_tweet_id = first_tweet.data['id']
    
    for tweet in tweets[1:]:
        reply_tweet = client.create_tweet(
            text=tweet,
            in_reply_to_tweet_id=last_tweet_id
        )
        last_tweet_id = reply_tweet.data['id']



def main():
    path_to_old_csv = get_latest_csv()
    df_old = pd.read_csv(path_to_old_csv)
    df_new = scrape_rating_update()

    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/GGST_Comparison_{current_datetime}.csv"
    df_new.to_csv(filename, index=False)

    
    df_old['Rank'] = df_old['Rank'].astype('int64')
    df_old['Rating'] = df_old['Rating'].astype('int64')
    df_old['Games Played'] = df_old['Games Played'].astype('int64')

    df_new['Rank'] = df_new['Rank'].astype('int64')
    df_new['Rating'] = df_new['Rating'].astype('int64')
    df_new['Games Played'] = df_new['Games Played'].astype('int64')



    matches = []
    off_top_100 = []
    old_combinations = set()

    for i, old_row in df_old.iterrows():
        old_name = old_row['Name']
        old_character = old_row['Character']
        old_combinations.add((old_name, old_character))

        match = df_new[(df_new['Name'] == old_name) & (df_new['Character'] == old_character)]

        if not match.empty:
            old_list = [old_row['Rank'], old_row['Name'], old_row['Character'], 
                         old_row['Rating'], old_row['Games Played']]

            new_row = match.iloc[0]
            new_list = [new_row['Rank'], new_row['Name'], new_row['Character'], 
                         new_row['Rating'], new_row['Games Played']]

            matches.append([old_list, new_list])
        else:
            off_top_100.append((old_row['Rank'], old_row['Name'], old_row['Character'], 
                                old_row['Rating'], old_row['Games Played']))

    for i, new_row in df_new.iterrows():
        new_name = new_row['Name']
        new_character = new_row['Character']

        if (new_name, new_character) not in old_combinations:
            new_list = [new_row['Rank'], new_row['Name'], new_row['Character'], 
                         new_row['Rating'], new_row['Games Played']]
            matches.append([None, new_list])
    
    matches = [match for match in matches if match[0] is None or match[0][4] != match[1][4]]
    
    rating_changes = []
    played_games_changes = []
    rank_changes = []

    for mat in matches:
        if mat[0] is not None:
            rating_changes.append([(mat[1][3] - mat[0][3]), mat[0][3], mat[1][3]])
            played_games_changes.append([(mat[1][4] - mat[0][4]), mat[1][4]])
            rank_changes.append([mat[1][0] - mat[0][0], mat[0][0], mat[1][0]])
        if mat[0] is None:
            rating_changes.append([100000, 'New', mat[1][3]])
            played_games_changes.append(['', mat[1][4]])
            rank_changes.append([100000, 'New', mat[1][0]])     
    

    rank_changes = process_rank_changes(rank_changes)
    rating_changes = process_rating_changes(rating_changes)

    all_changes = []
    for i in range(len(matches)):
        change = (f"{matches[i][1][1]} ({matches[i][1][2]})\n"
                f"Rank: {rank_changes[i][1]}->{rank_changes[i][2]} ({rank_changes[i][0]})\n"
                f"Rating: {rating_changes[i][1]}->{rating_changes[i][2]} ({rating_changes[i][0]})\n"
                f"Games Played: {played_games_changes[i][1]} ({played_games_changes[i][0]})\n"
                f"\n")
        all_changes.append(change)

    tweet_changes(all_changes)
         
if __name__ == "__main__":
    main()
