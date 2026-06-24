from google_play_scraper import reviews, Sort
import pandas as pd
# 1. Scrape using NEWEST, but grab a larger batch because we are going to throw a lot away

review_1,_ = reviews(app_id="com.zerodha.kite3", country= "IN",count=1000, filter_score_with=1)
review_2,_ = reviews(app_id="com.zerodha.kite3",country="IN",count=500, filter_score_with=2)
review_3,_ = reviews(app_id="com.zerodha.kite3",country="IN",count=200, filter_score_with=3)

# 2. Combine and Convert

review_combined = review_1 + review_2 + review_3
df = pd.DataFrame(review_combined)
df = df[['userName','score','at','content']]

# 3. THE DATA SCIENCE MAGIC: Filter out short "junk" reviews
# This keeps only rows where the 'content' string is longer than 50 characters
df = df[df['content'].str.len()>50]

# 4. Limit the final output to exactly 500 rows to match our scientific sample size
# (We sample proportionally: 300 1-star, 150 2-star, 50 3-star)

final_df = pd.concat([
    df[df['score']==1].head(300),
    df[df['score']==2].head(150),
    df[df['score']==3].head(50)
]
)    


# 5. Save the perfectly clean, recent, and highly detailed dataset
final_df.to_csv("raw_fintech_reviews.csv",index=None)
print(f"Successfully saved {len(final_df)} highly detailed recent reviews")


#print(df)
#df = df[['']]


