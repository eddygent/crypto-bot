from account import Account
from tradingviewscraper import check_signals
import time
SECONDS = 60
def runTvsBot(run_interval = 5):
    # run interval is in minutes
    acct = Account()
    while True:
        print('account value:', acct.balance)
        print('get balance usd:', acct.getBalanceUSD())
        print('active trades:', acct.active_trades)
        print('rsi indicator:', acct.rsi_indicator())
        print('rsi value:', acct.rsi_value())
        indicators_df = check_signals()
        print(indicators_df)
        print('entered into trades trade where:', acct.tvs_enter_trade(indicators_df))
        print('exited trades where:', acct.tvs_exit_trade(indicators_df))
        print(f"sleeping for {run_interval} minutes")
        time.sleep(SECONDS * run_interval)
def main():
    runTvsBot()

if __name__ == '__main__':
    main()