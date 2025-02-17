# 智能期权交易系统

![系统架构图](docs/architecture/flowchart.png)

## 功能特性
- 多维度策略分析（波动率、基本面、技术面等）
- 实时风险管理体系
- 策略回测与优化
- 自动再平衡机制
- 实时监控告警

## 快速开始
### 本地运行
```bash
pip install -r requirements.txt
python -m src.cli --ticker TSLA
```

### 生产部署
```bash
# Kubernetes部署
kubectl apply -f deploy/k8s/

# AWS Fargate部署
terraform -chdir=deploy/aws apply
```

## 核心模块
| 模块                | 功能描述                     |
|---------------------|----------------------------|
| `signal_generator`  | 生成交易策略                 |
| `risk_manager`      | 多维度风险控制               |
| `data_pipeline`     | 实时数据流处理               |
| `portfolio_rebalancer` | 自动调仓                 |

## 详细使用指南

### 1. 本地测试方案
```bash
# 运行单元测试
pytest tests/unit/

# 执行集成测试
pytest tests/integration/

# 性能基准测试
pytest tests/performance/ -m "not slow"
```

### 2. 数据回测方案
```python
from src.backtest import StrategyBacktester

backtester = StrategyBacktester(config)
backtester.load_data('TSLA', '2023-01-01', '2024-01-01')
results = backtester.run_backtest()
results.plot_performance()
```

### 3. 正式调用方案
#### CLI方式
```bash
python -m src.cli --ticker NVDA --strategy vertical_spread
```

#### API方式
```python
from src.core.interface import TradingSystem

system = TradingSystem('SPY')
strategies = system.get_recommendations()
print(f"推荐策略: {strategies[0]}")
```

### 4. 生产部署方案
#### 容器部署
```dockerfile
FROM python:3.9-slim
COPY . /app
RUN pip install -r requirements.txt
CMD ["python", "-m", "src.daemon"]
```

#### 云原生部署
```yaml
# Kubernetes部署配置示例
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: option-system
        image: registry.example.com/option-system:v1.3
        resources:
          limits:
            cpu: "1"
            memory: "2Gi"
```

## 监控告警
配置Prometheus监控规则：
```yaml
- alert: HighLatency
  expr: system_latency_seconds{quantile="0.95"} > 2
  for: 5m
  labels:
    severity: critical
```

## 版本规划
| 版本   | 功能                  | 预计上线时间 |
|--------|----------------------|-------------|
| v1.3   | 基础策略引擎          | 2025-Q2     |
| v2.0   | 机器学习优化          | 2025-Q3     |
| v3.0   | 实盘交易接口          | 2025-Q4     |

## 贡献指南
1. Fork项目仓库
2. 创建特性分支 (`git checkout -b feature/awesome`)
3. 提交修改 (`git commit -am 'Add awesome feature'`)
4. 推送到分支 (`git push origin feature/awesome`)
5. 创建Pull Request

## 许可协议
[MIT License](LICENSE)

> 📌 注意：实盘交易前请充分测试策略，建议初始资金不超过总资金的2%