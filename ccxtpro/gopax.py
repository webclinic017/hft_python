# -*- coding: utf-8 -*-

# PLEASE DO NOT EDIT THIS FILE, IT IS GENERATED AND WILL BE OVERWRITTEN:
# https://github.com/ccxt/ccxt/blob/master/CONTRIBUTING.md#how-to-contribute-code

from ccxtpro.base.exchange import Exchange
import ccxt.async_support as ccxt
from ccxtpro.base.cache import ArrayCache, ArrayCacheBySymbolById

# -----------------------------------------------------------------------------

try:
    basestring  # Python 3
except NameError:
    basestring = str  # Python 2
import hashlib
import json


class gopax(Exchange, ccxt.gopax):

    def describe(self):
        return self.deep_extend(super(gopax, self).describe(), {
            'has': {
                'ws': True,
                'watchOrderBook': True,
                'watchMyTrades': True,
                'watchBalance': True,
                'watchOrders': True,
            },
            'urls': {
                'api': {
                    'ws': 'wss://wsapi.gopax.co.kr',
                },
            },
            'options': {
                'tradesLimit': 1000,
                'ordersLimit': 1000,
                'OHLCVLimit': 1000,
            },
        })

    def get_signed_url(self):
        options = self.safe_value(self.options, 'ws', {})
        if 'url' in options:
            return options['url']
        self.check_required_credentials()
        nonce = str(self.nonce())
        auth = 't' + nonce
        rawSecret = self.base64_to_binary(self.secret)
        signature = self.hmac(self.encode(auth), rawSecret, hashlib.sha512, 'base64')
        query = {
            'apiKey': self.apiKey,
            'timestamp': nonce,
            'signature': signature,
        }
        url = self.urls['api']['ws'] + '?' + self.urlencode(query)
        options['url'] = url
        self.options['ws'] = options
        return url

    async def watch_order_book(self, symbol, limit=None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        name = 'orderbook'
        messageHash = name + ':' + market['id']
        url = self.get_signed_url()
        request = {
            'n': 'SubscribeToOrderBook',
            'o': {
                'tradingPairName': market['id'],
            },
        }
        subscription = {
            'messageHash': messageHash,
            'name': name,
            'symbol': symbol,
            'marketId': market['id'],
            'method': self.handle_order_book,
            'limit': limit,
            'params': params,
        }
        message = self.extend(request, params)
        orderbook = await self.watch(url, messageHash, message, messageHash, subscription)
        return orderbook.limit(limit)

    def handle_delta(self, orderbook, bookside, delta):
        #
        #     {
        #         entryId: 60949856,
        #         price: 31575000,
        #         volume: 0.3163,
        #         updatedAt: 1609420344.174
        #     }
        #
        entryId = self.safe_integer(delta, 'entryId')
        if (orderbook['nonce'] is not None) and (entryId >= orderbook['nonce']):
            price = self.safe_float(delta, 'price')
            amount = self.safe_float(delta, 'volume')
            bookside.store(price, amount)
        return entryId

    def handle_deltas(self, orderbook, bookside, deltas):
        nonce = 0
        for i in range(0, len(deltas)):
            n = self.handle_delta(orderbook, bookside, deltas[i])
            nonce = max(nonce, n)
        return nonce

    def handle_order_book_message(self, client, message, orderbook):
        #
        #     {
        #         i: -1,
        #         n: 'OrderBookEvent',
        #         o: {
        #             ask: [
        #                 {entryId: 60949856, price: 31575000, volume: 0.3163, updatedAt: 1609420344.174}
        #             ],
        #             bid: [],
        #             tradingPairName: 'BTC-KRW'
        #         }
        #     }
        #
        o = self.safe_value(message, 'o', {})
        askNonce = self.handle_deltas(orderbook, orderbook['asks'], self.safe_value(o, 'ask', []))
        bidNonce = self.handle_deltas(orderbook, orderbook['bids'], self.safe_value(o, 'bid', []))
        nonce = max(askNonce, bidNonce)
        orderbook['nonce'] = nonce
        return orderbook

    def handle_order_book(self, client, message):
        #
        # initial snapshot
        #
        #     {
        #         n: 'SubscribeToOrderBook',
        #         o: {
        #             ask: [
        #                 {entryId: 60490601, price: 32061000, volume: 0.09996, updatedAt: 1609412729.325},
        #                 {entryId: 60490959, price: 32078000, volume: 0.206, updatedAt: 1609412735.793},
        #                 {entryId: 60490687, price: 32085000, volume: 0.192, updatedAt: 1609412730.373},
        #             ],
        #             bid: [
        #                 {entryId: 60491143, price: 32059000, volume: 0.3118, updatedAt: 1609412740.011},
        #                 {entryId: 60490948, price: 32058000, volume: 0.00162449, updatedAt: 1609412735.555},
        #                 {entryId: 60488158, price: 32053000, volume: 0.206, updatedAt: 1609412680.169},
        #             ],
        #             tradingPairName: 'BTC-KRW',
        #             maxEntryId: 60491355
        #         }
        #     }
        #
        # delta update
        #
        #     {
        #         i: -1,
        #         n: 'OrderBookEvent',
        #         o: {
        #             ask: [
        #                 {entryId: 60949856, price: 31575000, volume: 0.3163, updatedAt: 1609420344.174}
        #             ],
        #             bid: [],
        #             tradingPairName: 'BTC-KRW'
        #         }
        #     }
        #
        n = self.safe_string(message, 'n')
        o = self.safe_value(message, 'o')
        marketId = self.safe_string(o, 'tradingPairName')
        market = self.safe_market(marketId, None, '-')
        symbol = market['symbol']
        # nonce = self.safe_integer(o, 'maxEntryId')
        name = 'orderbook'
        messageHash = name + ':' + market['id']
        subscription = self.safe_value(client.subscriptions, messageHash, {})
        limit = self.safe_integer(subscription, 'limit')
        if not (symbol in self.orderbooks):
            self.orderbooks[symbol] = self.order_book({}, limit)
        orderbook = self.safe_value(self.orderbooks, symbol)
        if n == 'SubscribeToOrderBook':
            orderbook['nonce'] = 0
            self.handle_order_book_message(client, message, orderbook)
            for i in range(0, len(orderbook.cache)):
                message = orderbook.cache[i]
                self.handle_order_book_message(client, message, orderbook)
            client.resolve(orderbook, messageHash)
        else:
            if orderbook['nonce'] is None:
                orderbook.cache.append(message)
            else:
                self.handle_order_book_message(client, message, orderbook)
                client.resolve(orderbook, messageHash)

    async def watch_orders(self, symbol=None, since=None, limit=None, params={}):
        await self.load_markets()
        name = 'orders'
        subscriptionHash = name
        messageHash = name
        if symbol is not None:
            messageHash += ':' + symbol
        url = self.get_signed_url()
        request = {
            'n': 'SubscribeToOrders',
            'o': {},
        }
        subscription = {
            'messageHash': messageHash,
            'name': name,
            'symbol': symbol,
            'method': self.handle_order_book,
            'limit': limit,
            'params': params,
        }
        message = self.extend(request, params)
        orders = await self.watch(url, messageHash, message, subscriptionHash, subscription)
        if self.newUpdates:
            limit = orders.getLimit(symbol, limit)
        return self.filter_by_symbol_since_limit(orders, symbol, since, limit, True)

    def parse_ws_order_status(self, status):
        statuses = {
            '1': 'open',
            '2': 'canceled',
            '3': 'closed',
            '4': 'open',
            # '5': 'reserved',
        }
        return self.safe_string(statuses, status, status)

    def parse_ws_order_type(self, orderType):
        types = {
            '1': 'limit',
            '2': 'market',
        }
        return self.safe_string(types, orderType, orderType)

    def parse_ws_order_side(self, side):
        sides = {
            '1': 'buy',
            '2': 'sell',
        }
        return self.safe_string(sides, side, side)

    def parse_ws_time_in_force(self, timeInForce):
        timeInForces = {
            '0': 'GTC',
            '1': 'PO',
            '2': 'IOC',
            '3': 'FOK',
        }
        return self.safe_string(timeInForces, timeInForce, timeInForce)

    def parse_ws_order(self, order, market=None):
        #
        #     {
        #         "orderId": 327347,           # order ID
        #         "status": 1,                 # 1(not filled), 2(canceled), 3(completely filled), 4(partially filled), 5(reserved)
        #         "side": 2,                   # 1(bid), 2(ask)
        #         "type": 1,                   # 1(limit), 2(market)
        #         "price": 5500000,            # price
        #         "orgAmount": 1,              # initially placed amount
        #         "remainAmount": 1,           # unfilled or remaining amount
        #         "createdAt": 1597218137,     # placement time
        #         "updatedAt": 1597218137,     # last update time
        #         "tradedBaseAmount": 0,       # filled base asset amount(in ZEC for self case)
        #         "tradedQuoteAmount": 0,      # filled quote asset amount(in KRW for self case)
        #         "feeAmount": 0,              # fee amount
        #         "rewardAmount": 0,           # reward amount
        #         "timeInForce": 0,            # 0(gtc), 1(post only), 2(ioc), 3(fok)
        #         "protection": 1,             # 1(not applied), 2(applied)
        #         "forcedCompletionReason": 0,  # 0(n/a), 1(timeInForce), 2(protection)
        #         "stopPrice": 0,              # stop price(> 0 only for stop orders)
        #         "takerFeeAmount": 0,         # fee amount paid as a taker position
        #         "tradingPairName": "ZEC-KRW"  # order book
        #     }
        #
        id = self.safe_string(order, 'orderId')
        clientOrderId = self.safe_string(order, 'clientOrderId')
        timestamp = self.safe_timestamp(order, 'createdAt')
        type = self.parse_ws_order_type(self.safe_string(order, 'type'))
        side = self.parse_ws_order_side(self.safe_string(order, 'side'))
        timeInForce = self.parse_ws_time_in_force(self.safe_string(order, 'timeInForce'))
        price = self.safe_float(order, 'price')
        amount = self.safe_float(order, 'orgAmount')
        stopPrice = self.safe_float(order, 'stopPrice')
        remaining = self.safe_float(order, 'remainAmount')
        marketId = self.safe_string(order, 'tradingPairName')
        market = self.safe_market(marketId, market, '-')
        status = self.parse_ws_order_status(self.safe_string(order, 'status'))
        filled = self.safe_float(order, 'tradedBaseAmount')
        cost = self.safe_float(order, 'tradedQuoteAmount')
        updated = None
        if (amount is not None) and (remaining is not None):
            filled = max(0, amount - remaining)
            if filled > 0:
                updated = self.safe_timestamp(order, 'updatedAt')
            if price is not None:
                cost = filled * price
        postOnly = None
        if timeInForce is not None:
            postOnly = (timeInForce == 'PO')
        fee = None
        return {
            'id': id,
            'clientOrderId': clientOrderId,
            'datetime': self.iso8601(timestamp),
            'timestamp': timestamp,
            'lastTradeTimestamp': updated,
            'status': status,
            'symbol': market['symbol'],
            'type': type,
            'timeInForce': timeInForce,
            'postOnly': postOnly,
            'side': side,
            'price': price,
            'stopPrice': stopPrice,
            'average': price,
            'amount': amount,
            'filled': filled,
            'remaining': remaining,
            'cost': cost,
            'trades': None,
            'fee': fee,
            'info': order,
        }

    def handle_order(self, client, message, order, market=None):
        parsed = self.parse_ws_order(order)
        if self.orders is None:
            limit = self.safe_integer(self.options, 'ordersLimit', 1000)
            self.orders = ArrayCacheBySymbolById(limit)
        orders = self.orders
        orders.append(parsed)
        return parsed

    def handle_orders(self, client, message):
        #
        # subscription response
        #
        #
        #     {
        #         "n": "SubscribeToOrders",
        #         "o": {
        #             "data": [
        #                 {
        #                     "orderId": 327347,           # order ID
        #                     "status": 1,                 # 1(not filled), 2(canceled), 3(completely filled), 4(partially filled), 5(reserved)
        #                     "side": 2,                   # 1(bid), 2(ask)
        #                     "type": 1,                   # 1(limit), 2(market)
        #                     "price": 5500000,            # price
        #                     "orgAmount": 1,              # initially placed amount
        #                     "remainAmount": 1,           # unfilled or remaining amount
        #                     "createdAt": 1597218137,     # placement time
        #                     "updatedAt": 1597218137,     # last update time
        #                     "tradedBaseAmount": 0,       # filled base asset amount(in ZEC for self case)
        #                     "tradedQuoteAmount": 0,      # filled quote asset amount(in KRW for self case)
        #                     "feeAmount": 0,              # fee amount
        #                     "rewardAmount": 0,           # reward amount
        #                     "timeInForce": 0,            # 0(gtc), 1(post only), 2(ioc), 3(fok)
        #                     "protection": 1,             # 1(not applied), 2(applied)
        #                     "forcedCompletionReason": 0,  # 0(n/a), 1(timeInForce), 2(protection)
        #                     "stopPrice": 0,              # stop price(> 0 only for stop orders)
        #                     "takerFeeAmount": 0,         # fee amount paid as a taker position
        #                     "tradingPairName": "ZEC-KRW"  # order book
        #                 }
        #             ]
        #         }
        #     }
        #
        # delta update
        #
        #     {
        #         "i": -1,                         # always -1 in case of delta push
        #         "n": "OrderEvent",
        #         "o": {
        #             "orderId": 327347,
        #             "status": 4,                 # changed to 4(partially filled)
        #             "side": 2,
        #             "type": 1,
        #             "price": 5500000,
        #             "orgAmount": 1,
        #             "remainAmount": 0.8,         # -0.2 as 0.2 ZEC is filled
        #             "createdAt": 1597218137,
        #             "updatedAt": 1599093631,     # updated
        #             "tradedBaseAmount": 0.2,     # 0.2 ZEC goes out
        #             "tradedQuoteAmount": 1100000,// 1,100,000 KRW comes in
        #             "feeAmount": 440,            # fee amount(in KRW and 0.04% for self case)
        #             "rewardAmount": 0,
        #             "timeInForce": 0,
        #             "protection": 1,
        #             "forcedCompletionReason": 0,
        #             "stopPrice": 0,
        #             "takerFeeAmount": 0,
        #             "tradingPairName": "ZEC-KRW"
        #         }
        #     }
        #
        o = self.safe_value(message, 'o', [])
        data = self.safe_value(o, 'data')
        messageHash = 'orders'
        if data is None:
            # single order delta update
            order = self.handle_order(client, message, data)
            symbol = order['symbol']
            client.resolve(self.orders, messageHash)
            client.resolve(self.orders, messageHash + ':' + symbol)
        else:
            # initial subscription response with multiple orders
            dataLength = len(data)
            if dataLength > 0:
                symbols = {}
                for i in range(0, dataLength):
                    order = self.handle_order(client, message, data[i])
                    symbol = order['symbol']
                    symbols[symbol] = True
                client.resolve(self.orders, messageHash)
                keys = list(symbols.keys())
                for i in range(0, len(keys)):
                    symbol = keys[i]
                    client.resolve(self.orders, messageHash + ':' + symbol)

    async def watch_my_trades(self, symbol=None, since=None, limit=None, params={}):
        await self.load_markets()
        name = 'myTrades'
        subscriptionHash = name
        messageHash = name
        if symbol is not None:
            messageHash += ':' + symbol
        url = self.get_signed_url()
        request = {
            'n': 'SubscribeToTrades',
            'o': {},
        }
        subscription = {
            'messageHash': messageHash,
            'name': name,
            'symbol': symbol,
            'method': self.handle_my_trades,
            'limit': limit,
            'params': params,
        }
        message = self.extend(request, params)
        trades = await self.watch(url, messageHash, message, subscriptionHash, subscription)
        if self.newUpdates:
            limit = trades.getLimit(symbol, limit)
        return self.filter_by_since_limit(trades, since, limit, 'timestamp', True)

    def handle_my_trades(self, client, message):
        #
        # subscription response
        #
        #     {n: 'SubscribeToTrades', o: {}}
        #
        #  regular update
        #
        #     {
        #         "i": -1,
        #         "n": "TradeEvent",
        #         "o": {
        #             "tradeId": 74072,            # trade ID
        #             "orderId": 453529,           # order ID
        #             "side": 2,                   # 1(bid), 2(ask)
        #             "type": 1,                   # 1(limit), 2(market)
        #             "baseAmount": 0.01,          # filled base asset amount(in ZEC for self case)
        #             "quoteAmount": 1,            # filled quote asset amount(in KRW for self case)
        #             "fee": 0.0004,               # fee
        #             "price": 100,                # price
        #             "isSelfTrade": False,        # whether both of matching orders are yours
        #             "occurredAt": 1603932107,    # trade occurrence time
        #             "tradingPairName": "ZEC-KRW"  # order book
        #         }
        #     }
        #
        o = self.safe_value(message, 'o', {})
        name = 'myTrades'
        messageHash = name
        trade = self.parse_trade(o)
        symbol = trade['symbol']
        array = self.safe_value(self.myTrades, symbol)
        if array is None:
            limit = self.safe_integer(self.options, 'tradesLimit', 1000)
            array = ArrayCache(limit)
        array.append(trade)
        self.myTrades[symbol] = array
        client.resolve(array, messageHash)
        client.resolve(array, messageHash + ':' + symbol)

    async def watch_balance(self, params={}):
        await self.load_markets()
        name = 'balance'
        messageHash = name
        url = self.get_signed_url()
        request = {
            'n': 'SubscribeToBalances',
            'o': {},
        }
        subscription = {
            'messageHash': messageHash,
            'name': name,
            'params': params,
        }
        message = self.extend(request, params)
        return await self.watch(url, messageHash, message, messageHash, subscription)

    def handle_balance(self, client, message):
        #
        #     {
        #         n: 'SubscribeToBalances',
        #         o: {
        #             result: True,
        #             data: [
        #                 {assetId: 1, avail: 30000.74103433, hold: 0, pendingWithdrawal: 0, blendedPrice: 1, lastUpdatedAt: 1609519939.412, isoAlpha3: 'KRW'},
        #                 {assetId: 3, avail: 0, hold: 0, pendingWithdrawal: 0, blendedPrice: 0, lastUpdatedAt: 0, isoAlpha3: 'ETH'},
        #                 {assetId: 4, avail: 0, hold: 0, pendingWithdrawal: 0, blendedPrice: 0, lastUpdatedAt: 0, isoAlpha3: 'BTC'},
        #             ],
        #         },
        #     }
        #
        #     {
        #         "i": -1,                             # always -1 in case of delta push
        #         "n": "BalanceEvent",
        #         "o": {
        #             "assetId": 7,
        #             "avail": 990.4998,               # +1 as you can use 1 ZEC more to place a new order
        #             "hold": 1,                       # -1 as you take it back from an order book
        #             "pendingWithdrawal": 0,
        #             "blendedPrice": 429413.08986192,
        #             "lastUpdatedAt": 1599098077.27,
        #             "isoAlpha3": "ZEC"
        #         }
        #     }
        #
        o = self.safe_value(message, 'o')
        data = self.safe_value(o, 'data')
        if data is None:
            balance = self.parse_balance_response([o])
            self.balance = self.parse_balance(self.extend(self.balance, balance))
        else:
            self.balance = self.parse_balance_response(data)
        messageHash = 'balance'
        client.resolve(self.balance, messageHash)

    async def pong(self, client, message):
        #
        #     "primus::ping::1609504526621"
        #
        messageString = json.loads(message)
        parts = messageString.split('::')
        requestId = self.safe_string(parts, 2)
        response = 'primus::pong::' + requestId
        await client.send(response)

    def handle_ping(self, client, message):
        self.spawn(self.pong, client, message)

    def handle_message(self, client, message):
        #
        # ping string message
        #
        #     "primus::ping::1609504526621"
        #
        # regular json message
        #
        #     {
        #         n: 'SubscribeToOrderBook',
        #         o: {
        #             ask: [
        #                 {entryId: 60490601, price: 32061000, volume: 0.09996, updatedAt: 1609412729.325},
        #                 {entryId: 60490959, price: 32078000, volume: 0.206, updatedAt: 1609412735.793},
        #                 {entryId: 60490687, price: 32085000, volume: 0.192, updatedAt: 1609412730.373},
        #             ],
        #             bid: [
        #                 {entryId: 60491143, price: 32059000, volume: 0.3118, updatedAt: 1609412740.011},
        #                 {entryId: 60490948, price: 32058000, volume: 0.00162449, updatedAt: 1609412735.555},
        #                 {entryId: 60488158, price: 32053000, volume: 0.206, updatedAt: 1609412680.169},
        #             ],
        #             tradingPairName: 'BTC-KRW',
        #             maxEntryId: 60491355
        #         }
        #     }
        #
        if isinstance(message, basestring):
            self.handle_ping(client, message)
        else:
            methods = {
                'OrderBookEvent': self.handle_order_book,
                'SubscribeToOrderBook': self.handle_order_book,
                # 'SubscribeToTrades': self.handle_my_trades,
                'TradeEvent': self.handle_my_trades,
                'SubscribeToOrders': self.handle_orders,
                'OrderEvent': self.handle_orders,
                'SubscribeToBalances': self.handle_balance,
                'BalanceEvent': self.handle_balance,
            }
            n = self.safe_string(message, 'n')
            method = self.safe_value(methods, n)
            if method is not None:
                return method(client, message)
        return message
