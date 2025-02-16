#!/usr/bin/env python3
import time
import schedule
import logging
from pathlib import Path
import telegram
from src.data_loader import DataLoader
from src.signal_generator import SignalGenerator
from src.risk_manager import RiskManager
import yaml
import os

# 配置日志
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "options_scanner.log"),
        logging.StreamHandler() if log_level == 'DEBUG' else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptionsScanner:
    def __init__(self):
        self.config = self._load_config()
        self.bot = self._setup_telegram()
        
    def _load_config(self):
        with open('config/config.yaml') as f:
            return yaml.safe_load(f)
            
    def _setup_telegram(self):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.warning("Telegram bot token not found")
            return None
        return telegram.Bot(token)
    
    def scan_ticker(self, ticker):
        """扫描单个股票"""
        try:
            dl = DataLoader(ticker)
            sg = SignalGenerator(dl)
            rm = RiskManager(dl.config['strategy'])
            
            # 获取必要数据
            earnings_dates = dl.get_earnings_dates()
            option_chain = dl.fetch_option_chain()
            
            # 风险检查
            if rm.check_event_risk(earnings_dates):
                return
                
            # 生成信号
            signal = sg.generate_vertical_spread_signal()
            
            if signal and rm.check_greeks(signal['greeks']):
                message = (
                    f"🎯 交易信号生成成功\n"
                    f"策略类型: {signal['strategy_type']}\n"
                    f"建议行权价: {signal['strikes']}\n"
                    f"预期胜率: {signal['probability']}%"
                )
                
                # 发送到Telegram
                if self.bot:
                    self.bot.send_message(
                        chat_id=os.getenv('TELEGRAM_CHAT_ID'),
                        text=message
                    )
                else:
                    print(message)
                    
        except Exception as e:
            logger.error(f"扫描 {ticker} 时发生错误: {str(e)}", exc_info=True)
    
    def scan_all(self):
        """扫描所有观察列表股票"""
        for ticker in self.config['watchlist']:
            self.scan_ticker(ticker)

def main():
    scanner = OptionsScanner()
    
    # 立即执行一次
    scanner.scan_all()
    
    # 设置定时任务
    schedule.every(1).minutes.do(scanner.scan_all)
    
    # 持续运行
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()