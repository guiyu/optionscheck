from yahooquery import Ticker
import pandas as pd
import yaml
import os
from datetime import datetime
import requests
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, ticker):
        self.ticker = ticker
        self.config = self._load_config()
        self.yahoo = Ticker(
            ticker, 
            asynchronous=True,
            formatted=False,
            retry=int(os.getenv('YAHOO_RETRIES', 5)),
            backoff_factor=float(os.getenv('YAHOO_BACKOFF', 0.3))
        )
    
    def _load_config(self):
        """加载配置，优先使用环境变量"""
        with open('config/config.yaml') as f:
            config = yaml.safe_load(f)
            
        # 使用环境变量覆盖配置文件
        if 'strategy' in config:
            config['strategy'].update({
                'iv_percentile_threshold': float(os.getenv('STRATEGY_IV_THRESHOLD', 
                    config['strategy'].get('iv_percentile_threshold', 60))),
                'min_volume': int(os.getenv('STRATEGY_MIN_VOLUME',
                    config['strategy'].get('min_volume', 100))),
                'max_spread_ratio': float(os.getenv('STRATEGY_MAX_SPREAD',
                    config['strategy'].get('max_spread_ratio', 0.1))),
                'max_vega': float(os.getenv('STRATEGY_MAX_VEGA',
                    config['strategy'].get('max_vega', 0.5)))
            })
            
        return config
    
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
    
    def fetch_option_chain(self, expiration=None):
        """获取完整期权链数据"""
        try:
            logger.debug(f"开始获取 {self.ticker} 期权数据")
            
            # 获取期权链
            chains = self.yahoo.option_chain
            if isinstance(chains, dict) or chains.empty:
                logger.debug(f"{self.ticker} 无可用期权数据")
                return pd.DataFrame()
            
            # 获取可用的期权到期日
            expiration_dates = chains.index.get_level_values('expiration').unique()
            logger.debug(f"可用的期权到期日: {expiration_dates.tolist()}")
            
            # 如果没有指定到期日，使用最近的到期日
            if expiration is None:
                expiration = expiration_dates[0]
                logger.debug(f"使用最近到期日: {expiration}")
            elif expiration not in expiration_dates:
                logger.debug(f"警告: 指定的到期日 {expiration} 不可用")
                return pd.DataFrame()
            
            try:
                # 获取指定到期日的数据
                exp_chains = chains[chains.index.get_level_values('expiration') == expiration]
                
                # 分离看涨和看跌期权
                # 检查数据结构
                logger.debug("\n数据结构信息:")
                logger.debug(f"列名: {exp_chains.columns.tolist()}")
                logger.debug(f"索引: {exp_chains.index.names}")
                logger.debug(f"样本数据:\n{exp_chains.head(1)}")
                
                # 根据索引级别分离看涨和看跌期权
                calls = exp_chains.xs('calls', level='optionType').assign(type='call')
                puts = exp_chains.xs('puts', level='optionType').assign(type='put')
                
                logger.debug(f"\n期权数据获取成功:")
                logger.debug(f"看涨期权数量: {len(calls)}")
                logger.debug(f"看跌期权数量: {len(puts)}")
                
                # 合并数据
                option_chain = pd.concat([calls, puts])
                
                # 添加到期日和剩余天数
                option_chain['expiration'] = expiration
                option_chain['days_to_expire'] = (
                    pd.to_datetime(expiration) - pd.Timestamp.now()
                ).days
                
                # 标准化列名
                column_mapping = {
                    'strike': 'strike',
                    'lastPrice': 'lastPrice',
                    'bid': 'bid',
                    'ask': 'ask',
                    'volume': 'volume',
                    'impliedVolatility': 'impliedVolatility',
                }
                
                # 重命名列
                option_chain = option_chain.rename(columns=column_mapping)
                
                # 确保所需列都存在
                required_cols = ['strike', 'bid', 'ask', 'volume', 'impliedVolatility',
                               'type', 'expiration', 'days_to_expire']
                
                for col in required_cols:
                    if col not in option_chain.columns:
                        logger.debug(f"添加缺失的列: {col}")
                        option_chain[col] = 0
                
                # 数据类型转换
                numeric_cols = ['strike', 'bid', 'ask', 'volume', 'impliedVolatility']
                for col in numeric_cols:
                    option_chain[col] = pd.to_numeric(option_chain[col], errors='coerce').fillna(0)
                
                result = option_chain[required_cols].reset_index(drop=True)
                
                logger.debug(f"\n最终数据信息:")
                logger.debug(f"总行数: {len(result)}")
                logger.debug(f"列名: {result.columns.tolist()}")
                if not result.empty:
                    logger.debug(f"样本数据:\n{result.head(1)}")
                
                return result
                
            except Exception as e:
                logger.error(f"处理期权数据失败: {str(e)}", exc_info=True)
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取期权链失败: {str(e)}", exc_info=True)
            return pd.DataFrame()
    
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