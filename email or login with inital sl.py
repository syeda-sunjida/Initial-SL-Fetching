import time
import pandas as pd
from sqlalchemy import create_engine

# Database connection details
db_config = {
    'user': 'readonly_user',
    'password': 'password123',
    'host': 'fn-prod-db-cluster.cluster-ro-cqtlpb5sm2vt.ap-northeast-1.rds.amazonaws.com',
    'database': 'api_backend',
    'port': 3306
}

# Example usage:
email_list = []
login_list = [11222729,11226064,13016625,13103774,13110570,13136805,13146055,13184904,13198490,13200740,13203762,13211773,13215593,13247894,13275444,13275454,13284042,13289717,13289717,13297337,13297406,13323765,13333592,13335035,13335118,13339033,13340665,13341426,13349261,13352844,13352860,13353155,13378396,13378483,13380799,13387162,13393545,13394324,13405905,13405905,13406330,13408970,13410186,13415790,13415821,13416191,13418228,13420443,13423234,13423236,13423274,13425117,13429336,13429852,13429996,13430023,13430047,13431671,13431751,13431816,13432387,13434063,13436672,13437225,13439929,13440318,13443111,13443114,13443116,13446635,13446983,13446988,13446997,13447173,13450920,55008451,55009408,55009979,55011226,55011365,55011366,55011368,55011616,55011983,55012064,55012328,55013043,55013121,55013179,55013290,55013391,55013606,55013646,55013710]

# Start measuring time
script_start_time = time.time()

