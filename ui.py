import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
# matplotlib相关导入
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import pandas as pd
import numpy as np
from processor import StockProcessor

class StockPortfolioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("美股仓位管理系统")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # 初始化处理器
        self.processor = StockProcessor()
        
        # 创建主框架
        self.create_main_frame()
        
        # 创建菜单
        self.create_menu()
        
        # 加载股票数据
        self.load_stocks()
        
        # 自动更新线程
        self.update_thread = None
        self.stop_thread = False
        
    def create_main_frame(self):
        # 创建左侧和右侧框架
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧框架 - 股票列表
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # 右侧框架 - 详细信息和图表
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=2)
        
        # 创建股票列表
        self.create_stock_list()
        
        # 创建详细信息区域
        self.create_detail_frame()
        
        # 创建图表区域
        self.create_chart_frame()
        
    def create_chart_frame(self):
        # Chart frame
        self.chart_frame = tk.LabelFrame(self.right_frame, text="Stock Chart", bg="#f0f0f0", font=("Arial", 12, "bold"))
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create figure for matplotlib
        self.figure = plt.Figure(figsize=(6, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.figure, self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initial chart message
        self.ax.text(0.5, 0.5, "Select a stock to view chart", ha="center", va="center", fontsize=12)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def update_chart(self, ticker):
        """更新股票图表"""
        if not ticker:
            return
        
        # 清除旧图表
        self.figure.clear()
        
        # 创建子图
        gs = self.figure.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.3)
        ax1 = self.figure.add_subplot(gs[0])
        ax2 = self.figure.add_subplot(gs[1])
        
        # 获取历史数据
        hist = self.processor.get_stock_data(ticker)
        if hist.empty:
            # 如果没有数据，显示提示信息
            self.ax.text(0.5, 0.5, "Unable to get stock data", ha="center", va="center", fontsize=12)
            self.canvas.draw()
            return
            
        dates = hist.index
        
        # 绘制K线图
        from mplfinance.original_flavor import candlestick_ohlc
        import matplotlib.dates as mdates

        hist['Date_Num'] = mdates.date2num(hist.index.to_pydatetime())
        ohlc = hist[['Date_Num', 'Open', 'High', 'Low', 'Close']].values

        candlestick_ohlc(ax1, ohlc, width=0.6,
                        colorup='#4CAF50', colordown='#F44336',
                        alpha=1.0)

        ax1.plot(dates, hist['Close'].rolling(window=20).mean(), label='20-day MA', color='#FFA726', linestyle='--')
        ax1.set_title(f"{ticker} Price Trend", pad=15)
        ax1.set_ylabel("Price (USD)")
        ax1.legend(loc='upper left', framealpha=0.8)
        ax1.grid(True, alpha=0.3)
        
        # 计算并绘制MACD
        exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
        exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist_macd = macd - signal
        
        # 使用numpy的方式处理MACD直方图，避免Series比较的问题
        import numpy as np
        # 确保数据是一维数组
        if isinstance(hist_macd, pd.Series):
            hist_macd_values = hist_macd.values
        else:
            hist_macd_values = hist_macd
            
        # 创建正值和负值掩码
        positive_mask = hist_macd_values >= 0
        negative_mask = hist_macd_values < 0
        
        # 使用掩码绘制直方图 - 修复索引错误
        try:
            # 安全地绘制MACD直方图
            positive_dates = [dates[i] for i in range(len(dates)) if i < len(hist_macd_values) and hist_macd_values[i] >= 0]
            positive_values = [hist_macd_values[i] for i in range(len(dates)) if i < len(hist_macd_values) and hist_macd_values[i] >= 0]
            
            negative_dates = [dates[i] for i in range(len(dates)) if i < len(hist_macd_values) and hist_macd_values[i] < 0]
            negative_values = [hist_macd_values[i] for i in range(len(dates)) if i < len(hist_macd_values) and hist_macd_values[i] < 0]
            
            # 分别绘制正值和负值
            if positive_dates:
                ax2.bar(positive_dates, positive_values, color='#4CAF50', alpha=0.7, width=1)
            if negative_dates:
                ax2.bar(negative_dates, negative_values, color='#F44336', alpha=0.7, width=1)
        except Exception as e:
            print(f"Error plotting MACD histogram: {e}")
            # 如果出现任何错误，跳过直方图绘制
            pass
        
        ax2.plot(dates, macd, label='MACD', color='#2196F3', linewidth=1.5)
        ax2.plot(dates, signal, label='Signal', color='#FF9800', linewidth=1.5)
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.2)
        ax2.set_xlabel("Date")
        ax2.set_ylabel("MACD")
        ax2.legend(loc='upper left', framealpha=0.8)
        ax2.grid(True, alpha=0.3)
        
        ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
        ax2.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
        self.figure.autofmt_xdate()
        
        # 获取当前价格和持仓信息
        try:
            current_price = hist['Close'].iloc[-1]
            position = 0
            ideal_position = 0
            
            # 查找当前持仓
            for stock in self.processor.portfolio['stocks']:
                if stock['ticker'] == ticker:
                    position = stock['shares']
                    break
                    
            # 计算理想持仓（如果processor有相关方法）
            try:
                ideal_position = round(self.processor.calculate_kelly_position(ticker) * 
                                      self.processor.portfolio['total_value'] / 100.0 / current_price)
            except:
                ideal_position = 0
            
            info_text = f"Current: {position} shares\nIdeal: {ideal_position} shares\nPrice: USD{current_price:.2f}"
            ax1.text(0.02, 0.02, info_text, transform=ax1.transAxes, bbox=dict(facecolor='white', alpha=0.7))
        except Exception as e:
            print(f"Error displaying position info: {e}")
        
        # 强制刷新画布
        self.canvas.draw()
        try:
            # 尝试使用flush_events强制处理事件
            self.canvas.flush_events()
        except:
            pass  # 某些版本的matplotlib可能不支持flush_events
        
        # 强制更新图表框架
        self.chart_frame.update()
        self.chart_frame.update_idletasks()
        self.canvas.draw()
        
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="添加股票", command=self.add_stock)
        file_menu.add_command(label="更新所有股票价格", command=self.update_all_stocks)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="开始自动更新", command=self.start_auto_update)
        tools_menu.add_command(label="停止自动更新", command=self.stop_auto_update)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
        
    def create_stock_list(self):
        # 创建标题框架
        title_frame = ttk.Frame(self.left_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(title_frame, text="投资组合", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=5)
        
        # 创建现金和总价值显示框架
        info_frame = ttk.Frame(self.left_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        # 现金显示和编辑
        cash_frame = ttk.Frame(info_frame)
        cash_frame.grid(row=0, column=0, sticky=tk.W, padx=5, columnspan=2)
        
        ttk.Label(cash_frame, text="现金:").pack(side=tk.LEFT, padx=2)
        self.cash_label = ttk.Label(cash_frame, text="$0")
        self.cash_label.pack(side=tk.LEFT, padx=2)
        
        # 添加编辑现金按钮
        self.edit_cash_button = ttk.Button(cash_frame, text="编辑", width=5, command=self.edit_cash)
        self.edit_cash_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(info_frame, text="总价值:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.total_value_label = ttk.Label(info_frame, text="$0")
        self.total_value_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # 创建股票列表
        columns = ("股票代码", "股价", "持股数", "市值", "盈亏%", "日涨跌%", "情绪")
        self.stock_tree = ttk.Treeview(self.left_frame, columns=columns, show="headings", height=20)
        
        # 设置列宽和标题
        self.stock_tree.column("股票代码", width=80)
        self.stock_tree.column("股价", width=80)
        self.stock_tree.column("持股数", width=80)
        self.stock_tree.column("市值", width=80)
        self.stock_tree.column("盈亏%", width=80)
        self.stock_tree.column("日涨跌%", width=80)
        self.stock_tree.column("情绪", width=100)
        
        for col in columns:
            self.stock_tree.heading(col, text=col)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.stock_tree.bind("<<TreeviewSelect>>", self.on_stock_select)
        
        # 绑定右键菜单
        self.stock_tree.bind("<Button-3>", self.show_context_menu)
        
    def create_detail_frame(self):
        # 创建详细信息框架
        self.detail_frame = ttk.LabelFrame(self.right_frame, text="股票详细信息")
        self.detail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建详细信息网格
        self.detail_grid = ttk.Frame(self.detail_frame)
        self.detail_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # 第一行
        ttk.Label(self.detail_grid, text="股票代码:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.ticker_label = ttk.Label(self.detail_grid, text="-")
        self.ticker_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(self.detail_grid, text="当前价格:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.price_label = ttk.Label(self.detail_grid, text="-")
        self.price_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(self.detail_grid, text="持股数量:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=2)
        self.shares_label = ttk.Label(self.detail_grid, text="-")
        self.shares_label.grid(row=0, column=5, sticky=tk.W, padx=5, pady=2)
        # 添加编辑持股数量按钮
        self.edit_shares_button = ttk.Button(self.detail_grid, text="编辑", width=5, 
                                          command=lambda: self.edit_shares(self.ticker_label.cget("text")))
        self.edit_shares_button.grid(row=0, column=6, sticky=tk.W, padx=5, pady=2)
        
        # 第二行
        ttk.Label(self.detail_grid, text="平均成本:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.avg_price_label = ttk.Label(self.detail_grid, text="-")
        self.avg_price_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        # 添加编辑平均成本按钮
        self.edit_avg_price_button = ttk.Button(self.detail_grid, text="编辑", width=5, 
                                             command=lambda: self.edit_avg_price(self.ticker_label.cget("text")))
        self.edit_avg_price_button.grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(self.detail_grid, text="市值:").grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        self.value_label = ttk.Label(self.detail_grid, text="-")
        self.value_label.grid(row=1, column=4, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(self.detail_grid, text="盈亏:").grid(row=1, column=5, sticky=tk.W, padx=5, pady=2)
        self.profit_loss_label = ttk.Label(self.detail_grid, text="-")
        self.profit_loss_label.grid(row=1, column=6, sticky=tk.W, padx=5, pady=2)
        
        # 第三行
        ttk.Label(self.detail_grid, text="市场情绪:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        
        # 创建只读标签显示市场情绪
        self.sentiment_var = tk.StringVar()
        self.sentiment_label = ttk.Label(self.detail_grid, textvariable=self.sentiment_var)
        self.sentiment_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 添加情绪解释按钮
        self.explain_button = ttk.Button(self.detail_grid, text="查看情绪解释", command=self.show_sentiment_explanation)
        self.explain_button.grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        
        # 更新按钮
        self.update_button = ttk.Button(self.detail_grid, text="更新股价", command=self.update_selected_stock)
        self.update_button.grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        # 计算建议按钮
        self.advice_button = ttk.Button(self.detail_grid, text="计算仓位建议", command=self.calculate_position_advice)
        self.advice_button.grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        # 仓位建议框架
        self.advice_frame = ttk.LabelFrame(self.right_frame, text="仓位建议")
        self.advice_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 仓位建议文本框
        self.advice_text = tk.Text(self.advice_frame, height=6, wrap=tk.WORD)
        self.advice_text.pack(fill=tk.X, padx=10, pady=10)
        self.advice_text.config(state=tk.DISABLED)
        
    def load_stocks(self):
        # 清空现有数据
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        # 更新现金和总价值
        self.cash_label.config(text=f"${self.processor.portfolio['cash']:.2f}")
        self.total_value_label.config(text=f"${self.processor.portfolio['total_value']:.2f}")
        
        # 添加股票到列表
        for stock in self.processor.portfolio['stocks']:
            values = (
                stock['ticker'],
                f"${stock['current_price']:.2f}",
                stock['shares'],
                f"${stock['value']:.2f}",
                f"{stock['profit_loss_percent']:.2f}%",
                f"{stock['daily_change']:.2f}%",
                stock['sentiment']
            )
            
            # 设置颜色
            tags = ()
            if stock['profit_loss_percent'] > 0:
                tags = ("profit",)
            elif stock['profit_loss_percent'] < 0:
                tags = ("loss",)
                
            self.stock_tree.insert("", tk.END, values=values, tags=tags)
        
        # 设置颜色
        self.stock_tree.tag_configure("profit", foreground="green")
        self.stock_tree.tag_configure("loss", foreground="red")
        
    def on_stock_select(self, event):
        # 获取选中的项目
        selection = self.stock_tree.selection()
        if not selection:
            return
            
        # 获取选中的股票代码
        item = self.stock_tree.item(selection[0])
        ticker = item['values'][0]
        
        # 查找股票数据
        selected_stock = None
        for stock in self.processor.portfolio['stocks']:
            if stock['ticker'] == ticker:
                selected_stock = stock
                break
                
        if not selected_stock:
            return
            
        # 更新详细信息
        self.ticker_label.config(text=selected_stock['ticker'])
        self.price_label.config(text=f"${selected_stock['current_price']:.2f}")
        self.shares_label.config(text=str(selected_stock['shares']))
        self.avg_price_label.config(text=f"${selected_stock['avg_price']:.2f}")
        self.value_label.config(text=f"${selected_stock['value']:.2f}")
        
        profit_loss_text = f"${selected_stock['profit_loss']:.2f} ({selected_stock['profit_loss_percent']:.2f}%)"
        if selected_stock['profit_loss'] > 0:
            self.profit_loss_label.config(text=profit_loss_text, foreground="green")
        elif selected_stock['profit_loss'] < 0:
            self.profit_loss_label.config(text=profit_loss_text, foreground="red")
        else:
            self.profit_loss_label.config(text=profit_loss_text, foreground="black")
            
        # 设置情绪标签
        self.sentiment_var.set(selected_stock['sentiment'])
        
        # 更新仓位建议
        self.advice_text.config(state=tk.NORMAL)
        self.advice_text.delete(1.0, tk.END)
        self.advice_text.insert(tk.END, selected_stock['position_advice'])
        self.advice_text.config(state=tk.DISABLED)
        
        # 确保所有标签都更新到最新状态
        self.detail_frame.update_idletasks()
        
        # 更新图表 - 强制重绘
        self.figure.clear()  # 确保先清除旧图表
        
        # 强制处理所有待处理的事件，确保UI状态更新
        self.root.update()
        self.root.update_idletasks()
        
        # 调用更新图表方法
        self.update_chart(ticker)
        
        # 强制刷新画布并处理事件，确保图表立即显示
        self.canvas.draw()
        try:
            self.canvas.flush_events()
        except:
            pass  # 某些版本的matplotlib可能不支持flush_events
        
        # 强制处理所有待处理的事件并更新整个窗口
        self.root.update()
        self.root.update_idletasks()
        
        # 确保图表框架完全更新
        self.chart_frame.update()
        self.chart_frame.update_idletasks()
        
        # 再次强制刷新画布，确保图表显示
        try:
            self.canvas.draw_idle()
        except:
            self.canvas.draw()  # 备选方案
        
    def add_stock(self):
        # 创建添加股票对话框
        add_window = tk.Toplevel(self.root)
        add_window.title("添加股票")
        add_window.geometry("400x200")
        add_window.resizable(False, False)
        add_window.transient(self.root)
        add_window.grab_set()
        
        # 创建表单
        ttk.Label(add_window, text="股票代码:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        ticker_entry = ttk.Entry(add_window, width=20)
        ticker_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        ttk.Label(add_window, text="股票价格:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        price_entry = ttk.Entry(add_window, width=20)
        price_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        
        ttk.Label(add_window, text="持股数量:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        shares_entry = ttk.Entry(add_window, width=20)
        shares_entry.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 添加按钮
        def on_add():
            try:
                ticker = ticker_entry.get().strip().upper()
                price = float(price_entry.get().strip())
                shares = int(shares_entry.get().strip())
                
                if not ticker or price <= 0 or shares <= 0:
                    messagebox.showerror("错误", "请输入有效的股票信息")
                    return
                    
                # 添加股票（不传递情绪参数，由系统自动判断）
                success = self.processor.add_stock(ticker, shares, price)
                if success:
                    messagebox.showinfo("成功", f"已添加股票 {ticker}")
                    add_window.destroy()
                    self.load_stocks()  # 刷新列表
                else:
                    messagebox.showerror("错误", "添加股票失败")
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        ttk.Button(add_window, text="添加", command=on_add).grid(row=3, column=0, padx=10, pady=20)
        ttk.Button(add_window, text="取消", command=add_window.destroy).grid(row=3, column=1, padx=10, pady=20)
        
    def update_selected_stock(self):
        # 获取选中的项目
        selection = self.stock_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个股票")
            return
            
        # 获取选中的股票代码
        item = self.stock_tree.item(selection[0])
        ticker = item['values'][0]
        
        # 更新股票价格
        self.processor.update_stock_prices()
        
        # 自动更新市场情绪
        self.processor.update_sentiment(ticker)
        
        self.load_stocks()
        
        # 重新选择该股票
        for item in self.stock_tree.get_children():
            values = self.stock_tree.item(item, 'values')
            if values[0] == ticker:
                self.stock_tree.selection_set(item)
                self.stock_tree.focus(item)
                self.on_stock_select(None)
                break
                
    def update_all_stocks(self):
        # 更新所有股票价格
        self.processor.update_stock_prices()
        
        # 自动更新所有股票的市场情绪
        for stock in self.processor.portfolio['stocks']:
            self.processor.update_sentiment(stock['ticker'])
            
        self.load_stocks()
        messagebox.showinfo("成功", "已更新所有股票价格和市场情绪")
        
    # 移除了update_sentiment方法，因为情绪现在是自动判断的
                
    def calculate_position_advice(self):
        # 获取选中的项目
        selection = self.stock_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个股票")
            return
            
        # 获取选中的股票代码
        item = self.stock_tree.item(selection[0])
        ticker = item['values'][0]
        
        # 计算仓位建议
        advice = self.processor.generate_position_advice(ticker)
        
        # 更新建议文本
        self.advice_text.config(state=tk.NORMAL)
        self.advice_text.delete(1.0, tk.END)
        self.advice_text.insert(tk.END, advice)
        self.advice_text.config(state=tk.DISABLED)
        
        # 刷新列表
        self.load_stocks()
        
        # 重新选择该股票
        for item in self.stock_tree.get_children():
            values = self.stock_tree.item(item, 'values')
            if values[0] == ticker:
                self.stock_tree.selection_set(item)
                self.stock_tree.focus(item)
                self.on_stock_select(None)
                break
                
    def show_context_menu(self, event):
        # 获取点击的项目
        item = self.stock_tree.identify_row(event.y)
        if not item:
            return
            
        # 选中该项目
        self.stock_tree.selection_set(item)
        self.stock_tree.focus(item)
        self.on_stock_select(None)
        
        # 获取股票代码
        selected_item = self.stock_tree.item(item)
        ticker = selected_item['values'][0]
        
        # 创建右键菜单
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="更新股价", command=self.update_selected_stock)
        context_menu.add_command(label="计算仓位建议", command=self.calculate_position_advice)
        context_menu.add_separator()
        context_menu.add_command(label="编辑持股数量", command=lambda: self.edit_shares(ticker))
        context_menu.add_command(label="编辑平均价格", command=lambda: self.edit_avg_price(ticker))
        context_menu.add_command(label="移除股票", command=lambda: self.remove_stock(ticker))
        
        # 显示菜单
        context_menu.tk_popup(event.x_root, event.y_root)
        
    def edit_shares(self, ticker):
        # 查找股票数据
        selected_stock = None
        for stock in self.processor.portfolio['stocks']:
            if stock['ticker'] == ticker:
                selected_stock = stock
                break
                
        if not selected_stock:
            return
            
        # 弹出对话框
        new_shares = simpledialog.askinteger("编辑持股数量", 
                                          f"请输入 {ticker} 的新持股数量:", 
                                          initialvalue=selected_stock['shares'],
                                          minvalue=0)
        
        if new_shares is None:
            return
            
        # 更新持股数量
        if new_shares == 0:
            # 确认是否删除
            if messagebox.askyesno("确认", f"确定要移除股票 {ticker} 吗?"):
                self.processor.remove_stock(ticker)
                self.load_stocks()
        else:
            success = self.processor.update_shares(ticker, new_shares)
            if not success:
                messagebox.showerror("错误", "现金不足")
            self.load_stocks()
            
            # 重新选择该股票
            for item in self.stock_tree.get_children():
                values = self.stock_tree.item(item, 'values')
                if values[0] == ticker:
                    self.stock_tree.selection_set(item)
                    self.stock_tree.focus(item)
                    self.on_stock_select(None)
                    break
                    
    def edit_avg_price(self, ticker):
        # 查找股票数据
        selected_stock = None
        for stock in self.processor.portfolio['stocks']:
            if stock['ticker'] == ticker:
                selected_stock = stock
                break
                
        if not selected_stock:
            return
            
        # 弹出对话框
        new_avg_price = simpledialog.askfloat("编辑平均价格", 
                                          f"请输入 {ticker} 的新平均价格:", 
                                          initialvalue=selected_stock['avg_price'],
                                          minvalue=0.01)
        
        if new_avg_price is None:
            return
            
        # 更新平均价格
        success = self.processor.update_avg_price(ticker, new_avg_price)
        if success:
            self.load_stocks()
            
            # 重新选择该股票
            for item in self.stock_tree.get_children():
                values = self.stock_tree.item(item, 'values')
                if values[0] == ticker:
                    self.stock_tree.selection_set(item)
                    self.stock_tree.focus(item)
                    self.on_stock_select(None)
                    break
    
    def remove_stock(self, ticker):
        # 确认是否删除
        if messagebox.askyesno("确认", f"确定要移除股票 {ticker} 吗?"):
            self.processor.remove_stock(ticker)
            self.load_stocks()
            
    def start_auto_update(self):
        # 检查是否已经在运行
        if self.update_thread and self.update_thread.is_alive():
            messagebox.showinfo("提示", "自动更新已经在运行")
            return
            
        # 重置停止标志
        self.stop_thread = False
        
        # 创建并启动线程
        self.update_thread = threading.Thread(target=self.auto_update_task)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        messagebox.showinfo("成功", "已启动自动更新 (每5分钟更新一次)")
        
    def stop_auto_update(self):
        # 设置停止标志
        self.stop_thread = True
        messagebox.showinfo("成功", "已停止自动更新")
        
    def auto_update_task(self):
        while not self.stop_thread:
            # 更新所有股票价格
            self.processor.update_stock_prices()
            
            # 在主线程中更新UI
            self.root.after(0, self.load_stocks)
            
            # 等待5分钟
            for _ in range(300):  # 5分钟 = 300秒
                if self.stop_thread:
                    break
                time.sleep(1)
                
    def edit_cash(self):
        # 弹出对话框让用户输入现金额
        current_cash = self.processor.portfolio['cash']
        new_cash = simpledialog.askfloat("编辑现金", 
                                      "请输入持有现金额:", 
                                      initialvalue=current_cash,
                                      minvalue=0)
        
        if new_cash is not None:
            # 更新现金额
            self.processor.portfolio['cash'] = new_cash
            self.processor.update_portfolio_value()
            self.processor.save_portfolio()
            self.load_stocks()
            messagebox.showinfo("成功", f"现金已更新为 ${new_cash:.2f}")
    
    def show_sentiment_explanation(self):
        # 获取选中的项目
        selection = self.stock_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个股票")
            return
            
        # 获取选中的股票代码
        item = self.stock_tree.item(selection[0])
        ticker = item['values'][0]
        
        # 查找股票数据
        selected_stock = None
        for stock in self.processor.portfolio['stocks']:
            if stock['ticker'] == ticker:
                selected_stock = stock
                break
                
        if not selected_stock:
            return
        
        # 获取情绪解释（如果没有，则重新计算）
        if 'sentiment_reason' not in selected_stock or not selected_stock['sentiment_reason']:
            self.processor.update_sentiment(ticker)
            # 重新获取更新后的股票数据
            for stock in self.processor.portfolio['stocks']:
                if stock['ticker'] == ticker:
                    selected_stock = stock
                    break
        
        # 创建一个更详细的情绪解释对话框
        explanation_window = tk.Toplevel(self.root)
        explanation_window.title(f"{ticker} - 市场情绪分析")
        explanation_window.geometry("500x400")
        explanation_window.transient(self.root)
        explanation_window.grab_set()
        
        # 创建滚动文本框
        frame = ttk.Frame(explanation_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text = tk.Text(frame, wrap=tk.WORD, height=20, width=60)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加内容
        text.insert(tk.END, f"市场情绪: {selected_stock['sentiment']}\n\n", "title")
        text.insert(tk.END, f"判断依据:\n{selected_stock.get('sentiment_reason', '无详细解释')}\n\n", "reason")
        
        # 添加技术指标数据
        try:
            data = self.processor.get_stock_data(ticker, period='1mo')  # 获取1个月数据用于分析
            if not data.empty and len(data) >= 20:
                # 计算一些基本指标
                current_price = data['Close'].iloc[-1].item()
                prev_price = data['Close'].iloc[-2].item()
                price_change = (current_price - prev_price) / prev_price * 100
                
                # 计算20日均线
                ma20 = data['Close'].rolling(window=20).mean().iloc[-1].item()
                ma20_prev = data['Close'].rolling(window=20).mean().iloc[-2].item()
                ma20_trend = "上升" if ma20 > ma20_prev else "下降"
                
                # 计算成交量变化
                current_volume = data['Volume'].iloc[-1].item()
                avg_volume = data['Volume'].rolling(window=20).mean().iloc[-1].item()
                volume_ratio = current_volume / avg_volume
                
                text.insert(tk.END, "技术指标分析:\n", "subtitle")
                text.insert(tk.END, f"- 当前价格: ${current_price:.2f} (日涨跌: {price_change:.2f}%)\n")
                text.insert(tk.END, f"- 20日均线: ${ma20:.2f} (趋势: {ma20_trend})\n")
                text.insert(tk.END, f"- 成交量: {current_volume:.0f} (是20日均量的 {volume_ratio:.1f} 倍)\n\n")
        except Exception as e:
            text.insert(tk.END, f"获取技术指标数据失败: {str(e)}\n\n")
        
        text.insert(tk.END, "情绪类型解释:\n", "subtitle")
        text.insert(tk.END, "- 突破前高+放量: 股价突破20日最高价且成交量明显放大，通常是强势上涨信号\n")
        text.insert(tk.END, "- 横盘震荡: 股价在一定区间内小幅波动，无明显趋势\n")
        text.insert(tk.END, "- 放量破位: 股价明显下跌且成交量放大，通常是看跌信号\n\n")
        
        text.insert(tk.END, "仓位建议:\n", "subtitle")
        if selected_stock['sentiment'] == "突破前高+放量":
            text.insert(tk.END, "市场情绪积极，可考虑适当加仓，建议参考凯利公式计算具体仓位\n")
        elif selected_stock['sentiment'] == "横盘震荡":
            text.insert(tk.END, "市场无明显趋势，建议保持现有仓位或小幅调整\n")
        elif selected_stock['sentiment'] == "放量破位":
            text.insert(tk.END, "市场情绪消极，建议减仓或观望，注意风险控制\n")
        
        # 设置文本样式
        text.tag_configure("title", font=("Arial", 12, "bold"))
        text.tag_configure("subtitle", font=("Arial", 10, "bold"))
        text.tag_configure("reason", font=("Arial", 9))
        
        # 设置只读
        text.config(state=tk.DISABLED)
        
        # 添加关闭按钮
        ttk.Button(explanation_window, text="关闭", command=explanation_window.destroy).pack(pady=10)
    
    def show_about(self):
        about_text = """美股仓位管理系统 v1.0

基于凯利公式的仓位管理策略
支持均线策略和MACD信号分析
包含风险控制机制

© 2023 All Rights Reserved"""
        messagebox.showinfo("关于", about_text)

# 主程序入口
if __name__ == "__main__":
    root = tk.Tk()
    app = StockPortfolioApp(root)
    root.mainloop()