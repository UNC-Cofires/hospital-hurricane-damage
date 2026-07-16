import numpy as np
import pandas as pd
import requests
import trafilatura
import os
import sys
import time
import json

### *** HELPER FUNCTIONS *** ###

def get_article_text(url,timeout=15,sleep_seconds=0.1):
    """
    Simple function to 
    """

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
               'Accept-Language': 'en-US,en;q=0.9',
               'Accept-Encoding': 'gzip, deflate, br',
               'Connection': 'keep-alive',
               'Upgrade-Insecure-Requests': '1',
               'Cache-Control': 'max-age=0'}

    try: 
        res = requests.get(url,headers=headers,timeout=timeout)
        time.sleep(sleep_seconds)
        status_code = res.status_code
        
        if res.status_code == 200:
            text = trafilatura.extract(res.text, url=url, favor_recall=True)
            if text is None:
                text = pd.NA
        else:
            text = pd.NA
    except requests.exceptions.RequestException as e:
        status_code = -1
        text = pd.NA

    return(text,status_code)

### *** INITIAL SETUP *** ###

# Load configuration file
with open('config.json', 'r') as f:
    config = json.load(f)

# Get current working directory 
pwd = os.getcwd()

# Specify batch size
BATCH_SIZE = 100

# Get name of local LLM used to screen titles
MODEL_ID = sys.argv[1]
MODEL_NAME = MODEL_ID.split('/')[-1]
print(f'\nLocal LLM: {MODEL_NAME}\n')

# Get mediacloud search results that have passed title screening
title_screening_dir = os.path.join(pwd,f'mediacloud/title_screening/flooding/{MODEL_NAME}')
files = np.sort(os.listdir(title_screening_dir))
files = np.flip(files)
periods = np.array([f.split('_')[0] for f in files])
input_filepaths = np.array([os.path.join(title_screening_dir,f) for f in files])

# Create folder for output
outfolder = os.path.join(pwd,'mediacloud/article_text/first_pass')
os.makedirs(outfolder,exist_ok=True)

### *** PROCESS ARTICLES *** ###

for i in range(len(periods)):

    period = periods[i]
    input_filepath = input_filepaths[i]
    output_filepath = os.path.join(outfolder,f'{period}_article_text.parquet')
    
    print(f'\n*** Downloading article text from {period} ***\n',flush=True)
    
    # Load URLs of relevant articles
    article_data = pd.read_parquet(input_filepath).drop_duplicates()
    article_data = article_data[article_data['classification']==True]
    article_data = article_data[['id','url','title']]
    
    num_articles = len(article_data)
    
    # Previously-geocoded addresses
    if os.path.exists(output_filepath):
        output_data = pd.read_parquet(output_filepath)
        
        # Remove addresses that have already been geocoded
        article_data = pd.concat([article_data,output_data[article_data.columns]]).drop_duplicates(keep=False)
    else:
        output_data = None
    
    # Process data in batches
    while len(article_data) > 0:
    
        batch = article_data.iloc[:BATCH_SIZE]
    
        article_text_list = []
        
        for index, row in batch.iterrows():
            article_info = dict(row)
            text,status_code = get_article_text(article_info['url'])
            article_info['status_code'] = status_code
            article_info['text'] = text
            article_text_list.append(article_info)
        
        processed_batch = pd.DataFrame(article_text_list)
    
        # Save results
        if output_data is not None:
            output_data = pd.concat([output_data,processed_batch])
        else:
            output_data = processed_batch
        
        output_data.to_parquet(output_filepath)
    
        # Update list of remaining articles
        article_data = article_data.iloc[BATCH_SIZE:]
        
        # Print update
        num_processed = len(output_data)
        percent_processed = 100*(num_processed / num_articles)
        num_remaining = len(article_data)
        print(f'Number of URLs processed: {num_processed} / {num_articles} ({percent_processed:.2f}%). Number remaining: {num_remaining}',flush=True)