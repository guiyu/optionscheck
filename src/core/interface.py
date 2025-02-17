class TradingSystem:
    def __init__(self, ticker):
        self.ticker = ticker
        self.data_loader = DataLoader(ticker)
        self.signal_generator = SignalGenerator(self.data_loader)
        self.risk_manager = RiskManager(self.data_loader.config)
        
    def get_recommendations(self):
        """获取合规交易建议"""
        strategies = self.signal_generator.generate_top_strategies()
        valid_strategies = [s for s in strategies if self.risk_manager.validate_strategy(s)]
        return sorted(valid_strategies, key=lambda x: x['score'], reverse=True) 