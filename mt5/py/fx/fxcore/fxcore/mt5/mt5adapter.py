import datetime
import logging
import logging.config
import time
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import pandas as pd

DEMO_LOGIN = None
DEMO_PASS = "ndqNVzRy"
DEMO_SERVER = "ICMarketsSC-Demo"


class MT5Adapter:
    def __init__(self, login=None, password=None, server=None):
        """
        >>> adapter = MT5Adapter(DEMO_LOGIN,DEMO_PASS,DEMO_SERVER)
        >>> assert adapter.info['login']>0
        """
        self.logger = logging.getLogger(__name__)

        if login is None:
            if not mt5.initialize():
                self.logger.exception("Init mt5 error: " + str(mt5.last_error()))
                raise Exception("MT5 not ready")
        else:
            if isinstance(login, str):
                login = int(login)
            if not mt5.initialize(login=login, password=password, server=server):
                self.logger.exception("Init mt5 error: " + str(mt5.last_error()))
                raise Exception("MT5 not ready")
        self.logger.info("Start MT5 success")
        self.tf_dic = {}
        for v in dir(mt5):
            if v.startswith('TIMEFRAME_'):
                tf = v.replace('TIMEFRAME_', '')
                symbol, num = tf[0], tf[1:]
                self.tf_dic[num + symbol.lower()] = getattr(mt5, v)

    def shutdown(self):
        mt5.shutdown()

    def get_info(self):
        return mt5.account_info()._asdict()

    # region candle

    def get_candle_from_date(self, symbol, start_timestamp):
        """
        >>> from datetime import datetime, timedelta
        >>> adapter = MT5Adapter(DEMO_LOGIN,DEMO_PASS,DEMO_SERVER)
        >>> nowts = (datetime.now() - timedelta(hours=72)).timestamp()
        >>> data=pd.concat( list(adapter.get_all_from_date('XAUUSD',nowts)))
        >>> assert len(data)>0, f"len data {len(data)}>0"

        """

        if isinstance(start_timestamp, str):
            start_timestamp = pd.to_datetime(
                start_timestamp, utc=True).timestamp()

        self.logger.debug(f"get_all_from_date symbol[{symbol}] start_time[{start_timestamp}]")
        i = 0
        data_frames = []
        while True:
            d_base = self.get_candle_from_pos(
                symbol, mt5.TIMEFRAME_M1, i, 1000)
            if len(d_base) <= 1:  # nothing to get from mt5
                break
            d_base = d_base[d_base['time'] > start_timestamp]
            i += len(d_base)
            if len(d_base) == 0:
                break
            else:
                data_frames.append(d_base)
            print(f'getting data: {i}')

        arr = []
        for v in reversed(data_frames):
            s = datetime.fromtimestamp(v.head(1).iloc[[0]]['time'].iloc[0])
            e = datetime.fromtimestamp(v.tail(1).iloc[[0]]['time'].iloc[0])
            self.logger.debug(f"Yield symbol [{symbol}] start [{s}] end [{e}] length [{len(v)}]")
            v['volume'] = v['tick_volume']
            v.set_index('time', inplace=True)
            v.index = pd.to_datetime(v.index, unit='s')
            arr.append(v)
        return pd.concat(arr)

    def get_candle_from_pos(self, symbol, timeframe, start, end, truncate_first=True) -> pd.DataFrame:
        """
        >>> adapter = MT5Adapter()
        >>> data = adapter.copy_rates_from_pos('EURUSD','1h',0,101)
        >>> assert len(data)==100,f"{len(data)} == 100"

        :param symbol: symbol, eg: XAUUSD
        :param timeframe: 1h
        :param start: 0
        :param end: 100
        :return: DataFrame
        """
        timeframe = self.tf_dic.get(timeframe, timeframe)
        if start == 0:
            self.logger.warning("Get post from current bar may return incomplete bar, thus the result will be trimmed")
        ticks = mt5.copy_rates_from_pos(symbol, timeframe, start, end)
        self.logger.info(f'getting data: {(symbol, timeframe, start, end)}')

        if ticks is None:
            self.logger.warning("Ticks is None")
            ticks = []
        if len(ticks) > 0 and start == 0 and truncate_first:
            ticks = ticks[:-1]
        if len(ticks) == 0:
            self.logger.warning("Ticks is Empty")
            d_base = pd.DataFrame({'time': [], 'open': [], 'high': [], 'low': [], 'close': [], 'tick_volume': []})
        else:
            d_base = pd.DataFrame(ticks)

        d_base['index'] = d_base['time']
        d_base = d_base.set_index('index')
        d_base.index = pd.to_datetime(d_base.index, unit='s')

        self.logger.info(f'getting data: {(symbol, timeframe, start, end)} result: {len(d_base)}')
        return d_base

    def stream(self, symbol, start_time):
        self.logger.debug(f"stream, symbol[{symbol}] start_time[{start_time}]")
        d_base = self.get_candle_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1000)
        d_base = d_base[d_base["time"] > start_time]
        if len(d_base) > 0:
            for i, _ in d_base.iterrows():
                yield d_base.loc[[i]]

        while True:
            d = self.get_candle_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 10)
            addition = d[~d['time'].isin(d_base['time'])]
            addition = addition[addition["time"] > start_time]
            if addition.empty:
                time.sleep(5)
                continue

            self.logger.info(f'Upload, symbol [{symbol}]  len[{len(addition)}]')
            addition.sort_values("time", ascending=True, inplace=True)
            for i, _ in addition.iterrows():
                yield addition.loc[[i]]

            d_base = pd.concat([d_base, addition])

    # endregion

    # region trade

    def close(self, position, dev=20):
        """
        >>> adapter = MT5Adapter(DEMO_LOGIN,DEMO_PASS,DEMO_SERVER)
        >>> _ = adapter.close_all("XAUUSD")
        >>> adapter.buy("XAUUSD",123,0.01,100,300,0,"hello")
        OrderSendResult(retcode=10009, ...
        >>> adapter.close(adapter.get_position("XAUUSD",123))
        OrderSendResult(retcode=10009, ...
        >>> adapter.close_all()


        # TradePosition(ticket=559932706, time=1585680773, time_msc=1585680773363, time_update=1585680773,
        #               time_update_msc=1585680773363, type=0, magic=234000, identifier=559932706, reason=3, volume=0.01,
        #               price_open=1.10124, sl=1.1002399999999999, tp=1.10324, price_current=1.10246, swap=0.0,
        #               profit=1.22, symbol='EURUSD', comment='test buy', external_id='')
        """
        self.logger.info(f"close [{position}]")
        for _ in range(5):
            deviation = dev
            if position.type == mt5.ORDER_TYPE_BUY:
                price = mt5.symbol_info_tick(position.symbol).bid
                order_type = mt5.ORDER_TYPE_SELL
            elif position.type == mt5.ORDER_TYPE_SELL:
                price = mt5.symbol_info_tick(position.symbol).ask
                order_type = mt5.ORDER_TYPE_BUY
            else:
                raise Exception("order type unsupported")

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position.identifier,
                "price": price,
                "deviation": deviation,
                "magic": position.magic,
                "comment": "python script close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.warning("Order error, order[{}]".format(result))
            return result

    def get_positions(self, symbol=None, magic=-1):
        """
        >>> adapter = MT5Adapter(DEMO_LOGIN,DEMO_PASS,DEMO_SERVER)
        >>> _ = adapter.close_all("XAUUSD")
        >>> adapter.buy("XAUUSD",123,0.01,100,300,0,"hello")
        OrderSendResult(retcode=10009, ...
        >>> len(adapter.get_positions(symbol="XAUUSD"))
        1
        >>> _ = adapter.close_all("XAUUSD")

        """

        if symbol is None:
            self.logger.debug(f"get_positions, symbol[{symbol}]")
            pos_with_symbol = list(mt5.positions_get())
        else:
            self.logger.debug(f"get_position, all symbols")
            pos_with_symbol = list(mt5.positions_get(symbol=symbol))

        if magic >= 0:
            pos_with_symbol = [x for x in pos_with_symbol if x.magic == magic]

        return pos_with_symbol

    def close_all(self, symbol=None, magic=-1, dev=20):
        """
        >>> adapter = MT5Adapter()
        >>> _ = adapter.buy('XAUUSD',123,0.01,100,200,20,'test')
        >>> r = adapter.close_all()
        >>> adapter.get_positions()
        []


        # :param symbol:
        # TradePosition(ticket=559932706, time=1585680773, time_msc=1585680773363, time_update=1585680773, time_update_msc=1585680773363, type=0, magic=234000, identifier=559932706, reason=3, volume=0.01, price_open=1.10124, sl=1.1002399999999999, tp=1.10324, price_current=1.10246, swap=0.0, profit=1.22, symbol='EURUSD', comment='test buy', external_id='')
        # """

        self.logger.debug(f"close_all, symbols[{symbol}]")
        positions = self.get_positions(symbol=symbol, magic=magic)
        if positions is None:
            self.logger.debug(f"close_all, no position found, symbols[{symbol}]")
            return []
        elif len(positions) > 0:
            result = []
            for position in positions:
                result.append(self.close(position, dev))
                self.logger.debug(f"close_all, close position[{position}]")
            return result
        return []

    def sell(self, symbol, magic, lot, sl_point, tp_point, deviation, comment):
        """
        >>> adapter = MT5Adapter()
        >>> _ = adapter.close_all("XAUUSD")
        >>> adapter.sell('XAUUSD',123,0.01,100,200,20,"test sell")
        OrderSendResult(retcode=10009, ...
        >>> adapter.close_all()
        [OrderSendResult(retcode=10009, ...

        :param id:
        :param lot:
        :param sl_point:
        :param tp_point:
        :param deviation:
        :param comment:
        :return:
        """

        self.logger.debug(f"sell, symbols[{symbol}] magic[{magic}] lot[{lot}] sl[{sl_point}] tp[{tp_point}]")

        point = mt5.symbol_info(symbol).point
        price = mt5.symbol_info_tick(symbol).bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": price + sl_point * point,
            "tp": price - tp_point * point,
            "deviation": deviation,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode == 10009:
            self.logger.debug(f"sell, sell success[{result}]")
        else:
            self.logger.warning(f"sell, sell error[{result}]")
        return result

    def buy(self, symbol, magic, lot, sl_point, tp_point, deviation, comment):
        """
        >>> adapter = MT5Adapter()
        >>> _ = adapter.close_all("XAUUSD")
        >>> adapter.buy('XAUUSD',123,0.01,100,200,20,"test buy")
        OrderSendResult(retcode=10009, ...
        >>> adapter.close_all()
        [OrderSendResult(retcode=10009, ...


        # :param id:
        # :param lot:
        # :param sl_point:
        # :param tp_point:
        # :param deviation:
        # :param comment:
        # :return:
        # """

        self.logger.debug(f"buy, symbols[{symbol}] magic[{magic}] lot[{lot}] sl[{sl_point}] tp[{tp_point}]")

        point = mt5.symbol_info(symbol).point
        price = mt5.symbol_info_tick(symbol).ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": price - sl_point * point,
            "tp": price + tp_point * point,
            "deviation": deviation,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        result = mt5.order_send(request)

        if result.retcode == 10009:
            self.logger.debug(f"buy, buy success[{result}]")
        else:
            self.logger.warning(f"buy, buy error[{result}]")

        return result

    def get_last_trade(self, magic=-1):
        from_date = datetime.now() - timedelta(days=1)
        to_date = datetime.now() + timedelta(days=1)
        d = mt5.history_deals_get(from_date, to_date)
        if magic >= 0:
            d = [x for x in d if x.magic == magic]
        if len(d) == 0:
            return None
        return d[-1]

    # endregion trade

# if __name__ == '__main__':
#     import doctest

#     doctest.testmod(optionflags=doctest.ELLIPSIS)
