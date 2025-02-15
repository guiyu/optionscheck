import click
from .data_loader import DataLoader
from .signal_generator import SignalGenerator

@click.command()
@click.option('--ticker', prompt='请输入标的代码', help='例如：QQQ, NVDA')
def main(ticker):
    """期权交易决策命令行工具"""
    dl = DataLoader(ticker)
    sg = SignalGenerator(dl)
    
    print(f"\n🔍 正在分析 {ticker} ...")
    signal = sg.generate_vertical_spread_signal()
    
    if signal:
        print("\n🎯 交易建议：")
        print(f"策略类型：{signal['strategy_type']}")
        print(f"建仓点位：{signal['entry_price']}")
        print(f"目标行权价：{signal['strikes']}")
        print(f"预期胜率：{signal['probability']}%")
    else:
        print("\n⚠️ 当前未找到符合条件的交易机会")

if __name__ == "__main__":
    main()