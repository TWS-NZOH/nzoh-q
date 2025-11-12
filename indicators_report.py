# Working overlay options for all data, including cash value contributions to account value at product level
# [ ] Query events/campaigns and search for coupons used to generate orders. Mark with verticle line on report in all charts
## With all-company data, events timing could be optimized for when customers are most generally open to buying
## On a rep-territory level, same applies
# [ ] Pipe amazon thru sellingview
# [ ] NuHealth data not displaying for recent orders

import pandas_ta as ta
import pandas as pd
from simple_salesforce import Salesforce, SFBulkHandler
import plotly.graph_objects as go
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np
import os
import sys
import shutil
from pathlib import Path

def get_account_name(account_id):
    query = f"""
        SELECT Id, Name FROM Account WHERE Id = '{account_id}'
    """
    account = sf.query_all(query)
    account_name = account['records'][0]['Name']
    
    # Clean up account name - remove (DSS) prefix if present
    if account_name.startswith('(DSS) '):
        account_name = account_name[6:]  # Remove "(DSS) " prefix
    
    return account_name

def get_account_info(account_id):
    """
    Get account name and owner username
    Returns dict with 'name' and 'owner_username' keys
    """
    query = f"""
        SELECT Id, Name, Owner.Username FROM Account WHERE Id = '{account_id}'
    """
    account = sf.query_all(query)
    record = account['records'][0]
    
    owner_username = ''
    if record.get('Owner') and record['Owner'].get('Username'):
        owner_username = record['Owner']['Username']
    
    return {
        'name': record['Name'],
        'owner_username': owner_username
    }

def get_child_accounts(parent_account_id):
    """
    Find all child accounts that have this account as their parent.
    Uses MBL_Custom_ParentAccountId_18__c to find child accounts.
    """
    query = f"""
        SELECT 
            Id, 
            Name, 
            MBL_Is_Child_Account__c 
        FROM Account 
        WHERE MBL_Custom_ParentAccountId_18__c = '{parent_account_id}'
        AND MBL_Is_Child_Account__c = true
    """
    
    try:
        child_accounts = sf.query_all(query)
        print(f"Found {len(child_accounts['records'])} child accounts")
        return child_accounts['records']
    except Exception as e:
        print(f"Error fetching child accounts: {str(e)}")
        return []

def get_account_orders(account_id, start_date=None, end_date=None):
    # Get child accounts first
    child_accounts = get_child_accounts(account_id)
    all_account_ids = [account_id] + [acc['Id'] for acc in child_accounts]
    
    # Build date filter if dates are provided
    date_filter = ""
    if start_date:
        date_filter += f" AND MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    if end_date:
        date_filter += f" AND MBL_Order_Shipped_Time__c <= {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    
    # Create account ID filter
    account_filter = "AccountId IN ('" + "','".join(all_account_ids) + "')"
    
    # Modify query to include Account.Name
    query = f"""
        SELECT 
            Id, 
            MBL_Order_Shipped_Time__c, 
            TotalAmount, 
            MBL_Total_Number_of_Products__c,
            AccountId,
            Account.Name,
            Type
        FROM Order 
        WHERE {account_filter}
        {date_filter}
        ORDER BY MBL_Order_Shipped_Time__c ASC
    """
    
    try:
        orders = sf.query_all(query)
        
        # Print summary of orders found
        print(f"\nOrder Summary:")
        print(f"Total orders found: {len(orders['records'])}")
        
        # Group orders by account
        orders_by_account = {}
        for order in orders['records']:
            acc_id = order['AccountId']
            acc_name = order['Account']['Name']
            if acc_id not in orders_by_account:
                orders_by_account[acc_id] = {'name': acc_name, 'count': 0}
            orders_by_account[acc_id]['count'] += 1
        
        # Print breakdown
        for acc_id, info in orders_by_account.items():
            print(f"  {info['name']}: {info['count']} orders")
            
        return orders['records']
        
    except Exception as e:
        print(f"Error fetching orders: {str(e)}")
        return []

def get_order_quantities(order_ids):
    """
    Get total quantities and prices from OrderItems for given Order IDs using Bulk API
    Returns a dictionary with quantity and price information
    """
    if not order_ids:
        return {}
    
    # Update query to include price information
    query = """
        SELECT 
            OrderId, 
            SUM(Quantity) total_quantity,
            SUM(TotalPrice) total_price,
            AVG(UnitPrice) avg_unit_price
        FROM OrderItem 
        WHERE OrderId IN ('{}')
        GROUP BY OrderId
    """.format("','".join(order_ids))
    
    try:
        # Execute bulk query using sf.bulk
        job = sf.bulk.OrderItem.query(query)
        results = list(job)
        
        # Create dictionary mapping Order ID to quantity and price info
        order_data = {
            record['OrderId']: {
                'quantity': float(record['total_quantity']),
                'total_price': float(record['total_price']),
                'unit_price': float(record['avg_unit_price'])
            }
            for record in results
        }
        
        return order_data
        
    except Exception as e:
        print(f"Bulk API Error: {str(e)}")
        print("Falling back to regular query with batched IDs...")
        
        # Fallback: Process in smaller batches
        batch_size = 100
        order_data = {}
        
        for i in range(0, len(order_ids), batch_size):
            batch_ids = order_ids[i:i + batch_size]
            order_id_string = "','".join(batch_ids)
            
            query = f"""
                SELECT 
                    OrderId, 
                    SUM(Quantity) total_quantity,
                    SUM(TotalPrice) total_price,
                    AVG(UnitPrice) avg_unit_price
                FROM OrderItem 
                WHERE OrderId IN ('{order_id_string}')
                GROUP BY OrderId
            """
            
            batch_results = sf.query_all(query)
            batch_data = {
                record['OrderId']: {
                    'quantity': float(record['total_quantity']),
                    'total_price': float(record['total_price']),
                    'unit_price': float(record['avg_unit_price'])
                }
                for record in batch_results['records']
            }
            order_data.update(batch_data)
        
        return order_data

def create_ohlcv_from_orders(orders, resolution='1M', ma_window=90):
    """
    Create OHLCV DataFrame showing how orders influence the quarterly moving average
    
    Parameters:
    - orders: Salesforce order records
    - resolution: Time period grouping ('3D', '1W', '2W', '1M')
    - ma_window: Moving average window in days (default 90 for quarterly)
    """
    freq_map = {
        '3D': '3D',
        '1W': 'W',
        '2W': '2W',
        '1M': 'M'
    }
    freq = freq_map[resolution]

    # Get order IDs and their quantities/prices
    order_ids = [order['Id'] for order in orders]
    order_data = get_order_quantities(order_ids)
    
    # Convert orders to DataFrame and sort by date
    df = pd.DataFrame(orders)
    df['MBL_Order_Shipped_Time__c'] = pd.to_datetime(df['MBL_Order_Shipped_Time__c'])
    df['TotalAmount'] = pd.to_numeric(df['TotalAmount'])
    
    # Add quantities and prices to DataFrame
    df['volume'] = df['Id'].map(lambda x: order_data.get(x, {}).get('quantity', 0))
    df['unit_price'] = df['Id'].map(lambda x: order_data.get(x, {}).get('unit_price', 0))
    df['volume'] = df['volume'].fillna(0)
    df['unit_price'] = df['unit_price'].fillna(0)
    
    df = df.sort_values('MBL_Order_Shipped_Time__c')
    
    # Calculate daily cumulative account value
    daily_df = df.set_index('MBL_Order_Shipped_Time__c')
    daily_df = daily_df.resample('D').agg({
        'TotalAmount': 'sum',
        'volume': 'sum',
        'unit_price': 'mean'  # Take mean of unit price for the day
    }).fillna(method='ffill')  # Forward fill unit prices
    
    # Calculate simple MA without normalization
    daily_df['MA'] = daily_df['TotalAmount'].rolling(
        window=ma_window, 
        min_periods=1
    ).mean()
    
    # Find first valid MA date (where we have full window)
    first_valid_ma = daily_df.index[ma_window-1] if len(daily_df) >= ma_window else None
    if first_valid_ma is None:
        print("Warning: Not enough data for MA calculation")
        return pd.DataFrame()  # Return empty frame if not enough data
        
    print(f"\nFirst valid MA date: {first_valid_ma.date()}")
    
    # Group by specified frequency for candlesticks
    grouped = df.groupby(pd.Grouper(key='MBL_Order_Shipped_Time__c', freq=freq)).agg({
        'TotalAmount': list,
        'volume': 'sum',
        'unit_price': 'mean'  # Take mean of unit price for the period
    })
    
    # Initialize OHLCV DataFrame
    ohlcv = pd.DataFrame(index=grouped.index)
    ohlcv['volume'] = grouped['volume']
    ohlcv['unit_price'] = grouped['unit_price'].fillna(method='ffill')  # Forward fill unit prices
    
    # Initialize is_live column (marks current open candle)
    ohlcv['is_live'] = False
    
    # Get the last available date with data
    last_data_date = daily_df.index[-1]
    
    # Process periods including current open candle
    for idx in grouped.index:
        if idx < first_valid_ma:
            continue
            
        period_start = idx
        period_end = idx + pd.Timedelta(freq)
        
        # Check if this is the current/open candle (period extends beyond available data)
        is_current_candle = period_end > last_data_date
        
        if is_current_candle:
            # LIVE CANDLE: Use current data through today
            print(f"  📊 Including LIVE candle: {period_start.date()} - {period_end.date()} (current through {last_data_date.date()})")
            
            # Get all MA data from period start through today
            period_ma = daily_df.loc[period_start:last_data_date, 'MA']
            
            if len(period_ma) == 0 or period_start not in daily_df.index:
                continue
            
            ma_start = daily_df.loc[period_start, 'MA']
            ma_current = daily_df['MA'].iloc[-1]  # Current MA value (today)
            
            # Set OHLC values using live data
            ohlcv.at[idx, 'open'] = ma_start
            ohlcv.at[idx, 'close'] = ma_current  # Live close value
            ohlcv.at[idx, 'high'] = period_ma.max()
            ohlcv.at[idx, 'low'] = period_ma.min()
            ohlcv.at[idx, 'is_live'] = True
            
        else:
            # CLOSED CANDLE: Use complete period data
            if period_end > daily_df['MA'].last_valid_index():
                continue
                
            period_orders = grouped.at[idx, 'TotalAmount']
            if not isinstance(period_orders, list) or len(period_orders) == 0:
                continue
            
            # Get MA values for closed candle
            ma_start = daily_df.loc[period_start, 'MA']
            ma_end = daily_df.loc[period_end, 'MA'] if period_end in daily_df.index else ma_start
            
            # Set OHLC values
            ohlcv.at[idx, 'open'] = ma_start
            ohlcv.at[idx, 'close'] = ma_end
            period_ma = daily_df.loc[period_start:period_end, 'MA']
            ohlcv.at[idx, 'high'] = period_ma.max()
            ohlcv.at[idx, 'low'] = period_ma.min()
            ohlcv.at[idx, 'is_live'] = False
    
    # Remove any periods without valid data
    ohlcv = ohlcv.dropna(subset=['open', 'close', 'high', 'low'])
    
    # Print analysis for valid periods only
    print(f"\nMoving Average Analysis:")
    print(f"Total valid periods: {len(ohlcv)}")
    live_candles = ohlcv['is_live'].sum()
    if live_candles > 0:
        print(f"  ✨ Including {live_candles} LIVE candle(s) with current data")
    print(f"Periods with declining MA: {(ohlcv['close'] < ohlcv['open']).sum()}")
    print(f"Periods with rising MA: {(ohlcv['close'] > ohlcv['open']).sum()}")
    
    # Calculate volume SMA
    ohlcv['volume_sma'] = ta.sma(ohlcv['volume'], length=14)
    
    return ohlcv

