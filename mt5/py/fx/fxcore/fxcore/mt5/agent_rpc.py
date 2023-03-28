from threading import Thread, Event
import sys
import string
import random
import pickle
import json
import os
from contextlib import suppress
import time


import logging.config
import redis
import logging
import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd
logging.basicConfig(level=logging.INFO)


__all__ = [
    'Client',
    'RemoteException',
    'TimeoutException'
]


def random_string(size=8, chars=string.ascii_uppercase + string.digits):
    """Ref: http://stackoverflow.com/questions/2257441"""
    return ''.join(random.choice(chars) for x in range(size))


class curry:
    """Ref: https://jonathanharrington.wordpress.com/2007/11/01/currying-and-python-a-practical-example/"""

    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()

    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs
            return self.fun(*(self.pending + args), **kw)


def decode_message(message):
    """Returns a (transport, decoded_message) pair."""
    # Try JSON, then try Python pickle, then fail.
    try:
        return JSONTransport.create(), json.loads(message.decode())
    except:
        pass
    return PickleTransport.create(), pickle.loads(message)


class JSONTransport(object):
    """Cross platform transport."""
    _singleton = None

    @classmethod
    def create(cls):
        if cls._singleton is None:
            cls._singleton = JSONTransport()
        return cls._singleton

    def dumps(self, obj):
        return json.dumps(obj)

    def loads(self, obj):
        return json.loads(obj.decode())


class PickleTransport(object):
    """Only works with Python clients and servers."""
    _singleton = None

    @classmethod
    def create(cls):
        if cls._singleton is None:
            cls._singleton = PickleTransport()
        return cls._singleton

    def dumps(self, obj):
        return pickle.dumps(obj, protocol=4)

    def loads(self, obj):
        return pickle.loads(obj)


class Server(object):
    """Executes function calls received from a Redis queue."""

    def __init__(self, redis_server, message_queue, local_object):
        self.redis_server = redis_server
        self.message_queue = message_queue
        self.local_object = local_object
        self.logger = logging.getLogger("Server")

    def run(self):
        # Flush the message queue.
        self.redis_server.delete(self.message_queue)
        while True:
            message_queue, message = self.redis_server.blpop(
                self.message_queue)
            message_queue = message_queue.decode()
            assert message_queue == self.message_queue
            self.logger.debug('RPC Request: %s' % message)
            transport, rpc_request = decode_message(message)
            response_queue = rpc_request['response_queue']
            function_call = rpc_request['function_call']
            try:
                f_name = function_call['name']
                f_args = function_call.get('args', ())
                f_kw = function_call.get('kwargs', {})
                func = getattr(self.local_object, f_name)
                return_value = func(*f_args, **f_kw)
                rpc_response = dict(return_value=return_value)
            except:
                (type, value, traceback) = sys.exc_info()
                rpc_response = dict(exception=repr(value))
            message = transport.dumps(rpc_response)
            self.logger.debug('RPC Response: %s' % message)
            self.redis_server.rpush(response_queue, message)


class RemoteException(Exception):
    """Raised by an RPC client when an exception occurs on the RPC server."""
    pass


class TimeoutException(Exception):
    """Raised by an RPC client when a timeout occurs."""
    pass


