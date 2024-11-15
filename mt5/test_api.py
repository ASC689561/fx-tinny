import pytest
import pandas as pd
import numpy as np
from api import app
from fastapi.testclient import TestClient
import pytest
import pandas as pd


mt5_client = TestClient(app)


@pytest.fixture()
def client():
    res = mt5_client.get('/account/login')
    assert res.json()['success'] == True
    yield mt5_client


def test_login(client):
    response = client.get("/account/login")
    assert response.json()['success'] == True


def test_info(client):
    response = client.get("/account/info")
    assert 'login' in response.json()


def test_test_candle(client):
    res = client.post('/candle/last', json={
        "symbol": "XAUUSD",
        "start": 0,
        "timeframe": "1h",
        "count": 1000
    })
    obj = res.json()
    assert len(obj) == 1000

    df = pd.DataFrame(obj, columns=['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])
    df['time'] = pd.to_datetime(df['time'], unit='s')
    assert len(df) == 1000


def test_get_deals(client):
    res = client.post('/deals/all', json={
        "symbol": "XAUUSD"
    })
    obj = res.json()
    assert len(obj) > 0
    columns = "ticket,order,time,time_msc,type,entry,magic,position_id,reason,volume,price,commission,swap,profit,fee,symbol,comment,external_id".split(',')
    df = pd.DataFrame(obj, columns=columns)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    assert len(df) == 1000
