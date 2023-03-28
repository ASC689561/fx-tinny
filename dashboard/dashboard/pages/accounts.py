from contextlib import suppress
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from pages.mt5_rpc import MT5Rpc
import redis
client = redis.Redis.from_url('redis://redis:6379')
rpc = MT5Rpc(redis_client=client,queue_name='/fx/rpc/51021509')

if st.button("Info"):
    st.write(rpc.get_info())

if st.button("Candle from pos"):
    data = rpc.get_candle_from_pos('XAUUSD','1m',0,100)
    st.write(data)

if st.checkbox("Auto Get Data"):
    count = st_autorefresh(interval=10000, limit=1000)
    data = rpc.get_candle_from_pos('XAUUSD','1m',0,10)
    data.sort_values('time',ascending=False,inplace=True)
    st.write(data)

if st.button("Get Trades"):
    data = rpc.get_deals(pd.to_datetime("2022-01-01").timestamp())
    st.write(data)


