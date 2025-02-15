import pandas as pd

class RiskManager:
    def __init__(self, config):
        self.config = config
        
    def check_greeks(self, portfolio_greeks):
        """希腊值风险检查"""
        return (
            abs(portfolio_greeks['delta']) < 0.5 and
            portfolio_greeks['vega'] < self.config['max_vega'] and
            portfolio_greeks['gamma'] < 0.1
        )
    
    def check_liquidity(self, contract):
        """合约流动性验证"""
        spread = contract['ask'] - contract['bid']
        spread_ratio = spread / contract['lastPrice']
        return (
            contract['volume'] > self.config['min_volume'] and
            spread_ratio < self.config['max_spread_ratio']
        )
    
    def check_event_risk(self, earnings_dates):
        """事件风险检查"""
        next_5_days = pd.Timestamp.now() + pd.DateOffset(days=5)
        return any(date <= next_5_days for date in earnings_dates)