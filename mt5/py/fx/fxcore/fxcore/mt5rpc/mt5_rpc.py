import pandas as pd
import logging
from cow.redis_rpc_ import Client


class MT5Rpc:

    def __init__(self, redis_client, queue_name='/fx/rpc'):
        self.redis_client = redis_client
        self.queue_name = queue_name
        self.logger = logging.getLogger('redisrpc')
        self.rpc_client = Client(self.redis_client, self.queue_name, timeout=60, transport='pickle')

    def get_test_instance():
        import redis
        c = redis.Redis.from_url('redis://:dsteam123@airflow-redis.workspace:6379')
        assert c.ping(), True
        client = MT5Rpc(redis_client=c)
        # client.login(5251919, '12345678@', 'ICMarketsSC-MT5')
        return client

    def login(self, login, password, server):
        """_summary_

        Args:
            login (_type_): _description_
            password (_type_): _description_
            server (_type_): _description_

        Returns:
            _type_: _description_

        >>> c = MT5Rpc.get_test_instance()
        >>> s= c.login(5251919, '12345678@', 'ICMarketsSC-MT5')
        >>> assert 'login' in s
        """
        assert isinstance(login, int)
        assert isinstance(password, str) and len(password) > 0
        assert isinstance(server, str) and len(server) > 0
        return self.rpc_client.login(login, password, server)

    def get_info(self):
        return self.rpc_client.get_info()

    def buy(self, symbol, magic, lot, sl_point, tp_point, deviation, comment):
        assert len(symbol.strip()) > 0, "symbol cannot empty"
        assert isinstance(lot, float) or isinstance(lot, int)
        assert isinstance(sl_point, int)
        assert isinstance(tp_point, int)
        assert isinstance(deviation, int)
        assert isinstance(comment, str)

        return self.rpc_client.buy(symbol, magic, lot, sl_point, tp_point, deviation, comment)

    def sell(self, symbol, magic, lot, sl_point, tp_point, deviation, comment):
        assert len(symbol.strip()) > 0, "symbol cannot empty"
        assert isinstance(lot, float) or isinstance(lot, int)
        assert isinstance(sl_point, int)
        assert isinstance(tp_point, int)
        assert isinstance(deviation, int)
        assert isinstance(comment, str)

        return self.rpc_client.sell(symbol, magic, lot, sl_point, tp_point, deviation, comment)

    def close(self, symbol, magic, deviation):
        assert len(symbol.strip()) > 0, "symbol cannot empty"
        assert magic > 0, "magic invalid"
        return self.rpc_client.close(symbol, magic, deviation)

    def get_last_trade(self,  magic):
        return self.rpc_client.get_last_trade(magic)

    def get_candle_from_date(self, symbol, start_timestamp):
        df = self.rpc_client.get_candle_from_date(symbol, start_timestamp)
        return df

    def get_candle_from_pos(self, symbol, timeframe, start, end):
        df = self.rpc_client.get_candle_from_pos(symbol, timeframe, start, end)
        return df

    def get_deals(self, from_date, to_date=None, group=None):
        df = self.rpc_client.get_deals(from_date, to_date, group)
        return df

    def get_candle_from_pos(self, symbol, timeframe, start, end, truncate_first=True):
        df = self.rpc_client.get_candle_from_pos(symbol, timeframe, start, end, truncate_first)
        return df

    def get_new_data(self, symbol, last_time, timeframe="1h", batch_size=10000, max_bar=300000, truncate_first=True):
        """get new data from mt5

        Args:
            symbol (string): symbol, eg: XAUUSD, EURUSD
            timeframe (string): timeframe, 1h, 1m, 5m, Default to 1h
            last_time (string): last_time need to get data, eg: 2020-01-01, or 1577836800, or 0
            batch_size (int, optional): batch size. Defaults to 10000.
            max_bar (int, optional): max bar to get. Defaults to None.
            min_time (string, optional): last date to get, eg: 2018-01-01. Defaults to None.
        Returns:
            dataframe: 
        >>> c = MT5Rpc.get_test_instance()
        >>> _=c.login(5251919, '12345678@', 'ICMarketsSC-MT5')
        >>> t = pd.to_datetime('2022-03-01').timestamp()
        >>> l = c.get_new_data('XAUUSD',t)
        >>> assert len(l)>0,"data not empty"

        """

        pd_all = pd.DataFrame()
        i = 0
        while True:
            data = self.get_candle_from_pos(symbol, timeframe, i, batch_size, truncate_first)

            i += len(data)
            if len(data) == 0:
                if i == 0:
                    logging.warning("cannot get any data from mt5")
                break

            new_data = data[data.time > last_time]

            print(f'data read [{len(new_data)}] last day [{new_data.index.min()}] total [{len(pd_all)}]')

            if len(new_data) == 0 or len(new_data) < len(data):  # không còn dữ liệu mới
                pd_all = pd.concat([pd_all, new_data])
                print('no new data,break', len(new_data))
                return pd_all

            if len(pd_all) > max_bar:
                print('reach limit data,break', len(pd_all))
                return pd_all

            pd_all = pd.concat([pd_all, data])

            # pd_all['week'] = pd_all.index.year.astype(str) + "-" + pd_all.index.strftime('%W')
            # count_week = pd_all.groupby('week')['time'].count()
            # for ii in reversed(range(len(count_week))):
            #     if count_week[ii] < 20 and count_week[ii-1] < 20:
            #         valid_data = pd_all[pd_all['week'] >= count_week.index[ii+1]]
            #         return valid_data
        return pd_all


if __name__ == "__main__":
    import doctest
    doctest.testmod()
