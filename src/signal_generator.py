from src.utils.volatility import calculate_iv_rank
from src.utils.greeks import calculate_greeks
from src.data_loader import DataLoader
import pandas as pd
import numpy as np
from scipy.stats import norm

class SignalGenerator:
    def __init__(self, data_loader):
        self.dl = data_loader
        self.config = data_loader.config
        self.spot_price = None
    
    def generate_vertical_spread_signal(self):
        """生成垂直价差信号"""
        # 获取基础数据
        df = self.dl.get_real_time_data()
        if df.empty:
            return None
            
        self.spot_price = df['Close'].iloc[-1]
        earnings_dates = self.dl.get_earnings_dates()
        
        # 获取期权链数据
        option_chain = self.dl.fetch_option_chain()
        if option_chain.empty:
            print("无法获取期权链数据")
            return None
        
        # 在访问字段前检查列是否存在
        required_cols = ['type', 'strike', 'impliedVolatility', 'days_to_expire']
        if not all(col in option_chain.columns for col in required_cols):
            print("期权链数据缺失关键列")
            return None
        
        # 检查财报风险
        if self._has_earnings_risk(earnings_dates):
            return None
            
        # 计算波动率指标
        iv_rank = calculate_iv_rank(self.dl.ticker)
        if iv_rank > self.config['strategy']['iv_percentile_threshold']:
            return None
            
        # 选择行权价
        call_strike = self._select_strike_by_delta('call', 0.3)
        put_strike = self._select_strike_by_delta('put', -0.3)
        
        if call_strike is None or put_strike is None:
            print("无法选择合适的行权价")
            return None
        
        # 获取合约信息
        call_contract = option_chain[
            (option_chain['strike'] == call_strike) &
            (option_chain['type'] == 'call')
        ]
        
        put_contract = option_chain[
            (option_chain['strike'] == put_strike) &
            (option_chain['type'] == 'put')
        ]
        
        if call_contract.empty or put_contract.empty:
            print("无法获取合约信息")
            return None
            
        # 计算概率
        prob = self._calculate_probability(call_strike)
        
        return {
            'ticker': self.dl.ticker,
            'strategy': 'BullCallSpread',
            'strikes': (call_strike, put_strike),
            'probability': round(prob, 2),
            'entry_price': self.spot_price,
            'expiration': call_contract['expiration'].iloc[0]
        }
    
    def _has_earnings_risk(self, dates):
        """检查未来5天内是否有财报"""
        next_5d = pd.Timestamp.now() + pd.DateOffset(days=5)
        return any(d <= next_5d for d in dates)
    
    def _select_strike_by_delta(self, option_type, target_delta):
        """基于Delta选择行权价（修正版）"""
        option_chain = self.dl.fetch_option_chain()
        if option_chain.empty:
            return None
        
        # 筛选指定类型的期权
        chain = option_chain[option_chain['type'] == option_type]
        
        # 计算Delta值
        deltas = []
        for _, row in chain.iterrows():
            g = calculate_greeks(
                option_type=row['type'],
                strike=row['strike'],
                spot=self.spot_price,
                t=row['days_to_expire'],
                iv=row['impliedVolatility']
            )
            deltas.append(g['delta'])
        
        # 找到最接近目标Delta的行权价
        chain = chain.assign(delta=deltas)
        closest_idx = np.abs(chain['delta'] - target_delta).argmin()
        return chain.iloc[closest_idx]['strike']
    
    def _calculate_probability(self, strike):
        """计算触及概率"""
        df = self.dl.get_real_time_data()  # 获取数据
        if df.empty:
            return 0
            
        log_returns = np.log(df['Close']/df['Close'].shift(1)).dropna()
        mu = log_returns.mean() * 252
        sigma = log_returns.std() * np.sqrt(252)
        
        t = 30/365
        d2 = (np.log(self.spot_price/strike) + 
             (mu - 0.5*sigma**2)*t) / (sigma*np.sqrt(t))
        return norm.cdf(d2)