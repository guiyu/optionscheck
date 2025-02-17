from src.data_loader import DataLoader
from src.signal_generator import SignalGenerator
from src.risk_manager import RiskManager
import pandas as pd
from unittest import mock

def test_full_trading_flow():
    # 在测试开始时添加
    with mock.patch('src.data_loader.DataLoader._fetch_raw_option_chain') as mock_fetch:
        mock_fetch.return_value = pd.DataFrame({
            'strike': [400, 410],
            'bid': [1.2, 1.1],
            'ask': [1.3, 1.2],
            'type': ['call', 'put'],
            'days_to_expire': [30, 45]
        })
        # 初始化模块
        dl = DataLoader('SPY')
        sg = SignalGenerator(dl)
        rm = RiskManager(dl.config)
        
        # 生成策略
        strategies = sg.generate_top_strategies()
        assert strategies, "未生成有效策略"
        
        # 风险校验
        valid_strategies = [s for s in strategies if rm.validate_strategy(s)]
        assert len(valid_strategies) >= 1, "所有策略均未通过风控"
        
        # 选择最佳策略
        best = valid_strategies[0]
        assert best['score'] == max(s['score'] for s in valid_strategies)
        
        # 验证策略参数
        if best['type'] == 'sell_put':
            assert 0.2 <= best['greeks']['delta'] <= 0.3
        else:
            strikes = best['strikes']
            assert strikes[0] > strikes[1], "价差策略行权价顺序错误" 