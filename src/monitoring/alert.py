class TradingAlerts:
    def __init__(self, config):
        self.thresholds = config['alerts']
        self.notifier = NotificationManager()
        
    def check_strategy_quality(self, strategies):
        """策略质量监控"""
        if len(strategies) < 1:
            self.notifier.send_alert("无有效策略生成")
        elif strategies[0]['score'] < 50:
            self.notifier.send_alert(f"最佳策略得分过低: {strategies[0]['score']}")
            
    def monitor_latency(self, latency_stats):
        """延迟监控"""
        if latency_stats['95th'] > 2.0:
            self.notifier.send_alert(f"系统延迟过高: {latency_stats['95th']}秒") 