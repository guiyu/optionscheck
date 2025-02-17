from src.data_loader import DataLoader
from src.signal_generator import SignalGenerator
from src.risk_manager import RiskManager
import click

@click.command()
@click.option('--ticker', help='股票代码')
@click.option('--debug', is_flag=True, help='调试模式')
def main(ticker, debug):
    """期权交易决策命令行接口"""
    dl = DataLoader(ticker)
    sg = SignalGenerator(dl)
    rm = RiskManager(dl.config['strategy'])
    
    print(f"\n🔍 正在分析 {ticker}...")
    
    # 获取必要数据
    earnings_dates = dl.get_earnings_dates()
    option_chain = dl.fetch_option_chain()
    
    # 风险检查
    if rm.check_event_risk(earnings_dates):
        print("⚠️ 存在近期财报事件风险")
        return
        
    # 生成信号
    signals = sg.generate_vertical_spread_signal()
    
    if signals:
        print("\n🏆 最佳交易机会排行：")
        for i, signal in enumerate(signals, 1):
            print(f"""\n#{i} {signal['name']}
    💡 策略类型: {signal['strategy_type']}
    📅 到期日: {signal['expiration']}
    ⚖️ 行权价范围: {signal['strikes'][0]} - {signal['strikes'][1]}
    🎯 预期胜率: {signal['probability']}%
    💰 最大收益: {signal['max_return']}%""")
    else:
        print("\n⚠️ 未找到符合要求的交易机会")

if __name__ == '__main__':
    main()