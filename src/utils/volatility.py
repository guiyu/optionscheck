import yfinance as yf
import numpy as np
import pandas as pd

def calculate_iv_rank(ticker):
    """计算波动率排名"""
    try:
        data = yf.Ticker(ticker).history(period="1y")['Close']
        returns = np.log(data / data.shift(1)).dropna()
        hist_vol = returns.std() * np.sqrt(252)
        return hist_vol
    except Exception as e:
        print(f"波动率计算失败: {str(e)}")
        return 0