import requests
import os
from threading import Thread

class NotificationManager:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.queue = []
        self._start_worker()

    def _send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        params = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        try:
            requests.post(url, params=params, timeout=5)
        except Exception as e:
            print(f"消息发送失败: {str(e)}")

    def _worker(self):
        while True:
            if self.queue:
                msg = self.queue.pop(0)
                self._send_telegram(msg)
            time.sleep(1)

    def _start_worker(self):
        Thread(target=self._worker, daemon=True).start()

    def notify_signal(self, signal):
        msg = f"""
        🚨 **交易信号警报** 🚨
        标的：`{signal['ticker']}`
        策略类型：`{signal['strategy_type']}`
        推荐操作：`{signal['action']}`
        预期胜率：`{signal['probability']}%`
        风险等级：`{signal['risk_level']}`
        """
        self.queue.append(msg)