from pandas import *


#first column HAS to be dates
df = DataFrame.from_csv("etf_data.csv")

prevSymbol=""
prevCut = 0
for i in range(0,len(df)):
	

	row = df.ix[i]
	#print row.name #diagnostic
	curSymbol = row['TICKER']
	if i==0:
		prevSymbol = curSymbol
	if (curSymbol != prevSymbol) or i==(len(df)-1):
		slicedDf = df[prevCut:i]
		prevCut = i
		filename = prevSymbol
		slicedDf.to_csv("data/"+prevSymbol+".csv")
		print ("writing "+prevSymbol+" csv") #diagnostic


	prevSymbol = curSymbol