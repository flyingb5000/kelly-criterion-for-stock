import json
import yfinance as yf
import pandas as pd
import numpy as np
# 设置matplotlib后端
import matplotlib
matplotlib.use('TkAgg')
# matplotlib相关导入
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import os

PORTFOLIO_FILE = 'portfolio.json'

class StockProcessor:
    def __init__(self):
        self.load_portfolio()
        
    def load_portfolio(self):
        """加载投资组合数据"""
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                self.portfolio = json.load(f)
        else:
            self.portfolio = {
                'cash': 10000,
                'stocks': [],
                'total_value': 10000
            }
            self.save_portfolio()
    
    def save_portfolio(self):
        """保存投资组合数据"""
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(self.portfolio, f, indent=4)
    
    def add_stock(self, ticker, shares, price, sentiment=None):
        """添加股票到投资组合"""
        # 检查股票代码是否有效
        try:
            stock_info = yf.Ticker(ticker).info
            current_price = stock_info.get('regularMarketPrice', price)
            if current_price is None:
                current_price = price
        except:
            current_price = price
            
        # 如果没有提供情绪参数，自动判断
        if sentiment is None:
            sentiment = self.auto_detect_sentiment(ticker)
        
        # 检查是否已存在该股票
        for stock in self.portfolio['stocks']:
            if stock['ticker'] == ticker:
                # 更新现有股票
                stock['shares'] += shares
                stock['avg_price'] = (stock['avg_price'] * (stock['shares'] - shares) + price * shares) / stock['shares']
                stock['current_price'] = current_price
                stock['value'] = stock['shares'] * stock['current_price']
                stock['sentiment'] = sentiment
                self.update_portfolio_value()
                self.save_portfolio()
                return True
        
        # 添加新股票
        new_stock = {
            'ticker': ticker,
            'shares': shares,
            'avg_price': price,
            'current_price': current_price,
            'value': shares * current_price,
            'sentiment': sentiment,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'kelly_position': 0,
            'ma_position': 0,
            'position_advice': '',
            'daily_change': 0
        }
        
        self.portfolio['stocks'].append(new_stock)
        self.update_portfolio_value()
        self.save_portfolio()
        return True
    
    def remove_stock(self, ticker):
        """从投资组合中移除股票"""
        for i, stock in enumerate(self.portfolio['stocks']):
            if stock['ticker'] == ticker:
                self.portfolio['cash'] += stock['shares'] * stock['current_price']
                self.portfolio['stocks'].pop(i)
                self.update_portfolio_value()
                self.save_portfolio()
                return True
        return False
    
    def update_shares(self, ticker, new_shares):
        """更新股票持仓数量"""
        for stock in self.portfolio['stocks']:
            if stock['ticker'] == ticker:
                price_diff = stock['current_price'] * (new_shares - stock['shares'])
                if price_diff > self.portfolio['cash'] and new_shares > stock['shares']:
                    return False  # 现金不足
                
                self.portfolio['cash'] -= price_diff
                stock['shares'] = new_shares
                stock['value'] = stock['shares'] * stock['current_price']
                stock['profit_loss'] = (stock['current_price'] - stock['avg_price']) * stock['shares']
                stock['profit_loss_percent'] = (stock['current_price'] - stock['avg_price']) / stock['avg_price'] * 100
                self.update_portfolio_value()
                self.save_portfolio()
                return True
        return False
        
    def update_avg_price(self, ticker, new_avg_price):
        """更新股票的平均价格"""
        for stock in self.portfolio['stocks']:
            if stock['ticker'] == ticker:
                stock['avg_price'] = new_avg_price
                stock['profit_loss'] = (stock['current_price'] - stock['avg_price']) * stock['shares']
                stock['profit_loss_percent'] = (stock['current_price'] - stock['avg_price']) / stock['avg_price'] * 100
                self.update_portfolio_value()
                self.save_portfolio()
                return True
        return False
    
    def update_sentiment(self, ticker, sentiment=None):
        """更新股票的市场情绪，如果不提供sentiment参数，则自动判断"""
        for stock in self.portfolio['stocks']:
            if stock['ticker'] == ticker:
                if sentiment is None:
                    # 自动判断市场情绪
                    sentiment = self.auto_detect_sentiment(ticker)
                stock['sentiment'] = sentiment
                self.save_portfolio()
                return True
        return False
        
    def get_stock_data(self, ticker, period='1y'):
        """获取股票历史数据"""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            
            # 确保当前价格信息被正确获取和更新
            if not data.empty:
                # 更新股票的当前价格
                for stock_item in self.portfolio['stocks']:
                    if stock_item['ticker'] == ticker:
                        # 获取最新收盘价作为当前价格
                        current_price = data['Close'].iloc[-1]
                        if not pd.isna(current_price):
                            stock_item['current_price'] = current_price
                            # 更新相关计算
                            stock_item['value'] = stock_item['shares'] * current_price
                            stock_item['profit_loss'] = (current_price - stock_item['avg_price']) * stock_item['shares']
                            stock_item['profit_loss_percent'] = (current_price - stock_item['avg_price']) / stock_item['avg_price'] * 100
                        break
                # 保存更新后的投资组合
                self.save_portfolio()
            
            return data
        except Exception as e:
            print(f"Error getting data for {ticker}: {e}")
            return pd.DataFrame()
            
    def plot_stock_chart(self, ticker, figure=None, period='1y'):
        """绘制股票价格图表和MACD指标"""
        data = self.get_stock_data(ticker, period=period)
        
        if data.empty:
            return None
        
        # 计算MACD
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        
        # 计算均线
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA200'] = data['Close'].rolling(window=200).mean()
        
        if figure is None:
            fig = Figure(figsize=(10, 8))
        else:
            fig = figure
            # 确保完全清除之前的图表
            fig.clear()
        
        # 调整子图比例，价格图占更多空间，MACD图放在下方
        gs = fig.add_gridspec(2, 1, height_ratios=[2, 1])
        
        # 价格子图
        ax1 = fig.add_subplot(gs[0])
        ax1.plot(data.index, data['Close'], label='Close', linewidth=1.5)
        ax1.plot(data.index, data['MA20'], label='MA20', linewidth=1.5, color='orange')
        ax1.plot(data.index, data['MA200'], label='MA200', linewidth=1.5, color='purple')
        
        # 标记当前股价
        current_price = data['Close'].iloc[-1]
        # 确保current_price是标量值而不是Series
        if isinstance(current_price, pd.Series):
            current_price = float(current_price.iloc[-1])
        
        ax1.scatter(data.index[-1], current_price, color='red', s=50, zorder=5)
        ax1.annotate(f'${current_price:.2f}', 
                    xy=(data.index[-1], current_price),
                    xytext=(10, 10),
                    textcoords='offset points',
                    fontweight='bold',
                    color='red')
        
        # 标记MA20当前值
        ma20_value = data['MA20'].iloc[-1]
        if not np.isnan(ma20_value):  # 确保MA20值不是NaN
            # 确保ma20_value是标量值
            if isinstance(ma20_value, pd.Series):
                ma20_value = float(ma20_value.iloc[-1])
                
            ax1.annotate(f'MA20: ${ma20_value:.2f}',
                        xy=(data.index[-1], ma20_value),
                        xytext=(10, -40),  # 将y方向的偏移从-20改为-40
                        textcoords='offset points',
                        fontweight='bold',
                        color='orange')
            
        # 标记MA200当前值
        ma200_value = data['MA200'].iloc[-1]
        if not np.isnan(ma200_value):  # 确保MA200值不是NaN
            if isinstance(ma200_value, pd.Series):
                ma200_value = float(ma200_value.iloc[-1])
                
            ax1.annotate(f'MA200: ${ma200_value:.2f}',
                        xy=(data.index[-1], ma200_value),
                        xytext=(10, -70),  # 在MA20下方显示
                        textcoords='offset points',
                        fontweight='bold',
                        color='purple')
        
        ax1.set_title(f'{ticker} Price Trend')
        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left')
        ax1.grid(True)
        
        # MACD子图 - 放在下方
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        ax2.plot(data.index, macd, label='MACD', color='blue', linewidth=1.2)
        ax2.plot(data.index, signal, label='Signal', color='red', linewidth=1.2)
        
        # 绘制MACD直方图
        # 确保数据是一维数组
        if isinstance(histogram, pd.Series):
            histogram = histogram.values
        
        # 创建正值和负值掩码
        positive_mask = histogram >= 0
        negative_mask = histogram < 0
        
        # 使用掩码创建正值和负值数组
        zeros = np.zeros_like(histogram)
        positive_values = np.where(positive_mask, histogram, zeros)
        negative_values = np.where(negative_mask, histogram, zeros)
        
        # 绘制直方图
        ax2.bar(data.index[positive_mask], positive_values[positive_mask], 
                color='green', alpha=0.5, label='Histogram+')
        ax2.bar(data.index[negative_mask], negative_values[negative_mask], 
                color='red', alpha=0.5, label='Histogram-')
        
        ax2.axhline(y=0, color='black', linestyle='-')
        ax2.set_title('MACD')
        ax2.set_ylabel('MACD Value')
        ax2.set_xlabel('Date')
        ax2.legend(loc='upper left')
        ax2.grid(True)
        
        fig.tight_layout()
        return fig
            
    def auto_detect_sentiment(self, ticker):
        """自动判断市场情绪（突破前高+放量、横盘震荡、放量破位）"""
        try:
            # 获取股票历史数据
            data = self.get_stock_data(ticker, period='3mo')  # 获取3个月数据
            
            if data.empty or len(data) < 20:
                return "横盘震荡"  # 数据不足时默认为横盘震荡
            
            # 计算20日最高价
            data['High_20d'] = data['High'].rolling(window=20).max()
            
            # 获取最近的价格和成交量数据
            current_price = data['Close'].iloc[-1]
            prev_price = data['Close'].iloc[-2]
            current_volume = data['Volume'].iloc[-1]
            
            # 计算20日平均成交量
            avg_volume_20d = data['Volume'].rolling(window=20).mean().iloc[-1]
            
            # 计算价格变动百分比
            price_change = (current_price - prev_price) / prev_price * 100
            
            # 判断是否放量（当日成交量超过20日平均成交量的1.5倍）
            is_high_volume = current_volume > avg_volume_20d * 1.5
            
            # 判断是否突破前高（当前价格超过20日最高价）
            is_breakout = current_price > data['High_20d'].iloc[-2]
            
            # 判断是否横盘震荡（最近5天价格波动小于3%）
            recent_prices = data['Close'].iloc[-5:]
            price_range = (recent_prices.max() - recent_prices.min()) / recent_prices.min() * 100
            is_consolidation = price_range < 3
            
            # 判断是否放量破位（放量且价格下跌超过2%）
            is_breakdown = is_high_volume and price_change < -2
            
            # 根据条件判断市场情绪
            sentiment = ""
            sentiment_reason = ""
            
            if is_breakout and is_high_volume:
                sentiment = "突破前高+放量"
                sentiment_reason = f"当前价格(${current_price:.2f})突破了20日最高价(${data['High_20d'].iloc[-2]:.2f})，且成交量(${current_volume:.0f})是20日均量(${avg_volume_20d:.0f})的{current_volume/avg_volume_20d:.1f}倍"
            elif is_breakdown:
                sentiment = "放量破位"
                sentiment_reason = f"股价下跌{abs(price_change):.2f}%，且成交量(${current_volume:.0f})是20日均量(${avg_volume_20d:.0f})的{current_volume/avg_volume_20d:.1f}倍"
            elif is_consolidation:
                sentiment = "横盘震荡"
                sentiment_reason = f"最近5天价格波动仅{price_range:.2f}%，处于盘整状态"
            else:
                sentiment = "横盘震荡"
                sentiment_reason = "未满足其他情绪条件，默认为横盘震荡"
            
            # 保存情绪判断原因
            for stock in self.portfolio['stocks']:
                if stock['ticker'] == ticker:
                    stock['sentiment_reason'] = sentiment_reason
                    break
            
            return sentiment
            
        except Exception as e:
            print(f"Error detecting sentiment for {ticker}: {e}")
            return "横盘震荡"  # 出错时默认为横盘震荡
    
    def update_portfolio_value(self):
        """更新投资组合总价值"""
        total_stock_value = sum(stock['value'] for stock in self.portfolio['stocks'])
        self.portfolio['total_value'] = self.portfolio['cash'] + total_stock_value
    
    def update_stock_prices(self):
        """更新所有股票的当前价格"""
        for stock in self.portfolio['stocks']:
            try:
                ticker_data = yf.Ticker(stock['ticker'])
                current_price = ticker_data.info.get('regularMarketPrice')
                prev_close = ticker_data.info.get('previousClose')
                
                # 确保current_price有值，如果API返回None，则使用现有价格或平均成本价
                if current_price is None:
                    current_price = stock.get('current_price', stock['avg_price'])
                
                # 确保prev_close有值，如果API返回None，则使用current_price
                if prev_close is None:
                    prev_close = current_price
                
                # 更新股票数据
                stock['current_price'] = current_price
                stock['value'] = stock['shares'] * current_price
                stock['profit_loss'] = (current_price - stock['avg_price']) * stock['shares']
                stock['profit_loss_percent'] = (current_price - stock['avg_price']) / stock['avg_price'] * 100
                stock['daily_change'] = (current_price - prev_close) / prev_close * 100
            except Exception as e:
                print(f"Error updating {stock['ticker']}: {e}")
        
        self.update_portfolio_value()
        self.save_portfolio()
    
    def get_vix_coefficient(self):
        """获取VIX波动率系数"""
        try:
            vix = yf.Ticker('^VIX')
            vix_value = vix.info.get('regularMarketPrice', 15)  # 默认值15
            
            if vix_value < 20:
                return 1.0
            elif 20 <= vix_value <= 30:
                return 1.5
            else:  # vix > 30
                return 2.0
        except:
            return 1.0  # 默认值
    
    def get_sentiment_probability(self, sentiment):
        """根据市场情绪获取上涨概率"""
        probabilities = {
            '突破前高+放量': 0.6,
            '横盘震荡': 0.5,
            '放量破位': 0.4
        }
        return probabilities.get(sentiment, 0.5)  # 默认为0.5
    
    def calculate_kelly_position(self, ticker):
        """计算凯利公式推荐的仓位比例"""
        for stock in self.portfolio['stocks']:
            if stock['ticker'] == ticker:
                sentiment_prob = self.get_sentiment_probability(stock['sentiment'])
                vix_coef = self.get_vix_coefficient()
                
                # 凯利公式: (上涨概率感官值 * 0.5) / 当前VIX波动率系数
                kelly_position = (sentiment_prob * 0.5) / vix_coef
                
                # 转换为百分比并限制在0-100%之间
                kelly_position = max(0, min(1, kelly_position)) * 100
                
                stock['kelly_position'] = kelly_position
                self.save_portfolio()
                return kelly_position
        return 0
    
    def calculate_ma_position(self, ticker):
        """计算基于均线的仓位建议"""
        try:
            # 获取股票历史数据
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=365)  # 获取一年的数据
            
            stock_data = yf.download(ticker, start=start_date, end=end_date)
            
            if len(stock_data) < 200:  # 确保有足够的数据计算200日均线
                return 0
            
            # 计算20日和200日均线
            stock_data['MA20'] = stock_data['Close'].rolling(window=20).mean()
            stock_data['MA200'] = stock_data['Close'].rolling(window=200).mean()
            
            # 获取最新价格和均线值
            latest_price = stock_data['Close'].iloc[-1]
            latest_ma20 = stock_data['MA20'].iloc[-1]
            latest_ma200 = stock_data['MA200'].iloc[-1]
            
            # 根据均线位置确定仓位
            if latest_price < latest_ma200:  # 价格在200日均线下方
                ma_position = 0
            elif latest_price < latest_ma20:  # 价格在20日均线下方
                ma_position = 5
            else:  # 价格在20日均线上方
                ma_position = 15
            
            # 更新股票信息
            for stock in self.portfolio['stocks']:
                if stock['ticker'] == ticker:
                    stock['ma_position'] = ma_position
                    self.save_portfolio()
                    break
            
            return ma_position
        except Exception as e:
            print(f"Error calculating MA position for {ticker}: {e}")
            return 0
    
    def check_macd_signal(self, ticker):
        """检查MACD信号"""
        try:
            # 获取股票历史数据
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=365)  # 获取一年的数据
            
            stock_data = yf.download(ticker, start=start_date, end=end_date)
            
            if len(stock_data) < 26:  # 确保有足够的数据计算MACD
                return 0
            
            # 计算MACD
            exp1 = stock_data['Close'].ewm(span=12, adjust=False).mean()
            exp2 = stock_data['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            
            # 检查是否金叉，使用.item()方法将Series转换为标量值再进行比较
            is_golden_cross = (macd.iloc[-2].item() < signal.iloc[-2].item()) and (macd.iloc[-1].item() > signal.iloc[-1].item())
            
            if not is_golden_cross:
                return 0
            
            # 检查是否在零轴上方
            if macd.iloc[-1] > 0:  # 零轴上方金叉
                return 5  # 加仓5%
            else:  # 零轴下方金叉
                return 3  # 加仓3%
        except Exception as e:
            print(f"Error checking MACD for {ticker}: {e}")
            return 0
    
    def check_risk_control(self, ticker):
        """检查风险控制信号"""
        for stock in self.portfolio['stocks']:
            if stock['ticker'] == ticker:
                # 检查单日波动
                if abs(stock['daily_change']) > 5:  # 单日波动大于5%
                    return {'action': 'reduce', 'percent': 50, 'reason': '单日波动大于5%（黑天鹅融断机制）'}
                
                # 检查止损
                if stock['current_price'] < stock['avg_price'] * 0.97:  # 跌破买入价3%
                    return {'action': 'sell_all', 'percent': 100, 'reason': '跌破买入价3%（止损机制）'}
                
                # 检查止盈
                if stock['profit_loss_percent'] > 15:  # 盈利达到15%
                    return {'action': 'take_profit', 'percent': 33, 'reason': '盈利达到15%（止盈机制）'}
                
                return {'action': 'hold', 'percent': 0, 'reason': '无风险控制信号'}
        return {'action': 'hold', 'percent': 0, 'reason': '无风险控制信号'}
    
    def generate_position_advice(self, ticker):
        """生成仓位建议"""
        # 计算凯利公式仓位
        kelly_position = self.calculate_kelly_position(ticker)
        
        # 计算均线仓位
        ma_position = self.calculate_ma_position(ticker)
        
        # 检查MACD信号
        macd_adjustment = self.check_macd_signal(ticker)
        
        # 检查风险控制
        risk_control = self.check_risk_control(ticker)
        
        # 生成建议
        for stock in self.portfolio['stocks']:
            if stock['ticker'] == ticker:
                # 基础建议
                advice = f"凯利公式建议仓位: {kelly_position:.1f}%, 均线建议仓位: {ma_position:.1f}%\n"
                
                # 风险控制建议
                if risk_control['action'] != 'hold':
                    advice += f"风险控制: {risk_control['reason']}, 建议{risk_control['action'] == 'reduce' and '减仓' or risk_control['action'] == 'sell_all' and '清仓' or '止盈'} {risk_control['percent']}%\n"
                
                # MACD信号
                if macd_adjustment > 0:
                    advice += f"MACD金叉信号: 建议加仓 {macd_adjustment}%\n"
                
                # 现金比例检查
                cash_ratio = self.portfolio['cash'] / self.portfolio['total_value'] * 100
                if cash_ratio < 30:
                    advice += "警告: 现金比例低于30%，建议保持足够的现金\n"
                
                # 单股仓位检查
                stock_ratio = stock['value'] / self.portfolio['total_value'] * 100
                if stock_ratio > 25:
                    advice += "警告: 单股仓位超过25%，建议分散投资\n"
                
                stock['position_advice'] = advice
                self.save_portfolio()
                return advice
        return ""
    
    def get_stock_data(self, ticker, period='1y'):
        """获取股票历史数据用于绘图"""
        try:
            data = yf.download(ticker, period=period)
            return data
        except Exception as e:
            print(f"Error getting data for {ticker}: {e}")
            return pd.DataFrame()
    
    def plot_stock_chart(self, ticker, figure=None, period='1y'):
        """绘制股票走势图和MACD图"""
        data = self.get_stock_data(ticker, period=period)
        
        if data.empty:
            return None
        
        # 计算MACD
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        
        # 计算均线
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA200'] = data['Close'].rolling(window=200).mean()
        
        if figure is None:
            fig = Figure(figsize=(10, 8))
        else:
            fig = figure
            fig.clear()
        
        # 调整子图比例，价格图占更多空间，MACD图放在下方
        gs = fig.add_gridspec(2, 1, height_ratios=[2, 1])
        
        # 价格子图
        ax1 = fig.add_subplot(gs[0])
        ax1.plot(data.index, data['Close'], label='Close', linewidth=1.5)
        ax1.plot(data.index, data['MA20'], label='MA20', linewidth=1.5, color='orange')
        ax1.plot(data.index, data['MA200'], label='MA200', linewidth=1.5, color='purple')
        
        # 标记当前股价和MA20
        current_price = float(data['Close'].iloc[-1]) if isinstance(data['Close'].iloc[-1], pd.Series) else data['Close'].iloc[-1]
        ma20_value = float(data['MA20'].iloc[-1]) if isinstance(data['MA20'].iloc[-1], pd.Series) else data['MA20'].iloc[-1]
        
        # 绘制标记点和标注
        ax1.scatter(data.index[-1], current_price, color='red', s=50, zorder=5)
        ax1.annotate(f'${current_price:.2f}', 
                    xy=(data.index[-1], current_price),
                    xytext=(10, 20),
                    textcoords='offset points',
                    fontweight='bold',
                    color='red')
        
        if not np.isnan(ma20_value):
            ax1.annotate(f'MA20: ${ma20_value:.2f}',
                        xy=(data.index[-1], ma20_value),
                        xytext=(10, -10),
                        textcoords='offset points',
                        fontweight='bold',
                        color='orange')
        
        ax1.set_title(f'{ticker} Price Trend')
        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left')
        ax1.grid(True)
        
        # MACD子图 - 放在下方
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        ax2.plot(data.index, macd, label='MACD', color='blue', linewidth=1.2)
        ax2.plot(data.index, signal, label='Signal', color='red', linewidth=1.2)
        
        # 绘制MACD直方图
        # 确保数据是一维数组
        if isinstance(histogram, pd.Series):
            histogram = histogram.values
        
        # 创建正值和负值掩码
        positive_mask = histogram >= 0
        negative_mask = histogram < 0
        
        # 使用掩码创建正值和负值数组
        zeros = np.zeros_like(histogram)
        positive_values = np.where(positive_mask, histogram, zeros)
        negative_values = np.where(negative_mask, histogram, zeros)
        
        # 绘制直方图
        ax2.bar(data.index[positive_mask], positive_values[positive_mask], 
                color='green', alpha=0.5, label='Histogram+')
        ax2.bar(data.index[negative_mask], negative_values[negative_mask], 
                color='red', alpha=0.5, label='Histogram-')
        
        ax2.axhline(y=0, color='black', linestyle='-')
        ax2.set_title('MACD')
        ax2.set_ylabel('MACD Value')
        ax2.set_xlabel('Date')
        ax2.legend(loc='upper left')
        ax2.grid(True)
        
        fig.tight_layout()
        return fig