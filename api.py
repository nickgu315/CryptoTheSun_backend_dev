import os
import sys
from flask import Flask, jsonify, request
from flask_restful import abort, Api, Resource
from flask_executor import Executor
import asyncio
import binance_control
from local_settings import internalport, binance_test
import ccxt
# from binance_backtrader import bt_start
import config
from concurrent.futures import ThreadPoolExecutor
from time import sleep
import bt_binance

app = Flask(__name__)
app.config.from_object('config.DevConfig')
api = Api(app)
executor = ThreadPoolExecutor(2)

alltw_id = []
alltw_id.append('gagahaha')

class news_id():
    def __init__(self):
        self.allnews_id = []


class CryptoBalance():
    async def getbalance(self, coin):
        # await asyncio.sleep(1)
        get_balance = binance_control.get_balance
        result = get_balance.coin_balance(self, coin)
        return result

    async def getallbalance(self, coin):
        # await asyncio.sleep(1)
        get_allbalance = binance_control.get_allbalance
        result = get_allbalance.allcoin_balance(self, coin)
        return result


@app.route('/trade', methods=['POST'])
def trade():
    coin = request.form.get('coin')
    amount = request.form.get('amount')
    # print(confidence)
    side = request.form.get('side')
    # amount = request.form.get('amount')
    tw_id = request.form.get('newsId')

    bt_test = request.form.get('bt_test')

    if coin == 'BTC':
        tocoin = 'BTC/USDT'
    elif coin == 'ETH':
        tocoin = 'ETH/USDT'
    elif coin == 'DOGE':
        tocoin = 'DOGE/USDT'
    elif coin == 'BNB':
        tocoin = 'BNB/USDT'

    if len(alltw_id) == 0:
        alltw_id.append(tw_id)
        print(tw_id)
        print("First Tweet id added")
    elif not tw_id:
        return jsonify(msg="No News Id", status="error", coin=tocoin, side=side, amount=amount)
    elif tw_id == alltw_id[-1]:
        print(tw_id)
        print(alltw_id[-1])
        print("Tweet Already Traded and All Tweets length: " + str(len(alltw_id)))
        return jsonify(msg="News Already Traded", status="error", coin=tocoin, side=side, amount=amount)

    # amount = 1*confidence  # somehow calculated from confidence

    thetrade = binance_control.CryptoTrade()
    result = asyncio.run(thetrade.tweet_order(tocoin, side, amount, tw_id))

    if thetrade.order_success is True:
        alltw_id.append(tw_id)
        print("news id: ", tw_id)
        print("New News Traded and All Tweets length: " + str(len(alltw_id)))

    if thetrade.error:
        return jsonify(msg=result, status="error", coin=tocoin, side=side, amount=amount)

    if thetrade.order_success is True:
        # bt_test = False
        if bt_test and bt_test == 'True':
            print("backtrader starting")
            future = executor.submit(bt_binance.main, [thetrade.params, coin])
        # bt_start.bt_start.submit()
        # return jsonify(msg=result[0], status=result[1]["info"]["status"], coin=coin, side=side, amount=amount)
        # start backtrader
        # provide socket connection to frontend
    return jsonify(msg=result[0], status=result[1]["info"]["status"], coin=tocoin, side=side, amount=amount)

# api.add_resource(CryptoTheSun, '/trade')


def backtrader(param):
    param1 = param
    print('Task #1 started'+str(param1))
    sleep(5)
    print('Task #1 is done'+str(param1))

@app.route('/balance', methods=['GET'])
def getbalance():
    coin = request.values.get('coin')
    if not coin:
        thebalance = CryptoBalance()
        result = asyncio.run(thebalance.getallbalance(coin))
        print("get all balance")
    else:
        thebalance = CryptoBalance()
        result = asyncio.run(thebalance.getbalance(coin))

    return jsonify(balance=result, coin=coin)


port = internalport['port']

if __name__ == '__main__':
    # 83 external port to 8282 internal port
    app.run(host="192.168.1.192", port=port, debug=True)
