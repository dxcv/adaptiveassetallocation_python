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

	sorted_symbols = list(sorted(momentum_dict, key=momentum_dict.__getitem__, reverse=True)) #sort keys by values
	
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
#volatility to scale portfolio to (first step)
to_scale = 0.07 #7 percent
total_weght = 1
volatility_lookback = 60
top = 5
momentum_lookback = 120

#for each day
firstIdx = 0
for idx in range(max(momentum_lookback,volatility_lookback),dayCount):
	#check if new month. rebalance monthly

	#if dates[idx].month==5 and dates[idx].year==2003 and dates[idx].day > 28:
	#	pdb.set_trace()

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

		#sort symbols by momentum
		tradable_symbols = sort_by_momentum(tradable_symbols, allDfs, dates, idx, momentum_lookback)
		#take only top symbols by momentum
		tradable_symbols = tradable_symbols[0:top]

		#pdb.set_trace()

		#calculate volatilities
		volatility_dict = {}
		cum_returns_dict = {}
		for symbol in tradable_symbols:
			#get their returns (what about -C returns?)
			old_returns = allDfs[symbol].ix[dates[firstIdx:idx]]['RET']
			#in case: convert cur_returns to doubles
			cur_returns = Series([float(x) for x in old_returns.values],index=old_returns.index)


			#calculate volatilities
			try:
				cur_volatility = cur_returns.std() #std of daily returns
				cum_returns = (cur_returns+1).cumprod() #get cumulative returns for the past month
			except:
				pdb.set_trace()
			volatility_dict[symbol] = cur_volatility
			cum_returns_dict[symbol] = cum_returns
		
		
		

		volatility_df = DataFrame(volatility_dict,index=['volatility'])
		

		#go through all symbols, equal weight by volatility, scale volatility up to 100% exposure
		target_vol = float(to_scale) / len(tradable_symbols) #the target vol for each position (for now). because we want risk parity, it is the same
		scale_factors = target_vol/volatility_df
		scale_factors_sum = scale_factors.sum(axis=1)['volatility']
		scale_factor_multiplier = 1/scale_factors_sum
		new_scale_factors = scale_factors * scale_factor_multiplier

		
		

		#then calculate weighted average returns based on volatility scales
		first_symbol = tradable_symbols.pop()
		average_returns = cum_returns_dict[first_symbol]*new_scale_factors[first_symbol]['volatility']
		
		for symbol in tradable_symbols:
			#take WEIGHTED average (weighted by volatility weights, determined before) of the CUM PROD (every day). this is the portfolio return
			average_returns += cum_returns_dict[symbol]*new_scale_factors[symbol]['volatility']
			
		#these are cum prod returns (e.g. levels). transform back into returns
		average_returns = cumprod_to_returns(average_returns)

		#set the beginning of next month
		firstIdx = idx+1

		#add these daily returns to a series
		portfolio_rets.extend(average_returns.values)
		portfolio_dates.extend(average_returns.index)

#convert to a df
portfolio_rets = Series(portfolio_rets,index=portfolio_dates)
portfolio_rets = DataFrame({'momvol':portfolio_rets})