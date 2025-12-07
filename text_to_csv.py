import csv
import re

def extract_tickers_to_csv(input_file, output_file):
    tickers = []
    
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip().strip("'\"")
            if line.isalpha() and line.isupper() and 1 <= len(line) <= 5:
                tickers.append(line)
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(tickers)
    
    print(f"Extracted {len(tickers)} tickers: {', '.join(tickers)}")

if __name__ == "__main__":
    extract_tickers_to_csv("311-XLK.txt", "2B-10B_sector_tickers/technology_mid.csv")