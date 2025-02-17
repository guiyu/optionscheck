def test_cli_workflow(capsys):
    from src.cli import main
    from unittest import mock
    
    # 正确模拟完整命令行参数
    with mock.patch('sys.argv', ['cli.py', '--ticker', 'NVDA']):
        try:
            main()
        except SystemExit:  # 捕获正常退出
            pass
        
    # 验证输出
    captured = capsys.readouterr()
    assert "推荐策略 TOP3" in captured.out
    assert "NVDA" in captured.out
    assert "SELL_PUT" in captured.out  # 更精确的断言 