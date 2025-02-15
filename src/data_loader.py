import yfinance as yf
import pandas as pd
import yaml
import os
from datetime import datetime
import requests

class DataLoader:
    def __init__(self, ticker):
        self.ticker = ticker
        self.config = self._load_config()
        # 添加自定义请求头
        self.stock = yf.Ticker(ticker, session=self._get_session())
    
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
            df = self.stock.history(period='1d', interval=interval)
            if df.empty:
                return pd.DataFrame()
            
            # 只保留需要的列
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            return df.dropna()
        except Exception as e:
            print(f"数据获取失败: {str(e)}")
            return pd.DataFrame()
    
    def fetch_option_chain(self, expiration=None):
        """获取完整期权链数据"""
        try:
            print("\n开始获取期权数据...")
            print(f"股票代码: {self.ticker}")
            
            # 获取可用的期权到期日
            print("\n尝试获取期权到期日...")
            try:
                expiration_dates = self.stock.options
                if not expiration_dates:
                    print(f"警告: {self.ticker} 没有可用的期权到期日")
                    return pd.DataFrame()
                print(f"可用的期权到期日: {expiration_dates}")
            except Exception as e:
                print(f"获取期权到期日失败: {str(e)}")
                return pd.DataFrame()
            
            # 如果没有指定到期日，使用最近的到期日
            if expiration is None:
                expiration = expiration_dates[0]
                print(f"使用最近到期日: {expiration}")
            elif expiration not in expiration_dates:
                print(f"警告: 指定的到期日 {expiration} 不可用")
                return pd.DataFrame()
            
            # 获取期权链数据
            print(f"\n获取 {expiration} 到期的期权数据...")
            try:
                # 直接获取指定到期日的期权链
                option_chain = self.stock.option_chain(expiration)
                if option_chain is None:
                    print("期权链数据获取失败")
                    return pd.DataFrame()
                
                # 获取看涨和看跌期权
                calls = option_chain.calls
                puts = option_chain.puts
                
                print(f"期权数据获取成功:")
                print(f"看涨期权数量: {len(calls)}")
                print(f"看跌期权数量: {len(puts)}")
                print(f"看涨期权列名: {calls.columns.tolist()}")
                
                # 添加期权类型和到期日
                calls = calls.assign(
                    type='call',
                    expiration=expiration,
                    days_to_expire=(pd.to_datetime(expiration) - pd.Timestamp.now()).days
                )
                puts = puts.assign(
                    type='put',
                    expiration=expiration,
                    days_to_expire=(pd.to_datetime(expiration) - pd.Timestamp.now()).days
                )
                
                # 合并数据
                chains = pd.concat([calls, puts])
                
                # 确保所需列都存在
                required_cols = ['strike', 'bid', 'ask', 'volume', 'impliedVolatility',
                               'type', 'expiration', 'days_to_expire']
                
                # 处理列名差异
                if 'impliedVolatility' not in chains.columns:
                    if 'implied_volatility' in chains.columns:
                        chains['impliedVolatility'] = chains['implied_volatility']
                    else:
                        print("警告: 缺少隐含波动率数据")
                        chains['impliedVolatility'] = 0
                
                # 确保所有必需列存在
                for col in required_cols:
                    if col not in chains.columns:
                        print(f"添加缺失的列: {col}")
                        chains[col] = 0
                
                # 选择所需列并重置索引
                result = chains[required_cols].reset_index(drop=True)
                
                # 数据类型转换
                numeric_cols = ['strike', 'bid', 'ask', 'volume', 'impliedVolatility']
                for col in numeric_cols:
                    result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0)
                
                print(f"\n最终数据信息:")
                print(f"总行数: {len(result)}")
                print(f"列名: {result.columns.tolist()}")
                if not result.empty:
                    print(f"样本数据:\n{result.head(1)}")
                
                return result
                
            except Exception as e:
                print(f"获取期权链数据失败: {str(e)}")
                return pd.DataFrame()
            
        except Exception as e:
            print(f"\n获取期权链时发生错误: {str(e)}")
            print(f"错误类型: {type(e)}")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return pd.DataFrame()
    
    def get_earnings_dates(self):
        """获取财报日历"""
        try:
            # 使用 yfinance 的财报日历功能
            earnings_dates = self.stock.earnings_dates
            if earnings_dates is None or earnings_dates.empty:
                return []
            
            # 获取未来的财报日期
            future_dates = earnings_dates.copy()  # 创建副本避免修改原始数据
            # 只保留日期索引列
            future_dates = future_dates.index[future_dates.index > pd.Timestamp.now()]
            return [d.to_pydatetime() for d in future_dates]
            
        except Exception as e:
            print(f"财报日历获取失败: {str(e)}")
            # ETF没有财报日期
            if 'QQQ' in self.ticker or 'SPY' in self.ticker:
                return []
            # 尝试从其他属性获取
            try:
                next_earnings = self.stock.calendar.iloc[0]['Earnings Date']
                if pd.notnull(next_earnings):
                    return [next_earnings.to_pydatetime()]
            except:
                pass
            return []