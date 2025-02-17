class StrategyBacktester:
    def __init__(self, strategy_config):
        self.strategy = strategy_config
        self.historical_data = {}
        
    def load_data(self, ticker, start_date, end_date):
        """加载历史数据"""
        self.historical_data[ticker] = yf.download(
            ticker, start=start_date, end=end_date, interval='1d')
            
    def run_backtest(self):
        """执行回测"""
        results = []
        for date in self._trading_dates():
            daily_result = self._simulate_day(date)
            results.append(daily_result)
        return pd.DataFrame(results)
        
    def _simulate_day(self, date):
        """模拟单日交易"""
        dl = HistoricalDataLoader(self.historical_data, date)
        sg = SignalGenerator(dl)
        strategies = sg.generate_top_strategies()
        return {
            'date': date,
            'best_strategy': strategies[0] if strategies else None,
            'market_condition': self._get_market_state(date)
        } 