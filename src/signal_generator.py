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
        self.spot_price = 0.0
    
    def generate_vertical_spread_signal(self):
        """生成垂直价差信号（多策略优化版）"""
        self.spot_price = float(self.dl.get_spot_price())
        print(f"\n📈 当前现货价格: {self.spot_price}")
        
        # 生成四种基本策略
        strategies = [
            self._generate_strategy('bull_call', "牛市看涨价差"),
            self._generate_strategy('bear_call', "熊市看涨价差"),
            self._generate_strategy('bull_put', "牛市看跌价差"),
            self._generate_strategy('bear_put', "熊市看跌价差")
        ]
        
        # 过滤并排序有效策略
        valid_signals = sorted([s for s in strategies if s], 
                             key=lambda x: x['probability'], 
                             reverse=True)[:3]
        
        return valid_signals or None

    def _generate_strategy(self, strategy_type, strategy_name):
        """通用策略生成方法"""
        try:
            if strategy_type in ['bull_call', 'bear_call']:
                return self._generate_call_spread(strategy_type, strategy_name)
            return self._generate_put_spread(strategy_type, strategy_name)
        except Exception as e:
            print(f"生成{strategy_type}策略失败: {str(e)}")
            return None

    def _generate_put_spread(self, strategy_type, strategy_name):
        """生成看跌期权价差（完整版）"""
        try:
            # 数据验证
            option_chain = self.dl.fetch_option_chain()
            if option_chain.empty:
                print("⚠️ 期权链数据为空")
                return None
                
            # 过滤有效put行权价
            put_strikes = option_chain[
                (option_chain['type'] == 'put') &
                (option_chain['strike'] > 0) &
                (option_chain['days_to_expire'] >= 21)
            ]['strike'].dropna().astype(float)
            
            if len(put_strikes) < 2:
                print("看跌期权行权价不足")
                return None
                
            put_strikes = np.unique(put_strikes)
            put_strikes.sort()
            
            # 安全搜索行权价位置
            idx = np.searchsorted(
                put_strikes.astype(np.float64), 
                np.float64(self.spot_price), 
                side='left'
            )
            
            # 边界保护
            idx = max(1, min(idx, len(put_strikes)-2))
            
            otm_put = put_strikes[idx-1]
            itm_put = put_strikes[idx]
            
            print(f"选择行权价范围: {otm_put} - {itm_put} (现货价: {self.spot_price})")
            
            # 计算概率
            prob = self._calculate_probability(otm_put, itm_put)
            
            # 计算收益参数
            expiration = self._select_expiration(option_chain)
            if pd.isna(expiration):
                print("无有效到期日")
                return None
                
            return {
                'name': strategy_name,
                'strategy_type': strategy_type,
                'strikes': (otm_put, itm_put),
                'probability': round(prob * 100, 1),
                'max_return': self._calculate_max_return(otm_put, itm_put),
                'expiration': expiration.strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            print(f"策略生成失败: {str(e)}")
            return None

    def _calculate_max_return(self, lower_strike, upper_strike):
        """计算最大收益率（增强版）"""
        # 获取两个合约的价格
        lower_price = self._get_contract_price(lower_strike, 'put')
        upper_price = self._get_contract_price(upper_strike, 'put')
        
        if lower_price == 0 or upper_price == 0:
            return 0.0
            
        net_debit = lower_price - upper_price
        spread_width = upper_strike - lower_strike
        if net_debit <= 0:
            print(f"⚠️ 异常价格: lower={lower_price}, upper={upper_price}")
            return 0.0
            
        return round((spread_width - net_debit) / net_debit * 100, 1)

    def _get_valid_contract(self, option_type, strike, min_volume):
        """获取符合要求的合约（增强容错版）"""
        chain = self.dl.fetch_option_chain()
        print(f"\n正在查找{option_type}合约: 目标行权价={strike}，允许偏差±10%")
        
        # 计算允许的行权价范围
        price_tolerance = self.spot_price * 0.10
        min_strike = strike - price_tolerance
        max_strike = strike + price_tolerance
        
        # 寻找替代行权价
        candidates = chain[
            (chain['type'] == option_type) &
            (chain['strike'].between(min_strike, max_strike)) &
            (chain['volume'] >= min_volume)
        ]
        
        if not candidates.empty:
            # 选择最接近目标的行权价
            candidates['strike_diff'] = abs(candidates['strike'] - strike)
            best_match = candidates.nsmallest(1, 'strike_diff').iloc[0]
            print(f"使用替代行权价: {best_match['strike']} (原目标: {strike})")
            return best_match.copy()
            
        print(f"附近无可用{option_type}合约，尝试其他策略...")
        return None

    def _generate_call_spread(self, strategy_type, strategy_name):
        """生成看涨期权价差（流动性优化版）"""
        try:
            option_chain = self.dl.fetch_option_chain()
            if option_chain.empty:
                print("⚠️ 期权链数据为空")
                return None
                
            # 过滤有效call行权价（考虑流动性）
            call_strikes = option_chain[
                (option_chain['type'] == 'call') &
                (option_chain['strike'] > 0) &
                (option_chain['days_to_expire'] >= 3) &
                (option_chain['volume'] >= self.config['strategy']['min_volume_fallback'])
            ]['strike'].dropna().astype(float)
            
            if len(call_strikes) < 2:
                print("看涨期权行权价不足，尝试放宽条件...")
                # 回退到基本流动性要求
                call_strikes = option_chain[
                    (option_chain['type'] == 'call') &
                    (option_chain['strike'] > 0) &
                    (option_chain['days_to_expire'] >= 3)
                ]['strike'].dropna().astype(float)
                if len(call_strikes) < 2:
                    return None

            call_strikes = np.unique(call_strikes)
            call_strikes.sort()
            
            # 选择合理范围内的行权价
            price_range = self.spot_price * 0.10  # 10%范围
            valid_strikes = call_strikes[
                (call_strikes >= self.spot_price - price_range) &
                (call_strikes <= self.spot_price + price_range)
            ]
            
            if len(valid_strikes) >= 2:
                lower_strike = valid_strikes[0]
                upper_strike = valid_strikes[1]
            else:
                # 选择最接近的两个行权价
                idx = np.searchsorted(call_strikes, self.spot_price)
                lower_strike = call_strikes[max(0, idx-1)]
                upper_strike = call_strikes[min(idx, len(call_strikes)-1)]
            
            print(f"看涨策略行权价范围: {lower_strike} - {upper_strike}")
            
            # 计算参数
            prob = self._calculate_probability(lower_strike, upper_strike)
            expiration = self._select_expiration(option_chain)
            if pd.isna(expiration):
                return None
                
            return {
                'name': strategy_name,
                'strategy_type': strategy_type,
                'strikes': (lower_strike, upper_strike),
                'probability': round(prob * 100, 1),
                'max_return': self._calculate_max_return(lower_strike, upper_strike),
                'expiration': expiration.strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            print(f"看涨策略生成失败: {str(e)}")
            return None

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
    
    def _calculate_probability(self, lower_strike, upper_strike):
        """计算牛市价差的真实概率"""
        # 添加参数验证
        if lower_strike >= upper_strike:
            print(f"参数错误：lower={lower_strike} >= upper={upper_strike}")
            return 0.0
            
        # 获取有效时间参数（至少1天）
        days = max(self.dl.fetch_option_chain().iloc[0]['days_to_expire'], 1)
        t = days / 365.0
        
        # 计算波动率曲面
        iv1 = self._get_surface_iv(lower_strike, t)
        iv2 = self._get_surface_iv(upper_strike, t)
        avg_iv = (iv1 + iv2) / 2
        
        # 计算d1值时添加波动率下限保护
        sigma = max(avg_iv, 0.05)  # 最低5%波动率
        
        # 重新计算d1值
        d1_lower = (np.log(self.spot_price/lower_strike) + (0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        d1_upper = (np.log(self.spot_price/upper_strike) + (0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        
        # 计算最终概率
        prob = norm.cdf(d1_upper) - norm.cdf(d1_lower)
        return max(0.05, min(0.95, prob))  # 限制在5%-95%之间
        
    def _get_surface_iv(self, strike, t):
        """从波动率曲面获取IV"""
        chain = self.dl.fetch_option_chain()
        mask = (chain['strike'] == strike) & (chain['days_to_expire'] >= t*365-3)
        if mask.any():
            return chain[mask]['impliedVolatility'].iloc[0]
        return chain['impliedVolatility'].mean()  # 回退到平均IV

    def _select_expiration(self, option_chain):
        """选择到期日（月期权优化版）"""
        # 计算目标时间范围
        now = pd.Timestamp.now().normalize()
        target_start = now + pd.DateOffset(days=25)  # 25-35天范围
        target_end = now + pd.DateOffset(days=35)
        
        # 过滤符合时间范围的合约
        valid = option_chain[
            (option_chain['expiration'] > target_start) &
            (option_chain['expiration'] < target_end)
        ]
        
        # 优先选择周三月期权（每月第三个周三）
        wednesdays = valid[valid['expiration'].dt.dayofweek == 2]
        third_wed = wednesdays[wednesdays['expiration'].dt.day >= 15]
        if not third_wed.empty:
            selected = third_wed.sort_values('volume', ascending=False).iloc[0]
            print(f"🌙 选择月期权到期日: {selected['expiration'].strftime('%Y-%m-%d')}")
            return selected['expiration']
            
        # 次选：成交量最大的近月合约
        if not valid.empty:
            selected = valid.sort_values(['volume', 'openInterest'], ascending=False).iloc[0]
            print(f"⏳ 选择次优到期日: {selected['expiration'].strftime('%Y-%m-%d')}")
            return selected['expiration']
            
        # 保底选择：最近的有效到期日
        fallback = option_chain[option_chain['expiration'] > now].iloc[0]
        print(f"⚠️ 使用保底到期日: {fallback['expiration'].strftime('%Y-%m-%d')}")
        return fallback['expiration']

    def _generate_straddle(self):
        """生成跨式组合策略（基础实现）"""
        print("\n正在尝试跨式组合策略...")
        try:
            # 获取平值期权行权价
            chain = self.dl.fetch_option_chain()
            if chain.empty:
                print("无可用期权数据")
                return None
                
            # 计算最接近现货的行权价
            atm_strike = chain.iloc[(chain['strike'] - self.spot_price).abs().argsort()[:1]]['strike'].values[0]
            print(f"选择平值行权价: {atm_strike}")
            
            # 获取合约
            call = self._get_valid_contract('call', atm_strike, self.config['strategy']['min_volume_fallback'])
            put = self._get_valid_contract('put', atm_strike, self.config['strategy']['min_volume_fallback'])
            
            if not call or not put:
                print("无法获取跨式组合所需合约")
                return None
                
            # 计算组合参数
            entry_cost = call['ask'] + put['ask']
            max_profit = "无限（方向性波动）"
            break_even = atm_strike + entry_cost
            
            return {
                'strategy_type': 'straddle',
                'strikes': (atm_strike, atm_strike),
                'entry_cost': round(entry_cost, 2),
                'max_profit': max_profit,
                'break_even': break_even,
                'expiration': call['expiration']
            }
            
        except Exception as e:
            print(f"生成跨式组合失败: {str(e)}")
            return None

    def _get_contract_price(self, strike, option_type):
        """获取合约中间价（带流动性检查）"""
        contract = self._get_valid_contract(
            option_type=option_type,
            strike=strike,
            min_volume=self.config['strategy']['min_volume_fallback']
        )
        if contract is not None:
            return (contract['bid'] + contract['ask']) / 2
        print(f"⚠️ 无法获取{strike} {option_type}合约价格")
        return 0.0

    def _is_monthly_expiration(self, date):
        """判断是否为月期权到期日（每月第三个周五）"""
        # 获取当月第三个周五
        first_day = date.replace(day=1)
        first_friday = first_day + pd.offsets.WeekOfMonth(week=0, weekday=4)
        third_friday = first_friday + pd.DateOffset(weeks=2)
        return date == third_friday