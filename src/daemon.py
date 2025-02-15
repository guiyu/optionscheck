import time
import yaml
from .data_loader import DataLoader
from .signal_generator import SignalGenerator
from .notification import NotificationManager

class TradingDaemon:
    def __init__(self):
        self.load_config()
        self.notifier = NotificationManager()
        self.interval = self.config['daemon']['polling_interval']
        self.watchlist = self.config['watchlist']

    def load_config(self):
        with open('config/config.yaml') as f:
            self.config = yaml.safe_load(f)

    def run_forever(self):
        while True:
            for ticker in self.watchlist:
                try:
                    dl = DataLoader(ticker)
                    sg = SignalGenerator(dl)
                    
                    if signal := sg.generate_vertical_spread_signal():
                        self.notifier.notify_signal(signal)
                        
                except Exception as e:
                    print(f"处理{ticker}时出错: {str(e)}")
            
            time.sleep(self.interval * 60)

if __name__ == "__main__":
    td = TradingDaemon()
    td.run_forever()