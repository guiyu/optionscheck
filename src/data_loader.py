from yahooquery import Ticker
import pandas as pd
import yaml
import os
from datetime import datetime
import requests
import yfinance as yf
import numpy as np
import time

class DataLoader:
    def __init__(self, ticker):
        self.ticker = ticker
        self.config = self._load_config()
        # 初始化请求时间属性
        self.last_request_time = 0
        self.request_interval = 2  # 默认请求间隔
        
        # 代理配置和请求头初始化
        proxies = self.config.get('api_settings', {}).get('yahoo', {}).get('proxies', None)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        
        # 初始化Yahoo API客户端
        self.yahoo = Ticker(
            ticker,
            headers=headers,
            asynchronous=True,
            formatted=False,
            retry=5,
            backoff_factor=0.3,
            validate=True,
            proxies=proxies
        )
        
        # 其他数据初始化
        self.spot_price = self._get_spot_price()
        self.option_chain = self._fetch_raw_option_chain()
        self.processed_chain = self._process_chain(self.option_chain)
        self.last_updated = datetime.now()
        if not self._validate_api_config():
            raise ValueError("Invalid API configuration")
    
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
        """使用正确的YahooQuery API方法"""
        self._rate_limit()  # 添加速率限制
        try:
            # 使用正确的API方法获取到期日
            exp_dates = self.yahoo.option_chain.expiration_dates
            if not exp_dates:
                raise ValueError("没有可用的期权到期日")
            
            # 获取最近三个到期日的数据
            all_chains = []
            for date in exp_dates[:3]:
                # 获取指定到期日的期权链
                options = self.yahoo.option_chain(date=date)
                if options and 'calls' in options and 'puts' in options:
                    # 处理看涨期权
                    calls = pd.DataFrame(options['calls'])
                    calls['type'] = 'call'
                    # 处理看跌期权
                    puts = pd.DataFrame(options['puts'])
                    puts['type'] = 'put'
                    # 合并数据
                    all_chains.append(pd.concat([calls, puts]))
            
            if not all_chains:
                raise ValueError("没有有效的期权数据")
            
            return pd.concat(all_chains, ignore_index=True)
            
        except Exception as e:
            print(f"API请求失败: {str(e)}")
            return self._get_fallback_data()

    def _process_chain(self, raw_chain):
        """处理真实API数据"""
        try:
            # 转换数据类型时使用安全方法
            type_mapping = {
                'strike': float,
                'bid': float,
                'ask': float,
                'volume': int,
                'impliedVolatility': float
            }
            # 仅转换存在的字段
            valid_columns = [col for col in type_mapping if col in raw_chain.columns]
            raw_chain = raw_chain.astype({col: type_mapping[col] for col in valid_columns})
            
            # 添加合约类型判断
            raw_chain['type'] = raw_chain['contractSymbol'].apply(
                lambda s: 'call' if s.endswith('C') else 'put'
            )
            
            # 添加日期处理保护
            if 'expiration' in raw_chain.columns:
                try:
                    raw_chain['expiration'] = pd.to_datetime(raw_chain['expiration'])
                    raw_chain['days_to_expire'] = (raw_chain['expiration'] - pd.Timestamp.now()).dt.days
                except Exception as e:
                    print(f"日期处理错误: {str(e)}")
            else:
                print("⚠️ 数据缺少expiration字段")
                return self._get_fallback_processed_data()
            
            # 转换为字典列表
            return [
                {
                    'type': row['type'],
                    'strike': row['strike'],
                    'bid': row['bid'],
                    'ask': row['ask'],
                    'volume': row['volume'],
                    'iv': row['impliedVolatility'],
                    'days_to_exp': row['days_to_expire']
                }
                for _, row in raw_chain.iterrows()
            ]
            
        except Exception as e:
            print(f"数据处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_processed_data()

    def _detect_contract_type(self, symbol):
        """根据合约代码判断类型"""
        return 'call' if symbol.endswith('C') else 'put'

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

    def is_data_fresh(self):
        """检查数据是否在5分钟内更新"""
        return (datetime.now() - self.last_updated).seconds < 300

    def refresh_data(self):
        """增强数据刷新逻辑"""
        if self.is_data_fresh():
            print("数据仍在有效期内，无需刷新")
            return
        
        try:
            self.option_chain = self._fetch_raw_option_chain()
            self.processed_chain = self._process_chain(self.option_chain)
            self.last_updated = datetime.now()
            print(f"数据刷新成功，最新更新时间：{self.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"数据刷新失败: {str(e)}")
            print("使用缓存数据继续运行")

    def _get_fallback_data(self):
        """生成带完整字段的模拟数据"""
        return pd.DataFrame({
            'contractSymbol': ['SPY220101C00400000', 'SPY220101P00410000', 'SPY220101C00420000'],
            'strike': [400.0, 410.0, 420.0],
            'bid': [1.2, 1.1, 1.0],
            'ask': [1.3, 1.2, 1.1],
            'volume': [1000, 2000, 1500],
            'impliedVolatility': [0.35, 0.4, 0.5],
            'expiration': [
                pd.Timestamp.now() + pd.Timedelta(days=30),
                pd.Timestamp.now() + pd.Timedelta(days=45),
                pd.Timestamp.now() + pd.Timedelta(days=60)
            ],
            'type': ['call', 'put', 'call']
        })

    def _get_fallback_processed_data(self):
        """生成处理后的模拟数据"""
        return self._process_chain(self._get_fallback_data())

    def check_api_connection(self):
        """检查API连通性"""
        try:
            test = requests.get('https://query1.finance.yahoo.com', timeout=5)
            return test.status_code == 200
        except Exception as e:
            print(f"网络连接异常: {str(e)}")
            return False

    def _validate_api_config(self):
        """验证必要配置项"""
        required_keys = ['api_settings', 'strategy']
        return all(k in self.config for k in required_keys)

    def check_network_connection(self):
        """检查网络连通性"""
        test_urls = [
            'https://finance.yahoo.com',
            'https://query1.finance.yahoo.com',
            'https://query2.finance.yahoo.com'
        ]
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code != 200:
                    print(f"连接失败: {url} (状态码: {response.status_code})")
                    return False
            except Exception as e:
                print(f"网络异常: {url} - {str(e)}")
                return False
        return True

    def _rate_limit(self):
        """更安全的速率限制方法"""
        try:
            current_time = time.time()
            elapsed = current_time - getattr(self, 'last_request_time', 0)
            interval = getattr(self, 'request_interval', 2)
            
            if elapsed < interval:
                sleep_time = interval - elapsed
                time.sleep(max(sleep_time, 0))  # 确保非负
            
            self.last_request_time = current_time
        except AttributeError:
            # 处理属性未初始化的情况
            self.last_request_time = time.time()
            self.request_interval = 2

    def __getattr__(self, name):
        """处理未初始化属性的访问"""
        if name in ['last_request_time', 'request_interval']:
            # 自动初始化时间相关属性
            self.last_request_time = time.time()
            self.request_interval = 2
            return getattr(self, name)
        raise AttributeError(f"'DataLoader' object has no attribute '{name}'")