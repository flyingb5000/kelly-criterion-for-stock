# 美股仓位管理系统 / Stock Position Management System

## 项目简介 / Project Overview

这是一个基于凯利公式的美股仓位管理系统，帮助投资者优化其股票投资组合和仓位配置。

This is a US stock position management system based on the Kelly Criterion, helping investors optimize their stock portfolio and position allocation.

## 主要功能 / Main Features

### 1. 仓位管理 / Position Management
- 添加和管理股票持仓信息 / Add and manage stock positions
- 记录持股数量和现金量 / Record share holdings and cash amount
- 实时更新股票数据 / Real-time stock data updates

### 2. 策略分析 / Strategy Analysis

#### 凯利公式策略 / Kelly Criterion Strategy
- 根据市场情况动态计算最优仓位 / Dynamically calculate optimal positions based on market conditions
- 上涨概率评估 / Upward probability assessment:
  - 突破前高+放量：60% / Breakthrough with high volume: 60%
  - 横盘震荡：50% / Sideways consolidation: 50%
  - 放量破位：40% / Volume breakout: 40%

#### VIX波动率调整 / VIX Volatility Adjustment
- VIX < 20：系数1.0 / Coefficient 1.0
- VIX 20-30：系数1.5 / Coefficient 1.5
- VIX > 30：系数2.0 / Coefficient 2.0

#### 均线策略 / Moving Average Strategy
- 20日均线上方：15%仓位 / Above 20-day MA: 15% position
- 20日均线下方：5%以下仓位 / Below 20-day MA: Below 5% position
- 200日均线下方：0%仓位 / Below 200-day MA: 0% position

### 3. 风险控制 / Risk Control
- 单股仓位上限25% / Single stock position limit: 25%
- 现金保持30%以上 / Maintain cash above 30%
- 单日波动>5%触发减仓机制 / Daily volatility >5% triggers position reduction

### 4. 技术分析 / Technical Analysis
- MACD信号分析 / MACD Signal Analysis
- 股票走势图显示 / Stock Trend Chart Display

## 安装和使用 / Installation and Usage

1. 确保安装Python环境 / Ensure Python is installed
2. 运行start_stock_manager.bat启动程序 / Run start_stock_manager.bat to start the program

## 技术架构 / Technical Architecture

- UI界面：Python GUI / UI Interface: Python GUI
- 数据存储：JSON文件 / Data Storage: JSON file
- 核心模块 / Core Modules:
  - ui.py：用户界面 / User Interface
  - processor.py：数据处理 / Data Processing
  - portfolio.json：投资组合数据 / Portfolio Data

## 注意事项 / Notes

- 系统提供的建议仅供参考 / System recommendations are for reference only
- 请结合个人风险承受能力做出投资决策 / Please make investment decisions based on personal risk tolerance
- 定期备份portfolio.json文件 / Regularly backup portfolio.json file