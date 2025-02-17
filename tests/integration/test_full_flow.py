def test_full_trading_flow():
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