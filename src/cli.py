from src.data_loader import DataLoader
from src.signal_generator import SignalGenerator
from src.risk_manager import RiskManager
import click

@click.command()
@click.option('--ticker', prompt='请输入标的代码', help='例如：QQQ, NVDA')
def main(ticker):
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
    signal = sg.generate_vertical_spread_signal()
    
    if signal and rm.check_greeks(signal['greeks']):
        print("\n🎯 交易信号生成成功")
        print(f"策略类型: {signal['strategy_type']}")
        print(f"建议行权价: {signal['strikes']}")
        print(f"预期胜率: {signal['probability']}%")
    else:
        print("\n❌ 未找到有效交易机会")

if __name__ == '__main__':
    main()