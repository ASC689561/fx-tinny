import rpyc
conn = rpyc.classic.connect(host="localhost",port=5678)
def login(login,passwd,server):
    import MetaTrader5 as mt5
     
    mt5.initialize(login=login, password=passwd, server=server)
    return mt5.account_info()._asdict()


# fn = conn.teleport(login)

# print(fn(<YOUR LOGIN>,"fX7dDCKu","ICMarketsSC-Demo"))


def get_data( ):
    import MetaTrader5 as mt5
     
    return mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M1, 0, 1000)
   

fn = conn.teleport(get_data)
print(fn())
