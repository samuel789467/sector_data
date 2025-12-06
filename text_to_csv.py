import csv
import re

def is_valid_ticker(symbol):
    """
    Check if a string is a valid ticker symbol.
    Valid tickers: 1-5 uppercase letters, no numbers or special chars
    """
    # Remove quotes if present
    symbol = symbol.strip().strip("'\"")
    
    # Check if it's purely alphabetic and uppercase (1-5 chars typically)
    if symbol.isalpha() and symbol.isupper() and 1 <= len(symbol) <= 5:
        return True
    return False

def extract_tickers_to_csv(input_file, output_file):
    """
    Read text file, extract valid ticker symbols, write to CSV.
    """
    tickers = []
    
    try:
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and lines containing 'SyntaxError' or numbers
                if not line or 'SyntaxError' in line or line.isdigit():
                    continue
                
                # Extract potential ticker (remove quotes)
                potential_ticker = line.strip("'\"")
                
                # Validate and add to list
                if is_valid_ticker(potential_ticker):
                    tickers.append(potential_ticker)
        
        # Write to CSV
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Ticker'])  # Header
            for ticker in tickers:
                writer.writerow([ticker])
        
        print(f"Successfully extracted {len(tickers)} valid ticker symbols to {output_file}")
        print(f"Tickers: {', '.join(tickers)}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except Exception as e:
        print(f"Error: {e}")

# Usage
if __name__ == "__main__":
    input_filename = "tickers.txt"  # Change this to your input file name
    output_filename = "tickers.csv"  # Change this to your desired output file name
    
    extract_tickers_to_csv(input_filename, output_filename)