class PortfolioRebalancer:
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.risk_model = RiskModel()
        
    def auto_rebalance(self):
        """自动再平衡逻辑"""
        current_risk = self.risk_model.analyze(self.portfolio)
        target_allocation = self._calculate_target_allocation()
        
        while not self._meets_risk_target(current_risk):
            adjustments = self._generate_adjustments(target_allocation)
            self._execute_trades(adjustments)
            current_risk = self.risk_model.analyze(self.portfolio)
            
    def _generate_adjustments(self, target):
        """生成调仓指令"""
        return [
            {'action': 'reduce', 'symbol': 'TSLA', 'qty': 100},
            {'action': 'add', 'symbol': 'SPY', 'qty': 50}
        ] 