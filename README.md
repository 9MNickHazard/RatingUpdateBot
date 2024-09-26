# RatingUpdateBot
A script that automates the scraping, cleaning, formatting, comparing and tweeting of changes in the Top 100 Guilty Gear Strive players, from this website: https://puddle.farm/top/all

When run, Scraping_Comparing_Tweeting_GGST_Top_100.py will grab the latest csv from the output folder within the current directory, scrape, format and then compare the new data from Rating Update with the old file and tweet out the results (to whichever account you have the credentials for in the .env file)

If you want to test the scraping without the comparison and tweeting, you can comment out all of the main() function except for this part:

def main():
df_new = scrape_rating_update()
current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"output/GGST_Comparison_{current_datetime}.csv"
df_new.to_csv(filename, index=False)


