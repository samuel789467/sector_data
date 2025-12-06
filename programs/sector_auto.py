import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import mplfinance as mpf
import matplotlib.pyplot as plt
import os
import glob

# --- Get all sector CSV files ---
sector_files = glob.glob("../lowcap_sector_tickers/*.csv")
print(f"Found {len(sector_files)} sector files to process\n")

for csv_filename in sector_files:
    print("=" * 80)
    print(f"PROCESSING: {csv_filename}")
    print("=" * 80)
    
    try:
        # --- Step 1: Load tickers from CSV ---
        sectorName = csv_filename.split("/")[-1].replace(".csv", "")
        
        tickers = pd.read_csv(csv_filename, header=None).iloc[0].dropna().tolist()
        if len(tickers) == 1:
            tickers = tickers[0].split(',')
        
        print(f"Total tickers loaded: {len(tickers)}")
        
        # --- Step 2: Download data ---
        print("Downloading price data...")
        data = yf.download(tickers, period='180d', interval='1d', group_by='ticker', threads=True, progress=False)
        
        # --- Step 3: Extract Close prices only for tickers with valid data ---
        valid_tickers = []
        missing_tickers = []
        
        for t in tickers:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    close_data = data[t]['Close'].dropna()
                else:
                    close_data = data['Close'].dropna()
                
                if len(close_data) > 0:
                    valid_tickers.append(t)
                else:
                    missing_tickers.append(t)
            except Exception:
                missing_tickers.append(t)
        
        print(f"✅ Valid tickers: {len(valid_tickers)}")
        print(f"❌ Missing or delisted tickers ({len(missing_tickers)}): {missing_tickers}")
        
        if len(valid_tickers) == 0:
            print(f"⚠️ No valid tickers for {sectorName}, skipping...\n")
            continue
        
        # Use only valid tickers
        adj_close = pd.concat([data[t]['Close'] for t in valid_tickers], axis=1)
        adj_close.columns = valid_tickers
        
        # --- Step 4: Get market caps safely ---
        market_caps = {}
        failed_caps = []
        
        for t in valid_tickers:
            try:
                info = yf.Ticker(t).info
                mc = info.get('marketCap')
                if mc:
                    market_caps[t] = mc
                else:
                    failed_caps.append(t)
            except Exception:
                failed_caps.append(t)
        
        print(f"✅ Market caps found: {len(market_caps)}")
        print(f"⚠️ Failed to fetch market cap for: {failed_caps}")
        
        if len(market_caps) == 0:
            print(f"⚠️ No market caps available for {sectorName}, skipping...\n")
            continue
        
        # --- Step 5: Filter tickers to those with valid market caps ---
        adj_close = adj_close[list(market_caps.keys())]
        
        # --- Step 6: Compute index FIRST ---
        total_mc = sum(market_caps.values())
        weights = {t: mc / total_mc for t, mc in market_caps.items()}
        
        returns = adj_close.pct_change().dropna()
        weighted_returns = returns.mul(pd.Series(weights), axis=1).sum(axis=1)
        index = (1 + weighted_returns).cumprod() * 100
        
        # --- Step 7: Calculate performance metrics with correlation filter ---
        print("\nCalculating top performers with correlation filter...")
        
        # Calculate correlations with the sector index
        correlations = {}
        for ticker in adj_close.columns:
            ticker_returns = adj_close[ticker].pct_change().dropna()
            aligned_data = pd.concat([ticker_returns, weighted_returns], axis=1).dropna()
            if len(aligned_data) > 20:
                corr = aligned_data.iloc[:, 0].corr(aligned_data.iloc[:, 1])
                correlations[ticker] = corr
        
        print(f"📊 Correlations calculated for {len(correlations)} tickers")
        
        # Filter tickers with at least 50% correlation
        high_corr_tickers = [t for t, corr in correlations.items() if corr >= 0.50]
        print(f"✅ Tickers with ≥50% correlation to sector index: {len(high_corr_tickers)}")
        
        if len(high_corr_tickers) == 0:
            print(f"⚠️ No tickers with ≥50% correlation for {sectorName}, skipping...\n")
            continue
        
        # Get the most recent trading day and calculate returns
        latest_price = adj_close[high_corr_tickers].iloc[-1]
        week_ago_price = adj_close[high_corr_tickers].iloc[-5] if len(adj_close) >= 5 else adj_close[high_corr_tickers].iloc[0]
        month_ago_price = adj_close[high_corr_tickers].iloc[-21] if len(adj_close) >= 21 else adj_close[high_corr_tickers].iloc[0]
        
        # Calculate percentage changes
        week_change = ((latest_price - week_ago_price) / week_ago_price * 100).dropna()
        month_change = ((latest_price - month_ago_price) / month_ago_price * 100).dropna()
        
        # Create performance dataframe
        performance = pd.DataFrame({
            'Ticker': week_change.index,
            'Week_Change_%': week_change.values,
            'Month_Change_%': month_change.values,
            'Correlation': [correlations[t] for t in week_change.index]
        })
        
        # Top 20 for the week
        top_week = performance.nlargest(20, 'Week_Change_%')[['Ticker', 'Week_Change_%', 'Correlation']].reset_index(drop=True)
        top_week.index = range(1, len(top_week) + 1)
        
        # Top 20 for the month
        top_month = performance.nlargest(20, 'Month_Change_%')[['Ticker', 'Month_Change_%', 'Correlation']].reset_index(drop=True)
        top_month.index = range(1, len(top_month) + 1)
        
        print("\n📈 TOP 20 PERFORMERS - LAST WEEK (≥50% Correlation)")
        print("-" * 60)
        print(top_week.to_string())
        
        print("\n📈 TOP 20 PERFORMERS - LAST MONTH (≥50% Correlation)")
        print("-" * 60)
        print(top_month.to_string())
        
        print(f"\n📊 CORRELATION STATISTICS")
        print("-" * 60)
        print(f"Average correlation (all tickers): {np.mean(list(correlations.values())):.2%}")
        print(f"Median correlation (all tickers): {np.median(list(correlations.values())):.2%}")
        print(f"Min correlation: {min(correlations.values()):.2%}")
        print(f"Max correlation: {max(correlations.values()):.2%}")
        
        # --- Step 8: Build synthetic OHLC for candlestick chart ---
        df = pd.DataFrame(index=index.index)
        df['Close'] = index
        df['Open'] = df['Close'].shift(1)
        df['High'] = df[['Open', 'Close']].max(axis=1) * (1 + np.random.uniform(0.001, 0.002, len(df)))
        df['Low'] = df[['Open', 'Close']].min(axis=1) * (1 - np.random.uniform(0.001, 0.002, len(df)))
        df.dropna(inplace=True)
        
        # --- Step 9: Save chart data to CSV ---
        base_filename = os.path.splitext(os.path.basename(csv_filename))[0]
        output_csv = f"../chart_data/{base_filename}.data.csv"
        df.to_csv(output_csv)
        print(f"\n💾 Chart data saved to: {output_csv}")
        
        # --- Step 10: Create and save PNG chart ---
        last_candle_date = df.index[-1]
        last_candle_str = last_candle_date.strftime('%Y-%m-%d %H:%M')
        chart_title = f'{sectorName} MA:25\nLast candle: {last_candle_str}'
        
        output_png = f"../chart_pics/{base_filename}.png"
        
        # Create the plot and save
        save_dict = dict(fname=output_png, dpi=100, bbox_inches='tight')
        
        mpf.plot(
            df,
            type='candle',
            style='charles',
            title=chart_title,
            ylabel='Index Value',
            mav=(25,),
            volume=False,
            figsize=(12, 6),
            tight_layout=True,
            savefig=save_dict
        )
        
        # Close the figure to free memory
        plt.close('all')
        
        print(f"📊 Chart saved to: {output_png}")
        print(f"📅 Last candle date: {last_candle_str}")
        print(f"\n✅ {sectorName} processed successfully!\n")
        
    except Exception as e:
        print(f"\n❌ ERROR processing {sectorName}: {str(e)}\n")
        continue

print("=" * 80)
print("ALL SECTORS PROCESSED!")