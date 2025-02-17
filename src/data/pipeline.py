class DataPipeline:
    def __init__(self):
        self.cache = RedisCache()
        self.stream = KafkaStream()
        
    def process_real_time_data(self):
        """实时数据处理流程"""
        while True:
            raw_data = self.stream.consume()
            cleaned = self._clean_data(raw_data)
            enriched = self._enrich_with_factors(cleaned)
            self.cache.update(enriched)
            
    def _enrich_with_factors(self, data):
        """添加量化因子"""
        data['iv_rank'] = self._calculate_iv_rank(data)
        data['sector_beta'] = self._calculate_sector_beta(data)
        return data 