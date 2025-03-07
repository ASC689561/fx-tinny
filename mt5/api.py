import logging
import threading
import time
import uvicorn
import traceback
from datetime import datetime, timedelta
from models import (
    BuyRequest,
    CloseRequest,
    SellRequest,
    GetLastCandleRequest,
    GetLastDealsHistoryRequest,
)
import socket
import json
import logging
import os
from contextlib import asynccontextmanager

log_file_path = "./fxscript.log"

logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.info("Starting api")


while True:
    try:
        from fastapi import FastAPI

        logging.warning("wait fastapi done")
        break
    except:
        logging.warning("waiting install fastapi")
        import time

        time.sleep(5)

while True:
    try:
        import MetaTrader5 as mt5

        logging.warning("waiting MetaTrader5 done")
        break
    except:
        logging.warning("waiting install MetaTrader5")
        import time

        time.sleep(5)

path = "/root/.wine/drive_c/Program Files/MetaTrader 5 IC Markets Global/terminal64.exe"

while not os.path.exists(path):
    logging.warning(f"Waiting for file: {path}")
    time.sleep(5)  # Đợi 5 giây trước khi kiểm tra lại
logging.warning(f"Waiting  {path} done")


tf_dic = {}
for v in dir(mt5):
    if v.startswith("TIMEFRAME_"):
        tf = v.replace("TIMEFRAME_", "")
        symbol, num = tf[0], tf[1:]
        tf_dic[num + symbol.lower()] = int(getattr(mt5, v))

for v in range(10):
    logging.info(f"Starting mt5")

    success = mt5.initialize(
        path,
        login=int(os.environ["ACCOUNT"]),
        password=os.environ["PASSWORD"],
        server=os.environ["SERVER"],
    )
    if not success:
        logging.warning(f"Cannot init mt5: {mt5.last_error()}")
        time.sleep(10)
        continue
    else:
        logging.info(f"Starting mt5 done")
        break

# # init kazzoo
# kazoo_client = KazooClient()
# logging.warning(f"Init ZOOKEEPER: {os.environ['ZOOKEEPER']}")
# conn_retry_policy = KazooRetry(max_tries=-1, delay=0.1, max_delay=4, ignore_expire=True)
# cmd_retry_policy = KazooRetry(max_tries=-1, delay=0.3, backoff=1, max_delay=4, ignore_expire=True)
# client = KazooClient(hosts=os.environ['ZOOKEEPER'], connection_retry=conn_retry_policy, command_retry=cmd_retry_policy)
# for _ in range(3):
#     try:
#         client.start()
#         break
#     except:
#         logging.warning(f"error when connect zk: {os.environ['ZOOKEEPER']}, {traceback.format_exc()}")


# def thread_function(name):
#     node_path = f"/account/{os.environ['ACCOUNT']}/running"
#     while True:
#         try:
#             if not client.exists(node_path):
#                 client.create(node_path, ephemeral=True)

#                 client.set(node_path, json.dumps({
#                     'service': 'http://' + socket.gethostbyname(socket.gethostname())+":8000",
#                     'wine': socket.gethostbyname(socket.gethostname())+":8080",
#                     **{x: os.environ[x] for x in ['ACCOUNT', 'PASSWORD', 'SERVER']}
#                 }, indent=3).encode())
#                 logging.warning(f"Create node: {node_path}")
#         except:
#             logging.exception("Error when create running node", exc_info=True)

#         import time
#         time.sleep(5)


# live_thread = threading.Thread(target=thread_function, args=(1,))
# live_thread.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # node_path = f"/account/{os.environ['ACCOUNT']}/running"
    # client.delete(node_path)


app = FastAPI(lifespan=lifespan)


@app.get("/healthz")
def healthz():
    if "login" in mt5.account_info()._asdict():
        return "ok"
    raise Exception(str(mt5.last_error()))


@app.get("/")
def read_root():
    try:
        res = mt5.account_info()._asdict()
        return res
    except:
        return mt5.last_error()