class FxMT5Client:
    def __init__(self) -> None:
        self.adapter = None
        self.logger = logging.getLogger(__name__)

    def get_deals(self, from_date, to_date=None, group=None):
        try:
            self.logger.info(f"get_deals ({( from_date, to_date, group)})")

            if isinstance(from_date, str):
                from_date = pd.to_datetime(from_date)
            if isinstance(to_date, str):
                to_date = pd.to_datetime(to_date)

            if to_date is None:
                to_date = datetime.now()
            if group is None:
                group = ""

            if group:
                deals = mt5.history_deals_get(from_date, to_date, group)
            else:
                deals = mt5.history_deals_get(from_date, to_date)

            if deals == None or len(deals) == 0:
                self.logger.warning("No deals, error code={}".format(mt5.last_error()))
                return None
            elif len(deals) > 0:
                self.logger.warning("Deal count: {}".format(len(deals)))
                df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
                df['time'] = pd.to_datetime(df['time'], unit='s')
                return df
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise

    def get_adapter(self):
        return self.adapter

    def login(self, login, password, server):
        try:
            from mt5adapter import MT5Adapter
            self.adapter = MT5Adapter(login, password, server)
            # mt5.login(login, password, server)
            return self.get_info()
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise

    def get_info(self):
        try:
            self.logger.info("get_info")
            return self.get_adapter().get_info()
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise

    def buy(self, symbol, magic, lot, sl_point, tp_point, deviation, comment):
        """

        :param symbol:
        :param magic:
        :param lot:
        :param sl_point:
        :param tp_point:
        :param deviation:
        :param comment:
        :return: dict or {}
        """
        try:
            existing_re = []

            self.logger.info(
                f'Buy, {(symbol, magic, lot, sl_point, tp_point, deviation, comment)} ')
            exists = self.get_adapter().get_positions(symbol, magic)

            if len(exists) > 1:
                existing_re = self.close(symbol, magic)
                r = self.get_adapter().buy(symbol, magic, lot, sl_point,
                                           tp_point, deviation, comment)
            elif len(exists) == 1:
                first = exists[0]
                if first.volume != lot or first.type != 0:
                    existing_re = self.close(symbol, magic)
                    r = self.get_adapter().buy(symbol, magic, lot, sl_point,
                                               tp_point, deviation, comment)
                else:
                    return {}
            else:
                r = self.get_adapter().buy(symbol, magic, lot, sl_point,
                                           tp_point, deviation, comment)

            if r.retcode != 10009:
                raise Exception(
                    "Buy error magic [{}] info[{}]".format(magic, str(r)))
            else:
                r = r._asdict()
                r['request'] = r['request']._asdict()
                return r, *existing_re
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise

    def sell(self, symbol, magic, lot, sl_point, tp_point, deviation, comment):
        """

        :param symbol:
        :param magic:
        :param lot:
        :param sl_point:
        :param tp_point:
        :param deviation:
        :param comment:
        :return: dict or {}

        """
        try:
            existing_re = []

            self.logger.info(
                f'sell, {(symbol, magic, lot, sl_point, tp_point, deviation, comment)} ')

            exists = self.get_adapter().get_positions(symbol, magic)
            if len(exists) > 1:
                existing_re = self. close(symbol, magic)
                r = self.get_adapter().sell(symbol, magic, lot, sl_point,
                                            tp_point, deviation, comment)
            elif len(exists) == 1:
                first = exists[0]
                if first.volume != lot or first.type != 1:
                    existing_re = self.close(symbol, magic)
                    r = self.get_adapter().sell(symbol, magic, lot, sl_point,
                                                tp_point, deviation, comment)
                else:
                    return {}

            else:
                r = self.get_adapter().sell(symbol, magic, lot, sl_point,
                                            tp_point, deviation, comment)

            if r.retcode != 10009:
                raise Exception(
                    "Sell error magic [{}] info[{}]".format(magic, str(r)))
            else:
                r = r._asdict()
                r['request'] = r['request']._asdict()
                return r, *existing_re
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise

    def close(self, symbol, magic, dev=20):
        """

        :param symbol:
        :param magic:
        :return: [dict]

        """
        try:
            self.logger.info(f'close, {(symbol, magic,dev)}')

            result = self.get_adapter().close_all(symbol, magic, dev)

            re = [x._asdict() for x in result]
            for v in re:
                v['request'] = v['request']._asdict()
            return re
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise

    def get_last_trade(self, magic):
        try:
            res = self. adapter.get_last_trade(magic)
            res_json = {
                "symbol": res.symbol,
                "profit": res.profit,
                "volume": res.volume,
                "price": res.price,
                "commission": res.commission,
                "swap": res.swap
            }

            return res_json
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise

    def get_candle_from_date(self, symbol, start_timestamp):
        try:
            self.logger.info(
                f"start get_candle_from_date: {( symbol, start_timestamp)}")
            df = self.get_adapter().get_candle_from_date(symbol, start_timestamp)
            df.drop_duplicates(inplace=True)
            self.logger.info(
                f"end get_candle_from_date: {( symbol, start_timestamp)} result len {len(df)}")
            return df
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise

    def get_candle_from_pos(self, symbol, timeframe, start, end, truncate_first=True):
        try:
            self.logger.info(f"get_candle_from_pos: {( symbol, timeframe, start, end, truncate_first)}")
            df = self.get_adapter().get_candle_from_pos(symbol, timeframe, start, end, truncate_first)
            df.drop_duplicates(inplace=True)
            self.logger.info(f"get_candle_from_pos: {( symbol, timeframe, start, end)}")
            return df
        except:
            self.logger.exception("Error on get_candle_from_pos", exc_info=True)
            raise


REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379')
ACCOUNT = int(os.environ.get('ACCOUNT', '123'))
PASSWORD = os.environ.get('PASSWORD', '123')
SERVER = os.environ.get('SERVER', 'ICMarketsSC-Demo')
REDIS_RPC = f'/fx/rpc/{ACCOUNT}'

redis_server = redis.Redis.from_url(REDIS_URL)
local_object = FxMT5Client()

 

account_node = f'/FS/accounts/{ACCOUNT}'
rpc_node = f'/FS/accounts/{ACCOUNT}/rpc'

  

server = Server(redis_server, REDIS_RPC, local_object)
for tried in range(20):
    try:
        info = local_object.login(ACCOUNT, PASSWORD, SERVER)
        assert info['login'] == ACCOUNT
        break
    except Exception as ex:
        print('Exception when init account, exc', ex)
        time.sleep(5)
else:
    raise RuntimeError("Can't start mt5")

logging.info(f"Start RPC server, url: {REDIS_URL} queue: {REDIS_RPC}")
server.run() 