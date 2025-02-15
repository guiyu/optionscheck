import numpy as np
import pandas as pd

def calculate_iv_rank(ticker, window=252):
    """计算隐含波动率百分位"""
    data = yf.Ticker(ticker).history(period="1y")['Close']
    log_returns = np.log(data/data.shift(1)).dropna()
    hist_vol = log_returns.rolling(window).std() * np.sqrt(252)
    
    current_iv = data.option_chain().calls.impliedVolatility.mean()
    return np.mean(current_iv > hist_vol.quantile([0.25, 0.5, 0.75]))