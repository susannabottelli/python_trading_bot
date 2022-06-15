import numpy as np

class TradingBotOne(QCAlgorithm):

    #initialise
    def Initialize(self):
        self.SetCash(23000) #starting cash balance (the number is for backtesting only, in real trading is taken from the broker's account balance)
        
        #back test period
        self.SetStartDate(2019,4,1)
        self.SetEndDate(2022,4,1)
        
        #security used for trading (resolution can also be hourly or minutely)
        self.symbol = self.AddEquity("Spy", Resolution.Daily).Symbol
        
        #initialise number of days to look back at break out point
        self.lookback = 20
        
        #constrains
        self.ceiling, self.floor = 30, 10 #upper and lower limit (can be different values...)
        
        #variable for trading stop loss
        self.initialStopRisk = 0.98 #how close the first stop loss will be to the security price - allows 2% loss before it gets hit
        self.trailingStopRisk = 0.9 #how close our trading stop will follow the assets price - here trade price at 10% (to give the price enough room to move not to get stopped out at every short-term reversal)

        self.Schedule.On(self.DateRules.EveryDay(self.symbol),
                         self.TimeRules.AfterMarketOpen(self.symbol, 20),
                         Action(self.EveryMarketOpen)) #when the method is called (every day)


    def OnData(self, data):
        self.Plot("Data Chart", self.symbol, self.Securities[self.symbol].Close)


    #implement the method
    def EveryMarketOpen(self):
        #determine look back legth for our breakout by looking at today's volatility and compare it with yesterday's
        #this info will adjust the length of the lookback window
        
        #closing price of our security over the past 31 days
        close = self.History(self.symbol, 31, Resolution.Daily)["close"] #returns dataframe with the close, high, low, and open price + volume for each day over the past 31 days
        
        #calculate volatility using standard deviation (np.std) of closing price over the past 30 days
        todayvol = np.std(close[1:31]) #current day
        yesterdayvol = np.std(close[0:30]) #day before
        
        #obtain normalized difference
        deltavol = (todayvol - yesterdayvol) / todayvol
        #multiply current lookback length by delta val +1 -> ensures that lookback length increases and decreases accordingly to volatility
        self.lookback = round(self.lookback * (1 + deltavol)) #lookback = number of days = int -> round to nearest int
        
        #check if resulting lookback length is within the upper and lower limits we defined
        if self.lookback > self.ceiling:
            self.lookback = self.ceiling #make sure it stays in limits
        elif self.lookback < self.floor:
            self.lookback = self.floor #""
            
        #check if breakout is happening (call history function to have list of all price highs from the period of the lookback length)
        self.high = self.History(self.symbol, self.lookback, Resolution.Daily)["high"]
        
        if not self.Securities[self.symbol].Invested and \
                self.Securities[self.symbol].Close >= max(self.high[:-1]):
            self.SetHoldings(self.symbol, 1)
            self.breakoutlvl = max(self.high[:-1])
            self.highestPrice = self.breakoutlvl
            
        if self.Securities[self.symbol].Invested:
            if not self.Transactions.GetOpenOrders(self.symbol):
                self.stopMarketTicket = self.StopMarketOrder(self.symbol, \
                                        - self.Portfolio[self.symbol].Quantity, \
                                        self.initialStopRisk * self.breakoutlvl)
                                        
            if self.Securities[self.symbol].Close > self.highestPrice and \
                    self.initialStopRisk * self.breakoutlvl < self.Securities[self.symbol].Close * self.trailingStopRisk:
                self.highestPrice = self.Securities[self.symbol].Close
                updateFields = UpdateOrderFields()
                updateFields.StopPrice = self.Securities[self.symbol].Close * self.trailingStopRisk
                self.stopMarketTicket.Update(updateFields)
                
                self.Debug(updateFields.StopPrice)
                
            self.Plot("Data Chart", "Stop Price", self.stopMarketTicket.Get(OrderField.StopPrice))
        
        
       
