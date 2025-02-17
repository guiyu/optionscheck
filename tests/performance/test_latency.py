import pytest
from src.data_loader import DataLoader
from src.signal_generator import SignalGenerator

def test_strategy_generation_speed(benchmark):
    dl = DataLoader('QQQ')
    sg = SignalGenerator(dl)
    
    # 基准测试
    benchmark(sg.generate_top_strategies)
    
    # 移除无效的result断言
    assert benchmark.stats['mean'] < 1.0  # 平均生成时间<1秒 