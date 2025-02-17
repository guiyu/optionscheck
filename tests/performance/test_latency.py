def test_strategy_generation_speed(benchmark):
    dl = DataLoader('QQQ')
    sg = SignalGenerator(dl)
    
    # 基准测试
    result = benchmark(sg.generate_top_strategies)
    
    assert len(result) <= 3
    assert benchmark.stats['mean'] < 1.0  # 平均生成时间<1秒 