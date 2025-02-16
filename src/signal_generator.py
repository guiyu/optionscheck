from src.utils.volatility import calculate_iv_rank
from src.utils.greeks import calculate_greeks
from src.data_loader import DataLoader
import pandas as pd
import numpy as np
from scipy.stats import norm
import os
import logging

logger = logging.getLogger(__name__)

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
        long_strike = self._select_strike_by_delta('call', 0.3)  # 买入期权
        short_strike = self._select_strike_by_delta('call', 0.2)  # 卖出期权
        
        if long_strike is None or short_strike is None:
            print("无法选择合适的行权价")
            return None
            
        # 确保牛市价差的正确顺序：买入低行权价，卖出高行权价
        if long_strike > short_strike:
            long_strike, short_strike = short_strike, long_strike
        
        # 获取合约信息
        long_contract = option_chain[
            (option_chain['strike'] == long_strike) &
            (option_chain['type'] == 'call')
        ].iloc[0]
        
        short_contract = option_chain[
            (option_chain['strike'] == short_strike) &
            (option_chain['type'] == 'call')
        ].iloc[0]
        
        if long_contract.empty or short_contract.empty:
            print("无法获取合约信息")
            return None
            
        # 计算组合希腊字母
        long_greeks = calculate_greeks(
            'call', 
            long_strike, 
            self.spot_price,
            long_contract['days_to_expire'],
            long_contract['impliedVolatility']
        )
        
        short_greeks = calculate_greeks(
            'call',
            short_strike,
            self.spot_price,
            short_contract['days_to_expire'],
            short_contract['impliedVolatility']
        )
        
        # 合并希腊字母
        portfolio_greeks = {
            'delta': long_greeks['delta'] - short_greeks['delta'],
            'gamma': long_greeks['gamma'] - short_greeks['gamma'],
            'vega': long_greeks['vega'] - short_greeks['vega'],
            'theta': long_greeks['theta'] - short_greeks['theta']
        }
            
        # 计算胜率
        prob = self._calculate_probability(long_strike, short_strike)
        
        # 只有当胜率超过阈值时才返回信号
        min_probability = float(os.getenv('STRATEGY_MIN_PROBABILITY', 60))
        if prob < min_probability:
            logger.debug(f"胜率 {prob:.2f}% 低于最小要求 {min_probability}%")
            return None
        
        return {
            'ticker': self.dl.ticker,
            'strategy_type': 'bull_call_spread',
            'strikes': (long_strike, short_strike),  # 正确的顺序：(低行权价, 高行权价)
            'probability': round(prob, 2),
            'entry_price': self.spot_price,
            'expiration': long_contract['expiration'],
            'greeks': portfolio_greeks
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
            # 确保天数大于0
            days = max(1, row['days_to_expire'])
            # 确保波动率大于0
            iv = max(0.0001, row['impliedVolatility'])
            
            g = calculate_greeks(
                option_type=row['type'],
                strike=row['strike'],
                spot=self.spot_price,
                t=days,
                iv=iv
            )
            deltas.append(g['delta'])
        
        # 找到最接近目标Delta的行权价
        chain = chain.assign(delta=deltas)
        # 过滤掉无效的Delta值
        valid_chain = chain[chain['delta'] != 0]
        if valid_chain.empty:
            return None
            
        closest_idx = np.abs(valid_chain['delta'] - target_delta).argmin()
        return valid_chain.iloc[closest_idx]['strike']
    
    def _calculate_probability(self, long_strike, short_strike):
        """计算牛市价差的获利概率"""
        df = self.dl.get_real_time_data()
        if df.empty:
            return 0
            
        # 计算历史波动率
        log_returns = np.log(df['Close']/df['Close'].shift(1)).dropna()
        sigma = log_returns.std() * np.sqrt(252)
        
        # 使用30天作为目标期限
        t = 30/365
        
        # 计算在到期时股价高于低行权价的概率
        d1_long = (np.log(self.spot_price/long_strike) + 
                  (0.05 + 0.5*sigma**2)*t) / (sigma*np.sqrt(t))
        prob_above_long = norm.cdf(d1_long)
        
        # 计算在到期时股价高于高行权价的概率
        d1_short = (np.log(self.spot_price/short_strike) + 
                   (0.05 + 0.5*sigma**2)*t) / (sigma*np.sqrt(t))
        prob_above_short = norm.cdf(d1_short)
        
        # 牛市价差的最大获利区间是在高行权价以下
        # 胜率 = P(长期价格 > 低行权价) - P(长期价格 > 高行权价)
        probability = (prob_above_long - prob_above_short) * 100
        
        return probability