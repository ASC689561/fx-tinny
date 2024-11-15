from pydantic import BaseModel, Field
from typing import Optional
from pydantic import BaseModel


class GetLastCandleRequest(BaseModel):
    symbol: Optional[str] = Field("XAUUSD", examples=["XAUUSD"])
    start: Optional[int] = Field(0, examples=[0, 100, 1000])
    timeframe: Optional[str] = Field("", examples=["1h"])
    count: Optional[int] = Field(100, examples=[100, 1000])


class BuyRequest(BaseModel):
    symbol: Optional[str] = Field("XAUUSD", examples=["XAUUSD"])
    magic: Optional[int] = Field(0, examples=[0])
    lot: Optional[float] = Field(0.01, examples=[0.01, 0.02])
    sl_point: Optional[int] = Field(200, examples=[200, 300])
    tp_point: Optional[int] = Field(200, examples=[200, 300])
    deviation: Optional[int] = Field(200, examples=[200, 300])
    comment: Optional[str] = Field("Buy 123", examples=["NO COMMENT"])


class SellRequest(BaseModel):
    symbol: Optional[str] = Field("XAUUSD", examples=["XAUUSD"])
    magic: Optional[int] = Field(0, examples=[0])
    lot: Optional[float] = Field(0.01, examples=[0.01, 0.02])
    sl_point: Optional[int] = Field(200, examples=[200, 300])
    tp_point: Optional[int] = Field(200, examples=[200, 300])
    deviation: Optional[int] = Field(200, examples=[200, 300])
    comment: Optional[str] = Field("Sell 123", examples=["NO COMMENT"])


class CloseRequest(BaseModel):
    symbol: Optional[str] = Field("XAUUSD", examples=["XAUUSD"])
    magic: Optional[int] = Field(0, examples=[0])
    deviation: Optional[int] = Field(200, examples=[200, 300])


class GetLastDealsHistoryRequest(BaseModel):
    symbol: Optional[str] = Field("XAUUSD", examples=["XAUUSD"])
