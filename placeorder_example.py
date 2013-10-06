'''Simple example of using the SWIG generated TWS wrapper to place an order
with interactive brokers.

'''


from pandas import *
import datetime as dt
import pdb as pdb


import sys
from time import sleep

from swigibpy import EWrapper, EPosixClientSocket, Contract, Order, TagValue,\
        TagValueList

try:
    input = raw_input
except:
    pass

###

orderId = None

availableFunds = 0
netLiquidationValue = 0


class PlaceOrderExample(EWrapper):
    '''Callback object passed to TWS, these functions will be called directly
    by TWS.

    '''

    def openOrderEnd(self):
        '''Not relevant for our example'''
        pass

    def execDetails(self, id, contract, execution):
        '''Not relevant for our example'''
        pass

    def managedAccounts(self, openOrderEnd):
        '''Not relevant for our example'''
        pass

    ###############

    def nextValidId(self, validOrderId):
        '''Capture the next order id'''
        global orderId
        orderId = validOrderId

    def orderStatus(self, id, status, filled, remaining, avgFillPrice, permId,
            parentId, lastFilledPrice, clientId, whyHeld):

        print(("Order #%s - %s (filled %d, remaining %d, avgFillPrice %f,"
               "last fill price %f)") % (
                id, status, filled, remaining, avgFillPrice, lastFilledPrice))

    def openOrder(self, orderID, contract, order, orderState):

        print("Order opened for %s" % contract.symbol)

    ####account value
    def updateAccountValue(self, key, value, currency, accountName):
        global availableFunds
        global netLiquidationValue

        #print 'key: '+key
        #print 'value: '+value
        #print 'currency: '+currency
        #print 'accountName: '+accountName
        #print ''

        #get how much current available funds we have, also our net liquidation value
        if currency == 'USD':

            if key == 'AvailableFunds':
                availableFunds = float(value)
            elif key=='NetLiquidation':
                netLiquidationValue = float(value)





prompt = input("WARNING: This example will place an order on your IB "
                   "account, are you sure? (Type yes to continue): ")
if prompt.lower() != 'yes':
    sys.exit()

# Instantiate our callback object
callback = PlaceOrderExample()

# Instantiate a socket object, allowing us to call TWS directly. Pass our
# callback object so TWS can respond.
tws = EPosixClientSocket(callback)

# Connect to tws running on localhost
tws.eConnect("", 7496, 42)

#account updates
tws.reqAccountUpdates(True,'DU15068')

sleep(1)
print 'available funds: %s' % (availableFunds)
print 'net liquidation value: %s' % (netLiquidationValue)

# Simple contract for GOOG
contract = Contract()
contract.symbol = "IBM"
contract.secType = "STK"
contract.exchange = "SMART"
contract.currency = "USD"

if orderId is None:
    print('Waiting for valid order id')
    sleep(1)
    while orderId is None:
        print('Still waiting for valid order id...')
        sleep(1)







# Order details
'''
algoParams = TagValueList()
algoParams.append(TagValue("componentSize","3"))
algoParams.append(TagValue("timeBetweenOrders","60"))
algoParams.append(TagValue("randomizeTime20","1"))
algoParams.append(TagValue("randomizeSize55","1"))
algoParams.append(TagValue("giveUp","1"))
algoParams.append(TagValue("catchUp","1"))
algoParams.append(TagValue("waitForFill","1"))
algoParams.append(TagValue("startTime","20110302-14:30:00 GMT"))
algoParams.append(TagValue("endTime","20110302-21:00:00 GMT"))
'''

order = Order()
order.action = 'BUY'
#order.lmtPrice = 140
#order.orderType = 'LMT'
order.orderType = 'MOC'
#order.orderType = 'MKT'
order.totalQuantity = 25
#order.algoStrategy = "AD"
#order.tif = 'GTC'
order.tif = 'DAY'
#order.algoParams = algoParams
order.transmit = True

#can't submit MOC orders outside of trading hours... tif has to be DAY to







###DELAY UNTIL MARKET HOURS
day_of_week = datetime.now().isoweekday()

#if weekday, and we scanned after midnight, set execution time to this morning at 10:30 am
time_now = datetime.now()
if day_of_week in range(1,6) and (time_now.hour >= 0 and time_now.hour<10) and (time_now.minute>=0 and time_now.minute<30):
    execution_time = datetime(year=time_now.year,month=time_now.month,day=time_now.day,hour=10,minute=30)


#otherwise, set to next trading day, morning at 10:30am
else:
    execution_time = datetime.now()
    execution_time = execution_time+dt.timedelta(days=1)
    while execution_time.isoweekday()>5:
        execution_time = execution_time+dt.timedelta(days=1)
    execution_time = datetime(year=execution_time.year,month=execution_time.month,day=execution_time.day,hour=10,minute=30)    


to_sleep = (execution_time-datetime.now()).total_seconds()
print "----------sleeping until execution time of %s---------------" % (execution_time)


#pdb.set_trace()



#sleep until that time
#sleep(to_sleep)

print("Placing order for %d %s's (id: %d)" % (order.totalQuantity,
        contract.symbol, orderId))






# Place the order
tws.placeOrder(
        orderId,                                    # orderId,
        contract,                                   # contract,
        order                                       # order
    )

print("\n=====================================================================")
print(" Order placed, waiting for TWS responses")
print("=====================================================================\n")


print("******************* Press ENTER to quit when done *******************\n")
input()

print("\nDisconnecting...")
tws.eDisconnect()
