# -*- coding: utf-8 -*-

import os
import sys
import asyncio
from local_settings import binance_test, binance_real
from binance_backtrader import bt_start
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(10)

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

import ccxt  # noqa: E402


class CryptoTrade:
    def __init__(self):
        self.test = binance_test['test']

        self.exchange = ccxt.binance({
            'apiKey': binance_test['apiKey'],
            'secret': binance_test['secret'],
            'enableRateLimit': False,
        })
        self.exchange.set_sandbox_mode(self.test)
        self.error = False
        self.order_success = False

    async def tweet_order(self, coin, side, amount, tw_id):
        # await asyncio.sleep(1)
        self.coin = coin
        self.side = side
        self.amount = amount

        # params = {'quoteOrderQty': amount}

        try:
            if side == "buy":
                # symbol = coin
                # price = None
                amount = None
                # type = 'market'  # or market
                side = side
                params = {'quoteOrderQty': self.amount,}
                # self.exchange.amount_to_precision(symbol, amount)
                # self.order = self.exchange.create_order(coin, type='market', side=side, amount = amount)
                self.order = self.exchange.create_order(symbol=coin, type='market', side=side, price=None, amount=None, params=params)
            elif side == "sell":
                self.order = self.exchange.create_order(coin, type='market', side=side, amount=amount)

            print("Market Order: ", self.order)

            '''
            if True and self.order:
                params = {'stopPrice': self.exchange.price_to_precision(coin, self.order['average']*0.98),
                          'price': self.exchange.price_to_precision(coin, self.order['average']*0.975),
                          'quantity': self.exchange.amount_to_precision(coin, 0.03),
                          'timeInForce': 'GTC',
                          'type': 'STOP_LOSS_LIMIT',
                          'side': "sell", }
                self.order3 = self.exchange.createOrder(symbol=coin, type='STOP_LOSS_LIMIT', side=side,
                                                        price=self.exchange.price_to_precision(coin, self.order['average']*0.975), amount=0.03, params=params)
                print("Stop Loss Limit Order: ", self.order3)
                '''
        except ccxt.NetworkError as e:
            self.error = True
            self.order_success = False
            print(self.exchange.id, 'fetch_order_book failed due to a network error:', str(e))
            # return(self.exchange.id + ' error: fetch_order_book failed due to a network error:' + str(e))
            return(str(e))

        except ccxt.ExchangeError as e:
            self.error = True
            self.order_success = False
            print(self.exchange.id, 'fetch_order_book failed due to exchange error:', str(e))
            # return(self.exchange.id + ' error: fetch_order_book failed due to exchange error:' + str(e))
            return(str(e))

        except Exception as e:
            self.error = True
            self.order_success = False
            print(self.exchange.id, 'fetch_order_book failed with:', str(e))
            # return(self.exchange.id + ' error: fetch_order_book failed with:' + str(e))
            return(str(e))


        # check if order is filled (successful)
        if self.order["info"]["status"] == "FILLED":
            self.order_fullyfilled = True
            self.orderpartiallyfilled = False
            self.order_success = True
            self.order_status = "Order Fully Filled"
            print("Order Fully Filled")
        elif float(self.order["filled"]) != 0:
            self.order_fullyfilled = False
            self.orderpartiallyfilled = True
            self.order_success = True
            self.order_status = "Order Partially Filled with quantity: " + str(self.order["filled"])
            print("Order Partially Filled with quantity: " + str(self.order["filled"]))
        elif float(self.order["filled"]) == 0:
            self.order_fullyfilled = False
            self.orderpartiallyfilled = False
            self.order_success = False
            self.order_status = "Order Not Filled at all"
            print("Order Not Filled at all")

        # if ordered filled, place oco order of STOPLOSS and TAKEPROFIT
        if self.order_fullyfilled or self.orderpartiallyfilled:

            if self.order_fullyfilled:
                self.ocosize = float(self.order["filled"])
                self.orderedprice = float(self.order["average"])
                print("To OCO size: " + str(self.ocosize) + " Ordered Price: " + str(self.orderedprice))

            elif self.orderpartiallyfilled:  # need to reconfirm if order expired? (in theory, market order doesn't need to be reconfirmed)
                self.ocosize = float(self.order["filled"])
                self.orderedprice = float(self.order["average"])
                print("To OCO size: " + str(self.ocosize) + " Ordered Price: " + str(self.orderedprice))

            await self.oco_order(self.coin, self.side, self.ocosize, self.orderedprice, tw_id, False)
            return([self.order_status, self.order, self.ocoorder, self.params])

        return([self.order_status, self.order])

    async def oco_order(self, coin, side, amount, price, tw_id, from_bt_OCO):
        no_oco_again = False
        if from_bt_OCO:
            self.test = binance_test['test']

            self.exchange = ccxt.binance({
                'apiKey': binance_test['apiKey'],
                'secret': binance_test['secret'],
                'enableRateLimit': False,
            })
            self.exchange.set_sandbox_mode(self.test)
            self.orderedprice = price  # new closing price from binance
            # no_oco_again = True

        take_profit_percent = 0.075
        stop_percent = 0.02
        stoplimit_percent = 0.025
        symbol = coin
        market = self.exchange.market(symbol)
        amount = amount

        if side == "buy":
            print("Creating Sell side OCO")

            oco_side = "sell"
            price = self.orderedprice*(1+take_profit_percent)
            stop_price = self.orderedprice*(1-stop_percent)
            stop_limit_price = self.orderedprice*(1-stoplimit_percent)

        if side == "sell":
            print("Creating Buy side OCO")

            oco_side = "buy"
            price = self.orderedprice*(1-take_profit_percent)
            stop_price = self.orderedprice*(1+stop_percent)
            stop_limit_price = self.orderedprice*(1+stoplimit_percent)

        self.ocoorder = self.exchange.private_post_order_oco({
            'symbol': market['id'],
            'side': oco_side,  # SELL, BUY
            'quantity': self.exchange.amount_to_precision(symbol, amount),
            'price': self.exchange.price_to_precision(symbol, price),
            'stopPrice': self.exchange.price_to_precision(symbol, stop_price),
            'stopLimitPrice': self.exchange.price_to_precision(symbol, stop_limit_price),  # If provided, stopLimitTimeInForce is required
            'stopLimitTimeInForce': 'GTC',  # GTC, FOK, IOC
            # 'listClientOrderId': exchange.uuid(),  # A unique Id for the entire orderList
            # 'limitClientOrderId': exchange.uuid(),  # A unique Id for the limit order
            # 'limitIcebergQty': exchangea.amount_to_precision(symbol, limit_iceberg_quantity),
            # 'stopClientOrderId': exchange.uuid()  # A unique Id for the stop loss/stop loss limit leg
            # 'stopIcebergQty': exchange.amount_to_precision(symbol, stop_iceberg_quantity),
            # 'newOrderRespType': 'ACK',  # ACK, RESULT, FULL
            })
        print(self.ocoorder)
        if self.ocoorder:
            self.order_status = self.order_status + " and OCO Order Created"
            if not no_oco_again:
                self.params = {'coin': coin,
                               'side': side,
                               'amount': amount,
                               'price': self.orderedprice,
                               'take_profit_price': self.exchange.price_to_precision(symbol, price),
                               'newsid': tw_id,
                               'orderid': self.ocoorder['orders'][0]['orderId'],
                               }
                print('oco params created')
                # future = executor.submit(bt_start.bt_start, params)
        else:
            self.order_status = self.order_status + " and OCO Order NOT Created"

        return(self.ocoorder, self.params)

    async def stoptrailing(self):  # only futures have stoptrailing
        print("Creating Stop Trailing Order")

        if self.side == "buy":
            stoptrailing_side = "sell"
        elif self.side == "sell":
            stoptrailing_side = "buy"

        self.stoptrailing_order = self.exchange.create_order(symbol=self.coin,
                                                             type='TRAILING_STOP_MARKET',
                                                             amount=self.ocosize,
                                                             side=stoptrailing_side,
                                                             # callbackRate=2.5,
                                                             price=self.orderedprice
                                                             )
        print(self.stoptrailing_order)
        return(self.stoptrailing_order)


class get_balance:
    def coin_balance(self, coin):
        test = binance_test['test']

        exchange = ccxt.binance({
            'apiKey': binance_test['apiKey'],
            'secret': binance_test['secret'],
            'enableRateLimit': False,
        })

        exchange.set_sandbox_mode(test)

        all_balance = exchange.fetch_balance()
        balance = all_balance[coin]
        return(balance)


class get_allbalance:
    def allcoin_balance(self, coin):
        test = binance_test['test']

        exchange = ccxt.binance({
            'apiKey': binance_test['apiKey'],
            'secret': binance_test['secret'],
            'enableRateLimit': False,
        })

        exchange.set_sandbox_mode(test)

        all_balance = exchange.fetch_balance()
        return(all_balance)
