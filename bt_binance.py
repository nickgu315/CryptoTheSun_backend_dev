import json
import os
import time
from datetime import datetime, timedelta
import decimal
import backtrader as bt
from backtrader import Order
import ccxt
from ccxtbt import CCXTStore
from local_settings import binance_test, binance_real


class StopTrailStrategy(bt.Strategy):
    params = (('dd', None), )

    def __init__(self):
        self.allparams = self.p.dd.copy()

        self.test = binance_test['test']

        self.exchange = ccxt.binance({
            'apiKey': binance_test['apiKey'],
            'secret': binance_test['secret'],
            'enableRateLimit': False,
        })
        self.exchange.set_sandbox_mode(self.test)

        self.exchange.load_markets()
        self.market = self.exchange.market(self.allparams['coin'])

        print("Inside Strategy All Params: ", self.allparams)
        print("Inside Strategy Coin: ", self.allparams['coin'])
        self.side = self.allparams['side']
        self.ocosize = self.allparams['amount']
        self.orderedprice = self.allparams["price"]
        self.coin = self.allparams['coin']
        self.ocoorderid = self.allparams['orderid']
        self.oco_take_profit_price = self.allparams["take_profit_price"]

        if self.side == "buy":
            self.real_side = "sell"
        elif self.side == "sell":
            self.real_side = "buy"

        self.trailpercent = 0.005
        self.order = None
        # self.take_profit_percent = 0.075
        self.stop_percent = 0.02
        self.stoplimit_percent = 0.025
        self.takeprofit_unchanged = True
        self.newocoorder = None
        self.oco_status = None

    def next(self):
        print('*' * 5, 'NEXT:', bt.num2date(self.data0.datetime[0]), self.data0.close[0])

        if True and self.live_data:
            if True:
                self.oco_status = self.exchange.fetchOrder(id=self.ocoorderid, symbol=self.coin)
                print("Existing OCO Status: ", self.oco_status['status'])

                if self.oco_status['status'] == 'open':
                    if self.data0.close[0] > self.orderedprice*(1+self.trailpercent):
                        # Cancel existing OCO
                        c_ocoorder = self.exchange.cancel_order(id=self.ocoorderid, symbol=self.coin)
                        print("Price Moved. Cancelled OCO Order: ", c_ocoorder)

                        if self.real_side == "sell":
                            print("Creating New Sell side OCO Data")
                            if self.takeprofit_unchanged:
                                price = self.oco_take_profit_price
                            stopPrice = self.data0.close[0]*(1-self.stop_percent)
                            stopLimitPrice = self.data0.close[0]*(1-self.stoplimit_percent)

                        elif self.real_side == "buy":
                            print("Creating New Buy side OCO Data")
                            if self.takeprofit_unchanged:
                                price = self.oco_take_profit_price
                            stopPrice = self.data0.close[0]*(1+self.stop_percent)
                            stopLimitPrice = self.data0.close[0]*(1+self.stoplimit_percent)

                        # print(self.market['id'])
                        # print('ocosize: ', decimal.Decimal('%.4f' % (self.ocosize * 1000 / 1000)))
                        # print(price)
                        # print(stopPrice)
                        # print(stopLimitPrice)
                        # print(decimal.Decimal('%.2f' % (price * 1000 / 1000)))
                        # print(decimal.Decimal('%.2f' % (stopPrice * 1000 / 1000)))
                        # print(decimal.Decimal('%.2f' % (stopLimitPrice * 1000 / 1000)))
                        ocoparams = {
                            'symbol': self.market['id'],
                            'side': self.real_side,  # SELL, BUY
                            'quantity': decimal.Decimal('%.4f' % (self.ocosize * 1000 / 1000)),
                            'price': price,
                            'stopPrice': decimal.Decimal('%.2f' % (stopPrice * 1000 / 1000)),
                            'stopLimitPrice': decimal.Decimal('%.2f' % (stopLimitPrice * 1000 / 1000)),
                            'stopLimitTimeInForce': 'GTC',
                            }
                        print("Passed Params")
                        # Place New OCO
                        self.newocoorder = self.exchange.private_post_order_oco(params=ocoparams)
                        print("New OCO Order: ", self.newocoorder)
                        if self.newocoorder['orderReports'][0]['status'] == 'NEW':
                            self.ocoorderid = self.newocoorder['orders'][0]['orderId']
                            self.orderedprice = self.data0.close[0]
                    else:
                        print("Existing OCO continues. Backtrader Instance NewsId: ", self.allparams['newsid'])

                else:
                    # Cancel bt if closed
                    print("Existing OCO order not open but: ", self.oco_status['status'])
                    if self.oco_status['status'] == 'expired':
                        print(self.oco_status)
                        self.cerebro.runstop()

        for data in self.datas:
            print('{} - {} | O: {} H: {} L: {} C: {} V:{}'.format(data.datetime.datetime(),
                                                                  data._name, data.open[0], data.high[0], data.low[0],
                                                                  data.close[0], data.volume[0]))

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg = 'Data Status: {}, Order Status: {}'.format(data._getstatusname(status), status)
        print(dt, dn, msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False


def main(param):
    # absolute dir the script is in
    '''
    script_dir = os.path.dirname(__file__)
    abs_file_path = os.path.join(script_dir, '../params.json')
    with open(abs_file_path, 'r') as f:
        params = json.load(f)
    '''
    cerebro = bt.Cerebro(quicknotify=True)

    cerebro.broker.setcash(100.0)

    # Add the strategy
    cerebro.addstrategy(StopTrailStrategy, dd=param[0])

    # Create our store
    config = {'apiKey': binance_real['apiKey'],
              'secret': binance_real['secret'],
              'enableRateLimit': True,
              'nonce': lambda: str(int(time.time() * 1000)),
              }

    store = CCXTStore(exchange='binance', currency=param[1], config=config, retries=5, debug=False)

    # Get the broker and pass any kwargs if needed.
    # ----------------------------------------------
    # Broker mappings have been added since some exchanges expect different values
    # to the defaults. Case in point, Kraken vs Bitmex. NOTE: Broker mappings are not
    # required if the broker uses the same values as the defaults in CCXTBroker.
    broker_mapping = {
        'order_types': {
            bt.Order.Market: 'market',
            bt.Order.Limit: 'LIMIT',
            bt.Order.Stop: 'stop-loss',  # stop-loss for kraken, stop for bitmex
            bt.Order.StopLimit: 'stop limit'
        },
        'mappings': {
            'closed_order': {
                'key': 'status',
                'value': 'closed'
            },
            'canceled_order': {
                'key': 'status',
                'value': 'canceled'
            }
        }
    }

    broker = store.getbroker(broker_mapping=broker_mapping)
    cerebro.setbroker(broker)

    # Get our data
    # Drop newest will prevent us from loading partial data from incomplete candles
    hist_start_date = datetime.utcnow() - timedelta(minutes=50)
    data = store.getdata(dataname=param[0]['coin'], name=param[0]['coin'],
                         timeframe=bt.TimeFrame.Minutes, fromdate=hist_start_date,
                         compression=1, ohlcv_limit=50, drop_newest=True)  # , historical=True)

    # Add the feed
    cerebro.adddata(data)

    # Run the strategy
    cerebro.run()
