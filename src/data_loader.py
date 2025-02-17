from yahooquery import Ticker
import pandas as pd
import yaml
import os
from datetime import datetime
import requests
import yfinance as yf
import numpy as np

class DataLoader:
    def __init__(self, ticker):
        self.ticker = ticker
        self.config = self._load_config()
        self.yahoo = Ticker(
            ticker, 
            asynchronous=True,
            formatted=False,
            retry=5,
            backoff_factor=0.3
        )
        self.spot_price = self._get_spot_price()
        self.option_chain = self._fetch_raw_option_chain()
        self.processed_chain = self._process_chain(self.option_chain)
    
    def _load_config(self):
        with open('config/config.yaml') as f:
            return yaml.safe_load(f)
    
    def _get_session(self):
        """创建带有自定义请求头的会话"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        return session
    
    def get_real_time_data(self, interval='5m'):
        """获取实时行情数据"""
        try:
            # 使用yahooquery获取历史数据
            df = self.yahoo.history(period='1d', interval=interval)
            if isinstance(df, dict) or df.empty:
                return pd.DataFrame()
            
            # 只保留需要的列
            df = df[['open', 'high', 'low', 'close', 'volume']]
            # 标准化列名
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df.dropna()
        except Exception as e:
            print(f"数据获取失败: {str(e)}")
            return pd.DataFrame()
    
    def fetch_option_chain(self):
        """获取并处理后的期权链数据"""
        return pd.DataFrame(self.processed_chain)  # 转换为DataFrame
    
    def get_earnings_dates(self):
        """获取财报日历"""
        try:
            # ETF没有财报日期
            if 'QQQ' in self.ticker or 'SPY' in self.ticker:
                return []
                
            # 使用yahooquery获取财报信息
            calendar = self.yahoo.calendar_events
            if isinstance(calendar, dict) or calendar.empty:
                return []
            
            # 获取未来的财报日期
            if 'Earnings Date' in calendar.columns:
                future_dates = calendar[
                    calendar['Earnings Date'] > pd.Timestamp.now()
                ]['Earnings Date']
                return [d.to_pydatetime() for d in future_dates]
            
            return []
            
        except Exception as e:
            print(f"财报日历获取失败: {str(e)}")
            return []
    
    def get_industry_iv(self):
        """获取行业平均IV"""
        # 实现行业数据获取逻辑
        return self._fetch_industry_data().get('average_iv', 0.3)
    
    def days_to_earnings(self):
        """距离下次财报的天数"""
        next_earnings = min([d for d in self.get_earnings_dates() if d > datetime.now()])
        return (next_earnings - datetime.now()).days
    
    def get_technical_data(self):
        """获取技术指标数据"""
        return {
            'price_to_support': self._calculate_support_distance(),
            'adx': self._calculate_adx(),
            '+di': self._calculate_positive_di(),
            'volume_ratio': self._volume_ratio()
        }
    
    def _volume_ratio(self):
        """计算成交量比率"""
        current_volume = self.get_real_time_data()['Volume'].iloc[-1]
        avg_volume = self.get_real_time_data()['Volume'].rolling(20).mean().iloc[-1]
        return current_volume / avg_volume

    def get_sector_data(self):
        """获取行业相关数据"""
        return {
            'sector_iv': self._get_sector_iv(),
            'competitor_performance': self._get_competitor_data(),
            'sector_correlation': self._calculate_sector_correlation()
        }

    def _get_competitor_data(self):
        """获取竞争对手表现"""
        # 实现行业竞争对手数据获取
        competitors = ['AMD', 'INTC'] if self.ticker == 'NVDA' else []
        return {c: self.__class__(c).get_performance() for c in competitors}

    def get_macro_factors(self):
        """获取宏观经济因子"""
        return {
            'cpi_sensitivity': self._get_cpi_sensitivity(),
            'rate_sensitivity': self._calculate_rate_beta(),
            'sector_policy_risk': self._evaluate_policy_risk()
        }
    
    def _get_cpi_sensitivity(self):
        """CPI敏感度分析"""
        # 实现行业CPI敏感度模型
        sector = self._get_sector()
        sensitivity_map = {
            'tech': 0.7, 
            'consumer': 1.2,
            'energy': 0.9
        }
        return sensitivity_map.get(sector, 1.0)
    
    def _calculate_rate_beta(self):
        """利率敏感度分析"""
        # 计算标的对10年期国债收益率的beta
        treasury_data = yf.Ticker('^TNX').history(period='1y')
        stock_returns = self.get_returns()
        return np.cov(stock_returns, treasury_data['Close'].pct_change().dropna())[0][1]

    def _get_spot_price(self):
        """获取标的现货价格"""
        data = yf.Ticker(self.ticker).history(period='1d')
        return data['Close'].iloc[-1]

    def _fetch_raw_option_chain(self):
        """包含完整字段的模拟数据"""
        return pd.DataFrame({
            'strike': [400, 410, 420],
            'bid': [1.2, 1.1, 1.0],
            'ask': [1.3, 1.2, 1.1],
            'type': ['call', 'call', 'put'],
            'days_to_expire': [30, 45, 60],
            'volume': [1000, 2000, 1500],
            'impliedVolatility': [0.35, 0.4, 0.5],
            'score': [65, 70, 75]  # 新增评分字段
        })

    def _process_chain(self, raw_chain):
        """将DataFrame转换为字典列表"""
        if raw_chain.empty:
            return []
        
        # 转换数据类型
        raw_chain = raw_chain.astype({
            'strike': float,
            'bid': float,
            'ask': float,
            'volume': int,
            'impliedVolatility': float,
            'days_to_expire': int
        })
        
        # 转换为字典列表并重命名键
        processed = [{
            'type': row['type'],
            'strike': row['strike'],
            'bid': row['bid'],
            'ask': row['ask'],
            'volume': row['volume'],
            'iv': row['impliedVolatility'],
            'days_to_exp': row['days_to_expire']
        } for _, row in raw_chain.iterrows()]
        
        # 添加有效性过滤
        print(f"\n🔎 数据清洗结果：")
        print(f"原始合约数量：{len(raw_chain)}")
        print(f"有效波动率合约：{len([c for c in processed if c['iv'] > 0])}")
        print(f"有效到期日合约：{len([c for c in processed if c['days_to_exp'] > 0])}")
        
        print("\n🔍 数据完整性检查：")
        print(f"最早到期日：{min(c['days_to_exp'] for c in processed)}天")
        print(f"最晚到期日：{max(c['days_to_exp'] for c in processed)}天")
        print(f"平均波动率：{np.mean([c['iv'] for c in processed]):.1%}")
        
        return [
            c for c in processed 
            if 3 <= c.get('days_to_exp', 0) <= 730  # 允许2年内的合约
            and c.get('iv', 0) > 0.15  # 进一步降低IV要求
            and c.get('volume', 0) > 0  # 至少要有成交量记录
        ]

    @property
    def chain(self):
        """确保返回字典列表"""
        return self.processed_chain  # 直接返回处理后的列表

    def _calculate_days_to_expire(self, expiration_date):
        """正确处理Timestamp类型日期"""
        # 转换为时区无关的日期对象
        if isinstance(expiration_date, pd.Timestamp):
            expire_date = expiration_date.tz_localize(None)
        else:
            expire_date = pd.to_datetime(expiration_date)
        
        # 计算天数差
        return (expire_date - pd.Timestamp.now().tz_localize(None)).days

    def _fetch_industry_data(self):
        """模拟行业数据获取"""
        return {
            'average_iv': 0.35,
            'sector': 'Technology',
            'peers': ['AAPL', 'MSFT', 'NVDA']
        }

    def get_iv_rank(self):
        """实现IV排名获取（模拟值）"""
        return 75

    def iv_term_structure(self):
        """模拟波动率期限结构"""
        return {
            '1M': 0.35,
            '3M': 0.4,
            '6M': 0.45
        }