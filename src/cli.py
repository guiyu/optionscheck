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
        
    # 生成策略
    top_strategies = sg.generate_top_strategies()
    
    if not top_strategies:
        print("\n❌ 未找到有效交易机会")
        return
    
    print("\n🏆 推荐策略 TOP3:")
    for i, strategy in enumerate(top_strategies, 1):
        print(f"\n#{i} {strategy['type'].upper()} [综合胜率: {strategy['score']:.1f}%]")
        print(f"行权价组合: {strategy.get('strike', strategy.get('strikes'))}")
        print("📊 关键指标:")
        print(f"  IV百分位: {strategy['details']['iv_rank']}%")
        print(f"  技术评分: {strategy['details']['technical']}/15")
        print(f"  时间价值比: {strategy['details']['greeks']['theta_delta_ratio']:.2f}")
        print(f"  合约流动性: {strategy['details']['liquidity']}手")
        print(f"  行业相关性: {dl.get_sector_data()['sector_correlation']:.2f}")

if __name__ == '__main__':
    main()