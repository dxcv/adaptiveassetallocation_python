from pandas import *
import glob
import os
import pdb

def cumprod_to_returns(cumprod):
	returns = [cumprod.values[0]]
	returns.extend([cumprod.values[i]/cumprod.values[i-1] for i in range(1,len(cumprod))])
	return Series(returns,index=cumprod.index)

#get all stock symbols by reading csv names from data folder
symbols = []
os.chdir("data/")
for afile in glob.glob("*.csv"):
	symbols.append(afile[:-4]) #slice out csv extension
os.chdir("../") #reset dir

allDfs = {}
#store all in memory (a dict of dfs). read from binary, if doesn't exist read from csv (and save binary)
for symbol in symbols:
	try:
		print "reading "+symbol+" data from binary file..."
		df = DataFrame.load("data/"+symbol+".df")
	except IOError:
		print "reading "+symbol+" data from CSV..."
		df = DataFrame.from_csv("data/"+symbol+".csv")
		df.save("data/"+symbol+".df")
	allDfs[symbol] = df

#get a ts of number of etfs in existence
generateTimeSeries = 0
if generateTimeSeries==1:
	print "generating time series of ETF count..."

	countTS = {}
	for date in allDfs['SPY'].index:
		count=0
		for symbol in allDfs.keys():
			try:
				allDfs[symbol].xs(date)
				count+=1
			except KeyError:
				continue
		countTS[date] = count


	countSeries = Series(countTS)

#set start-end date
startDate = allDfs['SPY'].index[0]
endDate = allDfs['SPY'].index[-1]
dates = allDfs['SPY'].index
dayCount = len(dates)


portfolio_rets = []
portfolio_dates = []

#equal weight logic
#for each day
firstIdx = 0
for idx in range(0,dayCount):
	#check if new month. rebalance monthly
	
	if dates[idx]==dates[-1] or (dates[idx].month != dates[idx+1].month):
		if firstIdx==0: #find the idx of the previous month because firstIdx hasn't been set yet
			curIdx = idx
			while dates[curIdx].month == dates[curIdx-1].month:
				curIdx-=1
			firstIdx = curIdx
		#get list of all tradable etfs at the beginning of the period (e.g. it has a return with double type)
		tradable_symbols = []
		for symbol in symbols:
			try:
				allDfs[symbol].ix[dates[firstIdx]]
				tradable_symbols.append(symbol)
			except KeyError:
				print symbol+" not tradable on "+str(dates[firstIdx])
		cum_returns_dict = {}
		for symbol in tradable_symbols:
			#get their returns (what about -C returns?)
			old_returns = allDfs[symbol].ix[dates[firstIdx:idx]]['RET']
			#in case: convert cur_returns to doubles
			cur_returns = Series([float(x) for x in old_returns.values],index=old_returns.index)

			#calculate cumprod (after adding 1)
			try:
				cum_returns = (cur_returns+1).cumprod()
			except:
				pdb.set_trace()
			cum_returns_dict[symbol] = cum_returns
		
		first_symbol = tradable_symbols.pop()
		sum_returns = cum_returns_dict[first_symbol]
		
		for symbol in tradable_symbols:
			#take arithmetic average of the CUM PROD (every day). this is the portfolio return
			sum_returns += cum_returns_dict[symbol]
		average_returns = sum_returns/(len(tradable_symbols)+1)
		#these are cum prod returns (e.g. levels). transform back into returns
		average_returns = cumprod_to_returns(average_returns)
		

		#add these daily returns to a df

		#set the beginning of next month
		firstIdx = idx+1
		
		portfolio_rets.extend(average_returns.values)
		portfolio_dates.extend(average_returns.index)

#convert to a df
portfolio_rets = Series(portfolio_rets,index=portfolio_dates)
portfolio_rets = DataFrame({'eqw':portfolio_rets})