# Function to fetch data by email or login
def fetch_data(email_list=None, login_list=None):
    # Create the connection string and engine inside the function
    connection_string = f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    engine = create_engine(connection_string)

    def format_tuple(input_list):
        return f"({','.join(f'\'{x}\'' for x in input_list)})" if len(input_list) > 1 else f"('{input_list[0]}')"

    def convert_unix_timestamp(timestamp):
        # Check if timestamp is 13 digits (milliseconds) or 10 digits (seconds)
        if len(str(timestamp)) == 13:
            return pd.to_datetime(timestamp, unit='ms', errors='coerce')
        else:
            return pd.to_datetime(timestamp, unit='s', errors='coerce')

    try:
        if email_list:
            # Fetch customer_id(s) from email(s)
            emails = format_tuple(email_list)
            customers_query = f"SELECT id AS customer_id, email FROM customers WHERE email IN {emails};"
            customers_df = pd.read_sql(customers_query, engine)

            if customers_df.empty:
                print("No customers found for the provided email(s).")
                return
            customer_ids = customers_df['customer_id'].tolist()

            # Fetch account(s) from customer_id(s)
            accounts_query = f"""
            SELECT id AS account_id, login, type AS type_account, customer_id, breachedby FROM accounts 
            WHERE customer_id IN {format_tuple(customer_ids)};
            """
            accounts_df = pd.read_sql(accounts_query, engine)
            accounts_df = pd.merge(accounts_df, customers_df, on='customer_id', how='left')

        elif login_list:
            # Fetch account(s) directly from login(s)
            logins = format_tuple(login_list)
            accounts_query = f"""
            SELECT id AS account_id, login, type AS type_account, customer_id, breachedby FROM accounts 
            WHERE login IN {logins};
            """
            accounts_df = pd.read_sql(accounts_query, engine)

            # Fetch emails by joining with customers table
            customer_ids = accounts_df['customer_id'].tolist()
            customers_query = f"""
            SELECT id AS customer_id, email FROM customers 
            WHERE id IN {format_tuple(customer_ids)};
            """
            customers_df = pd.read_sql(customers_query, engine)
            accounts_df = pd.merge(accounts_df, customers_df, on='customer_id', how='left')

        else:
            print("No emails or logins provided.")
            return

        if accounts_df.empty:
            print("No accounts found for the provided criteria.")
            return

        login_ids = format_tuple(accounts_df['login'].tolist())

        # Fetch trades data for the obtained logins
        trades_query = f"""
        SELECT id, open_time, close_time, symbol, open_price, close_price, login, volume, close_time_str, 
               commission, digits, open_time_str, profit, reason, sl, swap, ticket, tp, type_str, created_at,
               CASE 
                   WHEN login LIKE '70%' OR login LIKE '30%' THEN lots
                   ELSE volume / 100
               END AS FinalLot
        FROM trades
        WHERE login IN {login_ids};
        """
        trades_df = pd.read_sql(trades_query, engine)

        if trades_df.empty:
            print("No trades found for the provided criteria.")
            return

        # Convert UNIX timestamps to human-readable format
        trades_df['open_time'] = trades_df['open_time'].apply(convert_unix_timestamp)
        trades_df['close_time'] = trades_df['close_time'].apply(convert_unix_timestamp)
        trades_df['open_time'] = trades_df['open_time'].dt.strftime('%m/%d/%Y %I:%M:%S %p')
        trades_df['close_time'] = trades_df['close_time'].dt.strftime('%m/%d/%Y %I:%M:%S %p')

        # Fetch initial and latest SL data from trade_sl_tps table
        try:
            trade_ids = trades_df['id'].tolist()
            trade_ids_tuple = format_tuple(trade_ids)

            sl_query = f"""
            SELECT trade_id, value AS sl_value, created_at AS sl_created_at 
            FROM trade_sl_tps 
            WHERE trade_id IN {trade_ids_tuple} 
            AND type = 1
            AND created_at >= '2024-01-01 00:00:00'
            ORDER BY trade_id, sl_created_at;
            """
            sl_df = pd.read_sql(sl_query, engine)

            # Get the earliest (initial) SL for each trade
            initial_sl_df = sl_df.sort_values(by=['trade_id', 'sl_created_at']).drop_duplicates(subset='trade_id', keep='first')
            initial_sl_df.rename(columns={'sl_value': 'initial_sl', 'sl_created_at': 'initial_sl_created_at'}, inplace=True)

            # Get the latest SL for each trade
            latest_sl_df = sl_df.sort_values(by=['trade_id', 'sl_created_at']).drop_duplicates(subset='trade_id', keep='last')
            latest_sl_df.rename(columns={'sl_value': 'latest_sl', 'sl_created_at': 'latest_sl_created_at'}, inplace=True)

            # Merge initial and latest SL into trades_df
            trades_df = pd.merge(trades_df, initial_sl_df[['trade_id', 'initial_sl', 'initial_sl_created_at']],
                                 left_on='id', right_on='trade_id', how='left')

            trades_df = pd.merge(trades_df, latest_sl_df[['trade_id', 'latest_sl', 'latest_sl_created_at']],
                                 left_on='id', right_on='trade_id', how='left')

        except Exception as e:
            print(f"An error occurred while fetching initial and latest SL data: {e}")

        # Merge trades with account data
        combined_df = pd.merge(trades_df, accounts_df, on='login', suffixes=('_trade', '_account'))

        # Reorder columns
        final_df = combined_df[
            ['account_id', 'login', 'open_time', 'ticket', 'type_str', 'FinalLot', 'symbol', 'open_price', 'sl',
             'latest_sl_created_at', 'initial_sl', 'initial_sl_created_at', 'tp', 'close_time', 'close_price',
             'commission', 'swap', 'profit', 'type_account', 'email', 'breachedby']
        ]

        # Write to CSV
        csv_file_name = "trades_data_with_initial_and_latest_sl.csv"
        final_df.to_csv(csv_file_name, index=False)
        print(f"Data has been written to {csv_file_name}")

    except Exception as e:
        print(f"An error occurred: {e}")

    # End measuring time
    script_end_time = time.time()
    print(f"Time taken to run the script: {script_end_time - script_start_time} seconds")

# Run the function with the provided inputs
fetch_data(email_list=email_list)
fetch_data(login_list=login_list)
