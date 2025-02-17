from yahooquery import Ticker
import pandas as pd
import yaml
import os
from datetime import datetime
import requests

class DataLoader:
    def __init__(self, ticker):
        self.ticker = ticker
        self.config = self._load_config()
        self.yahoo = Ticker(
            ticker, 
            asynchronous=True,
            status_forcelist=[404, 429, 500],
            backoff_factor=0.3,
            verify=False
        )
        self.spot_price = None
        self.last_update = None
        self.session = requests.Session()
        self.cache = {}
    
    def _load_config(self):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), '../config/config.yaml')
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def get_spot_price(self):
        """获取实时现货价格（多源回退+智能缓存）"""
        try:
            if self._needs_refresh():
                self._refresh_spot_price()
            return float(self.spot_price)
        except Exception as e:
            print(f"价格获取失败: {e}, 使用最后缓存值")
            return self.spot_price or self._get_fallback_price()

    def _needs_refresh(self):
        """智能刷新判断"""
        if self.spot_price is None:
            return True
        elapsed = (pd.Timestamp.now() - self.last_update).seconds
        return elapsed > min(300, self.config['data_refresh_interval'])

    def _refresh_spot_price(self):
        """多数据源刷新策略"""
        sources = [
            ('alpha_vantage', self._fetch_alpha_vantage),
            ('yahoo', self._fetch_yahoo_realtime),
            ('backup', self._fetch_backup_api)
        ]
        
        for source_name, source_func in sources:
            try:
                price = source_func()
                if self._validate_price(price):
                    self.spot_price = price
                    self.last_update = pd.Timestamp.now()
                    print(f"✅ 从 {source_name} 获取最新价格: {price}")
                    return
            except Exception as e:
                print(f"⚠️ {source_name} 数据源异常: {str(e)}")
        
        print("⚠️ 所有数据源不可用，使用缓存")
        self.spot_price = self._get_cached_price()

    def _fetch_alpha_vantage(self):
        """AlphaVantage实时数据"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': self.ticker,
            'apikey': self.config['data_sources']['alpha_vantage']['api_key']
        }
        resp = self.session.get(
            self.config['data_sources']['alpha_vantage']['api_endpoint'],
            params=params,
            timeout=3
        )
        resp.raise_for_status()
        return float(resp.json()['Global Quote']['05. price'])

    def _fetch_yahoo_realtime(self):
        """Yahoo Finance实时报价"""
        data = self.yahoo.history(period='1d', interval='1m')
        if len(data) < 1:
            raise ValueError("无实时数据")
        return data['close'].iloc[-1]

    def _fetch_backup_api(self):
        """备用数据源（带本地缓存）"""
        cache_key = f"{self.ticker}_spot"
        if cache_key in self.cache:
            cached_time = self.cache[cache_key]['timestamp']
            if (pd.Timestamp.now() - cached_time).seconds < 7200:  # 2小时缓存
                return self.cache[cache_key]['price']
        
        # 从公开API获取
        resp = self.session.get(
            f"https://financialmodelingprep.com/api/v3/quote-short/{self.ticker}",
            params={'apikey': self.config['data_sources']['backup_api_key']},
            timeout=5
        )
        price = resp.json()[0]['price']
        self.cache[cache_key] = {
            'price': price,
            'timestamp': pd.Timestamp.now()
        }
        return price

    def _validate_price(self, price):
        """价格合理性验证"""
        if not isinstance(price, (int, float)):
            raise ValueError("价格类型错误")
        if price <= 0:
            raise ValueError("价格无效")
        if self.spot_price:  # 检查波动幅度
            change_pct = abs(price - self.spot_price) / self.spot_price
            if change_pct > 0.1:  # 单次波动超过10%需要确认
                print(f"⚠️ 价格波动异常: {change_pct*100:.2f}%")
                return False
        return True

    def _get_cached_price(self):
        """获取最近有效价格"""
        if self.spot_price:
            return self.spot_price
        # 获取历史数据
        hist = self.yahoo.history(period='5d')
        return hist['close'].iloc[-1] if not hist.empty else 0.0

    def _get_fallback_price(self):
        """最终回退方案"""
        try:
            return self.yahoo.price[self.ticker]['regularMarketPrice']
        except:
            return 0.0  # 确保程序不会崩溃

    def fetch_option_chain(self):
        """获取期权链数据（容错增强版）"""
        try:
            chain = self._fetch_option_chain_base()
            if chain.empty:
                print("⚠️ 获取到空期权链")
                return pd.DataFrame()
            
            # 转换日期格式
            chain['expiration'] = pd.to_datetime(chain['expiration'], errors='coerce')
            chain = chain.dropna(subset=['expiration'])
            
            # 添加特征工程
            now = pd.Timestamp.now().normalize()
            chain['days_to_expire'] = (chain['expiration'] - now).dt.days
            chain['is_weekly'] = chain['expiration'].dt.day.isin([15,22])
            chain['is_monthly'] = (chain['expiration'].dt.day >= 15) & (chain['expiration'].dt.day <= 21)
            
            print(f"✅ 处理后的期权链包含 {len(chain)} 条记录")
            return chain
            
        except Exception as e:
            print(f"期权链处理失败: {str(e)}")
            return pd.DataFrame()

    def _fetch_option_chain_base(self):
        """使用yahooquery获取期权链数据"""
        try:
            print("\n⌛ 正在通过yahooquery获取期权链...")
            # 获取期权链数据
            chain = self.yahoo.option_chain
            if isinstance(chain, dict) and 'error' in chain:
                print(f"❌ 错误响应: {chain['error']}")
                return pd.DataFrame()
                
            # 合并看涨和看跌期权
            calls = pd.DataFrame(chain.get('calls', []))
            puts = pd.DataFrame(chain.get('puts', []))
            
            # 添加type列
            if not calls.empty:
                calls['type'] = 'call'
            if not puts.empty:
                puts['type'] = 'put'
                
            chain = pd.concat([calls, puts], ignore_index=True)
            
            # 必要字段检查
            required_columns = ['expiration', 'strike', 'bid', 'ask']
            missing = [col for col in required_columns if col not in chain.columns]
            if missing:
                print(f"❌ 缺少必要字段: {missing}")
                return pd.DataFrame()
            
            # 转换日期格式
            chain['expiration'] = pd.to_datetime(chain['expiration'], errors='coerce')
            return chain[['expiration', 'strike', 'type', 'bid', 'ask', 'volume']]
            
        except Exception as e:
            print(f"❌ 获取期权链失败: {str(e)}")
            return pd.DataFrame()

    def get_earnings_dates(self):
        """获取财报日历（使用yahooquery）"""
        try:
            # ETF没有财报日期
            if any(etf in self.ticker.upper() for etf in ['QQQ', 'SPY', 'IWM']):
                return []
                
            # 使用yahooquery获取财报信息
            calendar = self.yahoo.calendar_events
            if isinstance(calendar, dict) or calendar.empty:
                return []
            
            # 解析财报日期
            if 'earnings_date' in calendar.columns:
                dates = pd.to_datetime(calendar['earnings_date'].iloc[0], errors='coerce')
                return [d.to_pydatetime() for d in dates if d > pd.Timestamp.now()]
            
            return []
            
        except Exception as e:
            print(f"财报日历获取失败: {str(e)}")
            return []