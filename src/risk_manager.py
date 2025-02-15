class RiskManager:
    def __init__(self, portfolio):
        self.portfolio = portfolio
        
    def check_greek_exposure(self):
        """检查希腊值风险敞口"""
        greeks = calculate_portfolio_greeks(self.portfolio)
        return {
            'vega_ok': greeks['vega'] < config.max_vega,
            'theta_ok': greeks['theta'] > -0.1,
            'delta_ok': abs(greeks['delta']) < 0.5
        }
    
    def liquidity_check(self, contract):
        """合约流动性验证"""
        spread_ratio = (contract.ask - contract.bid) / contract.lastPrice
        return (contract.volume > config.min_volume) and (spread_ratio < config.max_spread_ratio)