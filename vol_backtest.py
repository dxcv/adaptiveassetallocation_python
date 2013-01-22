from pandas import *
import glob
import os
import pdb

def cumprod_to_returns(cumprod):
	returns = [cumprod.values[0]]
	returns.extend([cumprod.values[i]/cumprod.values[i-1] for i in range(1,len(cumprod))])
	return Series(returns,index=cumprod.index)

def sort_by_momentum(symbols, allDfs, dates, idx, lookback):
	momentum_dict = {}

	for symbol in symbols:

		#if symbol=='SPY' and len(symbols)>1:
		#	pdb.set_trace()

		returns = allDfs[symbol].ix[dates[idx-lookback:idx]]['RET']
		returns = Series([float(x) if x != 'C' else 0 for x in returns.values],index=returns.index)
		momentum = (returns+1).cumprod()[-1]-1

		momentum_dict[symbol] = momentum

		#if symbol=='SPY' and len(symbols)>1:	
		#	pdb.set_trace()

	sorted_symbols = list(sorted(momentum_dict, key=momentum_dict.__getitem__, reverse=True))
	
	return sorted_symbols

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

#PORTFOLIO CONSTRUCTION LOGIC:
#risk parity: each asset contributes the same weighted volatility to portfolio
#to scale
to_scale = 7

#for each day
firstIdx = 0
for idx in range(momentum_lookback,dayCount-1):
	#check if new month. rebalance monthly
	if (dates[idx].month != dates[idx+1].month):
		
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
		
		#sort symbols by momentum
		tradable_symbols = sort_by_momentum(tradable_symbols, allDfs, dates, idx, momentum_lookback)


		first_symbol = tradable_symbols.pop(0)
		sum_returns = cum_returns_dict[first_symbol]
		popped = 1

		while len(tradable_symbols)>0 and popped<=top: #only grab returns of top 5 (or fewer) by momentum
			#take arithmetic average of the CUM PROD (every day). this is the portfolio return
			popped+=1
			tradable_symbols.pop(0)
			sum_returns += cum_returns_dict[symbol]

		average_returns = sum_returns/popped
		#these are cum prod returns (e.g. levels). transform back into returns
		average_returns = cumprod_to_returns(average_returns)
		


		#add these daily returns to a df

		#set the beginning of next month
		firstIdx = idx+1
		
		portfolio_rets.extend(average_returns.values)
		portfolio_dates.extend(average_returns.index)

#convert to a df
portfolio_rets = Series(portfolio_rets,index=portfolio_dates)
portfolio_rets = DataFrame({'mom':portfolio_rets})