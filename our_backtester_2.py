from pandas import *
import glob
import os
import pdb
import scikits.statsmodels.tsa.stattools as ts

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

#and constants such as L, formation period, trading period
L = 5
formationPeriod = 120
tradingPeriod = 20

#construct pairs from all stocks, Array((1,2)
pairs=[]
for i in range(0,len(symbols)):
	for j in range(i+1,len(symbols)):
		pairs.append((symbols[i],symbols[j]))


t=formationPeriod

##########BACKTESTING LOGIC##########
#for trading period isn't last 20 days in all of data
print "about to start while loop"

strategyRetDf = {}
strategyRetDf = DataFrame.from_dict(strategyRetDf)
datesToUse = []

while (t + tradingPeriod) < dayCount:

	print "on day "+str(t)+" of "+str(dayCount)

	# get relevant date ranges 
	formationDates = dates[t-120:t] 
	tradingDates = dates[t:t+20] 
	
	#print "t = " + str(t)
	#print "formationDates length = " + str(len(formationDates))
	#print "tradingDates length = " + str(len(tradingDates))
	
	# make dictionary in the form ( Residual, [ (Pair, Beta, +/-1) ] ) 
	residualsDct = {} 
	
	#print "entering for loop to run regressions on all pairs..." 
	for pair in pairs:
		#print "pair = " + str(pair) 
		
		# get formation period returns data for each ETF in the pair
		etf1 = allDfs[pair[0]]
		prc1 = etf1['PRC']
		ret1 = etf1['RET']
		formationPrc1 = prc1[formationDates[0]:formationDates[119]]
		formationPrc1 = formationPrc1.fillna(0)
		formationPrc1 = abs(formationPrc1) #treating negative prices (no volume days) as positive
		formationRet1 = ret1[formationDates[0]:formationDates[119]]
		formationRet1 = formationRet1.fillna(0)

		#pdb.set_trace()

		#print "formationRet1 length = " + str(len(formationPrc1))
		
		etf2 = allDfs[pair[1]]
		prc2 = etf2['PRC']
		ret2 = etf2['RET']
		formationPrc2 = prc2[formationDates[0]:formationDates[119]]
		formationPrc2 = formationPrc2.fillna(0)
		formationPrc2 = abs(formationPrc2)
		formationRet2 = ret2[formationDates[0]:formationDates[119]]
		formationRet2 = formationRet2.fillna(0)
		#print "formationPrc2 length = " + str(len(formationPrc2)) 
		
		#print "running regression..."
		# run regression on the formation period returns of the 2 ETFs 
		
		#regr = ols(y=formationPrc1, x=formationPrc2,intercept=False)
		regrPrc = ols(y=formationPrc1, x=formationPrc2)
		regrRet = ols(y=formationRet1, x=formationRet2)

		residualsPrc = regrPrc.resid
		residualsRet = regrRet.resid
		beta = regrPrc.beta[0]  
		intercept = regrPrc.beta[1]

		#if pair[0]=='EWP' and pair[1]=='EWL': #residual JUMPS
		#	pdb.set_trace()
		
		#print "residuals length = " + str(len(residuals))
		#print "running dickey fuller..." 
		#do dickey fuller to see if residuals are even cointegrated
		x = np.array(residualsRet) #residuals of Ret of Prc?
		#x = np.array(residualsPrc) #residuals of Ret of Prc?
		result = ts.adfuller(x)

		pval = result[1]
		#print "pval = " + str(pval)
		
		if pval < 0.05: 
			try:
				u = residualsPrc[119] 	# in terms of price 
			except:
				pdb.set_trace()

			#debug
			#if (pair[0]=='EWP' and pair[1]=='EWC'):
			#	print "before setting resids for EWP,EWC"
				#pdb.set_trace()

			if u >= 0:
				if u in residualsDct:
					val = residualsDct[u].append( (pair, beta, 1,intercept) )
				else:
					val = [ (pair, beta, 1, intercept) ]
			else: 
				u = -1*u
				if u in residualsDct:
					val = residualsDct[u].append( (pair, beta, -1,intercept) )
				else:
					val = [ (pair, beta, -1, intercept) ]
			
			# add to the dictionary 
			residualsDct[u] = val;
			#print "new entry to dictionary: resid = " + str(u) + ", value = " + str(val)
			
	# sort residuals by sorting the dictionary keys 
	sortedResiduals = residualsDct.keys()
	sortedResiduals.sort(reverse = True) 
	
	# make new dictionary of top 5 pairs in the form ( Pair, (Beta, Residual, +/-1) ) 
	top5 = {}
	count = 0
	i = 0
	


	while count < L:
		try:
			dctKey = sortedResiduals[i]
		except:
			#pdb.set_trace()
			#what to do when there are fewer than 5 pairs?
			count+=1
			i+=1

		dctVal = residualsDct[dctKey] 
		j = 0
		while j < len(dctVal) and count < L:
			elt = dctVal[j] 							# (Pair, Beta, +/-1) 
			top5[elt[0]] = (elt[1], elt[2]*dctKey, elt[2],elt[3]) 	# ( Pair, (Beta, Residual, +/-1) )
			count += 1
			j += 1
		i += 1 
	
	# make new dictionary to hold trading strategy returns
	pdDf = {} 


	# iterate through next 20 days and calculate y - beta*x = u 
	k = 0

	#pdb.set_trace()
	
	toTrade = {}
	for topPair in top5.keys():
		toTrade[topPair]=True

	while k < 20:
		dayDf = {}
		
		datesToUse.append(tradingDates[k])

		for topPair in top5.keys(): 
	

			#print topPair
			#pdb.set_trace()
			
			#debug
			#if topPair[0] == 'EWN' and topPair[1] == 'EWT':
				#pdb.set_trace() #was to check why we selected EWN and EWT as a top 5, but we weren't trading. reason: residuals are tiny...

			# get trading period returns data for each ETF in the pair
			etf1 = allDfs[topPair[0]]
			ret1 = etf1['RET']
			prc1 = etf1['PRC']
			tradingRet1 = ret1[tradingDates[0]:tradingDates[19]]
			tradingRet1 = float(tradingRet1[k])
			tradingPrc1 = prc1[tradingDates[0]:tradingDates[19]]
			tradingPrc1 = float(tradingPrc1[k]) 
			
			etf2 = allDfs[topPair[1]]
			ret2 = etf2['RET']
			prc2 = etf2['PRC']
			tradingRet2 = ret2[tradingDates[0]:tradingDates[19]]
			tradingRet2 = float(tradingRet2[k])
			tradingPrc2 = prc2[tradingDates[0]:tradingDates[19]]
			tradingPrc2 = float(tradingPrc2[k]) 


			
			beta = (top5[topPair])[0] 
			resid = (top5[topPair])[1]	# price residual from time t 
			const = (top5[topPair])[2] 
			intercept = (top5[topPair])[3] 
			
			# calculate current return and residual 
			try:
				currentReturn = const * ( (beta*tradingRet2) - tradingRet1 )
				currentResid = tradingPrc1 - (beta * tradingPrc2) - intercept
				#pdb.set_trace()
				
				#if topPair[0]=='EWP' and topPair[1]=='EWL':
				#	pdb.set_trace() #trying to look at time series of residuals
			except: 
				pdb.set_trace()
			
			# exit strategy 
			if (currentResid * resid) >= 0 and toTrade[topPair]:
				dayDf[topPair] = currentReturn 
			else: #exit
				toTrade[topPair] = False
				dayDf[topPair] = 0
		
		
		# add day return to period return dictionary 
		try:
			pdDf[tradingDates[k]] = dayDf 
			#print "new addition to period: tradingDate = " + str(tradingDates[k]) + ", day return = " + str(dayDf) 
		except:
			pdb.set_trace()

		k += 1
		
	# add period return dictionary to larger database
	## ?? 
	
	#move forward by 20 days
	t += tradingPeriod 
	
	testdf = DataFrame.from_dict(pdDf)
	testdf = testdf.T
	testdf.columns=Index([i for i in range(0,len(testdf.columns))])

	strategyRetDf = strategyRetDf.append(testdf, ignore_index=True)

	

	#pdb.set_trace()
	
	
strategyRetDf.index = datesToUse