def calculate_indicators(df, MA_length=20):
    """
    Calculate all technical indicators needed for plotting
    Returns DataFrame with added indicator columns and simulated decay data
    """
    # First check if we have the required OHLC columns
    required_columns = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_columns):
        print("Warning: Missing required OHLC columns for indicator calculation")
        df['insufficient_data'] = True
        return df
    
    # Initialize bbands to None
    bbands = None
    
    # Add indicator columns only if we have enough data
    if len(df) >= MA_length:
        try:
            df[f'sma_{MA_length}'] = ta.sma(df['close'], length=MA_length)
            df[f'ema_{MA_length}'] = ta.ema(df['close'], length=MA_length)
        except Exception as e:
            print(f"Warning: Could not calculate MA indicators: {str(e)}")
    
    # Bollinger Bands - require at least 20 points
    if len(df) >= 20:
        try:
            # Match simple_report_app exactly: use std=2.0 parameter
            bbands = ta.bbands(df['close'], length=20, std=2.0)
            if bbands is not None and not bbands.empty:
                # Debug: Check what columns we actually got
                if 'BBU_20_2.0' not in bbands.columns:
                    print(f"Debug: ta.bbands() returned columns: {list(bbands.columns)}")
                    print(f"Debug: DataFrame shape: {bbands.shape}, type: {type(bbands)}")
                    print(f"Debug: Looking for BBU_20_2.0, BBM_20_2.0, BBL_20_2.0")
                    # Try to find columns with similar names
                    upper_cols = [c for c in bbands.columns if 'BBU' in str(c) or 'upper' in str(c).lower()]
                    middle_cols = [c for c in bbands.columns if 'BBM' in str(c) or 'middle' in str(c).lower()]
                    lower_cols = [c for c in bbands.columns if 'BBL' in str(c) or 'lower' in str(c).lower()]
                    print(f"Debug: Found upper-like columns: {upper_cols}")
                    print(f"Debug: Found middle-like columns: {middle_cols}")
                    print(f"Debug: Found lower-like columns: {lower_cols}")
                    raise KeyError(f"BBU_20_2.0 column not found. Available columns: {list(bbands.columns)}")
                
                # Match simple_report_app exactly: access columns directly
                df['bb_upper'] = bbands['BBU_20_2.0']
                df['bb_middle'] = bbands['BBM_20_2.0']
                df['bb_lower'] = bbands['BBL_20_2.0']
                
                # Calculate decay simulation here while we have the BB data
                latest_close = df['close'].iloc[-1]
                latest_bb_lower = df['bb_lower'].iloc[-1]
                latest_bb_middle = df['bb_middle'].iloc[-1]
                
                # Get the last 90 periods for simulation
                close_values = df['close'].iloc[-90:].values
                current_ma = np.mean(close_values)
                
                # Function to simulate next period's MA only
                def simulate_next_period(values):
                    new_values = np.append(values[1:], 0)  # Remove oldest, add 0
                    new_ma = np.mean(new_values)
                    return new_values, new_ma
                
                # Initialize simulation results
                df['days_until_lower_breach'] = 0
                df['days_until_middle_breach'] = 0
                
                # Simulate for lower band if above it
                if latest_close > latest_bb_lower:
                    simulation_values = close_values.copy()
                    periods = 0
                    max_periods = 90  # Maximum 90 3-day periods
                    
                    while periods < max_periods:
                        simulation_values, new_ma = simulate_next_period(simulation_values)
                        if new_ma <= latest_bb_lower:
                            break
                        periods += 1
                    
                    df['days_until_lower_breach'] = periods * 3  # Convert to days
                
                # Simulate for middle band if above it
                if latest_close > latest_bb_middle:
                    simulation_values = close_values.copy()
                    periods = 0
                    max_periods = 90  # Maximum 90 3-day periods
                    
                    while periods < max_periods:
                        simulation_values, new_ma = simulate_next_period(simulation_values)
                        if new_ma <= latest_bb_middle:
                            break
                        periods += 1
                    
                    df['days_until_middle_breach'] = periods * 3  # Convert to days
            elif bbands is None:
                print(f"Debug: ta.bbands() returned None for {len(df)} data points")
            elif bbands.empty:
                print(f"Debug: ta.bbands() returned empty DataFrame for {len(df)} data points")
        except Exception as e:
            print(f"Warning: Could not calculate Bollinger Bands: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # RSI - requires at least 14 points
    if len(df) >= 14:
        try:
            df['rsi'] = ta.rsi(df['close'], length=14)
            if len(df) >= 28:  # Need at least 28 points for RSI MA
                df['rsi_ma'] = ta.sma(df['rsi'], length=14)
        except Exception as e:
            print(f"Warning: Could not calculate RSI: {str(e)}")
    
    # MACD - requires at least 26 points
    if len(df) >= 26:
        try:
            macd = ta.macd(df['close'])
            if macd is not None:
                df['macd'] = macd['MACD_12_26_9']
                df['macd_signal'] = macd['MACDs_12_26_9']
                df['macd_hist'] = macd['MACDh_12_26_9']
        except Exception as e:
            print(f"Warning: Could not calculate MACD: {str(e)}")
    
    # Mark if we have sufficient data
    df['insufficient_data'] = False
    
    return df

def get_account_order_products(account_id, start_date=None, end_date=None):
    """
    Get OrderItem records with product details for an account with cascading product name fallbacks
    """
    date_filter = ""
    if start_date:
        date_filter += f" AND Order.MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    if end_date:
        date_filter += f" AND Order.MBL_Order_Shipped_Time__c <= {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    
    query = f"""
        SELECT 
            Id,
            Order.MBL_Order_Shipped_Time__c,
            Order.TotalAmount,
            Product2Id,
            Product_Name__c,
            Product2.Name,
            Product2.ProductCode,
            Quantity,
            TotalPrice,
            UnitPrice
        FROM OrderItem 
        WHERE Order.AccountId = '{account_id}'
        {date_filter}
        ORDER BY Order.MBL_Order_Shipped_Time__c ASC
    """
    order_products = sf.query_all(query)
    
    # Apply cascading product name fallback logic to each record
    for record in order_products['records']:
        product_name = (record.get('Product_Name__c') or '').strip()
        product2_name = ''
        product2_code = ''
        
        if record.get('Product2'):
            product2_name = (record['Product2'].get('Name') or '').strip()
            product2_code = (record['Product2'].get('ProductCode') or '').strip()
        
        # Use Product_Name__c if available and non-empty
        if product_name:
            final_name = product_name
        # Otherwise try Product2.Name
        elif product2_name:
            final_name = product2_name
            print(f"  ℹ Using Product2.Name for Product2Id {record['Product2Id']}: {final_name}")
        # Last resort: use ProductCode
        elif product2_code:
            final_name = product2_code
            print(f"  ⚠ Using ProductCode for Product2Id {record['Product2Id']}: {final_name}")
        else:
            final_name = f"Unknown Product ({record['Product2Id']})"
            print(f"  ✗ No name found for Product2Id {record['Product2Id']}")
        
        # Update the record with the final name
        record['Product_Name__c'] = final_name
    
    return order_products['records']

def create_product_ohlcv(order_products, product_id, resolution='3D', ma_window=90, pricebook_prices=None):
    """
    Create OHLCV DataFrame for a specific product
    
    Args:
        order_products: List of OrderItem records
        product_id: Product2Id to filter for
        resolution: Time period grouping ('3D', '1W', '2W', '1M')
        ma_window: Moving average window in days
        pricebook_prices: Dict mapping Product2Id to current pricebook unit price (optional)
    """
    # Filter for specific product
    product_orders = [
        order for order in order_products 
        if order['Product2Id'] == product_id
    ]
    
    if not product_orders:
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(product_orders)
    
    # Extract nested Order fields
    df['date'] = pd.to_datetime([order['Order']['MBL_Order_Shipped_Time__c'] for order in product_orders])
    df['OrderTotalAmount'] = [order['Order']['TotalAmount'] for order in product_orders]
    df['TotalPrice'] = pd.to_numeric(df['TotalPrice'])
    df['Quantity'] = pd.to_numeric(df['Quantity'])
    
    # Determine unit price to use
    if pricebook_prices and product_id in pricebook_prices:
        # Use current pricebook price for all calculations
        current_unit_price = pricebook_prices[product_id]
        df['UnitPrice'] = current_unit_price
        print(f"    Using pricebook price: ${current_unit_price:.2f}")
    else:
        # Fallback to historical OrderItem prices
        df['UnitPrice'] = pd.to_numeric(df['UnitPrice'])
        avg_historical_price = df['UnitPrice'].mean()
        print(f"    Using historical average price: ${avg_historical_price:.2f}")
    
    # Sort by date
    df = df.sort_values('date')
    
    # Resample to daily and fill gaps
    daily_df = df.set_index('date').resample('D').agg({
        'TotalPrice': 'sum',
        'Quantity': 'sum',
        'UnitPrice': 'mean'  # Keep consistent unit price
    }).fillna(method='ffill')  # Forward fill unit prices
    
    # Calculate simple MA without normalization
    daily_df['MA'] = daily_df['TotalPrice'].rolling(
        window=ma_window,
        min_periods=1
    ).mean()
    
    # Find first valid MA date (where we have full window)
    first_valid_ma = daily_df.index[ma_window-1] if len(daily_df) >= ma_window else None
    if first_valid_ma is None:
        return None  # Not enough data
    
    # Group by resolution
    freq_map = {
        '3D': '3D',
        '1W': 'W',
        '2W': '2W',
        '1M': 'M'
    }
    freq = freq_map[resolution]
    
    grouped = df.groupby(pd.Grouper(key='date', freq=freq)).agg({
        'TotalPrice': list,
        'Quantity': 'sum'
    })
    
    # Create OHLCV DataFrame
    ohlcv = pd.DataFrame(index=grouped.index)
    ohlcv['volume'] = grouped['Quantity']
    ohlcv['unit_price'] = daily_df['UnitPrice'].resample(freq).mean().fillna(method='ffill')
    
    # Initialize is_live column (marks current open candle)
    ohlcv['is_live'] = False
    
    # Get the last available date with data
    last_data_date = daily_df.index[-1]
    
    # Calculate OHLC values including current open candle
    for idx in grouped.index:
        if idx < first_valid_ma:
            continue
            
        period_start = idx
        period_end = idx + pd.Timedelta(freq)
        
        # Check if period start is valid
        if period_start not in daily_df.index:
            continue
        
        # Check if this is the current/open candle
        is_current_candle = period_end > last_data_date
        
        if is_current_candle:
            # LIVE CANDLE: Use current data through today
            period_data = daily_df.loc[period_start:last_data_date, 'MA']
            
            if len(period_data) < 1:
                continue
            
            ma_start = period_data.iloc[0]
            ma_current = daily_df['MA'].iloc[-1]  # Current MA value
            
            # Set OHLC values using live data
            ohlcv.at[idx, 'open'] = ma_start
            ohlcv.at[idx, 'close'] = ma_current  # Live close value
            ohlcv.at[idx, 'high'] = period_data.max()
            ohlcv.at[idx, 'low'] = period_data.min()
            ohlcv.at[idx, 'is_live'] = True
            
        else:
            # CLOSED CANDLE: Use complete period data
            if period_end > daily_df.index[-1]:
                continue
                
            # Get MA values - handle case where we might not have enough data points
            period_data = daily_df.loc[period_start:period_end, 'MA']
            if len(period_data) < 2:
                continue
                
            ma_start = period_data.iloc[0]
            ma_end = period_data.iloc[-1]
            
            ohlcv.at[idx, 'open'] = ma_start
            ohlcv.at[idx, 'close'] = ma_end
            ohlcv.at[idx, 'high'] = period_data.max()
            ohlcv.at[idx, 'low'] = period_data.min()
            ohlcv.at[idx, 'is_live'] = False
    
    ohlcv = ohlcv.dropna()
    
    # Add volume SMA calculation before returning
    ohlcv['volume_sma'] = ta.sma(ohlcv['volume'], length=14)
    
    return ohlcv

def get_pricebook_prices(product_ids):
    """
    Get current unit prices from Pricebook for given Product2Ids
    Returns dict mapping Product2Id to unit price
    """
    if not product_ids:
        return {}
    
    print(f"\n🔍 Fetching pricebook prices for {len(product_ids)} products...")
    
    # First, get the standard pricebook ID
    try:
        std_pricebook = sf.query("SELECT Id FROM Pricebook2 WHERE IsStandard = true LIMIT 1")
        if not std_pricebook['records']:
            print("  ⚠️  Warning: No standard pricebook found, falling back to historical prices")
            return {}
        
        pricebook_id = std_pricebook['records'][0]['Id']
        print(f"  Using Standard Pricebook: {pricebook_id}")
    except Exception as e:
        print(f"  ⚠️  Error getting standard pricebook: {str(e)}")
        return {}
    
    # Query PricebookEntry for all products
    product_id_list = "','".join(product_ids)
    query = f"""
        SELECT Product2Id, UnitPrice, IsActive, Product2.Name
        FROM PricebookEntry
        WHERE Pricebook2Id = '{pricebook_id}'
        AND Product2Id IN ('{product_id_list}')
        AND IsActive = true
    """
    
    try:
        results = sf.query_all(query)
        price_map = {}
        
        for record in results['records']:
            product_id = record['Product2Id']
            unit_price = float(record['UnitPrice'])
            product_name = record['Product2']['Name'] if record.get('Product2') else 'Unknown'
            price_map[product_id] = unit_price
            print(f"  ✓ {product_name}: ${unit_price:.2f}")
        
        # Report any products not found in pricebook
        missing = set(product_ids) - set(price_map.keys())
        if missing:
            print(f"  ⚠️  {len(missing)} products not found in pricebook (will use historical prices)")
        
        print(f"  ✓ Found pricebook prices for {len(price_map)}/{len(product_ids)} products\n")
        return price_map
        
    except Exception as e:
        print(f"  ⚠️  Error querying pricebook entries: {str(e)}")
        return {}

def get_account_products(account_id, start_date, end_date):
    """
    Get unique products ordered by an account with full product name fallbacks
    """
    query = f"""
        SELECT 
            Product2Id,
            Product_Name__c,
            Product2.Name,
            Product2.ProductCode
        FROM OrderItem 
        WHERE Order.AccountId = '{account_id}'
        AND Order.MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}
        AND Order.MBL_Order_Shipped_Time__c <= {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}
    """
    products = sf.query_all(query)
    
    # Create dictionary of unique products with cascading name fallback
    unique_products = {}
    for record in products['records']:
        product_id = record['Product2Id']
        if product_id not in unique_products:
            # Cascade through available name fields - handle None values
            product_name = (record.get('Product_Name__c') or '').strip()
            
            # Debug output for each product
            print(f"Debug: Product2Id {product_id}")
            print(f"  - Product_Name__c: '{record.get('Product_Name__c')}'")
            print(f"  - Product2: {record.get('Product2')}")
            
            # If Product_Name__c is empty, try Product2.Name
            if not product_name and record.get('Product2'):
                product_name = (record['Product2'].get('Name') or '').strip()
                if product_name:
                    print(f"  ✓ Using Product2.Name: {product_name}")
            
            # If still empty, try Product2.ProductCode
            if not product_name and record.get('Product2'):
                product_name = (record['Product2'].get('ProductCode') or '').strip()
                if product_name:
                    print(f"  ⚠ Using ProductCode: {product_name}")
            
            # Last resort - query Product2 directly from Salesforce
            if not product_name:
                print(f"  ⚠ All name fields empty, querying Product2 directly...")
                try:
                    product_direct = sf.query(f"SELECT Name, ProductCode, Description FROM Product2 WHERE Id = '{product_id}'")
                    if product_direct['records']:
                        prod_record = product_direct['records'][0]
                        product_name = (prod_record.get('Name') or '').strip()
                        if not product_name:
                            product_name = (prod_record.get('ProductCode') or '').strip()
                        if not product_name:
                            product_name = (prod_record.get('Description') or '').strip()
                        if product_name:
                            print(f"  ✓ Retrieved from Product2 direct query: {product_name}")
                except Exception as e:
                    print(f"  ✗ Error querying Product2 directly: {str(e)}")
            
            # Final fallback
            if not product_name:
                product_name = f'Unknown Product ({product_id})'
                print(f"  ✗ No name found, using: {product_name}")
            
            unique_products[product_id] = product_name
    
    print(f"\nFound {len(unique_products)} unique products for account")
    return unique_products

def consolidate_product_data(analyses, resolution_freq, analysis_start_date, end_date_timestamp):
    """
    Consolidate all product data to ensure consistent time periods across all products.
    Returns a dictionary of {date: {product_name: value}}
    """
    # Create a uniform date range
    consolidated_range = pd.date_range(
        start=analysis_start_date,
        end=end_date_timestamp,
        freq=resolution_freq
    )
    
    # Initialize the consolidated data structure
    consolidated_data = {date: {} for date in consolidated_range}
    
    # Process each product's data
    for product_name, df in analyses.items():
        if product_name == 'Account Overview' or df is None or df.empty:
            continue
            
        print(f"Consolidating data for {product_name}: {len(df)} original data points")
        
        # For each date in our consolidated range, find the matching product value
        for target_date in consolidated_range:
            if target_date in df.index:
                # Direct match
                consolidated_data[target_date][product_name] = df.loc[target_date, 'close']
            else:
                # Find the most recent value before this date
                mask = df.index <= target_date
                if mask.any():
                    latest_value = df[mask]['close'].iloc[-1]
                    consolidated_data[target_date][product_name] = latest_value
    
    # Count unique products for debugging
    all_products = set()
    for date_data in consolidated_data.values():
        all_products.update(date_data.keys())
    
    print(f"Consolidated data includes {len(all_products)} unique products")
    
    return consolidated_data

def calculate_average_order_interval(df):
    """
    Calculate the average time between orders for a product
    Returns the interval in days
    """
    if df is None or df.empty or 'volume' not in df.columns:
        return None
    
    # Get dates where volume > 0 (actual orders)
    order_dates = df[df['volume'] > 0].index
    if len(order_dates) < 2:
        return None
    
    # Calculate differences between consecutive orders
    intervals = np.diff(order_dates)
    avg_interval = np.mean(intervals)
    
    # Convert timedelta to days
    return avg_interval.days

def get_trend_description(current_rsi):
    """
    Get a plain language description of the RSI trend
    """
    if current_rsi < 30:
        return "Very open to ordering"
    elif current_rsi < 40:
        return "Open to ordering"
    elif current_rsi < 45:
        return "Neutral"
    elif current_rsi < 50:
        return "Resistant to ordering"
    else:
        return "Strongly resistant to ordering"

def create_bb_spectrum(position_in_band):
    """
    Create a visual spectrum representation of position within Bollinger Bands
    Returns a string with wider spacing to match the key format
    """
    # Create a wider spectrum with more dashes
    spectrum = list('||---------------||----------------||')
    
    if position_in_band < 0:  # Below floor
        spectrum.insert(0, 'x')
    elif position_in_band > 100:  # Above ceiling
        spectrum.append('x')
    else:
        # Calculate position in the wider spectrum (now with more positions)
        # We have 31 possible positions (15 dashes in each section + the dividers)
        pos = int(2 + (position_in_band / 100.0 * 31))
        spectrum[pos] = 'x'
    
    return ''.join(spectrum)

def calculate_order_recommendations(opp):
    """
    Calculate recommended order quantities based on Bollinger Bands and product value
    Returns dict with recommendations and sustainability period
    """
    current_value = opp['current_close']
    bb_lower = opp['bb_lower']
    bb_middle = opp['bb_middle']
    bb_upper = opp['bb_upper']
    
    # Get the product's average price per unit from recent orders
    recent_volume = sum(opp['volume'][-14:])  # Last 14 periods
    if recent_volume == 0:
        return None  # Can't calculate without recent order data
        
    recent_value = sum(opp['volume'][-14:] * opp['current_close'])
    avg_price_per_unit = recent_value / recent_volume
    
    # Calculate how many days until value drops below lower band
    if current_value > bb_lower:
        # Use the average daily decline rate from the last period
        daily_decline = (opp['volume'][0] - opp['volume'][-1]) / len(opp['volume'])
        if daily_decline > 0:
            days_until_lower = (current_value - bb_lower) / daily_decline
        else:
            days_until_lower = float('inf')
    else:
        days_until_lower = 0
    
    def calculate_target_quantity(target_value):
        """Calculate quantity needed to reach a target value"""
        if current_value >= target_value:
            return 0
            
        # Calculate how much value we need to add
        value_gap = target_value - current_value
        
        # Convert value gap to quantity using price per unit
        # Consider the impact on the moving average
        # The new order will increase the MA by (order_value / MA_window)
        ma_window = 90  # This should match your MA_window parameter
        required_order_value = value_gap * ma_window
        
        # Convert to quantity
        quantity = required_order_value / avg_price_per_unit
        
        # Round to nearest whole unit
        return max(0, round(quantity))
    
    # Calculate 70% target between lower and upper Bollinger Bands
    bb_range = bb_upper - bb_lower
    bb_70_percent = bb_lower + (bb_range * 0.7)
    
    recommendations = {
        'conservative': {
            'quantity': calculate_target_quantity(bb_lower),
            'target': 'floor',
            'sustainability_days': round(days_until_lower)
        },
        'balanced': {
            'quantity': calculate_target_quantity(bb_middle),
            'target': 'average'
        },
        'aggressive': {
            'quantity': calculate_target_quantity(bb_70_percent),
            'target': '70% of range'
        }
    }
    
    return recommendations

def format_opportunity_report(opportunities, account_analysis=None):
    """
    Generate a formatted report with actionable order recommendations grouped by workweeks
    
    Parameters:
    - opportunities: List of product opportunities
    - account_analysis: Account overview DataFrame with indicators (optional)
    """
    try:
        report = ["Product Sales Opportunity Report"]
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add the report legend
        report.append("\n" + "=" * 80 + "\n")
        report.append("How to read this report:")
        report.append("1. Account Overview provides:")
        report.append("   - Current market position and trend analysis")
        report.append("   - 90-day spending targets (Conservative/Balanced/Aggressive)")
        report.append("   - Week-by-week order timeline with value ranges")
        report.append("2. Products are grouped by workweeks based on next order date")
        report.append("3. Priority ranking indicates product's contribution value")
        report.append("   and market position (lower number = higher priority)")
        report.append("4. Order recommendations show:")
        report.append("   - Conservative: Maintain floor support")
        report.append("   - Balanced: Target historical average")
        report.append("   - Aggressive: Reach upper band value")
        report.append("5. Weekly summaries include:")
        report.append("   - Total value ranges [Conservative < Balanced < Aggressive]")
        report.append("   - Number of products due")
        report.append("   - Individual product recommendations\n")
        report.append("=" * 80 + "\n")
        
        # Add account-level overview using the new format_account_overview function
        if account_analysis is not None and not account_analysis.empty:
            account_overview = format_account_overview(account_analysis, opportunities)
            report.append(account_overview)
            report.append("\n" + "=" * 80 + "\n")
        
        if not opportunities:
            report.append("No priority opportunities found matching criteria.\n")
            return "\n".join(report)

        # Group opportunities by workweek based on next order date
        order_weeks = {}
        for opp in opportunities:
            if opp.get('order_interval'):
                next_order_date = datetime.now() + timedelta(days=opp['order_interval'])
                days_until_monday = (next_order_date.weekday()) % 7
                week_start = next_order_date - timedelta(days=days_until_monday)
                week_end = week_start + timedelta(days=4)  # End on Friday
                week_key = f"{week_start.strftime('%Y.%m.%d')} - {week_end.strftime('%Y.%m.%d')}"
                
                if week_key not in order_weeks:
                    order_weeks[week_key] = {
                        'products': [],
                        'conservative': 0,
                        'balanced': 0,
                        'aggressive': 0,
                        'start_date': week_start,
                        'end_date': week_end
                    }
                order_weeks[week_key]['products'].append(opp)

        # Sort weeks chronologically
        sorted_week_keys = sorted(order_weeks.keys())
        
        # Process each week
        for i, week_key in enumerate(sorted_week_keys):
            week_data = order_weeks[week_key]
            week_products = week_data['products']
            
            # Calculate total recommended values for this week
            for opp in week_products:
                # Debug: Check for missing Bollinger Bands data
                if 'bb_upper' not in opp or 'bb_lower' not in opp or 'bb_middle' not in opp:
                    print(f"Debug: Missing BB data in week calculation for {opp.get('product', 'unknown')}")
                    print(f"  Available keys: {list(opp.keys())}")
                    print(f"  Has bb_upper: {'bb_upper' in opp}")
                    print(f"  Has bb_lower: {'bb_lower' in opp}")
                    print(f"  Has bb_middle: {'bb_middle' in opp}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                # Target the correct percentile levels:
                # Conservative = 50th percentile (bb_middle)
                # Balanced = 70th percentile (between middle and upper)
                # Aggressive = 100th percentile (bb_upper)
                bb_70th = opp['bb_lower'] + (opp['bb_upper'] - opp['bb_lower']) * 0.7
                
                cons_qty = calculate_target_quantity(opp, opp['bb_middle'])
                bal_qty = calculate_target_quantity(opp, bb_70th)
                agg_qty = calculate_target_quantity(opp, opp['bb_upper'])
                
                week_data['conservative'] += cons_qty * opp['unit_price']
                week_data['balanced'] += bal_qty * opp['unit_price']
                week_data['aggressive'] += agg_qty * opp['unit_price']
            
            # Add week header with value ranges
            report.append(f"ORDER WEEK: {week_key}")
            report.append(f"Value Range: [${week_data['conservative']:,.0f} < ${week_data['balanced']:,.0f} < ${week_data['aggressive']:,.0f}]")
            report.append(f"Products Due: {len(week_products)}\n")
            
            # Sort products within this week by priority score
            products = sorted(week_products, key=lambda x: x['priority_score'])
            
            # Process all products for this week
            for j, opp in enumerate(products):
                try:
                    # Debug: Check for missing Bollinger Bands data before processing
                    if 'bb_upper' not in opp or 'bb_lower' not in opp or 'bb_middle' not in opp:
                        print(f"Debug: Missing BB data in product formatting for {opp.get('product', 'unknown')}")
                        print(f"  Available keys: {list(opp.keys())}")
                        print(f"  Has bb_upper: {'bb_upper' in opp}")
                        print(f"  Has bb_lower: {'bb_lower' in opp}")
                        print(f"  Has bb_middle: {'bb_middle' in opp}")
                        print(f"  Full opportunity dict: {opp}")
                        import traceback
                        traceback.print_exc()
                        report.append(f"\nError: Missing Bollinger Bands data for {opp.get('product', 'unknown')}\n")
                        continue
                    
                    spectrum = create_bb_spectrum(opp['position_in_band'])
                    next_order = datetime.now() + timedelta(days=opp['order_interval'])
                    
                    # Add a blank line between products (but not before the first one)
                    if j > 0:
                        report.append("")
                    
                    # Format the product entry with indentation for hierarchy
                    report.append(f"  {opp['product']}")
                    report.append(f"     Priority: {opp['contribution_rank']}")
                    report.append(f"     Next Order Due: {next_order.strftime('%Y.%m.%d')}")
                    report.append(f"     Current Position:")
                    report.append(f"     {spectrum}")
                    report.append(f"     Floor -------- Average -------- Ceiling")
                    
                    # Add order recommendations with value projections
                    report.append("     Order Recommendations:")
                    
                    # Calculate quantities and values for each level
                    # Target the correct percentile levels:
                    # Conservative = 50th percentile (bb_middle)
                    # Balanced = 70th percentile (between middle and upper)
                    # Aggressive = 100th percentile (bb_upper)
                    bb_70th = opp['bb_lower'] + (opp['bb_upper'] - opp['bb_lower']) * 0.7
                    
                    cons_qty = calculate_target_quantity(opp, opp['bb_middle'])
                    bal_qty = calculate_target_quantity(opp, bb_70th)
                    agg_qty = calculate_target_quantity(opp, opp['bb_upper'])
                    
                    cons_value = cons_qty * opp['unit_price']
                    bal_value = bal_qty * opp['unit_price']
                    agg_value = agg_qty * opp['unit_price']
                    
                    # Format recommendations with both quantity and value
                    if cons_qty > 0:
                        report.append(f"     - Conservative: {cons_qty} units (${cons_value:,.2f})")
                    else:
                        report.append(f"     - Conservative: Maintain current position")
                        
                    if bal_qty > 0:
                        report.append(f"     - Balanced: {bal_qty} units (${bal_value:,.2f})")
                    else:
                        report.append(f"     - Balanced: At or above average")
                        
                    if agg_qty > 0:
                        report.append(f"     - Aggressive: {agg_qty} units (${agg_value:,.2f})")
                    else:
                        report.append(f"     - Aggressive: At upper target")
                    
                except Exception as e:
                    print(f"Debug: Error formatting opportunity: {str(e)}")
                    report.append(f"\nError formatting opportunity: {str(e)}\n")

            # Add separator between weeks
            if i < len(sorted_week_keys) - 1:
                report.append("\n" + "=" * 80 + "\n")
        
        # Add total opportunity summary at the end
        total_conservative = sum(week['conservative'] for week in order_weeks.values())
        total_balanced = sum(week['balanced'] for week in order_weeks.values())
        total_aggressive = sum(week['aggressive'] for week in order_weeks.values())
        
        report.append("\n" + "=" * 80)
        report.append("\nTOTAL OPPORTUNITY SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Value Range: [${total_conservative:,.0f} < ${total_balanced:,.0f} < ${total_aggressive:,.0f}]")
        report.append(f"Total Products: {sum(len(week['products']) for week in order_weeks.values())}")
        report.append(f"Total Weeks: {len(order_weeks)}")
        
        return "\n".join(report)
        
    except Exception as e:
        print(f"Debug: Critical error in report formatting: {str(e)}")
        import traceback
        print(f"Traceback:")
        traceback.print_exc()
        
        # Additional debugging info
        if 'opportunities' in locals():
            print(f"Number of opportunities: {len(opportunities)}")
            if opportunities:
                print(f"First opportunity keys: {list(opportunities[0].keys())}")
                print(f"First opportunity sample: {opportunities[0]}")
        
        return "Error generating report. Please check the logs."

def create_combined_analysis(account_id, start_date, end_date, resolution='3D', ma_window=90, warmup_days=None, orders=None):
    # If warmup_days is not specified, use the ma_window
    if warmup_days is None:
        warmup_days = ma_window
        
    # Calculate the actual data collection start date (earlier than analysis start)
    data_collection_start = start_date - timedelta(days=warmup_days)
    
    account_name = get_account_name(account_id)
    print(f"\nAnalyzing account: {account_name}")
    
    # Define color sequences up front
    color_sequence = px.colors.qualitative.Set3
    analysis_colors = px.colors.qualitative.Set2
    
    # Create dictionaries to store all analyses
    analyses = {'Account Overview': None}  # Will store DataFrames
    colors = {'Account Overview': None}    # Will store colors for volume bars
    
    # Get account-level analysis first - use the earlier start date for data collection
    orders = get_account_orders(account_id, data_collection_start, end_date)
    print(f"Retrieved {len(orders)} orders for account")
    account_df = create_ohlcv_from_orders(orders, resolution=resolution, ma_window=ma_window)
    
    # Filter the account_df to only include dates after the actual analysis start date
    if not account_df.empty:
        # Convert start_date to match the timezone of the DataFrame index
        # First check if the index has a timezone
        if account_df.index.tz is not None:
            # Convert start_date to a timezone-aware datetime with the same timezone
            start_date_tz = pd.Timestamp(start_date).tz_localize(account_df.index.tz)
        else:
            # If index is timezone-naive, use naive start_date
            start_date_tz = pd.Timestamp(start_date).tz_localize(None)
            
        # Now filter with matching timezone types
        analysis_mask = account_df.index >= start_date_tz
        analysis_account_df = account_df[analysis_mask].copy()
        
        # Only calculate indicators on the analysis period data
        analysis_account_df = calculate_indicators(analysis_account_df, MA_length=18)
        analyses['Account Overview'] = analysis_account_df
    
    # Check if account_df has the required columns before creating colors
    if not account_df.empty and all(col in account_df.columns for col in ['open', 'close']):
        colors['Account Overview'] = ['red' if row['open'] > row['close'] else 'green' 
                                    for i, row in account_df.iterrows()]
    else:
        # Provide default colors if OHLC data is missing
        colors['Account Overview'] = ['green'] * len(account_df) if not account_df.empty else []
    
    # Get product analyses - use data_collection_start to get all products
    products = get_account_products(account_id, data_collection_start, end_date)
    order_products = get_account_order_products(account_id, data_collection_start, end_date)
    
    print(f"Retrieved {len(order_products)} order items for product analysis")
    
    # Get current pricebook prices for all products
    pricebook_prices = get_pricebook_prices(list(products.keys()))
    
    # Filter and create product analyses
    for product_id, product_name in products.items():
        print(f"Processing product: {product_name}")
        
        # Create product OHLCV with the same ma_window as account level
        df = create_product_ohlcv(order_products, product_id, resolution, ma_window, pricebook_prices)
        if df is not None and not df.empty:
            # Filter to only include dates after the actual analysis start date
            # Use the same timezone handling as above
            if df.index.tz is not None:
                start_date_tz = pd.Timestamp(start_date).tz_localize(df.index.tz)
            else:
                start_date_tz = pd.Timestamp(start_date).tz_localize(None)
            
            analysis_mask = df.index >= start_date_tz
            analysis_df = df[analysis_mask].copy()
            
            if not analysis_df.empty:
                print(f"  - {product_name}: {len(analysis_df)} data points")
                analysis_df = calculate_indicators(analysis_df, MA_length=18)
                analyses[product_name] = analysis_df  # Store the analysis
                
                # Check if df has the required columns before creating colors
                if all(col in analysis_df.columns for col in ['open', 'close']):
                    colors[product_name] = ['red' if row['open'] > row['close'] else 'green' 
                                          for i, row in analysis_df.iterrows()]
                else:
                    # Provide default colors if OHLC data is missing
                    colors[product_name] = ['green'] * len(analysis_df)
            else:
                print(f"  - {product_name}: No data points after analysis start date")
        else:
            print(f"  - {product_name}: No valid OHLCV data")
    
    # Create a common date range for all products
    all_dates = set()
    for product_name, df in analyses.items():
        if df is not None and not df.empty:
            all_dates.update(df.index)
    all_dates = sorted(all_dates)

    # Debug: Print first and last dates for each product
    print("\nProduct date ranges:")
    for product_name, df in analyses.items():
        if product_name != 'Account Overview' and df is not None and not df.empty:
            print(f"  {product_name}: {df.index[0].date()} to {df.index[-1].date()}")

    # Define analysis_start_date - make sure account_df is valid before using it
    if not account_df.empty:
        if account_df.index.tz is not None:
            # If the account dataframe has timezone-aware index, match that
            analysis_start_date = pd.Timestamp(start_date).tz_localize(account_df.index.tz)
        else:
            # Otherwise use timezone-naive date
            analysis_start_date = pd.Timestamp(start_date).tz_localize(None)
    else:
        # Fallback if account_df is empty
        analysis_start_date = pd.Timestamp(start_date)
    
    # Print the analysis start date for debugging
    print(f"\nAnalysis start date: {analysis_start_date}")
    
    # Create the main figure
    fig = make_subplots(rows=5, cols=1,
                       row_heights=[0.4, 0.2, 0.2, 0.1, 0.1],
                       shared_xaxes=True,
                       vertical_spacing=0.05,
                       specs=[[{"secondary_y": False}],
                             [{"secondary_y": False}],
                             [{"secondary_y": False}],
                             [{"secondary_y": False}],
                             [{"secondary_y": False}]])
    
    # First, calculate the total account value for each time period
    account_df = analyses['Account Overview']
    
    # Make sure account_df has 'close' column before using it
    if not account_df.empty and 'close' in account_df.columns:
        total_values = account_df['close'].to_dict()  # Use close values as the total account value
        
        # Debug: Print periods with zero or very low total values
        zero_periods = [date for date, value in total_values.items() if value <= 0.01]
        if zero_periods:
            print(f"\nWarning: Found {len(zero_periods)} periods with zero or near-zero total values")
            print(f"First few zero periods: {zero_periods[:5]}")
    else:
        # Create an empty dict if no close values are available
        total_values = {}
        print("\nWarning: No account overview data available for analysis")
    
    # After adding all traces, calculate the min and max values for the OHLC chart
    ohlc_min = float('inf')
    ohlc_max = float('-inf')
    
    # Find min and max values across all visible OHLC traces
    for name, df in analyses.items():
        if df is None or df.empty:
            continue
            
        if all(col in df.columns for col in ['low', 'high']):
            # Only consider Account Overview by default (since it's the only one visible initially)
            if name == 'Account Overview':
                ohlc_min = min(ohlc_min, df['low'].min())
                ohlc_max = max(ohlc_max, df['high'].max())
    
    # Add buffer (10% on top, 5% on bottom)
    if ohlc_min != float('inf') and ohlc_max != float('-inf'):
        y_range = ohlc_max - ohlc_min
        y_min = max(0, ohlc_min - y_range * 0.05)  # 5% buffer at bottom, but never go below zero
        y_max = ohlc_max + y_range * 0.1  # 10% buffer at top
        
        # Update the y-axis range for the OHLC subplot
        fig.update_yaxes(
            title="Value",
            range=[y_min, y_max],  # Dynamic range based on data
            row=1, col=1
        )
    
    # STEP 1: ADD REGULAR ANALYSIS TRACES FIRST
    # Add the regular analysis traces before contribution traces
    for name, df in analyses.items():
        if df is None or df.empty:
            # print(f"Warning: No data for {name}, skipping visualization")
            continue
            
        # Set initial visibility - only Account Overview visible by default
        is_visible = name == 'Account Overview'
        
        # Generate a unique color for this analysis
        color_idx = list(analyses.keys()).index(name) % len(analysis_colors)
        base_color = analysis_colors[color_idx]
        
        # Parse the RGB values from the color string and make darker version (50% darker)
        if 'rgb' in base_color:
            rgb_values = base_color.strip('rgb()').split(',')
            r, g, b = [int(val) * 0.5 for val in rgb_values]  # Darken by 50%
            darker_color = f'rgba({int(r)}, {int(g)}, {int(b)}, 1)'
        else:
            # Fallback for hex colors or other formats
            darker_color = 'rgba(100, 100, 100, 1)'
        
        # OHLC chart - only add if all required columns exist and we have sufficient data
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            if 'insufficient_data' in df.columns and df['insufficient_data'].any():
                # Add a text annotation instead of the chart
                fig.add_annotation(
                    x=df.index[len(df.index)//2],  # Center of x-axis
                    y=0.5,  # Middle of the plot
                    text="NOT ENOUGH DATA FOR ANALYSIS",
                    showarrow=False,
                    font=dict(size=20, color="gray"),
                    row=1, col=1
                )
            else:
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name=f"{name} OHLC",
                        visible=is_visible,
                        increasing=dict(
                            line=dict(color=base_color),
                            fillcolor=base_color
                        ),
                        decreasing=dict(
                            line=dict(color=darker_color),
                            fillcolor='rgba(0,0,0,0)'
                        ),
                        opacity=0.6
                    ),
                    row=1, col=1
                )
        
        # Bollinger Bands with matching colors - only add if they exist
        for band, label in [('bb_upper', 'Upper'), ('bb_middle', 'Middle'), ('bb_lower', 'Lower')]:
            if band in df.columns and not df[band].isna().all():  # Check if column exists AND has valid data
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[band],
                        name=f"{name} BB {label}",
                        line=dict(
                            color=base_color,
                            width=1,
                            dash='dash'
                        ),
                        opacity=0.3,
                        visible=is_visible
                    ),
                    row=1, col=1
                )
        
        # Volume with color-coded bars - only add if volume column exists
        if 'volume' in df.columns:
            # Check if we have OHLC data for coloring
            if all(col in df.columns for col in ['open', 'close']):
                # Use OHLC data for coloring
                bar_colors = [
                    base_color if close >= open else darker_color
                    for open, close in zip(df['open'], df['close'])
                ]
                bar_opacities = [
                    0.6 if close >= open else 0.8
                    for open, close in zip(df['open'], df['close'])
                ]
            else:
                # Use default coloring if OHLC data is missing
                bar_colors = [base_color] * len(df)
                bar_opacities = [0.6] * len(df)
                
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name=f"{name} Volume",
                marker=dict(
                    color=bar_colors,
                    opacity=bar_opacities
                ),
                visible=is_visible
            ),
            row=3, col=1
        )
        
        # Add volume SMA if it exists
        if 'volume_sma' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['volume_sma'],
                    name=f"{name} Volume MA",
                    line=dict(
                        color=base_color,
                        width=1,
                        dash='dot'
                    ),
                    visible=is_visible
                ),
                row=3, col=1
            )
        
        # RSI with matching colors - only add if it exists
        if 'rsi' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['rsi'],
                    name=f"{name} RSI",
                    line=dict(color=base_color, width=1),
                    visible=is_visible
                ),
                row=4, col=1
            )
            
            # Add RSI MA if it exists
            if 'rsi_ma' in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df['rsi_ma'],
                        name=f"{name} RSI MA",
                        line=dict(
                            color=base_color, 
                            width=1,
                            dash='dot'  # Use dotted line to distinguish from RSI
                        ),
                        visible=is_visible
                    ),
                    row=4, col=1
                )
        
        # MACD lines and histogram - only add if they exist
        if all(col in df.columns for col in ['macd', 'macd_signal', 'macd_hist']):
            # First add the histogram
            # Prepare colors for MACD histogram
            macd_colors = [
                base_color if val >= 0 else darker_color
                for val in df['macd_hist']
            ]
            macd_opacities = [
                0.6 if val >= 0 else 0.8
                for val in df['macd_hist']
            ]
            
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['macd_hist'],
                    name=f"{name} MACD Hist",
                    marker=dict(
                        color=macd_colors,
                        opacity=macd_opacities
                    ),
                    visible=is_visible
                ),
                row=5, col=1
            )
            
            # Add MACD line
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['macd'],
                    name=f"{name} MACD",
                    line=dict(color=base_color, width=1),
                    visible=is_visible
                ),
                row=5, col=1
            )
            
            # Update MACD signal line style
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['macd_signal'],
                    name=f"{name} Signal",
                    line=dict(
                        color=base_color,
                        width=1,
                        dash='dot'
                    ),
                    visible=is_visible
                ),
                row=5, col=1
            )
        else:
            # Log that we're skipping this product due to missing OHLC data
            print(f"Skipping visualization for {name} - missing OHLC data")

    # STEP 2: ADD PRODUCT CONTRIBUTION TRACES SECOND
    # First collect and sort all product contributions before adding them
    all_product_contributions = []

    # Important: Make sure we have all products calculated first
    print(f"\nAvailable products for contribution calculation:")
    for product_name, df in analyses.items():
        if product_name != 'Account Overview' and df is not None and not df.empty:
            print(f"  {product_name}: {len(df)} data points")

    # Get the resolution frequency
    freq_map = {
        '3D': '3D',
        '1W': 'W',
        '2W': '2W',
        '1M': 'M'
    }
    resample_freq = freq_map[resolution]
    print(f"Using resolution frequency: {resample_freq} for product contributions")

    # Step 1: Define consistent date boundaries for the 3-day windows
    # Start with the earliest date in the analysis period and create a uniform grid of 3-day periods
    if account_df is not None and not account_df.empty:
        # Use the account dataframe start date as the reference 
        grid_start_date = account_df.index[0]
        # Get the timezone from account dataframe if available
        reference_tz = grid_start_date.tz
    else:
        # Fall back to the analysis start date if no account dataframe
        grid_start_date = analysis_start_date
        reference_tz = None

    # Define end_date_timestamp before we try to use it
    end_date_timestamp = pd.Timestamp(end_date)
    print(f"Initial end_date_timestamp: {end_date_timestamp}, timezone: {end_date_timestamp.tz}")

    # Make sure end_date has the same timezone as grid_start_date
    if reference_tz is not None:
        if end_date_timestamp.tz is None:
            end_date_timestamp = pd.Timestamp(end_date).tz_localize(reference_tz)
        elif end_date_timestamp.tz != reference_tz:
            end_date_timestamp = pd.Timestamp(end_date).tz_convert(reference_tz)
    else:
        # If reference has no timezone, make sure end_date also has no timezone
        if end_date_timestamp.tz is not None:
            end_date_timestamp = pd.Timestamp(end_date).tz_localize(None)

    # Define a fixed start date for the 3-day grid (ensure it's a consistent day)
    grid_offset = grid_start_date.weekday() % 3  # Ensure we always start on same day within 3-day cycle
    aligned_start = grid_start_date - pd.Timedelta(days=grid_offset)
    print(f"Using aligned start date for 3-day grid: {aligned_start}")
    print(f"Aligned start timezone: {aligned_start.tz}, End date timezone: {end_date_timestamp.tz}")

    # Generate fixed 3-day period boundaries
    date_range = pd.date_range(start=aligned_start, end=end_date_timestamp, freq=resample_freq)
    print(f"Created fixed grid with {len(date_range)} time periods")

    # Step 2: Collect all product values aligned to this fixed grid
    consolidated_product_data = consolidate_product_data(
        analyses, 
        resample_freq, 
        analysis_start_date, 
        end_date_timestamp
    )

    # Step 3: Calculate total value for each aligned time period
    date_totals = {}
    for date in consolidated_product_data:
        total = sum(consolidated_product_data[date].values())
        if total > 0:  # Skip dates with no data
            date_totals[date] = total

    # Print debug information
    print(f"Created consolidated values for {len(date_totals)} time periods")
    print(f"Number of products with data: {len(set().union(*[set(data.keys()) for data in consolidated_product_data.values()]))}")

    # Step 4: Create contribution traces for each product aligned to the grid
    # We need to collect ALL products that appear anywhere in our data
    all_product_names = set()
    for date_data in consolidated_product_data.values():
        all_product_names.update(date_data.keys())

    # Create a mapping of product names to their colors from the OHLC charts
    product_color_map = {}
    for name, df in analyses.items():
        if name == 'Account Overview' or df is None or df.empty:
            continue
        
        # Calculate the color index the same way we did for OHLC
        color_idx = list(analyses.keys()).index(name) % len(analysis_colors)
        product_color_map[name] = analysis_colors[color_idx]
        print(f"Assigned color to {name}: {analysis_colors[color_idx]}")

    # Now create traces for each product using our consolidated data
    for i, product_name in enumerate(all_product_names):
        dates = []
        values = []
        
        # Collect all dates where this product has data
        for date in sorted(consolidated_product_data.keys()):
            if product_name in consolidated_product_data[date]:
                dates.append(date)
                values.append(consolidated_product_data[date][product_name])
        
        if not dates:
            print(f"  Warning: No consolidated dates for {product_name}")
            continue
        
        max_value = max(values) if values else 0
        
        # Use the same color as the OHLC chart if available, otherwise use the color sequence
        if product_name in product_color_map:
            color = product_color_map[product_name]
            print(f"  Using matched OHLC color for {product_name}")
        else:
            color = color_sequence[i % len(color_sequence)]
            print(f"  Using default color sequence for {product_name}")
        
        all_product_contributions.append({
            'product_name': product_name,
            'dates': dates,
            'values': values,
            'max_value': max_value,
            'color': color  # Store the actual color instead of just an index
        })

    # Sort by maximum contribution value
    all_product_contributions.sort(key=lambda x: x['max_value'], reverse=True)

    # Print summary of contributions data
    print(f"\nFound {len(all_product_contributions)} products with contribution data")
    for product_data in all_product_contributions[:5]:  # Print top 5 contributors
        print(f"  {product_data['product_name']}: {len(product_data['dates'])} points, max: {product_data['max_value']:.2f}")

    # Now add the sorted contribution traces
    contribution_trace_indices = []  # Track indices of contribution traces

    for product_data in all_product_contributions:
        product_name = product_data['product_name']
        dates = product_data['dates'] 
        values = product_data['values']
        color = product_data['color']  # Use the stored color directly
        
        # Ensure we have valid data to plot
        if not dates or not values:
            print(f"  Warning: {product_name} has empty dates or values list, skipping trace")
            continue
        
        if len(dates) != len(values):
            print(f"  Warning: {product_name} has mismatched dates ({len(dates)}) and values ({len(values)}), skipping trace")
            continue
        
        # Add trace with absolute values and custom hover template
        trace = go.Scatter(
            x=dates,
            y=values,
            name=f"{product_name} - $ Contribution",
            line=dict(color=color),  # Use the consistent color
            visible=True,  # Always visible by default
            showlegend=True,
            connectgaps=True,  # Connect gaps for better visualization
            hovertemplate=f"{product_name}: %{{y:$,.2f}}<extra></extra>"
        )
        
        trace_idx = len(fig.data)  # Get the index before adding
        fig.add_trace(trace, row=2, col=1)
        contribution_trace_indices.append(trace_idx)  # Store the index
        print(f"  Added contribution trace for {product_name} at index {trace_idx} with color {color}")

    # STEP 3: CREATE TRACE GROUPS
    # Create a mapping of traces to their exact analysis name
    trace_groups = {}

    # First, identify all contribution traces
    contribution_trace_indices = []
    for i, trace in enumerate(fig.data):
        if "$ Contribution" in trace.name:
            contribution_trace_indices.append(i)

    # Then identify all non-contribution traces and group them
    for i, trace in enumerate(fig.data):
        # Skip contribution traces - they're handled separately
        if i in contribution_trace_indices:
            continue
            
        # Extract the full product name from the trace name
        trace_parts = trace.name.split()
        
        # For traces like "MegaMucosa OHLC" or "MegaMucosa Stick Packs OHLC"
        # We need to determine where the product name ends and the chart type begins
        chart_types = ["OHLC", "BB", "Volume", "RSI", "MACD", "Signal", "Hist", "MA", "Upper", "Middle", "Lower"]
        
        # Find where the chart type starts in the trace name
        chart_type_index = None
        for j, part in enumerate(trace_parts):
            if part in chart_types:
                chart_type_index = j
                break
        
        # If we found a chart type, everything before it is the product name
        if chart_type_index is not None:
            product_name = " ".join(trace_parts[:chart_type_index])
        else:
            # Fallback - use the first part as the product name
            product_name = trace_parts[0]
        
        # Add to trace groups
        if product_name not in trace_groups:
            trace_groups[product_name] = []
        trace_groups[product_name].append(i)

    print(f"\nTrace groups created: {list(trace_groups.keys())}")
    for group, indices in trace_groups.items():
        print(f"  {group}: {len(indices)} traces")
        # Print a few sample trace names for debugging
        sample_traces = [fig.data[idx].name for idx in indices[:3]]
        print(f"    Sample traces: {sample_traces}")

    # STEP 4: CREATE DROPDOWN BUTTONS
    # Create dropdown menu options
    buttons = []

    # Store y-axis ranges for each analysis
    y_axis_ranges = {}
    
    # Calculate y-axis ranges for all analyses
    for name, df in analyses.items():
        if df is not None and not df.empty:
            try:
                # Start with OHLC values if available
                if all(col in df.columns for col in ['low', 'high']):
                    min_value = df['low'].min()
                    max_value = df['high'].max()
                    
                    # Include Bollinger Bands if available (they often extend beyond OHLC values)
                    if 'bb_lower' in df.columns and not df['bb_lower'].isna().all():
                        min_value = min(min_value, df['bb_lower'].min())
                    if 'bb_upper' in df.columns and not df['bb_upper'].isna().all():
                        max_value = max(max_value, df['bb_upper'].max())
                    
                    # Apply more generous buffers (15% on bottom, 20% on top)
                    value_range = max_value - min_value
                    if value_range > 0:  # Ensure we have a valid range
                        y_min = min_value - value_range * 0.15
                        y_max = max_value + value_range * 0.20
                        
                        y_axis_ranges[name] = [y_min, y_max]
                        print(f"Y-axis range for {name}: {y_min:.2f} to {y_max:.2f}")
                    else:
                        print(f"Invalid value range for {name}: min={min_value}, max={max_value}")
                else:
                    print(f"Unable to calculate y-axis range for {name} - missing required columns")
            except Exception as e:
                print(f"Error calculating range for {name}: {str(e)}")

    # Also calculate volume y-axis ranges
    volume_axis_ranges = {}
    for name, df in analyses.items():
        if df is not None and not df.empty and 'volume' in df.columns:
            # Find max volume with a 30% buffer for better visualization
            max_volume = df['volume'].max() * 1.15
            volume_axis_ranges[name] = [0, max_volume]
            print(f"Volume range for {name}: 0 to {max_volume:.2f}")

    # 1. Select All button - shows all traces
    # For Select All, use the widest range to accommodate all data
    if y_axis_ranges:
        all_min = min([range_vals[0] for range_vals in y_axis_ranges.values()])
        all_max = max([range_vals[1] for range_vals in y_axis_ranges.values()])
        
        # Also get the max volume range for all analyses
        all_vol_max = 1.0
        if volume_axis_ranges:
            all_vol_max = max([range_vals[1] for range_vals in volume_axis_ranges.values()])
        
        buttons.append(dict(
            args=[{
                "visible": [True] * len(fig.data)
            }, {
                "yaxis.range[0]": all_min,
                "yaxis.range[1]": all_max,
                "yaxis3.range[0]": 0,
                "yaxis3.range[1]": all_vol_max
            }],
            label="Select All",
            method="update"
        ))
    else:
        buttons.append(dict(
            args=[{"visible": [True] * len(fig.data)}],
            label="Select All",
            method="update"
        ))

    # 2. Clear All button - hides all traces except product contributions
    clear_visible = [False] * len(fig.data)
    for i in contribution_trace_indices:
        clear_visible[i] = True
        
    buttons.append(dict(
        args=[{"visible": clear_visible}],
        label="Clear All",
        method="update"
    ))

    # 3. Account Overview button - shows Account Overview traces + ALL product contributions
    if "Account Overview" in trace_groups:
        account_visible = [False] * len(fig.data)
        
        # Show Account Overview traces
        for i in trace_groups["Account Overview"]:
            account_visible[i] = True
        
        # Always show ALL product contributions
        for i in contribution_trace_indices:
            account_visible[i] = True
        
        # Use pre-calculated y-axis range for Account Overview
        if 'Account Overview' in y_axis_ranges:
            y_min, y_max = y_axis_ranges['Account Overview']
            buttons.append(dict(
                args=[{
                    "visible": account_visible
                }, {
                    "yaxis.range[0]": y_min,
                    "yaxis.range[1]": y_max
                }],
                label="Account Overview",
                method="update"
            ))
        else:
            buttons.append(dict(
                args=[{"visible": account_visible}],
                label="Account Overview",
                method="update"
            ))

    # Now add the rest of the product buttons in alphabetical order
    # Get all product names except Account Overview and sort them alphabetically
    product_names = [name for name in trace_groups.keys() if name != "Account Overview"]
    product_names.sort()  # Sort alphabetically

    print(f"\nCreating buttons for products: {product_names}")

    # Add buttons for each product in alphabetical order
    for product_name in product_names:
        if product_name not in trace_groups:
            print(f"Warning: No traces found for {product_name}")
            continue
        
        indices = trace_groups[product_name]
        print(f"  {product_name}: {len(indices)} traces")
        
        # Create visibility array for this product
        product_visible = [False] * len(fig.data)
        
        # Show this product's traces
        for i in indices:
            product_visible[i] = True
            
        # Always show ALL product contributions
        for i in contribution_trace_indices:
            product_visible[i] = True
            
        # Set up the layout updates
        layout_updates = {}
        
        # Use pre-calculated y-axis range for this product's main chart
        if product_name in y_axis_ranges:
            y_min, y_max = y_axis_ranges[product_name]
            layout_updates["yaxis.range[0]"] = y_min
            layout_updates["yaxis.range[1]"] = y_max
            print(f"  {product_name} Y-axis range: {y_min:.2f} to {y_max:.2f}")
        
        # Also update volume chart range if available
        if product_name in volume_axis_ranges:
            vol_min, vol_max = volume_axis_ranges[product_name]
            layout_updates["yaxis3.range[0]"] = vol_min
            layout_updates["yaxis3.range[1]"] = vol_max
            print(f"  {product_name} Volume range: {vol_min:.2f} to {vol_max:.2f}")
            
        # Create the button with appropriate args
        if layout_updates:
            buttons.append(dict(
                args=[
                    {"visible": product_visible},
                    layout_updates
                ],
                label=product_name,
                method="update"
            ))
        else:
            print(f"  {product_name}: No axis ranges available")
            buttons.append(dict(
                args=[{"visible": product_visible}],
                label=product_name,
                method="update"
            ))

    # Update the layout with the dropdown menu positioned above the y-axis
    fig.update_layout(
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                showactive=True,
                active=2,  # Account Overview is active by default
                x=0.05,    # Position near the left side of the plot
                y=1.15,    # Position above the plot, near the title
                xanchor="left",
                yanchor="top",
                bgcolor="rgba(0,0,0,0.3)",
                bordercolor="rgba(255,255,255,0.3)",
                borderwidth=1,
                font=dict(size=12, color='white'),
                type="dropdown"
            )
        ],
        # Adjust top margin to make room for the dropdown
        margin=dict(t=150, r=120, l=80, b=20)
    )
    
    # Add vertical hover line for all subplots
    fig.update_layout(
        hovermode="x unified",  # Show hover info for all traces at the same x-coordinate
        hoverdistance=100,      # Increase hover distance for better usability
        spikedistance=1000,     # Increase spike distance
        hoverlabel=dict(
            bgcolor="rgba(0,0,0,0.8)",
            font_size=12,
            font_family="Arial"
        )
    )
    
    # Add spikes (vertical lines on hover)
    fig.update_xaxes(
        showspikes=True,
        spikecolor="white",
        spikesnap="cursor",
        spikemode="across",
        spikethickness=1
    )
    
    # Add gridlines and reference lines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)
    
    # Add reference lines at 25%, 50%, and 75%
    fig.add_hline(y=25, line_dash="dot", line_color="gray", opacity=0.5, row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.5, row=2, col=1)
    fig.add_hline(y=75, line_dash="dot", line_color="gray", opacity=0.5, row=2, col=1)

    # Update layout with minimal positioning
    fig.update_layout(
        title=f"Analysis - {account_name}",  # Simplified title
        template='plotly_dark',
        height=1000,  # Increased height for better visibility
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,  # Move legend outside the plot area (>1 moves it to the right)
            bgcolor="rgba(0,0,0,0.3)",  # Semi-transparent background
            bordercolor="rgba(255,255,255,0.3)",
            borderwidth=1
        ),
        yaxis=dict(
            title="3-Day Order Value<br>(90 Day MA)",
            layer="above traces"
        ),
        yaxis2=dict(
            title="Product Contributions ($)",
            layer="above traces",
            domain=[0.5, 0.7]  # Adjust the vertical position if needed
        ),
        yaxis3=dict(title="Item Count"),
        yaxis4=dict(title="Order Resistance"),
        yaxis5=dict(title="Trend"),
        yaxis2_showgrid=False,
        yaxis3_showgrid=False,
        yaxis4_showgrid=False,
        yaxis5_showgrid=False,
        xaxis=dict(
            rangeslider=dict(visible=False)  # Disable the rangeslider/mini-map
        )
    )

    # Update RSI axis range to focus on the 20-80 range instead of 0-100
    fig.update_yaxes(range=[20, 80], row=4, col=1)

    # Add RSI overbought/oversold lines (keep these, they're still useful)
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=4, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=4, col=1)
    # Add a center line at 50 for reference
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=4, col=1)

    # Add product contribution lines to their own subplot (row 2)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)
    
    print(f"\nCreated {len(trace_groups)} trace groups for dropdown menu")
    print(f"\nCreated {len(buttons)} dropdown menu buttons")

    # After creating all analyses and before returning the figure
    # Generate the opportunity report (keep in memory - no disk I/O)
    report = analyze_product_opportunities(analyses, consolidated_product_data, analyses['Account Overview'])
    
    # Create HTML content with both the chart and text report (keep in memory)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{account_name} Opportunity Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .report-container {{ margin-top: 30px; }}
            .text-report {{ 
                white-space: pre-wrap; 
                background-color: #f8f9fa; 
                padding: 15px; 
                border-radius: 5px;
                font-family: monospace;
                line-height: 1.5;
            }}
            h2 {{ color: #2c3e50; }}
        </style>
    </head>
    <body>
        <h2>{account_name} Opportunity Analysis</h2>
        <div id="chart-container">
            {fig.to_html(include_plotlyjs='cdn', full_html=False)}
        </div>
        <div class="report-container">
            <h2>Detailed Opportunity Report</h2>
            <div class="text-report">
                {report.replace('<', '&lt;').replace('>', '&gt;')}
            </div>
        </div>
    </body>
    </html>
    """
    
    print(f"\nAnalysis completed. Report data kept in memory (RAM storage mode).")
    
    # Return all data in memory instead of writing to disk
    # This eliminates file I/O and path resolution issues in PyInstaller executables
    return {
        'figure': fig,
        'html_content': html_content,
        'text_report': report,
        'account_name': account_name
    }

def is_fullscript_account(account_name):
    """Check if account is a FullScript account based on name prefix"""
    return account_name.startswith('(FS)')

def get_business_days_in_month(start_date, end_date):
    """Get all business days between two dates"""
    return pd.date_range(start=start_date, end=end_date, freq='B')

def distribute_monthly_orders(orders):
    """
    Distribute FullScript orders across previous month using weighted business day distribution
    """
    distributed_orders = []
    
    # Group orders by account first
    orders_by_account = {}
    for order in orders:
        acc_id = order['AccountId']
        if acc_id not in orders_by_account:
            orders_by_account[acc_id] = []
        orders_by_account[acc_id].append(order)
    
    for acc_id, acc_orders in orders_by_account.items():
        # Check if this is a FS account
        is_fs = is_fullscript_account(acc_orders[0]['Account']['Name'])
        
        if not is_fs:
            # Keep non-FS orders as is
            distributed_orders.extend(acc_orders)
            continue
            
        # Process FS orders
        for order in acc_orders:
            order_date = pd.to_datetime(order['MBL_Order_Shipped_Time__c'])
            
            # Calculate distribution period (previous month)
            end_date = order_date
            start_date = end_date - pd.DateOffset(months=1)
            
            # Get business days in the period
            business_days = get_business_days_in_month(start_date, end_date)
            
            if len(business_days) == 0:
                # Fallback if no business days found
                distributed_orders.append(order)
                continue
            
            # Create weights favoring certain parts of the month
            # Higher weights for early and late month, lower for mid-month
            weights = []
            for day in business_days:
                day_of_month = day.day
                total_days = end_date.days_in_month
                
                # Create a W-shaped weight distribution
                if day_of_month <= total_days / 4:  # First quarter
                    weight = 1.5 - (day_of_month / (total_days / 4)) * 0.5
                elif day_of_month <= total_days / 2:  # Second quarter
                    weight = 1.0 + (day_of_month - total_days / 4) / (total_days / 4) * 0.5
                elif day_of_month <= 3 * total_days / 4:  # Third quarter
                    weight = 1.5 - (day_of_month - total_days / 2) / (total_days / 4) * 0.5
                else:  # Fourth quarter
                    weight = 1.0 + (day_of_month - 3 * total_days / 4) / (total_days / 4) * 0.5
                
                # Adjust weight for day of week (higher for Tuesday-Thursday)
                dow_adjustment = 1.2 if day.dayofweek in [1, 2, 3] else 1.0
                weights.append(weight * dow_adjustment)
            
            # Normalize weights
            weights = np.array(weights) / sum(weights)
            
            # Calculate distributed amounts
            total_amount = float(order['TotalAmount'])
            distributed_amounts = weights * total_amount
            
            # Create distributed orders
            for day, amount in zip(business_days, distributed_amounts):
                distributed_order = order.copy()
                distributed_order['MBL_Order_Shipped_Time__c'] = day.strftime('%Y-%m-%dT%H:%M:%SZ')
                distributed_order['TotalAmount'] = float(amount)
                distributed_orders.append(distributed_order)
    
    return distributed_orders

def analyze_product_opportunities(analyses, consolidated_product_data, account_analysis=None):
    """
    Analyze all contributing products for trading opportunities
    """
    opportunities = []
    ma_window = 90
    
    # Define products to ignore
    ignored_products = ["Mouth Cleaner", "Mouth Freshener"]
    
    # Calculate contribution metrics for each product
    product_contributions = {}
    for date_data in consolidated_product_data.values():
        for product, value in date_data.items():
            # Skip products that contain any of the ignored terms
            if any(ignored_term in product for ignored_term in ignored_products):
                continue
                
            if product not in product_contributions:
                product_contributions[product] = []
            product_contributions[product].append(value)
    
    # Calculate average contribution for each product
    avg_contributions = {
        product: sum(values) / len(values)
        for product, values in product_contributions.items()
    }
    
    # Filter out products with very low contribution (e.g., less than 1% of max contribution)
    max_contribution = max(avg_contributions.values())
    min_contribution_threshold = max_contribution * 0.01
    active_products = {
        k: v for k, v in avg_contributions.items() 
        if v > min_contribution_threshold
    }
    
    # Calculate contribution ranks
    sorted_products = sorted(active_products.items(), key=lambda x: x[1], reverse=True)
    contribution_ranks = {product: i + 1 for i, (product, _) in enumerate(sorted_products)}
    
    print("\nAnalyzing contributing products:")
    for product, avg_contribution in active_products.items():
        print(f"\nProcessing {product}:")
        print(f"  Average contribution: ${avg_contribution:.2f}")
        print(f"  Contribution rank: {contribution_ranks[product]}")
        
        if product not in analyses or analyses[product] is None:
            continue
            
        df = analyses[product]
        
        # Check for required indicators
        required_cols = ['rsi', 'close', 'bb_lower', 'bb_middle', 'bb_upper', 'volume', 'unit_price']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"  Skipping {product}: Missing required columns: {missing_cols}")
            print(f"    Available columns: {list(df.columns)}")
            continue
            
        try:
            latest_data = df.iloc[-1]
            
            # Calculate technical indicators
            latest_close = latest_data['close']
            latest_rsi = latest_data['rsi']
            latest_bb_lower = latest_data['bb_lower']
            latest_bb_middle = latest_data['bb_middle']
            latest_bb_upper = latest_data['bb_upper']
            latest_unit_price = latest_data['unit_price']
            
            # Calculate position in Bollinger Bands
            bb_range = latest_bb_upper - latest_bb_lower
            if bb_range == 0:
                continue
                
            position_in_band = (latest_close - latest_bb_lower) / bb_range * 100
            
            # More lenient filtering criteria
            if latest_rsi > 75:  # Only skip extremely overbought conditions
                continue
                
            if position_in_band > 90:  # Only skip if very close to upper band
                continue
                
            if latest_unit_price == 0:
                continue
            
            # Calculate days until lower band breach
            days_until_lower = df['days_until_lower_breach'].iloc[-1]
            
            # Calculate average order interval
            order_interval = calculate_average_order_interval(df)
            
            # Add to opportunities list
            opportunities.append({
                'product': product,
                'current_close': latest_close,
                'current_rsi': latest_rsi,
                'position_in_band': position_in_band,
                'order_interval': order_interval,
                'bb_middle': latest_bb_middle,
                'bb_lower': latest_bb_lower,
                'bb_upper': latest_bb_upper,
                'unit_price': latest_unit_price,
                'days_until_lower': days_until_lower,
                'days_until_middle': df['days_until_middle_breach'].iloc[-1],  # Add this line
                'volume': df['volume'].values,
                'avg_contribution': avg_contribution,
                'contribution_rank': contribution_ranks[product]
            })
            
        except Exception as e:
            print(f"  Error processing {product}: {str(e)}")
            continue
    
    # Sort opportunities by composite score
    for opp in opportunities:
        rsi_score = opp['current_rsi'] / 75  # Normalize RSI (0-1 scale)
        position_score = opp['position_in_band'] / 100  # Normalize position (0-1 scale)
        rank_score = opp['contribution_rank'] / len(contribution_ranks)  # Normalize rank (0-1 scale)
        
        # Composite score weights contribution rank, RSI, and position
        opp['priority_score'] = (
            rank_score * 0.5 +  # 50% weight on contribution rank
            rsi_score * 0.3 +   # 30% weight on RSI
            position_score * 0.2 # 20% weight on BB position
        )
    
    # Sort by priority score (lower is better)
    opportunities.sort(key=lambda x: x['priority_score'])
    
    # Pass the account analysis to the report formatter
    return format_opportunity_report(opportunities, account_analysis)

def calculate_target_quantity(opp, target_value):
    """Calculate quantity needed to reach a target value"""
    current_value = opp['current_close']
    
    if current_value >= target_value:
        return 0
        
    # Calculate how much value we need to add
    value_gap = target_value - current_value
    
    # Convert value gap to quantity using unit price from Salesforce
    ma_window = 90  # This should match your MA_window parameter
    required_order_value = value_gap * ma_window
    
    # Convert to quantity using the actual unit price
    quantity = required_order_value / opp['unit_price']
    
    # Round to nearest whole unit
    return max(0, round(quantity))

def format_account_overview(account_analysis, opportunities):
    """Generate enhanced account overview section with intuitive metrics"""
    
    def analyze_macd_trend(latest_macd, latest_signal, previous_macd, previous_signal):
        """Analyze MACD trend and provide meaningful interpretation"""
        if abs(latest_macd - latest_signal) < abs(previous_macd - previous_signal):
            if latest_macd < latest_signal:
                return "MACD approaching bullish crossover"
            else:
                return "MACD approaching bearish crossover"
        else:
            if latest_macd > latest_signal:
                return "MACD confirms bullish trend"
            else:
                return "MACD trending lower"

    def analyze_volume_trend(volumes, periods=5):
        """Analyze volume trend over recent periods"""
        if len(volumes) < periods:
            return "Insufficient volume data"
            
        recent_volumes = volumes[-periods:]
        slope = np.polyfit(range(periods), recent_volumes, 1)[0]
        avg_volume = np.mean(recent_volumes)
        
        pct_change = (slope * periods) / avg_volume * 100
        
        if pct_change > 5:
            return "INCREASING"
        elif pct_change < -5:
            return "DECREASING"
        else:
            return "STABLE"

    def calculate_spending_targets(account_analysis, opportunities):
        """Calculate account-level spending targets based on actual opportunities"""
        # Create week timeline to get actual opportunity values
        weeks = create_week_timeline(opportunities, 90)
        
        # Sum up the actual opportunities across all weeks
        total_conservative = sum(week['conservative'] for week in weeks.values())
        total_balanced = sum(week['balanced'] for week in weeks.values())
        total_aggressive = sum(week['aggressive'] for week in weeks.values())
        
        # Calculate total order value for trailing 90 days (last 30 candlesticks)
        historical_values = account_analysis['close'].tail(30)
        total_historical = historical_values.sum() if not historical_values.empty else 0
        
        return {
            'conservative': total_conservative,
            'balanced': total_balanced,
            'aggressive': total_aggressive,
            'avg_historical': total_historical  # This is now the total for 90 days
        }

    def create_week_timeline(opportunities, report_timeframe):
        """Create timeline visualization for the report timeframe"""
        weeks = {}
        
        # Calculate the number of weeks in our timeframe
        start_date = datetime.now()
        end_date = start_date + timedelta(days=report_timeframe)
        
        # Initialize all weeks in the timeframe
        current_date = start_date
        while current_date < end_date:
            week_num = (current_date - start_date).days // 7
            weeks[week_num] = {
                'products': [],
                'total_value': 0,
                'position': 0,
                'start_date': current_date,
                'end_date': current_date + timedelta(days=6),
                'conservative': 0,
                'balanced': 0,
                'aggressive': 0
            }
            current_date += timedelta(days=7)
        
        # Group opportunities by week
        for opp in opportunities:
            if opp.get('order_interval'):
                next_order = datetime.now() + timedelta(days=opp['order_interval'])
                week_num = (next_order - start_date).days // 7
                
                if week_num in weeks:
                    # Calculate different ordering scenarios
                    # Target the correct percentile levels:
                    # Conservative = 50th percentile (bb_middle)
                    # Balanced = 70th percentile (between middle and upper)
                    # Aggressive = 100th percentile (bb_upper)
                    bb_70th = opp['bb_lower'] + (opp['bb_upper'] - opp['bb_lower']) * 0.7
                    
                    cons_qty = calculate_target_quantity(opp, opp['bb_middle'])
                    bal_qty = calculate_target_quantity(opp, bb_70th)
                    agg_qty = calculate_target_quantity(opp, opp['bb_upper'])
                    
                    weeks[week_num]['products'].append(opp)
                    weeks[week_num]['conservative'] += cons_qty * opp['unit_price']
                    weeks[week_num]['balanced'] += bal_qty * opp['unit_price']
                    weeks[week_num]['aggressive'] += agg_qty * opp['unit_price']
                    weeks[week_num]['position'] += opp['position_in_band']
        
        # Calculate average position for each week
        for week in weeks.values():
            if week['products']:
                week['position'] /= len(week['products'])
        
        return weeks

    # Format the account overview
    overview = ["ACCOUNT OVERVIEW"]
    overview.append("-" * 80)
    
    latest = account_analysis.iloc[-1]
    
    # Calculate and add BB position
    bb_range = latest['bb_upper'] - latest['bb_lower']
    if bb_range > 0:
        account_position = (latest['close'] - latest['bb_lower']) / bb_range * 100
        overview.append(f"Current Position in Bollinger Band: {account_position:.1f}%")
        overview.append(create_bb_spectrum(account_position))
        overview.append("Floor -------- Average -------- Ceiling")
    
    # Add MACD trend analysis
    if all(col in account_analysis.columns for col in ['macd', 'macd_signal']):
        macd_trend = analyze_macd_trend(
            latest['macd'],
            latest['macd_signal'],
            account_analysis.iloc[-2]['macd'],
            account_analysis.iloc[-2]['macd_signal']
        )
        overview.append(f"\nMACD Trend: {macd_trend}")
    
    # Add volume trend analysis
    if 'volume' in account_analysis.columns:
        volume_trend = analyze_volume_trend(account_analysis['volume'].values)
        overview.append(f"Volume Trend: {volume_trend}")
    
    # Add RSI context if available
    if 'rsi' in latest.index:
        rsi = latest['rsi']
        rsi_context = get_trend_description(rsi)
        overview.append(f"RSI Signal ({rsi:.1f}): {rsi_context.upper()}")
    
    # Calculate and add spending targets
    spending_targets = calculate_spending_targets(account_analysis, opportunities)
    overview.append("\nTARGET ACCOUNT SPEND (90-Day Period)")
    overview.append("-" * 80)
    overview.append(f"Conservative: ${spending_targets['conservative']:,.2f}")
    overview.append(f"Balanced:     ${spending_targets['balanced']:,.2f}")
    overview.append(f"Aggressive:   ${spending_targets['aggressive']:,.2f}")
    overview.append(f"\nTrailing 90-Day Average: ${spending_targets['avg_historical']:,.2f}")
    
    # Add week-by-week timeline for the next 90 days
    overview.append("\nORDER TIMELINE (Next 90 Days)")
    overview.append("-" * 80)
    
    weeks = create_week_timeline(opportunities, 90)  # 90-day timeframe
    
    for week_num in sorted(weeks.keys()):
        week = weeks[week_num]
        timeline = create_bb_spectrum(week['position'])
        
        # Format the week header with date range
        week_dates = f"{week['start_date'].strftime('%m/%d')} - {week['end_date'].strftime('%m/%d')}"
        
        # Format the order ranges
        if len(week['products']) > 0:
            order_range = f"[${week['conservative']:,.0f} < ${week['balanced']:,.0f} < ${week['aggressive']:,.0f}]"
            overview.append(
                f"Week {week_num + 1} ({week_dates}): {timeline} {order_range} "
                f"({len(week['products'])} products)"
            )
        else:
            overview.append(f"Week {week_num + 1} ({week_dates}): No orders due")
    
    # Add summary recommendations
    overview.append("\nRECOMMENDED ACTIONS")
    overview.append("-" * 80)
    
    # Find the week with the highest balanced value
    optimal_week = max(weeks.items(), key=lambda x: x[1]['balanced'])[0]
    week = weeks[optimal_week]
    
    if len(week['products']) > 0:
        overview.append(
            f"Primary Focus: Week {optimal_week + 1} "
            f"[${week['conservative']:,.0f} < ${week['balanced']:,.0f} < ${week['aggressive']:,.0f}]"
        )
        
        # Add key products for optimal week
        key_products = sorted(
            week['products'],
            key=lambda x: x['priority_score']
        )[:3]
        
        overview.append("Key Products to Focus:")
        for product in key_products:
            overview.append(f"  - {product['product']}")
    
    # Calculate total opportunity ranges
    total_conservative = sum(week['conservative'] for week in weeks.values())
    total_balanced = sum(week['balanced'] for week in weeks.values())
    total_aggressive = sum(week['aggressive'] for week in weeks.values())
    
    overview.append(f"\nTotal 90-Day Opportunity:")
    overview.append(f"[${total_conservative:,.0f} < ${total_balanced:,.0f} < ${total_aggressive:,.0f}]")
    
    return "\n".join(overview)

# Modified main execution code:
if __name__ == "__main__":
    # NOTE: For appified version, credentials are managed securely via app.py
    # This main block is disabled - the app will set indicators_report.sf directly
    print("This script is designed to be used as a module by app.py")
    print("Please run the application using app.py or the launcher")
    print("For credential setup, run: python scripts/setup_credentials.py")
    sys.exit(0)
    
    # OLD CODE - DISABLED FOR SECURITY
    # sf_user = 'mblintegration@novozymes.com'
    # sf_p = 'Bv67f$#68ZC8T8f$PYigvcwB*rNaMsgl'
    # sf_token = 'xxkFzAZQcRZGuPqDSll3BIQl4'
    # sf = Salesforce(username=sf_user, password=sf_p, security_token=sf_token)
    account_id = '0012j00000VutSnAAJ'

    # Grant's accounts:
    # '0012j00000Vuv0nAAB' # Dawn Flickema, MD

    # Joseph Soucie's accounts:
    # '0012j00000Vv6VYAAZ' # Be Optimal

    # Ceylon's accounts:
    # '0012j00000VvSlaAAF' # Family Medicine Liberty Lake
    # '0012j00000Vvb2jAAB' # Northwest Life Medicine
    # '0012j00000VvIUCAA3' # Sage Integrative Medicine
    # '0012j00000VutSnAAJ' # Evergreen Naturopathics
    # '0012j00000VvHqzAAF' # Clinic 5c
    # '0012j00000c7PZdAAM' # In Light Hyperbarics

    # '0012j00000Vv77lAAB' # John Tjenos
    # '001Ij000002h1SEIAY' # Functional Nutrition (#3 account)
    # '0012j00000VvIxhAAF' # Wellness for Life
    # '0012j00000Vv9TAAAZ' # Natural Health Clinic (zombie for Emily Sharpe)
    # '0012j00000Vvc8yAAB' # Dr Emily Sharpe
    # '0012j00000VvAx7AAF' # NuHealth / Nadene Neale

    '''no_rep_account_ids =  ['0012j00000VuumAAAR']
    no_rep_account_names = ['PureFormulas Inc']
    rep_mgm_account_ids = ['0012j00000VvDkqAAF',  '0012j00000VvOClAAN', ]
    rep_mgm_account_names = [ 'Innovative Health and Wellness',  'Evolutionary Wellness', ]'''

    # Ben's top accounts: 
    # '0012j00000VvOClAAN' # Evolutionary Wellness
    # '0012j00000Vv8jgAAB' # Vitamin Portfolio
    # '0012j00000VuuDGAAZ' # Johnson Compounding and Wellness


    # Get orders for full period plus warm-up
    op_period = 90
    end_date = datetime.now()
    analysis_start = end_date - timedelta(days=365 * 5)

    # No need to add warm-up period here, it's handled in create_combined_analysis

    print(f"\nAnalysis period: {analysis_start.date()} to {end_date.date()}")

    # Get orders and distribute FS orders
    orders = get_account_orders(account_id, analysis_start, end_date)
    distributed_orders = distribute_monthly_orders(orders)
    
    print(f"\nOrder distribution summary:")
    print(f"Original orders: {len(orders)}")
    print(f"After FS distribution: {len(distributed_orders)}")

    # Create and show combined analysis with distributed orders
    fig = create_combined_analysis(
        account_id,
        analysis_start,
        end_date,
        resolution='3D',
        ma_window=op_period,
        warmup_days=op_period * 2,
        orders=distributed_orders  # Pass the distributed orders
    )
    
    fig.show()


def upload_product_image(product_name: str, image_path: str) -> bool:
    """
    Upload a product image to the images directory
    
    Args:
        product_name: Name of the product (e.g., "MegaSporeBiotic")
        image_path: Path to the source image file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create images directory if it doesn't exist
        images_dir = Path(__file__).parent / "images"
        images_dir.mkdir(exist_ok=True)
        
        # Convert product name to filename format
        filename = product_name.lower().replace(' ', '_').replace('-', '_') + '.jpg'
        destination = images_dir / filename
        
        # Copy the image file
        shutil.copy2(image_path, destination)
        print(f"Product image uploaded: {product_name} -> {destination}")
        return True
        
    except Exception as e:
        print(f"Error uploading product image: {e}")
        return False


def get_product_image_path(product_name: str) -> str:
    """
    Get the image path for a product
    
    Args:
        product_name: Name of the product
    
    Returns:
        str: Path to the product image
    """
    filename = product_name.lower().replace(' ', '_').replace('-', '_') + '.jpg'
    return f"images/{filename}"


def list_available_product_images() -> list:
    """
    List all available product images
    
    Returns:
        list: List of product names that have images
    """
    images_dir = Path(__file__).parent / "images"
    if not images_dir.exists():
        return []
    
    image_files = list(images_dir.glob("*.jpg"))
    product_names = []
    
    for image_file in image_files:
        # Convert filename back to product name
        product_name = image_file.stem.replace('_', ' ').title()
        product_names.append(product_name)
    
    return sorted(product_names)



# Working overlay options for all data, including cash value contributions to account value at product level
# [ ] Query events/campaigns and search for coupons used to generate orders. Mark with verticle line on report in all charts
## With all-company data, events timing could be optimized for when customers are most generally open to buying
## On a rep-territory level, same applies
# [ ] Pipe amazon thru sellingview
# [ ] NuHealth data not displaying for recent orders

import pandas_ta as ta
import pandas as pd
from simple_salesforce import Salesforce, SFBulkHandler
import plotly.graph_objects as go
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np

def get_account_name(account_id):
    query = f"""
        SELECT Id, Name FROM Account WHERE Id = '{account_id}'
    """
    account = sf.query_all(query)
    account_name = account['records'][0]['Name']
    
    # Clean up account name - remove (DSS) prefix if present
    if account_name.startswith('(DSS) '):
        account_name = account_name[6:]  # Remove "(DSS) " prefix
    
    return account_name

def get_account_info(account_id):
    """
    Get account name and owner username
    Returns dict with 'name' and 'owner_username' keys
    """
    query = f"""
        SELECT Id, Name, Owner.Username FROM Account WHERE Id = '{account_id}'
    """
    account = sf.query_all(query)
    record = account['records'][0]
    
    owner_username = ''
    if record.get('Owner') and record['Owner'].get('Username'):
        owner_username = record['Owner']['Username']
    
    return {
        'name': record['Name'],
        'owner_username': owner_username
    }

def get_child_accounts(parent_account_id):
    """
    Find all child accounts that have this account as their parent.
    Uses MBL_Custom_ParentAccountId_18__c to find child accounts.
    """
    query = f"""
        SELECT 
            Id, 
            Name, 
            MBL_Is_Child_Account__c 
        FROM Account 
        WHERE MBL_Custom_ParentAccountId_18__c = '{parent_account_id}'
        AND MBL_Is_Child_Account__c = true
    """
    
    try:
        child_accounts = sf.query_all(query)
        print(f"Found {len(child_accounts['records'])} child accounts")
        return child_accounts['records']
    except Exception as e:
        print(f"Error fetching child accounts: {str(e)}")
        return []

def get_account_orders(account_id, start_date=None, end_date=None):
    # Get child accounts first
    child_accounts = get_child_accounts(account_id)
    all_account_ids = [account_id] + [acc['Id'] for acc in child_accounts]
    
    # Build date filter if dates are provided
    date_filter = ""
    if start_date:
        date_filter += f" AND MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    if end_date:
        date_filter += f" AND MBL_Order_Shipped_Time__c <= {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    
    # Create account ID filter
    account_filter = "AccountId IN ('" + "','".join(all_account_ids) + "')"
    
    # Modify query to include Account.Name
    query = f"""
        SELECT 
            Id, 
            MBL_Order_Shipped_Time__c, 
            TotalAmount, 
            MBL_Total_Number_of_Products__c,
            AccountId,
            Account.Name,
            Type
        FROM Order 
        WHERE {account_filter}
        {date_filter}
        ORDER BY MBL_Order_Shipped_Time__c ASC
    """
    
    try:
        orders = sf.query_all(query)
        
        # Print summary of orders found
        print(f"\nOrder Summary:")
        print(f"Total orders found: {len(orders['records'])}")
        
        # Group orders by account
        orders_by_account = {}
        for order in orders['records']:
            acc_id = order['AccountId']
            acc_name = order['Account']['Name']
            if acc_id not in orders_by_account:
                orders_by_account[acc_id] = {'name': acc_name, 'count': 0}
            orders_by_account[acc_id]['count'] += 1
        
        # Print breakdown
        for acc_id, info in orders_by_account.items():
            print(f"  {info['name']}: {info['count']} orders")
            
        return orders['records']
        
    except Exception as e:
        print(f"Error fetching orders: {str(e)}")
        return []

def get_order_quantities(order_ids):
    """
    Get total quantities and prices from OrderItems for given Order IDs using Bulk API
    Returns a dictionary with quantity and price information
    """
    if not order_ids:
        return {}
    
    # Update query to include price information
    query = """
        SELECT 
            OrderId, 
            SUM(Quantity) total_quantity,
            SUM(TotalPrice) total_price,
            AVG(UnitPrice) avg_unit_price
        FROM OrderItem 
        WHERE OrderId IN ('{}')
        GROUP BY OrderId
    """.format("','".join(order_ids))
    
    try:
        # Execute bulk query using sf.bulk
        job = sf.bulk.OrderItem.query(query)
        results = list(job)
        
        # Create dictionary mapping Order ID to quantity and price info
        order_data = {
            record['OrderId']: {
                'quantity': float(record['total_quantity']),
                'total_price': float(record['total_price']),
                'unit_price': float(record['avg_unit_price'])
            }
            for record in results
        }
        
        return order_data
        
    except Exception as e:
        print(f"Bulk API Error: {str(e)}")
        print("Falling back to regular query with batched IDs...")
        
        # Fallback: Process in smaller batches
        batch_size = 100
        order_data = {}
        
        for i in range(0, len(order_ids), batch_size):
            batch_ids = order_ids[i:i + batch_size]
            order_id_string = "','".join(batch_ids)
            
            query = f"""
                SELECT 
                    OrderId, 
                    SUM(Quantity) total_quantity,
                    SUM(TotalPrice) total_price,
                    AVG(UnitPrice) avg_unit_price
                FROM OrderItem 
                WHERE OrderId IN ('{order_id_string}')
                GROUP BY OrderId
            """
            
            batch_results = sf.query_all(query)
            batch_data = {
                record['OrderId']: {
                    'quantity': float(record['total_quantity']),
                    'total_price': float(record['total_price']),
                    'unit_price': float(record['avg_unit_price'])
                }
                for record in batch_results['records']
            }
            order_data.update(batch_data)
        
        return order_data

def create_ohlcv_from_orders(orders, resolution='1M', ma_window=90):
    """
    Create OHLCV DataFrame showing how orders influence the quarterly moving average
    
    Parameters:
    - orders: Salesforce order records
    - resolution: Time period grouping ('3D', '1W', '2W', '1M')
    - ma_window: Moving average window in days (default 90 for quarterly)
    """
    freq_map = {
        '3D': '3D',
        '1W': 'W',
        '2W': '2W',
        '1M': 'M'
    }
    freq = freq_map[resolution]

    # Get order IDs and their quantities/prices
    order_ids = [order['Id'] for order in orders]
    order_data = get_order_quantities(order_ids)
    
    # Convert orders to DataFrame and sort by date
    df = pd.DataFrame(orders)
    df['MBL_Order_Shipped_Time__c'] = pd.to_datetime(df['MBL_Order_Shipped_Time__c'])
    df['TotalAmount'] = pd.to_numeric(df['TotalAmount'])
    
    # Add quantities and prices to DataFrame
    df['volume'] = df['Id'].map(lambda x: order_data.get(x, {}).get('quantity', 0))
    df['unit_price'] = df['Id'].map(lambda x: order_data.get(x, {}).get('unit_price', 0))
    df['volume'] = df['volume'].fillna(0)
    df['unit_price'] = df['unit_price'].fillna(0)
    
    df = df.sort_values('MBL_Order_Shipped_Time__c')
    
    # Calculate daily cumulative account value
    daily_df = df.set_index('MBL_Order_Shipped_Time__c')
    daily_df = daily_df.resample('D').agg({
        'TotalAmount': 'sum',
        'volume': 'sum',
        'unit_price': 'mean'  # Take mean of unit price for the day
    }).fillna(method='ffill')  # Forward fill unit prices
    
    # Calculate simple MA without normalization
    daily_df['MA'] = daily_df['TotalAmount'].rolling(
        window=ma_window, 
        min_periods=1
    ).mean()
    
    # Find first valid MA date (where we have full window)
    first_valid_ma = daily_df.index[ma_window-1] if len(daily_df) >= ma_window else None
    if first_valid_ma is None:
        print("Warning: Not enough data for MA calculation")
        return pd.DataFrame()  # Return empty frame if not enough data
        
    print(f"\nFirst valid MA date: {first_valid_ma.date()}")
    
    # Group by specified frequency for candlesticks
    grouped = df.groupby(pd.Grouper(key='MBL_Order_Shipped_Time__c', freq=freq)).agg({
        'TotalAmount': list,
        'volume': 'sum',
        'unit_price': 'mean'  # Take mean of unit price for the period
    })
    
    # Initialize OHLCV DataFrame
    ohlcv = pd.DataFrame(index=grouped.index)
    ohlcv['volume'] = grouped['volume']
    ohlcv['unit_price'] = grouped['unit_price'].fillna(method='ffill')  # Forward fill unit prices
    
    # Initialize is_live column (marks current open candle)
    ohlcv['is_live'] = False
    
    # Get the last available date with data
    last_data_date = daily_df.index[-1]
    
    # Process periods including current open candle
    for idx in grouped.index:
        if idx < first_valid_ma:
            continue
            
        period_start = idx
        period_end = idx + pd.Timedelta(freq)
        
        # Check if this is the current/open candle (period extends beyond available data)
        is_current_candle = period_end > last_data_date
        
        if is_current_candle:
            # LIVE CANDLE: Use current data through today
            print(f"  📊 Including LIVE candle: {period_start.date()} - {period_end.date()} (current through {last_data_date.date()})")
            
            # Get all MA data from period start through today
            period_ma = daily_df.loc[period_start:last_data_date, 'MA']
            
            if len(period_ma) == 0 or period_start not in daily_df.index:
                continue
            
            ma_start = daily_df.loc[period_start, 'MA']
            ma_current = daily_df['MA'].iloc[-1]  # Current MA value (today)
            
            # Set OHLC values using live data
            ohlcv.at[idx, 'open'] = ma_start
            ohlcv.at[idx, 'close'] = ma_current  # Live close value
            ohlcv.at[idx, 'high'] = period_ma.max()
            ohlcv.at[idx, 'low'] = period_ma.min()
            ohlcv.at[idx, 'is_live'] = True
            
        else:
            # CLOSED CANDLE: Use complete period data
            if period_end > daily_df['MA'].last_valid_index():
                continue
                
            period_orders = grouped.at[idx, 'TotalAmount']
            if not isinstance(period_orders, list) or len(period_orders) == 0:
                continue
            
            # Get MA values for closed candle
            ma_start = daily_df.loc[period_start, 'MA']
            ma_end = daily_df.loc[period_end, 'MA'] if period_end in daily_df.index else ma_start
            
            # Set OHLC values
            ohlcv.at[idx, 'open'] = ma_start
            ohlcv.at[idx, 'close'] = ma_end
            period_ma = daily_df.loc[period_start:period_end, 'MA']
            ohlcv.at[idx, 'high'] = period_ma.max()
            ohlcv.at[idx, 'low'] = period_ma.min()
            ohlcv.at[idx, 'is_live'] = False
    
    # Remove any periods without valid data
    ohlcv = ohlcv.dropna(subset=['open', 'close', 'high', 'low'])
    
    # Print analysis for valid periods only
    print(f"\nMoving Average Analysis:")
    print(f"Total valid periods: {len(ohlcv)}")
    live_candles = ohlcv['is_live'].sum()
    if live_candles > 0:
        print(f"  ✨ Including {live_candles} LIVE candle(s) with current data")
    print(f"Periods with declining MA: {(ohlcv['close'] < ohlcv['open']).sum()}")
    print(f"Periods with rising MA: {(ohlcv['close'] > ohlcv['open']).sum()}")
    
    # Calculate volume SMA
    ohlcv['volume_sma'] = ta.sma(ohlcv['volume'], length=14)
    
    return ohlcv

def calculate_indicators(df, MA_length=20):
    """
    Calculate all technical indicators needed for plotting
    Returns DataFrame with added indicator columns and simulated decay data
    """
    # First check if we have the required OHLC columns
    required_columns = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_columns):
        print("Warning: Missing required OHLC columns for indicator calculation")
        df['insufficient_data'] = True
        return df
    
    # Initialize bbands to None
    bbands = None
    
    # Add indicator columns only if we have enough data
    if len(df) >= MA_length:
        try:
            df[f'sma_{MA_length}'] = ta.sma(df['close'], length=MA_length)
            df[f'ema_{MA_length}'] = ta.ema(df['close'], length=MA_length)
        except Exception as e:
            print(f"Warning: Could not calculate MA indicators: {str(e)}")
    
    # Bollinger Bands - require at least 20 points
    if len(df) >= 20:
        try:
            # Match simple_report_app exactly: use std=2.0 parameter
            bbands = ta.bbands(df['close'], length=20, std=2.0)
            if bbands is not None and not bbands.empty:
                # Debug: Check what columns we actually got
                if 'BBU_20_2.0' not in bbands.columns:
                    print(f"Debug: ta.bbands() returned columns: {list(bbands.columns)}")
                    print(f"Debug: DataFrame shape: {bbands.shape}, type: {type(bbands)}")
                    print(f"Debug: Looking for BBU_20_2.0, BBM_20_2.0, BBL_20_2.0")
                    # Try to find columns with similar names
                    upper_cols = [c for c in bbands.columns if 'BBU' in str(c) or 'upper' in str(c).lower()]
                    middle_cols = [c for c in bbands.columns if 'BBM' in str(c) or 'middle' in str(c).lower()]
                    lower_cols = [c for c in bbands.columns if 'BBL' in str(c) or 'lower' in str(c).lower()]
                    print(f"Debug: Found upper-like columns: {upper_cols}")
                    print(f"Debug: Found middle-like columns: {middle_cols}")
                    print(f"Debug: Found lower-like columns: {lower_cols}")
                    raise KeyError(f"BBU_20_2.0 column not found. Available columns: {list(bbands.columns)}")
                
                # Match simple_report_app exactly: access columns directly
                df['bb_upper'] = bbands['BBU_20_2.0']
                df['bb_middle'] = bbands['BBM_20_2.0']
                df['bb_lower'] = bbands['BBL_20_2.0']
                
                # Calculate decay simulation here while we have the BB data
                latest_close = df['close'].iloc[-1]
                latest_bb_lower = df['bb_lower'].iloc[-1]
                latest_bb_middle = df['bb_middle'].iloc[-1]
                
                # Get the last 90 periods for simulation
                close_values = df['close'].iloc[-90:].values
                current_ma = np.mean(close_values)
                
                # Function to simulate next period's MA only
                def simulate_next_period(values):
                    new_values = np.append(values[1:], 0)  # Remove oldest, add 0
                    new_ma = np.mean(new_values)
                    return new_values, new_ma
                
                # Initialize simulation results
                df['days_until_lower_breach'] = 0
                df['days_until_middle_breach'] = 0
                
                # Simulate for lower band if above it
                if latest_close > latest_bb_lower:
                    simulation_values = close_values.copy()
                    periods = 0
                    max_periods = 90  # Maximum 90 3-day periods
                    
                    while periods < max_periods:
                        simulation_values, new_ma = simulate_next_period(simulation_values)
                        if new_ma <= latest_bb_lower:
                            break
                        periods += 1
                    
                    df['days_until_lower_breach'] = periods * 3  # Convert to days
                
                # Simulate for middle band if above it
                if latest_close > latest_bb_middle:
                    simulation_values = close_values.copy()
                    periods = 0
                    max_periods = 90  # Maximum 90 3-day periods
                    
                    while periods < max_periods:
                        simulation_values, new_ma = simulate_next_period(simulation_values)
                        if new_ma <= latest_bb_middle:
                            break
                        periods += 1
                    
                    df['days_until_middle_breach'] = periods * 3  # Convert to days
            elif bbands is None:
                print(f"Debug: ta.bbands() returned None for {len(df)} data points")
            elif bbands.empty:
                print(f"Debug: ta.bbands() returned empty DataFrame for {len(df)} data points")
        except Exception as e:
            print(f"Warning: Could not calculate Bollinger Bands: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # RSI - requires at least 14 points
    if len(df) >= 14:
        try:
            df['rsi'] = ta.rsi(df['close'], length=14)
            if len(df) >= 28:  # Need at least 28 points for RSI MA
                df['rsi_ma'] = ta.sma(df['rsi'], length=14)
        except Exception as e:
            print(f"Warning: Could not calculate RSI: {str(e)}")
    
    # MACD - requires at least 26 points
    if len(df) >= 26:
        try:
            macd = ta.macd(df['close'])
            if macd is not None:
                df['macd'] = macd['MACD_12_26_9']
                df['macd_signal'] = macd['MACDs_12_26_9']
                df['macd_hist'] = macd['MACDh_12_26_9']
        except Exception as e:
            print(f"Warning: Could not calculate MACD: {str(e)}")
    
    # Mark if we have sufficient data
    df['insufficient_data'] = False
    
    return df

def get_account_order_products(account_id, start_date=None, end_date=None):
    """
    Get OrderItem records with product details for an account with cascading product name fallbacks
    """
    date_filter = ""
    if start_date:
        date_filter += f" AND Order.MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    if end_date:
        date_filter += f" AND Order.MBL_Order_Shipped_Time__c <= {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    
    query = f"""
        SELECT 
            Id,
            Order.MBL_Order_Shipped_Time__c,
            Order.TotalAmount,
            Product2Id,
            Product_Name__c,
            Product2.Name,
            Product2.ProductCode,
            Quantity,
            TotalPrice,
            UnitPrice
        FROM OrderItem 
        WHERE Order.AccountId = '{account_id}'
        {date_filter}
        ORDER BY Order.MBL_Order_Shipped_Time__c ASC
    """
    order_products = sf.query_all(query)
    
    # Apply cascading product name fallback logic to each record
    for record in order_products['records']:
        product_name = (record.get('Product_Name__c') or '').strip()
        product2_name = ''
        product2_code = ''
        
        if record.get('Product2'):
            product2_name = (record['Product2'].get('Name') or '').strip()
            product2_code = (record['Product2'].get('ProductCode') or '').strip()
        
        # Use Product_Name__c if available and non-empty
        if product_name:
            final_name = product_name
        # Otherwise try Product2.Name
        elif product2_name:
            final_name = product2_name
            print(f"  ℹ Using Product2.Name for Product2Id {record['Product2Id']}: {final_name}")
        # Last resort: use ProductCode
        elif product2_code:
            final_name = product2_code
            print(f"  ⚠ Using ProductCode for Product2Id {record['Product2Id']}: {final_name}")
        else:
            final_name = f"Unknown Product ({record['Product2Id']})"
            print(f"  ✗ No name found for Product2Id {record['Product2Id']}")
        
        # Update the record with the final name
        record['Product_Name__c'] = final_name
    
    return order_products['records']

def create_product_ohlcv(order_products, product_id, resolution='3D', ma_window=90, pricebook_prices=None):
    """
    Create OHLCV DataFrame for a specific product
    
    Args:
        order_products: List of OrderItem records
        product_id: Product2Id to filter for
        resolution: Time period grouping ('3D', '1W', '2W', '1M')
        ma_window: Moving average window in days
        pricebook_prices: Dict mapping Product2Id to current pricebook unit price (optional)
    """
    # Filter for specific product
    product_orders = [
        order for order in order_products 
        if order['Product2Id'] == product_id
    ]
    
    if not product_orders:
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(product_orders)
    
    # Extract nested Order fields
    df['date'] = pd.to_datetime([order['Order']['MBL_Order_Shipped_Time__c'] for order in product_orders])
    df['OrderTotalAmount'] = [order['Order']['TotalAmount'] for order in product_orders]
    df['TotalPrice'] = pd.to_numeric(df['TotalPrice'])
    df['Quantity'] = pd.to_numeric(df['Quantity'])
    
    # Determine unit price to use
    if pricebook_prices and product_id in pricebook_prices:
        # Use current pricebook price for all calculations
        current_unit_price = pricebook_prices[product_id]
        df['UnitPrice'] = current_unit_price
        print(f"    Using pricebook price: ${current_unit_price:.2f}")
    else:
        # Fallback to historical OrderItem prices
        df['UnitPrice'] = pd.to_numeric(df['UnitPrice'])
        avg_historical_price = df['UnitPrice'].mean()
        print(f"    Using historical average price: ${avg_historical_price:.2f}")
    
    # Sort by date
    df = df.sort_values('date')
    
    # Resample to daily and fill gaps
    daily_df = df.set_index('date').resample('D').agg({
        'TotalPrice': 'sum',
        'Quantity': 'sum',
        'UnitPrice': 'mean'  # Keep consistent unit price
    }).fillna(method='ffill')  # Forward fill unit prices
    
    # Calculate simple MA without normalization
    daily_df['MA'] = daily_df['TotalPrice'].rolling(
        window=ma_window,
        min_periods=1
    ).mean()
    
    # Find first valid MA date (where we have full window)
    first_valid_ma = daily_df.index[ma_window-1] if len(daily_df) >= ma_window else None
    if first_valid_ma is None:
        return None  # Not enough data
    
    # Group by resolution
    freq_map = {
        '3D': '3D',
        '1W': 'W',
        '2W': '2W',
        '1M': 'M'
    }
    freq = freq_map[resolution]
    
    grouped = df.groupby(pd.Grouper(key='date', freq=freq)).agg({
        'TotalPrice': list,
        'Quantity': 'sum'
    })
    
    # Create OHLCV DataFrame
    ohlcv = pd.DataFrame(index=grouped.index)
    ohlcv['volume'] = grouped['Quantity']
    ohlcv['unit_price'] = daily_df['UnitPrice'].resample(freq).mean().fillna(method='ffill')
    
    # Initialize is_live column (marks current open candle)
    ohlcv['is_live'] = False
    
    # Get the last available date with data
    last_data_date = daily_df.index[-1]
    
    # Calculate OHLC values including current open candle
    for idx in grouped.index:
        if idx < first_valid_ma:
            continue
            
        period_start = idx
        period_end = idx + pd.Timedelta(freq)
        
        # Check if period start is valid
        if period_start not in daily_df.index:
            continue
        
        # Check if this is the current/open candle
        is_current_candle = period_end > last_data_date
        
        if is_current_candle:
            # LIVE CANDLE: Use current data through today
            period_data = daily_df.loc[period_start:last_data_date, 'MA']
            
            if len(period_data) < 1:
                continue
            
            ma_start = period_data.iloc[0]
            ma_current = daily_df['MA'].iloc[-1]  # Current MA value
            
            # Set OHLC values using live data
            ohlcv.at[idx, 'open'] = ma_start
            ohlcv.at[idx, 'close'] = ma_current  # Live close value
            ohlcv.at[idx, 'high'] = period_data.max()
            ohlcv.at[idx, 'low'] = period_data.min()
            ohlcv.at[idx, 'is_live'] = True
            
        else:
            # CLOSED CANDLE: Use complete period data
            if period_end > daily_df.index[-1]:
                continue
                
            # Get MA values - handle case where we might not have enough data points
            period_data = daily_df.loc[period_start:period_end, 'MA']
            if len(period_data) < 2:
                continue
                
            ma_start = period_data.iloc[0]
            ma_end = period_data.iloc[-1]
            
            ohlcv.at[idx, 'open'] = ma_start
            ohlcv.at[idx, 'close'] = ma_end
            ohlcv.at[idx, 'high'] = period_data.max()
            ohlcv.at[idx, 'low'] = period_data.min()
            ohlcv.at[idx, 'is_live'] = False
    
    ohlcv = ohlcv.dropna()
    
    # Add volume SMA calculation before returning
    ohlcv['volume_sma'] = ta.sma(ohlcv['volume'], length=14)
    
    return ohlcv

def get_pricebook_prices(product_ids):
    """
    Get current unit prices from Pricebook for given Product2Ids
    Returns dict mapping Product2Id to unit price
    """
    if not product_ids:
        return {}
    
    print(f"\n🔍 Fetching pricebook prices for {len(product_ids)} products...")
    
    # First, get the standard pricebook ID
    try:
        std_pricebook = sf.query("SELECT Id FROM Pricebook2 WHERE IsStandard = true LIMIT 1")
        if not std_pricebook['records']:
            print("  ⚠️  Warning: No standard pricebook found, falling back to historical prices")
            return {}
        
        pricebook_id = std_pricebook['records'][0]['Id']
        print(f"  Using Standard Pricebook: {pricebook_id}")
    except Exception as e:
        print(f"  ⚠️  Error getting standard pricebook: {str(e)}")
        return {}
    
    # Query PricebookEntry for all products
    product_id_list = "','".join(product_ids)
    query = f"""
        SELECT Product2Id, UnitPrice, IsActive, Product2.Name
        FROM PricebookEntry
        WHERE Pricebook2Id = '{pricebook_id}'
        AND Product2Id IN ('{product_id_list}')
        AND IsActive = true
    """
    
    try:
        results = sf.query_all(query)
        price_map = {}
        
        for record in results['records']:
            product_id = record['Product2Id']
            unit_price = float(record['UnitPrice'])
            product_name = record['Product2']['Name'] if record.get('Product2') else 'Unknown'
            price_map[product_id] = unit_price
            print(f"  ✓ {product_name}: ${unit_price:.2f}")
        
        # Report any products not found in pricebook
        missing = set(product_ids) - set(price_map.keys())
        if missing:
            print(f"  ⚠️  {len(missing)} products not found in pricebook (will use historical prices)")
        
        print(f"  ✓ Found pricebook prices for {len(price_map)}/{len(product_ids)} products\n")
        return price_map
        
    except Exception as e:
        print(f"  ⚠️  Error querying pricebook entries: {str(e)}")
        return {}

def get_account_products(account_id, start_date, end_date):
    """
    Get unique products ordered by an account with full product name fallbacks
    """
    query = f"""
        SELECT 
            Product2Id,
            Product_Name__c,
            Product2.Name,
            Product2.ProductCode
        FROM OrderItem 
        WHERE Order.AccountId = '{account_id}'
        AND Order.MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}
        AND Order.MBL_Order_Shipped_Time__c <= {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}
    """
    products = sf.query_all(query)
    
    # Create dictionary of unique products with cascading name fallback
    unique_products = {}
    for record in products['records']:
        product_id = record['Product2Id']
        if product_id not in unique_products:
            # Cascade through available name fields - handle None values
            product_name = (record.get('Product_Name__c') or '').strip()
            
            # Debug output for each product
            print(f"Debug: Product2Id {product_id}")
            print(f"  - Product_Name__c: '{record.get('Product_Name__c')}'")
            print(f"  - Product2: {record.get('Product2')}")
            
            # If Product_Name__c is empty, try Product2.Name
            if not product_name and record.get('Product2'):
                product_name = (record['Product2'].get('Name') or '').strip()
                if product_name:
                    print(f"  ✓ Using Product2.Name: {product_name}")
            
            # If still empty, try Product2.ProductCode
            if not product_name and record.get('Product2'):
                product_name = (record['Product2'].get('ProductCode') or '').strip()
                if product_name:
                    print(f"  ⚠ Using ProductCode: {product_name}")
            
            # Last resort - query Product2 directly from Salesforce
            if not product_name:
                print(f"  ⚠ All name fields empty, querying Product2 directly...")
                try:
                    product_direct = sf.query(f"SELECT Name, ProductCode, Description FROM Product2 WHERE Id = '{product_id}'")
                    if product_direct['records']:
                        prod_record = product_direct['records'][0]
                        product_name = (prod_record.get('Name') or '').strip()
                        if not product_name:
                            product_name = (prod_record.get('ProductCode') or '').strip()
                        if not product_name:
                            product_name = (prod_record.get('Description') or '').strip()
                        if product_name:
                            print(f"  ✓ Retrieved from Product2 direct query: {product_name}")
                except Exception as e:
                    print(f"  ✗ Error querying Product2 directly: {str(e)}")
            
            # Final fallback
            if not product_name:
                product_name = f'Unknown Product ({product_id})'
                print(f"  ✗ No name found, using: {product_name}")
            
            unique_products[product_id] = product_name
    
    print(f"\nFound {len(unique_products)} unique products for account")
    return unique_products

def consolidate_product_data(analyses, resolution_freq, analysis_start_date, end_date_timestamp):
    """
    Consolidate all product data to ensure consistent time periods across all products.
    Returns a dictionary of {date: {product_name: value}}
    """
    # Create a uniform date range
    consolidated_range = pd.date_range(
        start=analysis_start_date,
        end=end_date_timestamp,
        freq=resolution_freq
    )
    
    # Initialize the consolidated data structure
    consolidated_data = {date: {} for date in consolidated_range}
    
    # Process each product's data
    for product_name, df in analyses.items():
        if product_name == 'Account Overview' or df is None or df.empty:
            continue
            
        print(f"Consolidating data for {product_name}: {len(df)} original data points")
        
        # For each date in our consolidated range, find the matching product value
        for target_date in consolidated_range:
            if target_date in df.index:
                # Direct match
                consolidated_data[target_date][product_name] = df.loc[target_date, 'close']
            else:
                # Find the most recent value before this date
                mask = df.index <= target_date
                if mask.any():
                    latest_value = df[mask]['close'].iloc[-1]
                    consolidated_data[target_date][product_name] = latest_value
    
    # Count unique products for debugging
    all_products = set()
    for date_data in consolidated_data.values():
        all_products.update(date_data.keys())
    
    print(f"Consolidated data includes {len(all_products)} unique products")
    
    return consolidated_data

def calculate_average_order_interval(df):
    """
    Calculate the average time between orders for a product
    Returns the interval in days
    """
    if df is None or df.empty or 'volume' not in df.columns:
        return None
    
    # Get dates where volume > 0 (actual orders)
    order_dates = df[df['volume'] > 0].index
    if len(order_dates) < 2:
        return None
    
    # Calculate differences between consecutive orders
    intervals = np.diff(order_dates)
    avg_interval = np.mean(intervals)
    
    # Convert timedelta to days
    return avg_interval.days

def get_trend_description(current_rsi):
    """
    Get a plain language description of the RSI trend
    """
    if current_rsi < 30:
        return "Very open to ordering"
    elif current_rsi < 40:
        return "Open to ordering"
    elif current_rsi < 45:
        return "Neutral"
    elif current_rsi < 50:
        return "Resistant to ordering"
    else:
        return "Strongly resistant to ordering"

def create_bb_spectrum(position_in_band):
    """
    Create a visual spectrum representation of position within Bollinger Bands
    Returns a string with wider spacing to match the key format
    """
    # Create a wider spectrum with more dashes
    spectrum = list('||---------------||----------------||')
    
    if position_in_band < 0:  # Below floor
        spectrum.insert(0, 'x')
    elif position_in_band > 100:  # Above ceiling
        spectrum.append('x')
    else:
        # Calculate position in the wider spectrum (now with more positions)
        # We have 31 possible positions (15 dashes in each section + the dividers)
        pos = int(2 + (position_in_band / 100.0 * 31))
        spectrum[pos] = 'x'
    
    return ''.join(spectrum)

def calculate_order_recommendations(opp):
    """
    Calculate recommended order quantities based on Bollinger Bands and product value
    Returns dict with recommendations and sustainability period
    """
    current_value = opp['current_close']
    bb_lower = opp['bb_lower']
    bb_middle = opp['bb_middle']
    bb_upper = opp['bb_upper']
    
    # Get the product's average price per unit from recent orders
    recent_volume = sum(opp['volume'][-14:])  # Last 14 periods
    if recent_volume == 0:
        return None  # Can't calculate without recent order data
        
    recent_value = sum(opp['volume'][-14:] * opp['current_close'])
    avg_price_per_unit = recent_value / recent_volume
    
    # Calculate how many days until value drops below lower band
    if current_value > bb_lower:
        # Use the average daily decline rate from the last period
        daily_decline = (opp['volume'][0] - opp['volume'][-1]) / len(opp['volume'])
        if daily_decline > 0:
            days_until_lower = (current_value - bb_lower) / daily_decline
        else:
            days_until_lower = float('inf')
    else:
        days_until_lower = 0
    
    def calculate_target_quantity(target_value):
        """Calculate quantity needed to reach a target value"""
        if current_value >= target_value:
            return 0
            
        # Calculate how much value we need to add
        value_gap = target_value - current_value
        
        # Convert value gap to quantity using price per unit
        # Consider the impact on the moving average
        # The new order will increase the MA by (order_value / MA_window)
        ma_window = 90  # This should match your MA_window parameter
        required_order_value = value_gap * ma_window
        
        # Convert to quantity
        quantity = required_order_value / avg_price_per_unit
        
        # Round to nearest whole unit
        return max(0, round(quantity))
    
    recommendations = {
        'conservative': {
            'quantity': calculate_target_quantity(bb_lower),
            'target': 'floor',
            'sustainability_days': round(days_until_lower)
        },
        'balanced': {
            'quantity': calculate_target_quantity(bb_middle),
            'target': 'average'
        },
        'aggressive': {
            'quantity': calculate_target_quantity(bb_upper),
            'target': 'ceiling'
        }
    }
    
    return recommendations

def format_opportunity_report(opportunities, account_analysis=None):
    """
    Generate a formatted report with actionable order recommendations grouped by workweeks
    
    Parameters:
    - opportunities: List of product opportunities
    - account_analysis: Account overview DataFrame with indicators (optional)
    """
    try:
        report = ["Product Sales Opportunity Report"]
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add the report legend
        report.append("\n" + "=" * 80 + "\n")
        report.append("How to read this report:")
        report.append("1. Account Overview provides:")
        report.append("   - Current market position and trend analysis")
        report.append("   - 90-day spending targets (Conservative/Balanced/Aggressive)")
        report.append("   - Week-by-week order timeline with value ranges")
        report.append("2. Products are grouped by workweeks based on next order date")
        report.append("3. Priority ranking indicates product's contribution value")
        report.append("   and market position (lower number = higher priority)")
        report.append("4. Order recommendations show:")
        report.append("   - Conservative: Maintain floor support")
        report.append("   - Balanced: Target historical average")
        report.append("   - Aggressive: Reach upper band value")
        report.append("5. Weekly summaries include:")
        report.append("   - Total value ranges [Conservative < Balanced < Aggressive]")
        report.append("   - Number of products due")
        report.append("   - Individual product recommendations\n")
        report.append("=" * 80 + "\n")
        
        # Add account-level overview using the new format_account_overview function
        if account_analysis is not None and not account_analysis.empty:
            account_overview = format_account_overview(account_analysis, opportunities)
            report.append(account_overview)
            report.append("\n" + "=" * 80 + "\n")
        
        if not opportunities:
            report.append("No priority opportunities found matching criteria.\n")
            return "\n".join(report)

        # Group opportunities by workweek based on next order date
        order_weeks = {}
        for opp in opportunities:
            if opp.get('order_interval'):
                next_order_date = datetime.now() + timedelta(days=opp['order_interval'])
                days_until_monday = (next_order_date.weekday()) % 7
                week_start = next_order_date - timedelta(days=days_until_monday)
                week_end = week_start + timedelta(days=4)  # End on Friday
                week_key = f"{week_start.strftime('%Y.%m.%d')} - {week_end.strftime('%Y.%m.%d')}"
                
                if week_key not in order_weeks:
                    order_weeks[week_key] = {
                        'products': [],
                        'conservative': 0,
                        'balanced': 0,
                        'aggressive': 0,
                        'start_date': week_start,
                        'end_date': week_end
                    }
                order_weeks[week_key]['products'].append(opp)

        # Sort weeks chronologically
        sorted_week_keys = sorted(order_weeks.keys())
        
        # Process each week
        for i, week_key in enumerate(sorted_week_keys):
            week_data = order_weeks[week_key]
            week_products = week_data['products']
            
            # Calculate total recommended values for this week
            for opp in week_products:
                # Debug: Check for missing Bollinger Bands data
                if 'bb_upper' not in opp or 'bb_lower' not in opp or 'bb_middle' not in opp:
                    print(f"Debug: Missing BB data in week calculation for {opp.get('product', 'unknown')}")
                    print(f"  Available keys: {list(opp.keys())}")
                    print(f"  Has bb_upper: {'bb_upper' in opp}")
                    print(f"  Has bb_lower: {'bb_lower' in opp}")
                    print(f"  Has bb_middle: {'bb_middle' in opp}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                # Target the correct percentile levels:
                # Conservative = 50th percentile (bb_middle)
                # Balanced = 70th percentile (between middle and upper)
                # Aggressive = 100th percentile (bb_upper)
                bb_70th = opp['bb_lower'] + (opp['bb_upper'] - opp['bb_lower']) * 0.7
                
                cons_qty = calculate_target_quantity(opp, opp['bb_middle'])
                bal_qty = calculate_target_quantity(opp, bb_70th)
                agg_qty = calculate_target_quantity(opp, opp['bb_upper'])
                
                week_data['conservative'] += cons_qty * opp['unit_price']
                week_data['balanced'] += bal_qty * opp['unit_price']
                week_data['aggressive'] += agg_qty * opp['unit_price']
            
            # Add week header with value ranges
            report.append(f"ORDER WEEK: {week_key}")
            report.append(f"Value Range: [${week_data['conservative']:,.0f} < ${week_data['balanced']:,.0f} < ${week_data['aggressive']:,.0f}]")
            report.append(f"Products Due: {len(week_products)}\n")
            
            # Sort products within this week by priority score
            products = sorted(week_products, key=lambda x: x['priority_score'])
            
            # Process all products for this week
            for j, opp in enumerate(products):
                try:
                    # Debug: Check for missing Bollinger Bands data before processing
                    if 'bb_upper' not in opp or 'bb_lower' not in opp or 'bb_middle' not in opp:
                        print(f"Debug: Missing BB data in product formatting for {opp.get('product', 'unknown')}")
                        print(f"  Available keys: {list(opp.keys())}")
                        print(f"  Has bb_upper: {'bb_upper' in opp}")
                        print(f"  Has bb_lower: {'bb_lower' in opp}")
                        print(f"  Has bb_middle: {'bb_middle' in opp}")
                        print(f"  Full opportunity dict: {opp}")
                        import traceback
                        traceback.print_exc()
                        report.append(f"\nError: Missing Bollinger Bands data for {opp.get('product', 'unknown')}\n")
                        continue
                    
                    spectrum = create_bb_spectrum(opp['position_in_band'])
                    next_order = datetime.now() + timedelta(days=opp['order_interval'])
                    
                    # Add a blank line between products (but not before the first one)
                    if j > 0:
                        report.append("")
                    
                    # Format the product entry with indentation for hierarchy
                    report.append(f"  {opp['product']}")
                    report.append(f"     Priority: {opp['contribution_rank']}")
                    report.append(f"     Next Order Due: {next_order.strftime('%Y.%m.%d')}")
                    report.append(f"     Current Position:")
                    report.append(f"     {spectrum}")
                    report.append(f"     Floor -------- Average -------- Ceiling")
                    
                    # Add order recommendations with value projections
                    report.append("     Order Recommendations:")
                    
                    # Calculate quantities and values for each level
                    # Target the correct percentile levels:
                    # Conservative = 50th percentile (bb_middle)
                    # Balanced = 70th percentile (between middle and upper)
                    # Aggressive = 100th percentile (bb_upper)
                    bb_70th = opp['bb_lower'] + (opp['bb_upper'] - opp['bb_lower']) * 0.7
                    
                    cons_qty = calculate_target_quantity(opp, opp['bb_middle'])
                    bal_qty = calculate_target_quantity(opp, bb_70th)
                    agg_qty = calculate_target_quantity(opp, opp['bb_upper'])
                    
                    cons_value = cons_qty * opp['unit_price']
                    bal_value = bal_qty * opp['unit_price']
                    agg_value = agg_qty * opp['unit_price']
                    
                    # Format recommendations with both quantity and value
                    if cons_qty > 0:
                        report.append(f"     - Conservative: {cons_qty} units (${cons_value:,.2f})")
                    else:
                        report.append(f"     - Conservative: Maintain current position")
                        
                    if bal_qty > 0:
                        report.append(f"     - Balanced: {bal_qty} units (${bal_value:,.2f})")
                    else:
                        report.append(f"     - Balanced: At or above average")
                        
                    if agg_qty > 0:
                        report.append(f"     - Aggressive: {agg_qty} units (${agg_value:,.2f})")
                    else:
                        report.append(f"     - Aggressive: At upper target")
                    
                except Exception as e:
                    print(f"Debug: Error formatting opportunity: {str(e)}")
                    report.append(f"\nError formatting opportunity: {str(e)}\n")

            # Add separator between weeks
            if i < len(sorted_week_keys) - 1:
                report.append("\n" + "=" * 80 + "\n")
        
        # Add total opportunity summary at the end
        total_conservative = sum(week['conservative'] for week in order_weeks.values())
        total_balanced = sum(week['balanced'] for week in order_weeks.values())
        total_aggressive = sum(week['aggressive'] for week in order_weeks.values())
        
        report.append("\n" + "=" * 80)
        report.append("\nTOTAL OPPORTUNITY SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Value Range: [${total_conservative:,.0f} < ${total_balanced:,.0f} < ${total_aggressive:,.0f}]")
        report.append(f"Total Products: {sum(len(week['products']) for week in order_weeks.values())}")
        report.append(f"Total Weeks: {len(order_weeks)}")
        
        return "\n".join(report)
        
    except Exception as e:
        print(f"Debug: Critical error in report formatting: {str(e)}")
        import traceback
        print(f"Traceback:")
        traceback.print_exc()
        
        # Additional debugging info
        if 'opportunities' in locals():
            print(f"Number of opportunities: {len(opportunities)}")
            if opportunities:
                print(f"First opportunity keys: {list(opportunities[0].keys())}")
                print(f"First opportunity sample: {opportunities[0]}")
        
        return "Error generating report. Please check the logs."

def create_combined_analysis(account_id, start_date, end_date, resolution='3D', ma_window=90, warmup_days=None, orders=None):
    # If warmup_days is not specified, use the ma_window
    if warmup_days is None:
        warmup_days = ma_window
        
    # Calculate the actual data collection start date (earlier than analysis start)
    data_collection_start = start_date - timedelta(days=warmup_days)
    
    account_name = get_account_name(account_id)
    print(f"\nAnalyzing account: {account_name}")
    
    # Define color sequences up front
    color_sequence = px.colors.qualitative.Set3
    analysis_colors = px.colors.qualitative.Set2
    
    # Create dictionaries to store all analyses
    analyses = {'Account Overview': None}  # Will store DataFrames
    colors = {'Account Overview': None}    # Will store colors for volume bars
    
    # Get account-level analysis first - use the earlier start date for data collection
    orders = get_account_orders(account_id, data_collection_start, end_date)
    print(f"Retrieved {len(orders)} orders for account")
    account_df = create_ohlcv_from_orders(orders, resolution=resolution, ma_window=ma_window)
    
    # Filter the account_df to only include dates after the actual analysis start date
    if not account_df.empty:
        # Convert start_date to match the timezone of the DataFrame index
        # First check if the index has a timezone
        if account_df.index.tz is not None:
            # Convert start_date to a timezone-aware datetime with the same timezone
            start_date_tz = pd.Timestamp(start_date).tz_localize(account_df.index.tz)
        else:
            # If index is timezone-naive, use naive start_date
            start_date_tz = pd.Timestamp(start_date).tz_localize(None)
            
        # Now filter with matching timezone types
        analysis_mask = account_df.index >= start_date_tz
        analysis_account_df = account_df[analysis_mask].copy()
        
        # Only calculate indicators on the analysis period data
        analysis_account_df = calculate_indicators(analysis_account_df, MA_length=18)
        analyses['Account Overview'] = analysis_account_df
    
    # Check if account_df has the required columns before creating colors
    if not account_df.empty and all(col in account_df.columns for col in ['open', 'close']):
        colors['Account Overview'] = ['red' if row['open'] > row['close'] else 'green' 
                                    for i, row in account_df.iterrows()]
    else:
        # Provide default colors if OHLC data is missing
        colors['Account Overview'] = ['green'] * len(account_df) if not account_df.empty else []
    
    # Get product analyses - use data_collection_start to get all products
    products = get_account_products(account_id, data_collection_start, end_date)
    order_products = get_account_order_products(account_id, data_collection_start, end_date)
    
    print(f"Retrieved {len(order_products)} order items for product analysis")
    
    # Get current pricebook prices for all products
    pricebook_prices = get_pricebook_prices(list(products.keys()))
    
    # Filter and create product analyses
    for product_id, product_name in products.items():
        print(f"Processing product: {product_name}")
        
        # Create product OHLCV with the same ma_window as account level
        df = create_product_ohlcv(order_products, product_id, resolution, ma_window, pricebook_prices)
        if df is not None and not df.empty:
            # Filter to only include dates after the actual analysis start date
            # Use the same timezone handling as above
            if df.index.tz is not None:
                start_date_tz = pd.Timestamp(start_date).tz_localize(df.index.tz)
            else:
                start_date_tz = pd.Timestamp(start_date).tz_localize(None)
            
            analysis_mask = df.index >= start_date_tz
            analysis_df = df[analysis_mask].copy()
            
            if not analysis_df.empty:
                print(f"  - {product_name}: {len(analysis_df)} data points")
                analysis_df = calculate_indicators(analysis_df, MA_length=18)
                analyses[product_name] = analysis_df  # Store the analysis
                
                # Check if df has the required columns before creating colors
                if all(col in analysis_df.columns for col in ['open', 'close']):
                    colors[product_name] = ['red' if row['open'] > row['close'] else 'green' 
                                          for i, row in analysis_df.iterrows()]
                else:
                    # Provide default colors if OHLC data is missing
                    colors[product_name] = ['green'] * len(analysis_df)
            else:
                print(f"  - {product_name}: No data points after analysis start date")
        else:
            print(f"  - {product_name}: No valid OHLCV data")
    
    # Create a common date range for all products
    all_dates = set()
    for product_name, df in analyses.items():
        if df is not None and not df.empty:
            all_dates.update(df.index)
    all_dates = sorted(all_dates)

    # Debug: Print first and last dates for each product
    print("\nProduct date ranges:")
    for product_name, df in analyses.items():
        if product_name != 'Account Overview' and df is not None and not df.empty:
            print(f"  {product_name}: {df.index[0].date()} to {df.index[-1].date()}")

    # Define analysis_start_date - make sure account_df is valid before using it
    if not account_df.empty:
        if account_df.index.tz is not None:
            # If the account dataframe has timezone-aware index, match that
            analysis_start_date = pd.Timestamp(start_date).tz_localize(account_df.index.tz)
        else:
            # Otherwise use timezone-naive date
            analysis_start_date = pd.Timestamp(start_date).tz_localize(None)
    else:
        # Fallback if account_df is empty
        analysis_start_date = pd.Timestamp(start_date)
    
    # Print the analysis start date for debugging
    print(f"\nAnalysis start date: {analysis_start_date}")
    
    # Create the main figure
    fig = make_subplots(rows=5, cols=1,
                       row_heights=[0.4, 0.2, 0.2, 0.1, 0.1],
                       shared_xaxes=True,
                       vertical_spacing=0.05,
                       specs=[[{"secondary_y": False}],
                             [{"secondary_y": False}],
                             [{"secondary_y": False}],
                             [{"secondary_y": False}],
                             [{"secondary_y": False}]])
    
    # First, calculate the total account value for each time period
    account_df = analyses['Account Overview']
    
    # Make sure account_df has 'close' column before using it
    if not account_df.empty and 'close' in account_df.columns:
        total_values = account_df['close'].to_dict()  # Use close values as the total account value
        
        # Debug: Print periods with zero or very low total values
        zero_periods = [date for date, value in total_values.items() if value <= 0.01]
        if zero_periods:
            print(f"\nWarning: Found {len(zero_periods)} periods with zero or near-zero total values")
            print(f"First few zero periods: {zero_periods[:5]}")
    else:
        # Create an empty dict if no close values are available
        total_values = {}
        print("\nWarning: No account overview data available for analysis")
    
    # After adding all traces, calculate the min and max values for the OHLC chart
    ohlc_min = float('inf')
    ohlc_max = float('-inf')
    
    # Find min and max values across all visible OHLC traces
    for name, df in analyses.items():
        if df is None or df.empty:
            continue
            
        if all(col in df.columns for col in ['low', 'high']):
            # Only consider Account Overview by default (since it's the only one visible initially)
            if name == 'Account Overview':
                ohlc_min = min(ohlc_min, df['low'].min())
                ohlc_max = max(ohlc_max, df['high'].max())
    
    # Add buffer (10% on top, 5% on bottom)
    if ohlc_min != float('inf') and ohlc_max != float('-inf'):
        y_range = ohlc_max - ohlc_min
        y_min = max(0, ohlc_min - y_range * 0.05)  # 5% buffer at bottom, but never go below zero
        y_max = ohlc_max + y_range * 0.1  # 10% buffer at top
        
        # Update the y-axis range for the OHLC subplot
        fig.update_yaxes(
            title="Value",
            range=[y_min, y_max],  # Dynamic range based on data
            row=1, col=1
        )
    
    # STEP 1: ADD REGULAR ANALYSIS TRACES FIRST
    # Add the regular analysis traces before contribution traces
    for name, df in analyses.items():
        if df is None or df.empty:
            # print(f"Warning: No data for {name}, skipping visualization")
            continue
            
        # Set initial visibility - only Account Overview visible by default
        is_visible = name == 'Account Overview'
        
        # Generate a unique color for this analysis
        color_idx = list(analyses.keys()).index(name) % len(analysis_colors)
        base_color = analysis_colors[color_idx]
        
        # Parse the RGB values from the color string and make darker version (50% darker)
        if 'rgb' in base_color:
            rgb_values = base_color.strip('rgb()').split(',')
            r, g, b = [int(val) * 0.5 for val in rgb_values]  # Darken by 50%
            darker_color = f'rgba({int(r)}, {int(g)}, {int(b)}, 1)'
        else:
            # Fallback for hex colors or other formats
            darker_color = 'rgba(100, 100, 100, 1)'
        
        # OHLC chart - only add if all required columns exist and we have sufficient data
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            if 'insufficient_data' in df.columns and df['insufficient_data'].any():
                # Add a text annotation instead of the chart
                fig.add_annotation(
                    x=df.index[len(df.index)//2],  # Center of x-axis
                    y=0.5,  # Middle of the plot
                    text="NOT ENOUGH DATA FOR ANALYSIS",
                    showarrow=False,
                    font=dict(size=20, color="gray"),
                    row=1, col=1
                )
            else:
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name=f"{name} OHLC",
                        visible=is_visible,
                        increasing=dict(
                            line=dict(color=base_color),
                            fillcolor=base_color
                        ),
                        decreasing=dict(
                            line=dict(color=darker_color),
                            fillcolor='rgba(0,0,0,0)'
                        ),
                        opacity=0.6
                    ),
                    row=1, col=1
                )
        
        # Bollinger Bands with matching colors - only add if they exist
        for band, label in [('bb_upper', 'Upper'), ('bb_middle', 'Middle'), ('bb_lower', 'Lower')]:
            if band in df.columns and not df[band].isna().all():  # Check if column exists AND has valid data
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[band],
                        name=f"{name} BB {label}",
                        line=dict(
                            color=base_color,
                            width=1,
                            dash='dash'
                        ),
                        opacity=0.3,
                        visible=is_visible
                    ),
                    row=1, col=1
                )
        
        # Volume with color-coded bars - only add if volume column exists
        if 'volume' in df.columns:
            # Check if we have OHLC data for coloring
            if all(col in df.columns for col in ['open', 'close']):
                # Use OHLC data for coloring
                bar_colors = [
                    base_color if close >= open else darker_color
                    for open, close in zip(df['open'], df['close'])
                ]
                bar_opacities = [
                    0.6 if close >= open else 0.8
                    for open, close in zip(df['open'], df['close'])
                ]
            else:
                # Use default coloring if OHLC data is missing
                bar_colors = [base_color] * len(df)
                bar_opacities = [0.6] * len(df)
                
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name=f"{name} Volume",
                marker=dict(
                    color=bar_colors,
                    opacity=bar_opacities
                ),
                visible=is_visible
            ),
            row=3, col=1
        )
        
        # Add volume SMA if it exists
        if 'volume_sma' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['volume_sma'],
                    name=f"{name} Volume MA",
                    line=dict(
                        color=base_color,
                        width=1,
                        dash='dot'
                    ),
                    visible=is_visible
                ),
                row=3, col=1
            )
        
        # RSI with matching colors - only add if it exists
        if 'rsi' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['rsi'],
                    name=f"{name} RSI",
                    line=dict(color=base_color, width=1),
                    visible=is_visible
                ),
                row=4, col=1
            )
            
            # Add RSI MA if it exists
            if 'rsi_ma' in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df['rsi_ma'],
                        name=f"{name} RSI MA",
                        line=dict(
                            color=base_color, 
                            width=1,
                            dash='dot'  # Use dotted line to distinguish from RSI
                        ),
                        visible=is_visible
                    ),
                    row=4, col=1
                )
        
        # MACD lines and histogram - only add if they exist
        if all(col in df.columns for col in ['macd', 'macd_signal', 'macd_hist']):
            # First add the histogram
            # Prepare colors for MACD histogram
            macd_colors = [
                base_color if val >= 0 else darker_color
                for val in df['macd_hist']
            ]
            macd_opacities = [
                0.6 if val >= 0 else 0.8
                for val in df['macd_hist']
            ]
            
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['macd_hist'],
                    name=f"{name} MACD Hist",
                    marker=dict(
                        color=macd_colors,
                        opacity=macd_opacities
                    ),
                    visible=is_visible
                ),
                row=5, col=1
            )
            
            # Add MACD line
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['macd'],
                    name=f"{name} MACD",
                    line=dict(color=base_color, width=1),
                    visible=is_visible
                ),
                row=5, col=1
            )
            
            # Update MACD signal line style
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['macd_signal'],
                    name=f"{name} Signal",
                    line=dict(
                        color=base_color,
                        width=1,
                        dash='dot'
                    ),
                    visible=is_visible
                ),
                row=5, col=1
            )
        else:
            # Log that we're skipping this product due to missing OHLC data
            print(f"Skipping visualization for {name} - missing OHLC data")

    # STEP 2: ADD PRODUCT CONTRIBUTION TRACES SECOND
    # First collect and sort all product contributions before adding them
    all_product_contributions = []

    # Important: Make sure we have all products calculated first
    print(f"\nAvailable products for contribution calculation:")
    for product_name, df in analyses.items():
        if product_name != 'Account Overview' and df is not None and not df.empty:
            print(f"  {product_name}: {len(df)} data points")

    # Get the resolution frequency
    freq_map = {
        '3D': '3D',
        '1W': 'W',
        '2W': '2W',
        '1M': 'M'
    }
    resample_freq = freq_map[resolution]
    print(f"Using resolution frequency: {resample_freq} for product contributions")

    # Step 1: Define consistent date boundaries for the 3-day windows
    # Start with the earliest date in the analysis period and create a uniform grid of 3-day periods
    if account_df is not None and not account_df.empty:
        # Use the account dataframe start date as the reference 
        grid_start_date = account_df.index[0]
        # Get the timezone from account dataframe if available
        reference_tz = grid_start_date.tz
    else:
        # Fall back to the analysis start date if no account dataframe
        grid_start_date = analysis_start_date
        reference_tz = None

    # Define end_date_timestamp before we try to use it
    end_date_timestamp = pd.Timestamp(end_date)
    print(f"Initial end_date_timestamp: {end_date_timestamp}, timezone: {end_date_timestamp.tz}")

    # Make sure end_date has the same timezone as grid_start_date
    if reference_tz is not None:
        if end_date_timestamp.tz is None:
            end_date_timestamp = pd.Timestamp(end_date).tz_localize(reference_tz)
        elif end_date_timestamp.tz != reference_tz:
            end_date_timestamp = pd.Timestamp(end_date).tz_convert(reference_tz)
    else:
        # If reference has no timezone, make sure end_date also has no timezone
        if end_date_timestamp.tz is not None:
            end_date_timestamp = pd.Timestamp(end_date).tz_localize(None)

    # Define a fixed start date for the 3-day grid (ensure it's a consistent day)
    grid_offset = grid_start_date.weekday() % 3  # Ensure we always start on same day within 3-day cycle
    aligned_start = grid_start_date - pd.Timedelta(days=grid_offset)
    print(f"Using aligned start date for 3-day grid: {aligned_start}")
    print(f"Aligned start timezone: {aligned_start.tz}, End date timezone: {end_date_timestamp.tz}")

    # Generate fixed 3-day period boundaries
    date_range = pd.date_range(start=aligned_start, end=end_date_timestamp, freq=resample_freq)
    print(f"Created fixed grid with {len(date_range)} time periods")

    # Step 2: Collect all product values aligned to this fixed grid
    consolidated_product_data = consolidate_product_data(
        analyses, 
        resample_freq, 
        analysis_start_date, 
        end_date_timestamp
    )

    # Step 3: Calculate total value for each aligned time period
    date_totals = {}
    for date in consolidated_product_data:
        total = sum(consolidated_product_data[date].values())
        if total > 0:  # Skip dates with no data
            date_totals[date] = total

    # Print debug information
    print(f"Created consolidated values for {len(date_totals)} time periods")
    print(f"Number of products with data: {len(set().union(*[set(data.keys()) for data in consolidated_product_data.values()]))}")

    # Step 4: Create contribution traces for each product aligned to the grid
    # We need to collect ALL products that appear anywhere in our data
    all_product_names = set()
    for date_data in consolidated_product_data.values():
        all_product_names.update(date_data.keys())

    # Create a mapping of product names to their colors from the OHLC charts
    product_color_map = {}
    for name, df in analyses.items():
        if name == 'Account Overview' or df is None or df.empty:
            continue
        
        # Calculate the color index the same way we did for OHLC
        color_idx = list(analyses.keys()).index(name) % len(analysis_colors)
        product_color_map[name] = analysis_colors[color_idx]
        print(f"Assigned color to {name}: {analysis_colors[color_idx]}")

    # Now create traces for each product using our consolidated data
    for i, product_name in enumerate(all_product_names):
        dates = []
        values = []
        
        # Collect all dates where this product has data
        for date in sorted(consolidated_product_data.keys()):
            if product_name in consolidated_product_data[date]:
                dates.append(date)
                values.append(consolidated_product_data[date][product_name])
        
        if not dates:
            print(f"  Warning: No consolidated dates for {product_name}")
            continue
        
        max_value = max(values) if values else 0
        
        # Use the same color as the OHLC chart if available, otherwise use the color sequence
        if product_name in product_color_map:
            color = product_color_map[product_name]
            print(f"  Using matched OHLC color for {product_name}")
        else:
            color = color_sequence[i % len(color_sequence)]
            print(f"  Using default color sequence for {product_name}")
        
        all_product_contributions.append({
            'product_name': product_name,
            'dates': dates,
            'values': values,
            'max_value': max_value,
            'color': color  # Store the actual color instead of just an index
        })

    # Sort by maximum contribution value
    all_product_contributions.sort(key=lambda x: x['max_value'], reverse=True)

    # Print summary of contributions data
    print(f"\nFound {len(all_product_contributions)} products with contribution data")
    for product_data in all_product_contributions[:5]:  # Print top 5 contributors
        print(f"  {product_data['product_name']}: {len(product_data['dates'])} points, max: {product_data['max_value']:.2f}")

    # Now add the sorted contribution traces
    contribution_trace_indices = []  # Track indices of contribution traces

    for product_data in all_product_contributions:
        product_name = product_data['product_name']
        dates = product_data['dates'] 
        values = product_data['values']
        color = product_data['color']  # Use the stored color directly
        
        # Ensure we have valid data to plot
        if not dates or not values:
            print(f"  Warning: {product_name} has empty dates or values list, skipping trace")
            continue
        
        if len(dates) != len(values):
            print(f"  Warning: {product_name} has mismatched dates ({len(dates)}) and values ({len(values)}), skipping trace")
            continue
        
        # Add trace with absolute values and custom hover template
        trace = go.Scatter(
            x=dates,
            y=values,
            name=f"{product_name} - $ Contribution",
            line=dict(color=color),  # Use the consistent color
            visible=True,  # Always visible by default
            showlegend=True,
            connectgaps=True,  # Connect gaps for better visualization
            hovertemplate=f"{product_name}: %{{y:$,.2f}}<extra></extra>"
        )
        
        trace_idx = len(fig.data)  # Get the index before adding
        fig.add_trace(trace, row=2, col=1)
        contribution_trace_indices.append(trace_idx)  # Store the index
        print(f"  Added contribution trace for {product_name} at index {trace_idx} with color {color}")

    # STEP 3: CREATE TRACE GROUPS
    # Create a mapping of traces to their exact analysis name
    trace_groups = {}

    # First, identify all contribution traces
    contribution_trace_indices = []
    for i, trace in enumerate(fig.data):
        if "$ Contribution" in trace.name:
            contribution_trace_indices.append(i)

    # Then identify all non-contribution traces and group them
    for i, trace in enumerate(fig.data):
        # Skip contribution traces - they're handled separately
        if i in contribution_trace_indices:
            continue
            
        # Extract the full product name from the trace name
        trace_parts = trace.name.split()
        
        # For traces like "MegaMucosa OHLC" or "MegaMucosa Stick Packs OHLC"
        # We need to determine where the product name ends and the chart type begins
        chart_types = ["OHLC", "BB", "Volume", "RSI", "MACD", "Signal", "Hist", "MA", "Upper", "Middle", "Lower"]
        
        # Find where the chart type starts in the trace name
        chart_type_index = None
        for j, part in enumerate(trace_parts):
            if part in chart_types:
                chart_type_index = j
                break
        
        # If we found a chart type, everything before it is the product name
        if chart_type_index is not None:
            product_name = " ".join(trace_parts[:chart_type_index])
        else:
            # Fallback - use the first part as the product name
            product_name = trace_parts[0]
        
        # Add to trace groups
        if product_name not in trace_groups:
            trace_groups[product_name] = []
        trace_groups[product_name].append(i)

    print(f"\nTrace groups created: {list(trace_groups.keys())}")
    for group, indices in trace_groups.items():
        print(f"  {group}: {len(indices)} traces")
        # Print a few sample trace names for debugging
        sample_traces = [fig.data[idx].name for idx in indices[:3]]
        print(f"    Sample traces: {sample_traces}")

    # STEP 4: CREATE DROPDOWN BUTTONS
    # Create dropdown menu options
    buttons = []

    # Store y-axis ranges for each analysis
    y_axis_ranges = {}
    
    # Calculate y-axis ranges for all analyses
    for name, df in analyses.items():
        if df is not None and not df.empty:
            try:
                # Start with OHLC values if available
                if all(col in df.columns for col in ['low', 'high']):
                    min_value = df['low'].min()
                    max_value = df['high'].max()
                    
                    # Include Bollinger Bands if available (they often extend beyond OHLC values)
                    if 'bb_lower' in df.columns and not df['bb_lower'].isna().all():
                        min_value = min(min_value, df['bb_lower'].min())
                    if 'bb_upper' in df.columns and not df['bb_upper'].isna().all():
                        max_value = max(max_value, df['bb_upper'].max())
                    
                    # Apply more generous buffers (15% on bottom, 20% on top)
                    value_range = max_value - min_value
                    if value_range > 0:  # Ensure we have a valid range
                        y_min = min_value - value_range * 0.15
                        y_max = max_value + value_range * 0.20
                        
                        y_axis_ranges[name] = [y_min, y_max]
                        print(f"Y-axis range for {name}: {y_min:.2f} to {y_max:.2f}")
                    else:
                        print(f"Invalid value range for {name}: min={min_value}, max={max_value}")
                else:
                    print(f"Unable to calculate y-axis range for {name} - missing required columns")
            except Exception as e:
                print(f"Error calculating range for {name}: {str(e)}")

    # Also calculate volume y-axis ranges
    volume_axis_ranges = {}
    for name, df in analyses.items():
        if df is not None and not df.empty and 'volume' in df.columns:
            # Find max volume with a 30% buffer for better visualization
            max_volume = df['volume'].max() * 1.15
            volume_axis_ranges[name] = [0, max_volume]
            print(f"Volume range for {name}: 0 to {max_volume:.2f}")

    # 1. Select All button - shows all traces
    # For Select All, use the widest range to accommodate all data
    if y_axis_ranges:
        all_min = min([range_vals[0] for range_vals in y_axis_ranges.values()])
        all_max = max([range_vals[1] for range_vals in y_axis_ranges.values()])
        
        # Also get the max volume range for all analyses
        all_vol_max = 1.0
        if volume_axis_ranges:
            all_vol_max = max([range_vals[1] for range_vals in volume_axis_ranges.values()])
        
        buttons.append(dict(
            args=[{
                "visible": [True] * len(fig.data)
            }, {
                "yaxis.range[0]": all_min,
                "yaxis.range[1]": all_max,
                "yaxis3.range[0]": 0,
                "yaxis3.range[1]": all_vol_max
            }],
            label="Select All",
            method="update"
        ))
    else:
        buttons.append(dict(
            args=[{"visible": [True] * len(fig.data)}],
            label="Select All",
            method="update"
        ))

    # 2. Clear All button - hides all traces except product contributions
    clear_visible = [False] * len(fig.data)
    for i in contribution_trace_indices:
        clear_visible[i] = True
        
    buttons.append(dict(
        args=[{"visible": clear_visible}],
        label="Clear All",
        method="update"
    ))

    # 3. Account Overview button - shows Account Overview traces + ALL product contributions
    if "Account Overview" in trace_groups:
        account_visible = [False] * len(fig.data)
        
        # Show Account Overview traces
        for i in trace_groups["Account Overview"]:
            account_visible[i] = True
        
        # Always show ALL product contributions
        for i in contribution_trace_indices:
            account_visible[i] = True
        
        # Use pre-calculated y-axis range for Account Overview
        if 'Account Overview' in y_axis_ranges:
            y_min, y_max = y_axis_ranges['Account Overview']
            buttons.append(dict(
                args=[{
                    "visible": account_visible
                }, {
                    "yaxis.range[0]": y_min,
                    "yaxis.range[1]": y_max
                }],
                label="Account Overview",
                method="update"
            ))
        else:
            buttons.append(dict(
                args=[{"visible": account_visible}],
                label="Account Overview",
                method="update"
            ))

    # Now add the rest of the product buttons in alphabetical order
    # Get all product names except Account Overview and sort them alphabetically
    product_names = [name for name in trace_groups.keys() if name != "Account Overview"]
    product_names.sort()  # Sort alphabetically

    print(f"\nCreating buttons for products: {product_names}")

    # Add buttons for each product in alphabetical order
    for product_name in product_names:
        if product_name not in trace_groups:
            print(f"Warning: No traces found for {product_name}")
            continue
        
        indices = trace_groups[product_name]
        print(f"  {product_name}: {len(indices)} traces")
        
        # Create visibility array for this product
        product_visible = [False] * len(fig.data)
        
        # Show this product's traces
        for i in indices:
            product_visible[i] = True
            
        # Always show ALL product contributions
        for i in contribution_trace_indices:
            product_visible[i] = True
            
        # Set up the layout updates
        layout_updates = {}
        
        # Use pre-calculated y-axis range for this product's main chart
        if product_name in y_axis_ranges:
            y_min, y_max = y_axis_ranges[product_name]
            layout_updates["yaxis.range[0]"] = y_min
            layout_updates["yaxis.range[1]"] = y_max
            print(f"  {product_name} Y-axis range: {y_min:.2f} to {y_max:.2f}")
        
        # Also update volume chart range if available
        if product_name in volume_axis_ranges:
            vol_min, vol_max = volume_axis_ranges[product_name]
            layout_updates["yaxis3.range[0]"] = vol_min
            layout_updates["yaxis3.range[1]"] = vol_max
            print(f"  {product_name} Volume range: {vol_min:.2f} to {vol_max:.2f}")
            
        # Create the button with appropriate args
        if layout_updates:
            buttons.append(dict(
                args=[
                    {"visible": product_visible},
                    layout_updates
                ],
                label=product_name,
                method="update"
            ))
        else:
            print(f"  {product_name}: No axis ranges available")
            buttons.append(dict(
                args=[{"visible": product_visible}],
                label=product_name,
                method="update"
            ))

    # Update the layout with the dropdown menu positioned above the y-axis
    fig.update_layout(
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                showactive=True,
                active=2,  # Account Overview is active by default
                x=0.05,    # Position near the left side of the plot
                y=1.15,    # Position above the plot, near the title
                xanchor="left",
                yanchor="top",
                bgcolor="rgba(0,0,0,0.3)",
                bordercolor="rgba(255,255,255,0.3)",
                borderwidth=1,
                font=dict(size=12, color='white'),
                type="dropdown"
            )
        ],
        # Adjust top margin to make room for the dropdown
        margin=dict(t=150, r=120, l=80, b=20)
    )
    
    # Add vertical hover line for all subplots
    fig.update_layout(
        hovermode="x unified",  # Show hover info for all traces at the same x-coordinate
        hoverdistance=100,      # Increase hover distance for better usability
        spikedistance=1000,     # Increase spike distance
        hoverlabel=dict(
            bgcolor="rgba(0,0,0,0.8)",
            font_size=12,
            font_family="Arial"
        )
    )
    
    # Add spikes (vertical lines on hover)
    fig.update_xaxes(
        showspikes=True,
        spikecolor="white",
        spikesnap="cursor",
        spikemode="across",
        spikethickness=1
    )
    
    # Add gridlines and reference lines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)
    
    # Add reference lines at 25%, 50%, and 75%
    fig.add_hline(y=25, line_dash="dot", line_color="gray", opacity=0.5, row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.5, row=2, col=1)
    fig.add_hline(y=75, line_dash="dot", line_color="gray", opacity=0.5, row=2, col=1)

    # Update layout with minimal positioning
    fig.update_layout(
        title=f"Analysis - {account_name}",  # Simplified title
        template='plotly_dark',
        height=1000,  # Increased height for better visibility
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,  # Move legend outside the plot area (>1 moves it to the right)
            bgcolor="rgba(0,0,0,0.3)",  # Semi-transparent background
            bordercolor="rgba(255,255,255,0.3)",
            borderwidth=1
        ),
        yaxis=dict(
            title="3-Day Order Value<br>(90 Day MA)",
            layer="above traces"
        ),
        yaxis2=dict(
            title="Product Contributions ($)",
            layer="above traces",
            domain=[0.5, 0.7]  # Adjust the vertical position if needed
        ),
        yaxis3=dict(title="Item Count"),
        yaxis4=dict(title="Order Resistance"),
        yaxis5=dict(title="Trend"),
        yaxis2_showgrid=False,
        yaxis3_showgrid=False,
        yaxis4_showgrid=False,
        yaxis5_showgrid=False,
        xaxis=dict(
            rangeslider=dict(visible=False)  # Disable the rangeslider/mini-map
        )
    )

    # Update RSI axis range to focus on the 20-80 range instead of 0-100
    fig.update_yaxes(range=[20, 80], row=4, col=1)

    # Add RSI overbought/oversold lines (keep these, they're still useful)
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=4, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=4, col=1)
    # Add a center line at 50 for reference
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=4, col=1)

    # Add product contribution lines to their own subplot (row 2)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)
    
    print(f"\nCreated {len(trace_groups)} trace groups for dropdown menu")
    print(f"\nCreated {len(buttons)} dropdown menu buttons")

    # After creating all analyses and before returning the figure
    # Generate the opportunity report (keep in memory - no disk I/O)
    report = analyze_product_opportunities(analyses, consolidated_product_data, analyses['Account Overview'])
    
    # Create HTML content with both the chart and text report (keep in memory)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{account_name} Opportunity Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .report-container {{ margin-top: 30px; }}
            .text-report {{ 
                white-space: pre-wrap; 
                background-color: #f8f9fa; 
                padding: 15px; 
                border-radius: 5px;
                font-family: monospace;
                line-height: 1.5;
            }}
            h2 {{ color: #2c3e50; }}
        </style>
    </head>
    <body>
        <h2>{account_name} Opportunity Analysis</h2>
        <div id="chart-container">
            {fig.to_html(include_plotlyjs='cdn', full_html=False)}
        </div>
        <div class="report-container">
            <h2>Detailed Opportunity Report</h2>
            <div class="text-report">
                {report.replace('<', '&lt;').replace('>', '&gt;')}
            </div>
        </div>
    </body>
    </html>
    """
    
    print(f"\nAnalysis completed. Report data kept in memory (RAM storage mode).")
    
    # Return all data in memory instead of writing to disk
    # This eliminates file I/O and path resolution issues in PyInstaller executables
    return {
        'figure': fig,
        'html_content': html_content,
        'text_report': report,
        'account_name': account_name
    }

def is_fullscript_account(account_name):
    """Check if account is a FullScript account based on name prefix"""
    return account_name.startswith('(FS)')

def get_business_days_in_month(start_date, end_date):
    """Get all business days between two dates"""
    return pd.date_range(start=start_date, end=end_date, freq='B')

def distribute_monthly_orders(orders):
    """
    Distribute FullScript orders across previous month using weighted business day distribution
    """
    distributed_orders = []
    
    # Group orders by account first
    orders_by_account = {}
    for order in orders:
        acc_id = order['AccountId']
        if acc_id not in orders_by_account:
            orders_by_account[acc_id] = []
        orders_by_account[acc_id].append(order)
    
    for acc_id, acc_orders in orders_by_account.items():
        # Check if this is a FS account
        is_fs = is_fullscript_account(acc_orders[0]['Account']['Name'])
        
        if not is_fs:
            # Keep non-FS orders as is
            distributed_orders.extend(acc_orders)
            continue
            
        # Process FS orders
        for order in acc_orders:
            order_date = pd.to_datetime(order['MBL_Order_Shipped_Time__c'])
            
            # Calculate distribution period (previous month)
            end_date = order_date
            start_date = end_date - pd.DateOffset(months=1)
            
            # Get business days in the period
            business_days = get_business_days_in_month(start_date, end_date)
            
            if len(business_days) == 0:
                # Fallback if no business days found
                distributed_orders.append(order)
                continue
            
            # Create weights favoring certain parts of the month
            # Higher weights for early and late month, lower for mid-month
            weights = []
            for day in business_days:
                day_of_month = day.day
                total_days = end_date.days_in_month
                
                # Create a W-shaped weight distribution
                if day_of_month <= total_days / 4:  # First quarter
                    weight = 1.5 - (day_of_month / (total_days / 4)) * 0.5
                elif day_of_month <= total_days / 2:  # Second quarter
                    weight = 1.0 + (day_of_month - total_days / 4) / (total_days / 4) * 0.5
                elif day_of_month <= 3 * total_days / 4:  # Third quarter
                    weight = 1.5 - (day_of_month - total_days / 2) / (total_days / 4) * 0.5
                else:  # Fourth quarter
                    weight = 1.0 + (day_of_month - 3 * total_days / 4) / (total_days / 4) * 0.5
                
                # Adjust weight for day of week (higher for Tuesday-Thursday)
                dow_adjustment = 1.2 if day.dayofweek in [1, 2, 3] else 1.0
                weights.append(weight * dow_adjustment)
            
            # Normalize weights
            weights = np.array(weights) / sum(weights)
            
            # Calculate distributed amounts
            total_amount = float(order['TotalAmount'])
            distributed_amounts = weights * total_amount
            
            # Create distributed orders
            for day, amount in zip(business_days, distributed_amounts):
                distributed_order = order.copy()
                distributed_order['MBL_Order_Shipped_Time__c'] = day.strftime('%Y-%m-%dT%H:%M:%SZ')
                distributed_order['TotalAmount'] = float(amount)
                distributed_orders.append(distributed_order)
    
    return distributed_orders

def analyze_product_opportunities(analyses, consolidated_product_data, account_analysis=None):
    """
    Analyze all contributing products for trading opportunities
    """
    opportunities = []
    ma_window = 90
    
    # Define products to ignore
    ignored_products = ["Mouth Cleaner", "Mouth Freshener"]
    
    # Calculate contribution metrics for each product
    product_contributions = {}
    for date_data in consolidated_product_data.values():
        for product, value in date_data.items():
            # Skip products that contain any of the ignored terms
            if any(ignored_term in product for ignored_term in ignored_products):
                continue
                
            if product not in product_contributions:
                product_contributions[product] = []
            product_contributions[product].append(value)
    
    # Calculate average contribution for each product
    avg_contributions = {
        product: sum(values) / len(values)
        for product, values in product_contributions.items()
    }
    
    # Filter out products with very low contribution (e.g., less than 1% of max contribution)
    max_contribution = max(avg_contributions.values())
    min_contribution_threshold = max_contribution * 0.01
    active_products = {
        k: v for k, v in avg_contributions.items() 
        if v > min_contribution_threshold
    }
    
    # Calculate contribution ranks
    sorted_products = sorted(active_products.items(), key=lambda x: x[1], reverse=True)
    contribution_ranks = {product: i + 1 for i, (product, _) in enumerate(sorted_products)}
    
    print("\nAnalyzing contributing products:")
    for product, avg_contribution in active_products.items():
        print(f"\nProcessing {product}:")
        print(f"  Average contribution: ${avg_contribution:.2f}")
        print(f"  Contribution rank: {contribution_ranks[product]}")
        
        if product not in analyses or analyses[product] is None:
            continue
            
        df = analyses[product]
        
        # Check for required indicators
        required_cols = ['rsi', 'close', 'bb_lower', 'bb_middle', 'bb_upper', 'volume', 'unit_price']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"  Skipping {product}: Missing required columns: {missing_cols}")
            print(f"    Available columns: {list(df.columns)}")
            continue
            
        try:
            latest_data = df.iloc[-1]
            
            # Calculate technical indicators
            latest_close = latest_data['close']
            latest_rsi = latest_data['rsi']
            latest_bb_lower = latest_data['bb_lower']
            latest_bb_middle = latest_data['bb_middle']
            latest_bb_upper = latest_data['bb_upper']
            latest_unit_price = latest_data['unit_price']
            
            # Calculate position in Bollinger Bands
            bb_range = latest_bb_upper - latest_bb_lower
            if bb_range == 0:
                continue
                
            position_in_band = (latest_close - latest_bb_lower) / bb_range * 100
            
            # More lenient filtering criteria
            if latest_rsi > 75:  # Only skip extremely overbought conditions
                continue
                
            if position_in_band > 90:  # Only skip if very close to upper band
                continue
                
            if latest_unit_price == 0:
                continue
            
            # Calculate days until lower band breach
            days_until_lower = df['days_until_lower_breach'].iloc[-1]
            
            # Calculate average order interval
            order_interval = calculate_average_order_interval(df)
            
            # Add to opportunities list
            opportunities.append({
                'product': product,
                'current_close': latest_close,
                'current_rsi': latest_rsi,
                'position_in_band': position_in_band,
                'order_interval': order_interval,
                'bb_middle': latest_bb_middle,
                'bb_lower': latest_bb_lower,
                'bb_upper': latest_bb_upper,
                'unit_price': latest_unit_price,
                'days_until_lower': days_until_lower,
                'days_until_middle': df['days_until_middle_breach'].iloc[-1],  # Add this line
                'volume': df['volume'].values,
                'avg_contribution': avg_contribution,
                'contribution_rank': contribution_ranks[product]
            })
            
        except Exception as e:
            print(f"  Error processing {product}: {str(e)}")
            continue
    
    # Sort opportunities by composite score
    for opp in opportunities:
        rsi_score = opp['current_rsi'] / 75  # Normalize RSI (0-1 scale)
        position_score = opp['position_in_band'] / 100  # Normalize position (0-1 scale)
        rank_score = opp['contribution_rank'] / len(contribution_ranks)  # Normalize rank (0-1 scale)
        
        # Composite score weights contribution rank, RSI, and position
        opp['priority_score'] = (
            rank_score * 0.5 +  # 50% weight on contribution rank
            rsi_score * 0.3 +   # 30% weight on RSI
            position_score * 0.2 # 20% weight on BB position
        )
    
    # Sort by priority score (lower is better)
    opportunities.sort(key=lambda x: x['priority_score'])
    
    # Pass the account analysis to the report formatter
    return format_opportunity_report(opportunities, account_analysis)

def calculate_target_quantity(opp, target_value):
    """Calculate quantity needed to reach a target value"""
    current_value = opp['current_close']
    
    if current_value >= target_value:
        return 0
        
    # Calculate how much value we need to add
    value_gap = target_value - current_value
    
    # Convert value gap to quantity using unit price from Salesforce
    ma_window = 90  # This should match your MA_window parameter
    required_order_value = value_gap * ma_window
    
    # Convert to quantity using the actual unit price
    quantity = required_order_value / opp['unit_price']
    
    # Round to nearest whole unit
    return max(0, round(quantity))

def format_account_overview(account_analysis, opportunities):
    """Generate enhanced account overview section with intuitive metrics"""
    
    def analyze_macd_trend(latest_macd, latest_signal, previous_macd, previous_signal):
        """Analyze MACD trend and provide meaningful interpretation"""
        if abs(latest_macd - latest_signal) < abs(previous_macd - previous_signal):
            if latest_macd < latest_signal:
                return "MACD approaching bullish crossover"
            else:
                return "MACD approaching bearish crossover"
        else:
            if latest_macd > latest_signal:
                return "MACD confirms bullish trend"
            else:
                return "MACD trending lower"

    def analyze_volume_trend(volumes, periods=5):
        """Analyze volume trend over recent periods"""
        if len(volumes) < periods:
            return "Insufficient volume data"
            
        recent_volumes = volumes[-periods:]
        slope = np.polyfit(range(periods), recent_volumes, 1)[0]
        avg_volume = np.mean(recent_volumes)
        
        pct_change = (slope * periods) / avg_volume * 100
        
        if pct_change > 5:
            return "INCREASING"
        elif pct_change < -5:
            return "DECREASING"
        else:
            return "STABLE"

    def calculate_spending_targets(account_analysis, opportunities):
        """Calculate account-level spending targets based on actual opportunities"""
        # Create week timeline to get actual opportunity values
        weeks = create_week_timeline(opportunities, 90)
        
        # Sum up the actual opportunities across all weeks
        total_conservative = sum(week['conservative'] for week in weeks.values())
        total_balanced = sum(week['balanced'] for week in weeks.values())
        total_aggressive = sum(week['aggressive'] for week in weeks.values())
        
        # Calculate total order value for trailing 90 days (last 30 candlesticks)
        historical_values = account_analysis['close'].tail(30)
        total_historical = historical_values.sum() if not historical_values.empty else 0
        
        return {
            'conservative': total_conservative,
            'balanced': total_balanced,
            'aggressive': total_aggressive,
            'avg_historical': total_historical  # This is now the total for 90 days
        }

    def create_week_timeline(opportunities, report_timeframe):
        """Create timeline visualization for the report timeframe"""
        weeks = {}
        
        # Calculate the number of weeks in our timeframe
        start_date = datetime.now()
        end_date = start_date + timedelta(days=report_timeframe)
        
        # Initialize all weeks in the timeframe
        current_date = start_date
        while current_date < end_date:
            week_num = (current_date - start_date).days // 7
            weeks[week_num] = {
                'products': [],
                'total_value': 0,
                'position': 0,
                'start_date': current_date,
                'end_date': current_date + timedelta(days=6),
                'conservative': 0,
                'balanced': 0,
                'aggressive': 0
            }
            current_date += timedelta(days=7)
        
        # Group opportunities by week
        for opp in opportunities:
            if opp.get('order_interval'):
                next_order = datetime.now() + timedelta(days=opp['order_interval'])
                week_num = (next_order - start_date).days // 7
                
                if week_num in weeks:
                    # Calculate different ordering scenarios
                    # Target the correct percentile levels:
                    # Conservative = 50th percentile (bb_middle)
                    # Balanced = 70th percentile (between middle and upper)
                    # Aggressive = 100th percentile (bb_upper)
                    bb_70th = opp['bb_lower'] + (opp['bb_upper'] - opp['bb_lower']) * 0.7
                    
                    cons_qty = calculate_target_quantity(opp, opp['bb_middle'])
                    bal_qty = calculate_target_quantity(opp, bb_70th)
                    agg_qty = calculate_target_quantity(opp, opp['bb_upper'])
                    
                    weeks[week_num]['products'].append(opp)
                    weeks[week_num]['conservative'] += cons_qty * opp['unit_price']
                    weeks[week_num]['balanced'] += bal_qty * opp['unit_price']
                    weeks[week_num]['aggressive'] += agg_qty * opp['unit_price']
                    weeks[week_num]['position'] += opp['position_in_band']
        
        # Calculate average position for each week
        for week in weeks.values():
            if week['products']:
                week['position'] /= len(week['products'])
        
        return weeks

    # Format the account overview
    overview = ["ACCOUNT OVERVIEW"]
    overview.append("-" * 80)
    
    latest = account_analysis.iloc[-1]
    
    # Calculate and add BB position
    bb_range = latest['bb_upper'] - latest['bb_lower']
    if bb_range > 0:
        account_position = (latest['close'] - latest['bb_lower']) / bb_range * 100
        overview.append(f"Current Position in Bollinger Band: {account_position:.1f}%")
        overview.append(create_bb_spectrum(account_position))
        overview.append("Floor -------- Average -------- Ceiling")
    
    # Add MACD trend analysis
    if all(col in account_analysis.columns for col in ['macd', 'macd_signal']):
        macd_trend = analyze_macd_trend(
            latest['macd'],
            latest['macd_signal'],
            account_analysis.iloc[-2]['macd'],
            account_analysis.iloc[-2]['macd_signal']
        )
        overview.append(f"\nMACD Trend: {macd_trend}")
    
    # Add volume trend analysis
    if 'volume' in account_analysis.columns:
        volume_trend = analyze_volume_trend(account_analysis['volume'].values)
        overview.append(f"Volume Trend: {volume_trend}")
    
    # Add RSI context if available
    if 'rsi' in latest.index:
        rsi = latest['rsi']
        rsi_context = get_trend_description(rsi)
        overview.append(f"RSI Signal ({rsi:.1f}): {rsi_context.upper()}")
    
    # Calculate and add spending targets
    spending_targets = calculate_spending_targets(account_analysis, opportunities)
    overview.append("\nTARGET ACCOUNT SPEND (90-Day Period)")
    overview.append("-" * 80)
    overview.append(f"Conservative: ${spending_targets['conservative']:,.2f}")
    overview.append(f"Balanced:     ${spending_targets['balanced']:,.2f}")
    overview.append(f"Aggressive:   ${spending_targets['aggressive']:,.2f}")
    overview.append(f"\nTrailing 90-Day Average: ${spending_targets['avg_historical']:,.2f}")
    
    # Add week-by-week timeline for the next 90 days
    overview.append("\nORDER TIMELINE (Next 90 Days)")
    overview.append("-" * 80)
    
    weeks = create_week_timeline(opportunities, 90)  # 90-day timeframe
    
    for week_num in sorted(weeks.keys()):
        week = weeks[week_num]
        timeline = create_bb_spectrum(week['position'])
        
        # Format the week header with date range
        week_dates = f"{week['start_date'].strftime('%m/%d')} - {week['end_date'].strftime('%m/%d')}"
        
        # Format the order ranges
        if len(week['products']) > 0:
            order_range = f"[${week['conservative']:,.0f} < ${week['balanced']:,.0f} < ${week['aggressive']:,.0f}]"
            overview.append(
                f"Week {week_num + 1} ({week_dates}): {timeline} {order_range} "
                f"({len(week['products'])} products)"
            )
        else:
            overview.append(f"Week {week_num + 1} ({week_dates}): No orders due")
    
    # Add summary recommendations
    overview.append("\nRECOMMENDED ACTIONS")
    overview.append("-" * 80)
    
    # Find the week with the highest balanced value
    optimal_week = max(weeks.items(), key=lambda x: x[1]['balanced'])[0]
    week = weeks[optimal_week]
    
    if len(week['products']) > 0:
        overview.append(
            f"Primary Focus: Week {optimal_week + 1} "
            f"[${week['conservative']:,.0f} < ${week['balanced']:,.0f} < ${week['aggressive']:,.0f}]"
        )
        
        # Add key products for optimal week
        key_products = sorted(
            week['products'],
            key=lambda x: x['priority_score']
        )[:3]
        
        overview.append("Key Products to Focus:")
        for product in key_products:
            overview.append(f"  - {product['product']}")
    
    # Calculate total opportunity ranges
    total_conservative = sum(week['conservative'] for week in weeks.values())
    total_balanced = sum(week['balanced'] for week in weeks.values())
    total_aggressive = sum(week['aggressive'] for week in weeks.values())
    
    overview.append(f"\nTotal 90-Day Opportunity:")
    overview.append(f"[${total_conservative:,.0f} < ${total_balanced:,.0f} < ${total_aggressive:,.0f}]")
    
    return "\n".join(overview)

# Modified main execution code:
if __name__ == "__main__":
    # NOTE: For appified version, credentials are managed securely via app.py
    # This main block is disabled - the app will set indicators_report.sf directly
    print("This script is designed to be used as a module by app.py")
    print("Please run the application using app.py or the launcher")
    print("For credential setup, run: python scripts/setup_credentials.py")
    sys.exit(0)
    
    # OLD CODE - DISABLED FOR SECURITY
    # sf_user = 'mblintegration@novozymes.com'
    # sf_p = 'Bv67f$#68ZC8T8f$PYigvcwB*rNaMsgl'
    # sf_token = 'xxkFzAZQcRZGuPqDSll3BIQl4'
    # sf = Salesforce(username=sf_user, password=sf_p, security_token=sf_token)
    account_id = '0012j00000VutSnAAJ'

    # Grant's accounts:
    # '0012j00000Vuv0nAAB' # Dawn Flickema, MD

    # Joseph Soucie's accounts:
    # '0012j00000Vv6VYAAZ' # Be Optimal

    # Ceylon's accounts:
    # '0012j00000VvSlaAAF' # Family Medicine Liberty Lake
    # '0012j00000Vvb2jAAB' # Northwest Life Medicine
    # '0012j00000VvIUCAA3' # Sage Integrative Medicine
    # '0012j00000VutSnAAJ' # Evergreen Naturopathics
    # '0012j00000VvHqzAAF' # Clinic 5c
    # '0012j00000c7PZdAAM' # In Light Hyperbarics

    # '0012j00000Vv77lAAB' # John Tjenos
    # '001Ij000002h1SEIAY' # Functional Nutrition (#3 account)
    # '0012j00000VvIxhAAF' # Wellness for Life
    # '0012j00000Vv9TAAAZ' # Natural Health Clinic (zombie for Emily Sharpe)
    # '0012j00000Vvc8yAAB' # Dr Emily Sharpe
    # '0012j00000VvAx7AAF' # NuHealth / Nadene Neale

    '''no_rep_account_ids =  ['0012j00000VuumAAAR']
    no_rep_account_names = ['PureFormulas Inc']
    rep_mgm_account_ids = ['0012j00000VvDkqAAF',  '0012j00000VvOClAAN', ]
    rep_mgm_account_names = [ 'Innovative Health and Wellness',  'Evolutionary Wellness', ]'''

    # Ben's top accounts: 
    # '0012j00000VvOClAAN' # Evolutionary Wellness
    # '0012j00000Vv8jgAAB' # Vitamin Portfolio
    # '0012j00000VuuDGAAZ' # Johnson Compounding and Wellness


    # Get orders for full period plus warm-up
    op_period = 90
    end_date = datetime.now()
    analysis_start = end_date - timedelta(days=365 * 5)

    # No need to add warm-up period here, it's handled in create_combined_analysis

    print(f"\nAnalysis period: {analysis_start.date()} to {end_date.date()}")

    # Get orders and distribute FS orders
    orders = get_account_orders(account_id, analysis_start, end_date)
    distributed_orders = distribute_monthly_orders(orders)
    
    print(f"\nOrder distribution summary:")
    print(f"Original orders: {len(orders)}")
    print(f"After FS distribution: {len(distributed_orders)}")

    # Create and show combined analysis with distributed orders
    fig = create_combined_analysis(
        account_id,
        analysis_start,
        end_date,
        resolution='3D',
        ma_window=op_period,
        warmup_days=op_period * 2,
        orders=distributed_orders  # Pass the distributed orders
    )
    
    fig.show()



