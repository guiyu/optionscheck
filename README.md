# 智能期权交易系统

## 系统架构设计
![架构图](https://via.placeholder.com/800x400.png?text=Option+Trading+System+Architecture)

### 设计模式
1. **观察者模式** - 市场数据变动时自动通知策略引擎
2. **策略模式** - 不同交易策略可插拔替换
3. **工厂模式** - 期权合约对象的统一创建
4. **装饰器模式** - 风险控制规则的动态叠加

### 数据流
1. 数据层：Yahoo Finance/Polygon → DataLoader
2. 处理层：SignalGenerator + RiskManager
3. 输出层：Telegram通知/日志记录

### 核心模块
| 模块 | 职责 | 关键技术 |
|------|-----|---------|
| DataLoader | 实时数据采集 | yfinance, API轮询 |
| VolatilityEngine | 波动率分析 | GARCH模型, IV曲面拟合 | 
| GreekCalculator | 风险指标计算 | 自动微分, 数值逼近 |
| TelegramBot | 消息通知 | 异步IO, 消息队列 |

### 策略图
graph TD
    A[启动守护进程] --> B[轮询标的列表]
    B --> C{符合条件?}
    C -->|Yes| D[执行策略分析]
    D --> E[风险检查]
    E --> F[生成信号]
    F --> G[发送Telegram通知]
    C -->|No| H[等待下一周期]

## 部署指南

### 后台服务运行
```bash
# 复制系统服务文件
sudo cp systemd/option_trading.service /etc/systemd/system/

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start option_trading