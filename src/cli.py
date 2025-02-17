from src.data_loader import DataLoader
from src.signal_generator import SignalGenerator
from src.risk_manager import RiskManager
import click
import numpy as np

@click.command()
@click.option('--ticker', required=True, help='标的代码，例如：QQQ, NVDA')
@click.option('--no-color', is_flag=True, help='禁用彩色输出')
def main(ticker, no_color):
    """期权交易决策命令行接口"""
    # 添加颜色控制
    if no_color:
        click.echo = lambda x, **kw: click.secho(x, **kw)
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
        
    # 生成策略
    top_strategies = sg.generate_top_strategies()
    
    if not top_strategies:
        print("\n💡 操作建议：")
        print("1. 执行周期权扫描命令：python -m src.cli --ticker TSLA --weekly")
        print("2. 调整风险参数：编辑 config/config.yaml 中的 iv_threshold")
        print("3. 查看详细数据报告：python -m src.report --ticker TSLA")
        return
    
    print("\n🏆 推荐策略 TOP3:")
    for i, strategy in enumerate(top_strategies, 1):
        print(f"\n#{i} {strategy['type'].upper()} [评分: {strategy['score']:.1f}]")
        print(f"行权价: {strategy.get('strike', 'N/A')}")
        print(f"波动率评分: {strategy['details']['iv_rank']}%")
        print(f"流动性评分: {strategy['details']['liquidity']}手")

    print("\n📈 策略生成详情：")
    for i, s in enumerate(top_strategies, 1):
        print(f"{i}. {s['type'].upper()}@{s.get('strike', 'N/A')}")
        print(f"   得分：{s['score']:.1f} | 波动率：{s['details']['iv_rank']}%")
        print(f"   风险：{s.get('risk', '未评估')} | 流动性：{s['details']['liquidity']}手")

if __name__ == '__main__':
    main()