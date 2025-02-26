Fetch Initial SL Script

Overview
This Python script fetches trade data along with initial and latest Stop Loss (SL) values from a MySQL database. The script takes a list of email addresses or login IDs to retrieve relevant trade details and exports the data into a CSV file.

How It Works

- Database Connection
- Establishes a connection with a MySQL database using SQLAlchemy.
- The connection details (host, port, user, password, and database name) are specified in the db_config dictionary.

  
- Fetching Customer and Account Details
- If email_list is provided, it retrieves customer IDs from the customers table.
- If login_list is provided, it directly retrieves account details from the accounts table.

  
- Fetching Trade Data
- Based on the obtained login IDs, the script retrieves trade data from the trades table.
- Fetching Initial and Latest Stop Loss (SL) Values

- Queries the trade_sl_tps table to fetch SL values for each trade.
- Determines the initial SL (earliest SL value) and latest SL (most recent SL value).
  
- Data Formatting and Output
-Converts UNIX timestamps into human-readable format.
-Merges trade data with account and SL details.
-Saves the final dataset to a CSV file (trades_data_with_initial_and_latest_sl.csv).

Output
- The script outputs a CSV file containing:
- Trade details (open/close time, price, lot size, etc.)
- Initial and latest SL values
- Account details (email, breached status, etc.)
