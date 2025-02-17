def test_cli_workflow(capsys):
    from src.cli import main
    import mock
    
    # 模拟用户输入
    with mock.patch('click.prompt', return_value='NVDA'):
        main()
        
    # 验证输出
    captured = capsys.readouterr()
    assert "推荐策略 TOP3" in captured.out
    assert "NVDA" in captured.out
    assert any(word in captured.out for word in ['SELL_PUT', 'BULL_PUT_SPREAD']) 