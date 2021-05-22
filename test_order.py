# -*- coding: utf-8 -*-

import os
import sys
import math
import decimal
import time
# import asyncio
from local_settings import binance_test, binance_real
# from binance_backtrader import bt_start
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(10)

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

import ccxt  # noqa: E402

test = binance_real['test']

exchange = ccxt.binance({
    'apiKey': binance_real['apiKey'],
    'secret': binance_real['secret'],
    'enableRateLimit': False,
})
exchange.set_sandbox_mode(test)

coin = 'BNB/USDT'
# market = exchange.market(coin)
# exchange.load_markets()
# print(market)

if False:  # and self.order:
    params = {'stopPrice': 205.4433,
              # 'price': 376,
              # 'quantity': 0.0523,
              'timeInForce': 'GTC',
              # 'type': 'STOP_LOSS_LIMIT',
              # 'side': "sell",
              }
    order = exchange.createOrder(symbol=coin, type='STOP_LOSS_LIMIT', side='sell',
                                 price=201.3333, amount=0.05555, params=params)
    print("Stop Loss Limit Order: ", order)

    orderid = order['info']['orderId']

    c_order = exchange.cancel_order(id=orderid, symbol=coin)
    print("Cancelled Order: ", c_order)

if True:
    exchange.load_markets()
    market = exchange.market(coin)

    quantity = 0.555555
    price = 400.189345
    stopPrice = 205.121212
    stopLimitPrice = 201.121212
    print('MARKET ID: ',market['id'])
    params = {
        'symbol': market['id'],
        'side': 'sell',  # SELL, BUY
        'quantity': decimal.Decimal('%.4f' % (quantity * 1000 / 1000)),
        'price': decimal.Decimal('%.2f' % (price * 1000 / 1000)),
        'stopPrice': decimal.Decimal('%.2f' % (stopPrice * 1000 / 1000)),
        'stopLimitPrice': decimal.Decimal('%.2f' % (stopLimitPrice * 1000 / 1000)),  # If provided, stopLimitTimeInForce is required
        'stopLimitTimeInForce': 'GTC',  # GTC, FOK, IOC
        # 'listClientOrderId': exchange.uuid(),  # A unique Id for the entire orderList
        # 'limitClientOrderId': exchange.uuid(),  # A unique Id for the limit order
        # 'limitIcebergQty': exchangea.amount_to_precision(symbol, limit_iceberg_quantity),
        # 'stopClientOrderId': exchange.uuid()  # A unique Id for the stop loss/stop loss limit leg
        # 'stopIcebergQty': exchange.amount_to_precision(symbol, stop_iceberg_quantity),
        # 'newOrderRespType': 'ACK',  # ACK, RESULT, FULL
        }
    ocoorder = exchange.private_post_order_oco(params=params)
    print("OCO Order: ", ocoorder)
    time.sleep(2)
    ocoorderid = ocoorder['orders'][0]['orderId']
    ocoorderListId = ocoorder['orderListId']

    o_status = exchange.fetchOpenOrders(symbol=coin)
    print("Open Order: ", o_status)

    oco_status = exchange.fetchOrder(id=ocoorderid, symbol=coin)
    print("Oco Status: ", oco_status['status'])
    if oco_status['status'] == 'open':
        print("Oco Order Still Running")


    c_ocoorder = exchange.cancel_order(id=ocoorderid, symbol=coin)
    print("Cancelled OCO Order: ", c_ocoorder)
