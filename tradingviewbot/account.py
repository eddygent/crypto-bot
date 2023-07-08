import config
import ccxt
from rsi_indicator import rsi
from tradingviewscraper import check_signals
from redmail import gmail
gmail.username = config.email
gmail.password = config.password
import time
from datetime import datetime, timedelta

MIN_HOLD_HOURS = 6 # amount of hours to hold before buying more
STOP_LOSS = .03
TAKE_PROFIT = .05

class Account:
    def __init__(self):
        exchange_id = config.exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        exch = exchange_class({
            'apiKey': config.apiKey,
            'secret': config.apiSecret
        })
        self.exch = exch
        self.balance = self.getBalanceInUSD()
        self.active_trades = self.getActiveTrades()
        self.recently_purchased = {}

    def getBalanceInUSD(self):
        exchange = self.exch
        balances = exchange.fetch_balance()['free']
        balance = 0
        for token, value in balances.items():
            if float(value) != 0:
                if token != 'USDT' or token != 'USD':
                    request = token + '/USDT'
                    try:
                        price = float(exchange.fetchTicker(request)['last'])
                    except:
                        try:
                            request = token + '/BTC'
                            price = float(exchange.fetchTicker(request)['last'])
                            val_btc = (float(value)) * price
                            price = float(exchange.fetchTicker('BTC/USDT')['last'])
                            balance += val_btc * price
                        except:
                            try:
                                request = token + '/ETH'
                                price = float(exchange.fetchTicker(request)['last'])
                                val_btc = (float(value)) * price
                                price = float(exchange.fetchTicker('ETH/USDT')['last'])
                                balance += val_btc * price

                            except:
                                balance += float(value)
                    else:
                        balance += price * float(value)
                else:
                    balance += float(value)
        return balance

    def _recent_trade(self, symbol='ETH/USD'):
        trades = self.exch.fetch_my_trades(symbol)

        latest_timestamp = float('-inf')
        for trade in trades:
            if latest_timestamp < trade['timestamp']:
                latest_timestamp = trade['timestamp']
                print(trade)
        print(symbol)
        print("convert timestamp:",latest_timestamp)
        try:
            latest = datetime.utcfromtimestamp(latest_timestamp/1000)
        except OverflowError as e:
            print(e)
            try:
                latest = datetime(1970, 1, 1) + timedelta(seconds=int(latest_timestamp/1000))
            except OverflowError as e:
                print("Infinity Error. This does not exist so because it's not a recent trade, returning true")
                return False
        dnow = datetime.now()
        timediff = dnow - latest
        if timediff.total_seconds()/60 > 60 * MIN_HOLD_HOURS:
            return False
        return True

    def _should_sell(self, symbol='ETH'):
        if symbol in self.active_trades.keys():

            if self.active_trades[symbol]['total_gain_fees'] < STOP_LOSS * -1:
                print("Should sell, total loss + fees is below above 3%")
                return True
            elif self.active_trades[symbol]['total_gain_fees'] > TAKE_PROFIT:
                print("Should sell, total gain + fees is below above 5%")
                return True
            else:
                print("Hold, parameters not met.")
                return False
        print("Should not sell")
        return False
    def getBalanceUSD(self):
        exchange = self.exch
        balances = exchange.fetch_balance()['free']
        balance = 0
        for token, value in balances.items():
            if float(value) != 0:
                balance += float(value)
        return balance
    def average_purchase_price(self, symbol='ETH/USD'):
        print(f'average_purchasse_price({symbol})')
        exchange = self.exch
        associated_trades = exchange.fetchMyTrades(symbol=symbol)
        avg_sum = 0
        shares_owned = 0
        for trade in associated_trades:
            if trade['side'] == 'buy':
                avg_sum += trade['amount'] * trade['price']
                shares_owned += trade['amount']
            elif trade['side'] == 'sell':
                avg_sum -= trade['amount'] * trade['price']
                shares_owned -= trade['amount']
        print('\tsymbol',symbol)
        print('\tavg_sum',avg_sum)
        print('\tshares_owned',shares_owned)
        try:
            avg_purchase_price = avg_sum / shares_owned
        except ZeroDivisionError as e:
            print(e)
            symbol = symbol.replace('USD','USDT')
            avg_purchase_price = self.average_purchase_price(symbol=symbol)
        return avg_purchase_price

    def shares_outstanding(self, symbol='ETH/USD'):
        exchange = self.exch
        associated_trades = exchange.fetchMyTrades(symbol=symbol)
        shares_owned = 0
        for trade in associated_trades:
            if trade['side'] == 'buy':
                shares_owned += trade['amount']
            elif trade['side'] == 'sell':
                shares_owned -= trade['amount']
        return shares_owned

    def total_fees(self, symbol='ETH/USD'):
        exchange = self.exch
        associated_trades = exchange.fetchMyTrades(symbol=symbol)
        fee = 0
        for trade in associated_trades:
            if trade['fee']['currency'] == 'USD':
                fee += trade['fee']['cost']
            else:
                request = trade['fee']['currency'] + '/USD'
                fee = trade['fee']['cost'] * float(exchange.fetch_ticker(request)['last'])
        return fee

    def getActiveTrades(self):
        active_trades = {}
        for key, value in self.exch.fetch_balance().items():
            if key == 'info' or key == 'free' or key == 'USD' or key == 'used' or key == 'total': continue
            check_entry = key + '/USD'

            entry = self.average_purchase_price(check_entry)
            latest_price = float(self.exch.fetchTicker(check_entry)['last'])
            total_fees = self.total_fees(check_entry)
            active_trades[key] = {
                'amount': self.shares_outstanding(check_entry),
                'entry': entry,
                'total_fees': total_fees,
                'latest_price': latest_price,
                'total_gain': (latest_price/entry)-1,
                'total_gain_fees': (latest_price/(entry + total_fees))-1
            }
        return active_trades

    def rsi_value(self, symbol='ETH/USD'):
        _rsi = rsi(exchange=self.exch, symbol=symbol)
        # 30 is the sweet spot and 70 is the max tolerance ... if it's 30 or below 1, if it's 70 or above -1
        rsi_value = _rsi['RSI_14'].iloc[-1]
        return rsi_value

    def rsi_indicator(self, symbol='ETH/USD'):
        _rsi = rsi(exchange=self.exch, symbol=symbol)
        # 30 is the sweet spot and 70 is the max tolerance ... if it's 30 or below 1, if it's 70 or above -1
        rsi_value = self.rsi_value( symbol='ETH/USD')

        indicator = 0
        if rsi_value <= 30: indicator = 1
        elif rsi_value >= 70: indicator = -1
        elif rsi_value <= 50:
            indicator = abs(1-(abs (30-rsi_value)/20) )*1
        elif rsi_value <70:
            indicator = abs(1-( abs(rsi_value-70) / 20)) * -1
        return indicator

    def place_buy_market_order(self, symbol, amt, tries = 0):
        tries += 1
        last_price = self.exch.fetchTicker(symbol)['last']
        try:
            order = self.exch.create_limit_order(symbol=symbol, side='buy', amount=amt, price=last_price)
        except Exception as e:
            # try to buy with USD instead of usdt
            symbol_split = symbol.split("/")
            if "USD" == symbol_split[1] and tries == 0:
                # try with usdt
                new_symbol = f"{symbol_split[0]}/USDT"
                self.place_buy_market_order(new_symbol, amt, tries) # try with a new symbol if we dont have enough usdt
            elif "USDT" == symbol_split[1] and tries == 0: # to protect us from continuously going back and forth
                # try with usd
                new_symbol = f"{symbol_split[0]}/USD" # try with a new symbol if we dont have enough usd
                self.place_buy_market_order(new_symbol, amt, tries)
            print(f"\t{e}\n\t\tInvalid Limit Order Quantity.")
            gmail.send(
                subject=f"CMon: Buy Order FAILED {symbol}. Amount: {amt}",
                sender=f"{config.email}",
                receivers=[f"{config.email}"],
                # A plot in body
                html=f"""Market buy order FAILED for {symbol}. Amount: {amt}.
                        <br>Account Balance: {self.getBalanceInUSD()}
                        <br>Active Trades: { self.getActiveTrades()}"""
            )
            return {'status': f'Invalid Limit Order Quantity: {e}'}
        return order

    def place_sell_market_order(self, symbol, amt):
        last_price = self.exch.fetchTicker(symbol)['last']
        try:
            order = self.exch.create_limit_order(symbol=symbol, side='sell', amount=amt, price=last_price)
        except Exception as e:
            print(f"\t{e}\n\t\tInvalid Limit Order Quantity.")
            gmail.send(
                subject=f"CMon: Sell Order FAILED {symbol}. Amount: {amt}",
                sender=f"{config.email}",
                receivers=[f"{config.email}"],
                # A plot in body
                html=f"""Market Sell order FAILED for {symbol}. Amount: {amt}.
                <br>Account Balance: {self.getBalanceInUSD()}
                <br>Active Trades: { self.getActiveTrades()}
                    """
            )
            return {'status': f'Invalid Limit Order Quantity: {e}'}
        return order

    def tvs_enter_trade(self, check_signals):
        # first look for opportunities in tradingview scraper
        tvscraper = check_signals.query("decision == 'BUY'")

        purchased = []
        if tvscraper.empty:
            print("No trades to enter.")
            return None
        for index,row in tvscraper.iterrows():
            if row['with'] == 'USDT' or row['with'] == 'USD':
                free_balance = self.getBalanceUSD()
            elif row['with'] in self.active_trades.keys():
                free_balance = self.active_trades[row['with']]['amount']
            symbol = f'{row["buy"]}/{row["with"]}'
            print('symbol', symbol, 'free balance', free_balance)
            if free_balance != 0 and not self._recent_trade(symbol): # if it's not a recent trade then execute trade
                weight = row['total weight']
                # we want to get the total ((100/4) / 5 ) * weight
                amount_free_to_use = (((1/4)/5) * weight) * free_balance
                print(amount_free_to_use)
                # convert from the amount we want to use to the specified amount
                amt =  amount_free_to_use/ self.exch.fetchTicker(symbol)['last']
                print('buy', symbol, 'with', amt)
                order = self.place_buy_market_order(symbol, amt)
                print("order", order)
                if order['status'] == 'filled':
                    gmail.send(
                        subject=f"CMon: Buy Order Filled {symbol}. Amount: {amt}",
                        sender=f"{config.email}",
                        receivers=[f"{config.email}"],
                        # A plot in body
                        html=f"""
                            Market buy order filled for {symbol}. Amount: {amt}.
                            <br>Account Balance: {self.getBalanceInUSD()}
                            <br>Active Trades: { self.getActiveTrades()}
                            """
                    )
                    purchased.append(symbol)
                    print("Market buy order filled")
                else:
                    print("Market buy order failed")
        return purchased
    def tvs_exit_trade(self, check_signals):
        # first look for opportunities in tradingview scraper
        tvscraper = check_signals.query("decision == 'SELL'")
        sold = []
        if tvscraper.empty:
            print("No trades to exit.")
            return None
        for index,row in tvscraper.iterrows():
            print("symbol", row['buy'], "in  active trades", self.active_trades.keys())
            if row['buy'] == 'USDT' or row['buy'] == 'USD':
                free_balance = self.getBalanceUSD()
            elif row['buy'] in self.active_trades.keys():
                free_balance = self.active_trades[row['buy']]['amount']
            else:
                print(f"Don't have security {row['buy']}. Cannot sell.")
                continue
            symbol = f'{row["buy"]}/{row["with"]}'
            print('symbol', symbol, 'free balance', free_balance)

            if free_balance != 0 and self._should_sell(symbol): # if we should sell then go forward
                amount_free_to_use = free_balance
                # convert from the amount we want to use to the specified amount
                amt =  amount_free_to_use / self.exch.fetchTicker(symbol)['last']
                print('sell', symbol, 'with', amt)
                order = self.place_sell_market_order(symbol, amt)
                if order['status'] == 'filled':
                    gmail.send(
                        subject=f"CMon: Sell Order Filled {symbol}. Amount: {amt}",
                        sender=f"{config.email}",
                        receivers=[f"{config.email}"],
                        # A plot in body
                        html=f"""
                            Market Sell order filled for {symbol}. Amount: {amt}.
                            <br>Account Balance: {self.getBalanceInUSD()}
                            <br>Active Trades: { self.getActiveTrades()}
                            """
                    )
                    sold.append(symbol)
                    print("Market Sell order filled")
                else:
                    print("Market Sell order failed")
        return sold