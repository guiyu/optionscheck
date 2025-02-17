class StrategyDashboard:
    def __init__(self):
        self.figures = {}
        
    def create_main_view(self):
        """创建策略监控主面板"""
        layout = [
            [self._create_control_panel()],
            [self._create_strategy_matrix()],
            [self._create_risk_indicator()]
        ]
        return layout
    
    def _create_strategy_matrix(self):
        """策略矩阵可视化"""
        return sg.Table(
            headings=['排名', '类型', '胜率', '行权价', '风险等级'],
            values=self._get_current_strategies(),
            auto_size_columns=True
        )
    
    def _create_risk_indicator(self):
        """风险指标仪表盘"""
        return sg.Graph(
            canvas_size=(400, 200),
            graph_bottom_left=(0,0),
            graph_top_right=(400,200),
            background_color='lightgray'
        ) 