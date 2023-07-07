import websocket, json, numpy,talib, pprint,sys
from binance.enums import *
from binance.client import Client
from sentiment_analysis import news_sentiment
from config import *
import datetime
import random

close_prices = []
today = datetime.datetime.now()
dateFrom = today - datetime.timedelta(days=BACK_DAYS)
dateFrom = dateFrom.strftime('%Y-%m-%d')
sentiment = news_sentiment(dateFrom, 'Ethereum', SENTIMENT_API_KEY)
sentiment.GetTrainingData()
results = sentiment.aggregate_sentiment()
px = []
for i in range(100):
    px.append(float(random.randint(100,30000)))

print(talib.MACD(numpy.array(px)))
client = Client(API_KEY, API_SECRET, tld='us')

def order(side, quantity, symbol,order_type='MARKET'):
    try:
        print("sending order")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        print(order)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return True

def on_open(ws):
    print('opened connection')

def on_close(ws):
    print('closed connection')

def eval_crypto_sentiment():
    news = news_sentiment(dateFrom, 'Ethereum', '35774d72fac245bda2d88fe095f44def')
    for source in SOURCES:
        news_sentiment.NewsFromSource(news,source)
    news.GetTrainingData()
    news.aggregate_sentiment()
    return (news.good, news.bad, news.neutral)
# refine to use HH - LH, HL - LL, LW - HH and LL - HL

def on_message(ws, message):
    global closes, in_position
    sentiment = news_sentiment(dateFrom, 'Ethereum',SENTIMENT_API_KEY)
    print('here')
    sentiment.GetTrainingData()
    results = sentiment.aggregate_sentiment()
    print(results)
    sys.exit()
    print('received message')
    #Calculate all relevant signals in sequence, in order of priority, and back out if any of them not sufficient
    json_message = json.loads(message)
    pprint.pprint(json_message)

    candle = json_message['k']

    is_candle_closed = candle['x']
    close = candle['c']

    if is_candle_closed:
        print("candle closed at {}".format(close))
        closes.append(float(close))
        print("closes")
        print(closes)

        if len(closes) > RSI_PERIOD and len(closes) > MACD_PERIOD:
            #Consider caching these calculations for prices within % tolerance of given price range
            #Consider tuning params

            #Eval MACD
            macd1, macd2, macd3 = talib.MACD(closes, fastperiod=MACD_FAST,slowperiod=MACD_SLOW,signalperiod=MACD_SIGNAL)
            signal=macd2
            if signal > MACD_BUY_TRIGGER_THRESHOLD:
                macd_buy = True
            elif signal < MACD_SELL_TRIGGER_THRESHOLD:
                macd_sell = True
            else:
                #Most critical indicator not sufficient, ignore signal
                return
            #Eval RSI
            np_closes = numpy.array(closes)
            rsi = talib.RSI(np_closes, RSI_PERIOD)
            print("all rsis calculated so far")
            print(rsi)
            last_rsi = rsi[-1]
            print("the current rsi is {}".format(last_rsi))

            if last_rsi > RSI_OVERBOUGHT:
                rsi_buy = True
            elif last_rsi < RSI_OVERSOLD:
                rsi_sell = True
            else:
                return

            #Eval sentiment
            sentimemnt = news_sentiment(datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=BACK_DAYS),'%Y%m%d'),'Ethereum',SENTIMENT_API_KEY )
            sentiment.GetTrainingData()
            results = sentiment.aggregate_sentiment()
            print(results)
            '''
                if in_position:
                    print("Overbought! Sell! Sell! Sell!")
                    # put binance sell logic here
                    order_succeeded = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)
                    if order_succeeded:
                        in_position = False
                else:
                    print("It is overbought, but we don't own any. Nothing to do.")

            if last_rsi < RSI_OVERSOLD:
                if in_position:
                    print("It is oversold, but you already own it, nothing to do.")
                else:
                    print("Oversold! Buy! Buy! Buy!")
                    # put binance buy order logic here
                    order_succeeded = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
                    if order_succeeded:
                        in_position = True
            '''

ws = websocket.WebSocketApp(SOCKET,on_open=on_open,on_close=on_close,on_message=on_message)
ws.run_forever()