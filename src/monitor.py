import json
from websocket import create_connection
from src.data_loader import DataLoader
from src.signal_generator import SignalGenerator

class RealTimeMonitor:
    def __init__(self, tickers):
        self.tickers = tickers
        self.websocket = None
        
    def start(self):
        """启动实时监控"""
        self.websocket = create_connection("wss://options-data-stream.com")
        while True:
            data = self.websocket.recv()
            self.process_update(json.loads(data))
            
    def process_update(self, data):
        """处理实时数据更新"""
        for ticker in self.tickers:
            if data['symbol'] == ticker:
                self._update_strategy_scores(ticker, data)
                
    def _update_strategy_scores(self, ticker, data):
        """动态更新策略评分"""
        dl = DataLoader(ticker)
        sg = SignalGenerator(dl)
        
        # 获取当前推荐策略
        current_strategies = sg.generate_top_strategies()
        
        # 动态调整权重
        if data['iv_change'] > 0.1:
            self._adjust_weights(ticker, 'iv', 0.25)
            
        # 触发再平衡条件
        if data['price'] < current_strategies[0]['strike'] * 0.95:
            self._trigger_rebalance(ticker) 