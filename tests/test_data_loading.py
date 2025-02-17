import unittest
from src.data_loader import DataLoader

class TestDataLoading(unittest.TestCase):
    def setUp(self):
        self.dl = DataLoader("QQQ")
        
    def test_real_time_data(self):
        data = self.dl.get_real_time_data()
        self.assertFalse(data.empty)
        self.assertIn('Close', data.columns)
        
    def test_option_chain(self):
        chain = self.dl.fetch_option_chain()
        self.assertGreaterEqual(len(chain), 3)
        self.assertTrue({'strike', 'bid', 'ask'}.issubset(chain.columns))

if __name__ == '__main__':
    unittest.main()