from src.utils.volatility import calculate_iv_rank
from src.utils.greeks import calculate_greeks
from src.data_loader import DataLoader
from src.risk_manager import RiskManager
import pandas as pd
import numpy as np
from scipy.stats import norm

class SignalGenerator:
    def __init__(self, data_loader):
        self.dl = data_loader
        self.config = data_loader.config
        self.spot_price = data_loader.spot_price
        self.chain = data_loader.fetch_option_chain()
    
    def generate_vertical_spread_signal(self):
        """生成垂直价差信号"""
        # 获取基础数据
        df = self.dl.get_real_time_data()
        if df.empty:
            return None
            
        self.spot_price = df['Close'].iloc[-1]
        earnings_dates = self.dl.get_earnings_dates()
        
        # 获取期权链数据
        option_chain = self.dl.fetch_option_chain()
        if option_chain.empty:
            print("无法获取期权链数据")
            return None
        
        # 在访问字段前检查列是否存在
        required_cols = ['type', 'strike', 'impliedVolatility', 'days_to_expire']
        if not all(col in option_chain.columns for col in required_cols):
            print("期权链数据缺失关键列")
            return None
        
        # 检查财报风险
        if self._has_earnings_risk(earnings_dates):
            return None
            
        # 计算波动率指标
        iv_rank = calculate_iv_rank(self.dl.ticker)
        if iv_rank > self.config['strategy']['iv_percentile_threshold']:
            return None
            
        # 选择行权价
        call_strike = self._select_strike_by_delta('call', 0.3)
        put_strike = self._select_strike_by_delta('put', -0.3)
        
        if call_strike is None or put_strike is None:
            print("无法选择合适的行权价")
            return None
        
        # 获取合约信息
        call_contract = option_chain[
            (option_chain['strike'] == call_strike) &
            (option_chain['type'] == 'call')
        ].iloc[0]
        
        put_contract = option_chain[
            (option_chain['strike'] == put_strike) &
            (option_chain['type'] == 'put')
        ].iloc[0]
        
        if call_contract.empty or put_contract.empty:
            print("无法获取合约信息")
            return None
            
        # 计算组合希腊字母
        call_greeks = calculate_greeks(
            'call', 
            call_strike, 
            self.spot_price,
            call_contract['days_to_expire'],
            call_contract['impliedVolatility']
        )
        
        put_greeks = calculate_greeks(
            'put',
            put_strike,
            self.spot_price,
            put_contract['days_to_expire'],
            put_contract['impliedVolatility']
        )
        
        # 合并希腊字母
        portfolio_greeks = {
            'delta': call_greeks['delta'] - put_greeks['delta'],
            'gamma': call_greeks['gamma'] - put_greeks['gamma'],
            'vega': call_greeks['vega'] - put_greeks['vega'],
            'theta': call_greeks['theta'] - put_greeks['theta']
        }
            
        # 计算概率
        prob = self._calculate_probability(call_strike)

        # 修正行权价选择逻辑
        call_strikes = option_chain[option_chain['type'] == 'call']['strike'].unique()
        put_strikes = option_chain[option_chain['type'] == 'put']['strike'].unique()

        # 选择价内Call和价外Call构建价差
        itm_call = call_strikes[call_strikes < self.spot_price].max()
        otm_call = call_strikes[call_strikes > self.spot_price].min()
        
        risk_level = RiskManager(self.config['strategy']).calculate_risk_level(portfolio_greeks)

        
        # 验证行权价合理性
        if itm_call >= otm_call or (otm_call - itm_call) > self.spot_price * 0.1:
            print("价差不符合要求")
            return None
        
        return {
            'strategy_type': 'bull_call_spread',
            'ticker': self.dl.ticker,
            'strikes': (itm_call, otm_call),
            'risk_level': risk_level,
            'probability': round(prob * 100, 2),
            'entry_price': self.spot_price,
            'expiration': call_contract['expiration'],
            'greeks': portfolio_greeks  # 添加希腊字母数据
        }
    
    def _has_earnings_risk(self, dates):
        """检查未来5天内是否有财报"""
        next_5d = pd.Timestamp.now() + pd.DateOffset(days=5)
        return any(d <= next_5d for d in dates)
    
    def _select_strike_by_delta(self, option_type, target_delta):
        """基于Delta选择行权价（修正版）"""
        option_chain = self.dl.fetch_option_chain()
        if option_chain.empty:
            return None
        
        # 筛选指定类型的期权
        chain = option_chain[option_chain['type'] == option_type]
        
        # 计算Delta值
        deltas = []
        for _, row in chain.iterrows():
            g = calculate_greeks(
                option_type=row['type'],
                strike=row['strike'],
                spot=self.spot_price,
                t=row['days_to_expire'],
                iv=row['impliedVolatility']
            )
            deltas.append(g['delta'])
        
        # 找到最接近目标Delta的行权价
        chain = chain.assign(delta=deltas)
        closest_idx = np.abs(chain['delta'] - target_delta).argmin()
        return chain.iloc[closest_idx]['strike']
    
    def _calculate_probability(self, strike):
        # 获取真实剩余天数
        days_to_expire = self.dl.fetch_option_chain().iloc[0]['days_to_expire']
        t = max(days_to_expire / 365, 0.001)  # 防止除零
        
        # 使用合约的隐含波动率
        chain = self.dl.fetch_option_chain()
        iv = chain[chain['strike'] == strike]['impliedVolatility'].iloc[0]
        
        # 标的价格获取方式优化
        df = self.dl.get_real_time_data()
        spot = df['Close'].iloc[-1] if not df.empty else self.spot_price
        
        # 使用Black-Scholes公式计算Delta修正概率
        d1 = (np.log(spot/strike) + (0.5 * iv**2) * t) / (iv * np.sqrt(t))
        return norm.cdf(d1)  # 返回真实概率

    def _calculate_strategy_score(self, contract):
        """根据PRD权重计算策略得分"""
        score = 0
        
        # 波动率指标（20%）
        score += self._iv_analysis_score(contract) * 0.2
        
        # 公司基本面（15%）
        score += self._fundamental_score() * 0.15
        
        # 宏观经济（15%）
        score += self._macro_economic_score() * 0.15
        
        # 技术分析（12%）
        score += self._technical_score() * 0.12
        
        # 希腊字母（12%）
        score += self._greeks_score(contract) * 0.12
        
        # 行业相关（10%）
        score += self._industry_correlation_score() * 0.1
        
        # 市场情绪（8%）
        score += self._market_sentiment_score() * 0.08
        
        # 流动性（5%）
        score += self._liquidity_score(contract) * 0.05
        
        # 特殊事件（3%）
        score += self._event_risk_score() * 0.03
        
        return min(score * 100, 100)  # 转换为百分比

    def generate_top_strategies(self):
        strategies = []
        if not isinstance(self.dl.chain, list):
            return []
        
        # 为每个合约生成评分
        scored_contracts = [self._score_contract(c) for c in self.dl.chain if isinstance(c, dict)]
        
        puts = [c for c in scored_contracts if c.get('type') == 'put']
        calls = [c for c in scored_contracts if c.get('type') == 'call']
        
        # 生成看跌策略
        for put in sorted(puts, key=lambda x: x.get('score', 0), reverse=True)[:3]:
            strategies.append({
                'type': 'sell_put',
                'strike': put.get('strike'),
                'score': put.get('score', 0),
                'risk': '高风险' if put.get('iv', 0) > 0.4 else '中风险',
                'details': {
                    'iv_rank': self._iv_analysis_score(put),
                    'liquidity': put.get('volume', 0)
                }
            })
        
        # 生成看涨策略
        for call in sorted(calls, key=lambda x: x.get('score', 0), reverse=True)[:3]:
            strategies.append({
                'type': 'bull_call_spread',
                'strikes': [call.get('strike'), call.get('strike') + 5],
                'score': call.get('score', 0),
                'details': {
                    'iv_rank': self._iv_analysis_score(call),
                    'liquidity': call.get('volume', 0)
                }
            })
        
        return sorted(strategies, key=lambda x: x['score'], reverse=True)[:3]

    def _create_fallback_strategy(self, contract):
        """创建备选策略"""
        return {
            'type': 'sell_put' if contract['type'] == 'put' else 'sell_call',
            'strike': contract['strike'],
            'score': max(contract['score'], 35),  # 最低展示分
            'details': self._get_score_details(contract),
            'risk': '极高风险（备选）',
            'warning': '⚠️ 该策略未完全满足风控要求'
        }

    def _filter_valid_contracts(self, option_type):
        """正确过滤合约类型"""
        return [
            c for c in self.dl.chain 
            if c.get('type') == option_type and
            c.get('score', 0) > 50  # 添加最低分过滤
        ]

    def _get_score_details(self, contract):
        """获取各维度得分明细"""
        return {
            'iv_rank': self.dl.get_iv_rank(),
            'technical': self.dl.get_technical_score(),
            'greeks': self.dl.get_greeks_analysis(contract),
            'liquidity': contract['volume']
        }

    def _iv_analysis_score(self, contract):
        """更精确的波动率评分"""
        iv = contract.get('iv', 0)
        industry_iv = self.dl.get_industry_iv()
        iv_rank = self.dl.get_iv_rank()
        
        # 计算相对波动率溢价
        iv_premium = iv / industry_iv if industry_iv > 0 else 0
        
        return min(
            100 * (0.4 * iv_rank/100 + 
                   0.3 * iv_premium + 
                   0.3 * (contract.get('volume',0)/1000)),
            100
        )

    def _fundamental_score(self):
        """公司基本面评分（15%）"""
        score = 0
        # 财报窗口检查
        if self.dl.days_to_earnings() < 15:
            score -= 8
        # 内部人交易
        if self.dl.insider_buying() > 0.001:  # 增持超过0.1%
            score += 5
        # 机构持股变动
        if self.dl.institutional_holding_change() > 0.05:
            score += 3
        return score / 10

    def _macro_economic_score(self):
        """宏观经济评分（15%）"""
        macro = self.dl.get_macro_factors()
        score = 0
        
        # CPI敏感度
        if macro['cpi_sensitivity'] > 1.0:
            score -= 3  # 高敏感度扣分
        elif macro['cpi_sensitivity'] < 0.8:
            score += 2
            
        # 利率敏感度
        if abs(macro['rate_sensitivity']) > 0.3:
            score -= 2
            
        # 行业政策风险
        if macro['sector_policy_risk'] > 0.7:
            score -= 5
            
        return score / 10

    def _technical_score(self):
        """技术分析评分（12%）"""
        tech_data = self.dl.get_technical_data()
        score = 0
        # 支撑位距离
        if tech_data['price_to_support'] < 0.03:
            score += 4
        # 趋势强度
        if tech_data['adx'] > 25 and tech_data['+di'] > tech_data['-di']:
            score += 5
        # 成交量分析
        if tech_data['volume_ratio'] < 0.8:
            score += 3
        return score / 10

    def _greeks_score(self, contract):
        """希腊字母评分（12%）"""
        greeks = self.dl.get_greeks_analysis(contract)
        score = 0
        # Theta/Delta比值
        if greeks['theta'] / abs(greeks['delta']) >= 0.5:
            score += 6
        # Gamma风险控制
        if greeks['gamma'] < 0.08:
            score += 4
        # Vega暴露
        if contract['iv'] > 0.3 and abs(greeks['vega']) < 0.5:
            score += 2
        return score / 10

    def _industry_correlation_score(self):
        """行业相关评分（10%）"""
        # 实现行业相关评分逻辑
        return 0  # 临时返回值，需要根据实际逻辑实现

    def _market_sentiment_score(self):
        """市场情绪评分（8%）"""
        # 实现市场情绪评分逻辑
        return 0  # 临时返回值，需要根据实际逻辑实现

    def _liquidity_score(self, contract):
        """流动性评分（5%）"""
        return min(contract.get('volume', 0) / 1000, 5)  # 每1000手得1分，最高5分

    def _event_risk_score(self):
        """特殊事件评分（3%）"""
        # 实现特殊事件评分逻辑
        return 0  # 临时返回值，需要根据实际逻辑实现

    def _generate_near_expiry_strategies(self):
        """生成临近到期日的应急策略"""
        # 实现短期策略逻辑
        return [{
            'type': 'weekly_put',
            'strike': ...,
            'score': ...,
            'risk': '极高风险'
        }]

    def _handle_special_market(self):
        """处理临近到期日的特殊市场状态"""
        if self.dl.chain and all(c['days_to_exp'] < 7 for c in self.dl.chain):
            print("⚠️ 进入特殊市场模式（周期权策略）")
            return self._generate_weekly_strategies()
        return []

    def _score_contract(self, contract):
        """综合评分计算（完整实现）"""
        bid = contract.get('bid', 0)
        ask = contract.get('ask', 1)
        spread_ratio = (ask - bid) / ask if ask > 0 else 0
        
        return {
            'score': (
                contract.get('iv', 0) * 100 * 0.4 +
                contract.get('volume', 0) / 1000 * 0.3 +
                (1 - spread_ratio) * 0.3
            ),
            'risk': '未评估',
            **contract
        }

    def _technical_analysis_score(self):
        """技术分析评分（20%）"""
        return 15  # 模拟值