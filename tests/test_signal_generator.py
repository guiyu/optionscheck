import pytest
from src.data_loader import DataLoader
from src.signal_generator import SignalGenerator

class TestSignalGenerator:
    @pytest.fixture
    def tsla_generator(self):
        dl = DataLoader('TSLA')
        return SignalGenerator(dl)
        
    def test_iv_scoring(self, tsla_generator):
        contract = {'iv': 0.5, 'iv_rank': 75}
        score = tsla_generator._iv_analysis_score(contract)
        assert 0 <= score <= 1
        assert score > 0.5  # 高IV应得高分
        
    def test_strategy_filtering(self, tsla_generator):
        strategies = tsla_generator.generate_top_strategies()
        assert len(strategies) <= 3
        for s in strategies:
            assert s['type'] in ['sell_put', 'bull_put_spread']
            assert s['score'] >= 50  # 合格策略最低分 