@app.post("/candle/last")
def candle_last(inp: GetLastCandleRequest):
    try:
        timeframe = tf_dic.get(inp.timeframe, None)
        assert timeframe, f"timeframe invalid: {inp.timeframe}"
        r = mt5.copy_rates_from_pos(inp.symbol, timeframe, inp.start, inp.count)
        if inp.start == 0:
            return r.tolist()[:-1]
        return r.tolist()
    except:
        raise RuntimeError(mt5.last_error())


@app.post("/deals/all")
def deals_all(inp: GetLastDealsHistoryRequest):
    """
    https://pastebin.com/raw/9QgW5yYi
    """
    try:
        from_date = datetime(2023, 1, 1)
        to_date = datetime.now() + timedelta(days=3)
        if inp.symbol:
            r = mt5.history_deals_get(from_date, to_date, group=inp.symbol)
        else:
            r = mt5.history_deals_get(from_date, to_date)
        return r
    except:
        raise RuntimeError(mt5.last_error())


@app.get("/account/login")
def account_login():
    success = mt5.initialize(
        path="/config/.winecfg_mt5/drive_c/Program Files/MetaTrader 5 IC Markets Global/terminal64.exe",
        login=int(os.environ["ACCOUNT"]),
        password=os.environ["PASSWORD"],
        server=os.environ["SERVER"],
    )
    if not success:
        return {"success": success, "last_error": mt5.last_error()}
    return {"success": success}


@app.get("/account/info")
def account_info():
    try:
        res = mt5.account_info()._asdict()
        return res
    except:
        return mt5.last_error()


@app.post("/trade/buy")
def trade_buy(request: BuyRequest):
    close_all(request.symbol, request.magic, request.deviation)

    try:
        symbol = request.symbol

        point = mt5.symbol_info(symbol).point
        price = mt5.symbol_info_tick(symbol).ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": price - point * request.sl_point,
            "tp": price + point * request.tp_point,
            "deviation": request.deviation,
            "magic": request.magic,
            "comment": request.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # send a trading request
        result = mt5.order_send(request)
        return result._asdict()
    except:
        return mt5.last_error()


@app.post("/trade/sell")
def trade_sell(request: SellRequest):
    close_all(request.symbol, request.magic, request.deviation)
    try:
        symbol = request.symbol

        point = mt5.symbol_info(symbol).point
        price = mt5.symbol_info_tick(symbol).bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.lot,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": price + point * request.sl_point,
            "tp": price - point * request.tp_point,
            "deviation": request.deviation,
            "magic": request.magic,
            "comment": request.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # send a trading request
        result = mt5.order_send(request)
        return result._asdict()
    except:
        return mt5.last_error()


def close_all(symbol, magic, deviation):
    positions = mt5.positions_get(symbol=symbol)
    # (TradePosition(ticket=658189343, time=1716288623, time_msc=1716288623438, time_update=1716288623, time_update_msc=1716288623438, type=0, magic=0, identifier=
    # 658189343, reason=3, volume=0.01, price_open=2420.07, sl=2418.07, tp=2422.07, price_current=2419.91, swap=0.0, profit=-0.16, symbol='XAUUSD', comment='NO COM
    # MENT', external_id=''),)
    arr = []
    for p in positions:
        if p.magic == magic:
            arr.append(p)

    cur_tick = mt5.symbol_info_tick(symbol)
    res = []
    for p in arr:
        if p.type == mt5.ORDER_TYPE_BUY:
            price = cur_tick.bid
            order_type = mt5.ORDER_TYPE_SELL
        elif p.type == mt5.ORDER_TYPE_SELL:
            price = cur_tick.ask
            order_type = mt5.ORDER_TYPE_BUY
        else:
            raise Exception("order type unsupported")
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": p.volume,
            "type": order_type,
            "position": p.identifier,
            "price": price,
            "deviation": deviation,
            "magic": p.magic,
            "comment": "python script close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        tmp = mt5.order_send(request)
        res.append(tmp)
    return res


@app.post("/trade/close")
def trade_close(request: CloseRequest):
    try:
        return close_all(request.symbol, request.magic, request.deviation)
    except:
        return mt5.last_error()


if __name__ == "__main__":
    uvicorn.run("api:app", port=8000, host="0.0.0.0", reload=False, log_level="debug")


# uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4 --reload --reload-include *.yml"
