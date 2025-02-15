import yfinance as yf
import requests
import pandas as pd
import yaml
import os
from datetime import datetime

class DataLoader:
    def __init__(self, ticker):
        self.ticker = ticker
        self.config = self._load_config()
        self.ew_api_key = os.getenv("EW_API_KEY")
        
    def _load_config(self):
        with open('config/config.yaml') as f:
            return yaml.safe_load(f)
    
    def get_real_time_data(self, interval='5m'):
        """获取实时行情数据"""
        try:
            stock = yf.Ticker(self.ticker)
            df = stock.history(period='1d', interval=interval)
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            return df.dropna()
        except Exception as e:
            print(f"数据获取失败: {str(e)}")
            return pd.DataFrame()
    
    def fetch_option_chain(self, expiration=None):
        """获取完整期权链数据"""
        try:
            stock = yf.Ticker(self.ticker)
            exps = stock.options
            chains = pd.DataFrame()
            
            for exp in exps:
                opt = stock.option_chain(exp)
                calls = opt.calls.assign(expiration=exp, type='call')
                puts = opt.puts.assign(expiration=exp, type='put')
                chains = pd.concat([chains, calls, puts])
            
            chains['days_to_expire'] = (pd.to_datetime(chains.expiration) - 
                                      pd.Timestamp.now()).dt.days
            return chains
        except Exception as e:
            print(f"期权链获取失败: {str(e)}")
            return pd.DataFrame()
    
    def get_earnings_dates(self):
        """获取财报日历"""
        try:
            headers = {'Authorization': f'Bearer {self.ew_api_key}'}
            params = {'tickers': self.ticker}
            response = requests.get(
                self.config['data_sources']['earnings_whisper']['api_endpoint'],
                headers=headers,
                params=params,
                timeout=5
            )
            dates = [datetime.strptime(d, '%Y-%m-%d') 
                     for d in response.json().get('dates', [])]
            return dates
        except Exception as e:
            print(f"财报日历获取失败: {str(e)}")
            return []