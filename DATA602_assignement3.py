# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
DATA 602 Assignment 2
Created on Tue Mar  6 13:47:52 2018

@author: Nathan Cooper

My design strategy was that I wanted to write functions for as many repetative
tasks as I could. Those include:
    The menu, which checks for correct input.
    User input function which checks for correct input, checks for confirmation
    Webscraping that returns both bid and ask prices simulaniously
    Regex methods for removing unwanted data from the scraping
    WAP calculator
    P/L calculator
    Ledger for tracking cash
    Invatory calculator for tracking positions
    
My blotter and P\L logs are pandas Dataframes. I wanted to pass back and forth
between DF's and functions to keep code compact and to keep data management iniuitve.

I also wanted robustness so that mistypes don't crash the program.    
"""

import pandas as pd # I am storing my data in a Pandas dataframe
import numpy as np
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import re
from tabulate import tabulate #to render Blotter and P\L table
import pymongo
#import websocket
import requests
#import json
import datetime
#from flask import Flask
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.arima_model import ARMA
from statsmodels.tsa.arima_model import ARIMA


#app = Flask(__name__)
#@app.route("/")


    
"""
Here I am creating a mongod instance for the blotter database
"""


#api_key = '66CB9AA7-B785-46A1-A7BF-41FC64603026'
MONGO_DB = "blotter"
client = pymongo.MongoClient('mongodb://njcooper137:data-602-instance@cluster0-shard-00-00-bfvpf.mongodb.net:27017,cluster0-shard-00-01-bfvpf.mongodb.net:27017,cluster0-shard-00-02-bfvpf.mongodb.net:27017/test?ssl=true&replicaSet=Cluster0-shard-0&authSource=admin')
blotter = client[MONGO_DB]

"""
These functions were provided by the cryptocompare.com api for generating a list
and current price of all crypto currancies available. I modified them from the original code to
rerturn  dataframes instead of dicts.
"""

def coin_list():
    url = 'https://www.cryptocompare.com/api/data/coinlist/'
    page = requests.get(url)
    data = page.json()['Data']
    df = pd.DataFrame(data).transpose() # I added this to make it return a df with crypto symbols as the index
    return df


def price(symbol, comparison_symbols=['USD'], exchange=''):
    url = 'https://min-api.cryptocompare.com/data/price?fsym={}&tsyms={}'\
            .format(symbol.upper(), ','.join(comparison_symbols).upper())
    if exchange:
        url += '&e={}'.format(exchange)
    page = requests.get(url)
    data = page.json()
    df = pd.DataFrame.from_dict(data,orient='index').transpose()
    return df




"""
These functions were provided by the cryptocompare.com api for passing historical
data into pandas dataframes. I will use them to create the data visualizations
for the 100 day closing price and the 20D moving average.
"""
def daily_price_historical(symbol, comparison_symbol, all_data=True, limit=1, aggregate=1, exchange=''):
    url = 'https://min-api.cryptocompare.com/data/histoday?fsym={}&tsym={}&limit={}&aggregate={}'\
            .format(symbol.upper(), comparison_symbol.upper(), limit, aggregate)
    if exchange:
        url += '&e={}'.format(exchange)
    if all_data:
        url += '&allData=true'
    page = requests.get(url)
    data = page.json()['Data']
    df = pd.DataFrame(data)
    df['timestamp'] = [datetime.datetime.fromtimestamp(d) for d in df.time]
    return df

def hourly_price_historical(symbol, comparison_symbol, limit, aggregate, exchange=''):
    url = 'https://min-api.cryptocompare.com/data/histohour?fsym={}&tsym={}&limit={}&aggregate={}'\
            .format(symbol.upper(), comparison_symbol.upper(), limit, aggregate)
    if exchange:
        url += '&e={}'.format(exchange)
    page = requests.get(url)
    data = page.json()['Data']
    df = pd.DataFrame(data)
    df['timestamp'] = [datetime.datetime.fromtimestamp(d) for d in df.time]
    return df

#daily100_df['Datetime'] = pd.to_datetime(daily100_df['timestamp'])
            #daily100_df = daily100_df.set_index('Datetime')
            #daily100_df = daily100_df.drop(columns = ['timestamp'])
            #daily100_df.head()
            #daily100_df.resample('20D').mean().plot(subplots=True)

#switching https to http did not get rid of the warnings so I suppressed warnings
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# This regular expression function came from: https://tutorialedge.net/python/removing-html-from-string/
def remove_tags(text):
    TAG_RE = re.compile('<[^>]+>')
    return TAG_RE.sub('', text)

def remove_shares(text):
    SH_RE = re.compile(' [xX] \d+$')
    return SH_RE.sub('', text)

""" I designed this to give a mutable top cryptocurrency list, but did not use it as it is too slow.
def top_cryptos(symbols):
    d = []
    for c in coin_list().index.values:
        d = d.append({'coin': c, 'price': price(c)})
    df = pd.DataFrame(d)
    return df.head()
"""

# Function for Calculating WAP using previous WAP, current price, Invatory and Volume
def wap_calc(wap, inv, price, vol):
    wap = ((wap*inv)+(vol*price))/(inv+vol)
    return wap
        
# Updates the Position by adding or subtracting from the latest trade volume
def inv_calc(inv,vol,b_s):
    if(b_s == 'Buy'):
        return inv + vol
    elif(b_s == 'Sell' and (inv - vol) >= 0):
        return inv- vol
    else:
        return "Invalid Trade"

#This is the function for calculating P\L, it works for both realized and unrealized based on the values you pass it
def p_l_calc(wap,price,inv):
    return inv*(price-wap)
        
#Updates Cash Balance based on buy or sell amount
def ledger(b_s,balance,amount):
    try:
        if(b_s == "Buy"):
            balance = balance - amount
            return balance
        elif(b_s == "Sell"):
            balance = balance + amount
            return balance
    except ValueError:
        print("Invalid Option.")
        
"""
This menu function is written to be extensable and reuseable.

You can enter any greeting of your choice, which is a string
intended to give instructions to the user. 

The options are a list of strings
that describe the options within the program. 

To make the menu more robust I added some logic tests:
    
The try-except is in case the user enters a non integer as an option.
The if-else is in case the user enters an option that is out of range.
In both cases the menu should repeat until the user enters appropreiate values.

The input_check works on a similiar prinicple, save it can be adjusted to check for
strings or integer input by the Buy-Sell-Stock (b_se_st) variable, and askes for
confirmation for a trade
""" 

def menu(greeting,options):
    print(greeting)
    for option in options:
        print(option)
    try:
        choice = int(input("Please select an option:"))
        if(choice >= 1 and choice <= len(options)):
            return int(choice)
        else:
            print("\n Invalid Input \n")
            return menu(greeting,options)
    except ValueError:
        print("\n Doesn't seem to be anything there. Try again. \n")
        return menu(greeting,options)

def input_check(message, b_se_st, price = 0, crypt = ''):
    if(b_se_st == "B-S"):
        try:
            proceed = input("Price per coin is currently $" + str(price) + ". Do you wish to proceed [Y]es/[N]o? ")
            if(proceed == "Y") or (proceed == "y") or (proceed == "yes") or (proceed == "Yes") or (proceed == "YES"):
                choice = int(input(message))
                return choice
            else:
                return 0
        except ValueError:
            print("\n Invalid Input \n")
            return input_check(message, b_se_st, price)
    elif(b_se_st == "ABV"):
        choice = input(message)
        if choice in coin_list().index:
            return choice
        else:
            print("\n Invalid Input \n")
            return input_check(message, b_se_st)
    elif(b_se_st == "CN"):
        choice = input(message)
        if choice in coin_list()['CoinName'].values:
            return choice
        else:
            print("\n Invalid Input \n")
            return input_check(message, b_se_st)       
            
def allocation_by_shares(coin,df): 
    total_shares = df["Volume"].sum()
    coin_df = df.loc[(df['Coin']==coin)]
    coin_shares = coin_df["Volume"].sum()
    return coin_shares/total_shares

def allocation_by_dollars(coin,df): 
    total_dollars = 100000000 - df.iloc[0]['Cash']
    coin_df = df.loc[(df['Coin']==coin)]
    coin_dollars = sum(coin_df.Volume * coin_df.Price)
    return coin_dollars/total_dollars

# Here I create a few data strutures that will be used through out the program.
greeting = "\nWelcome to the Crypto Trading App! \nEnter the number for your desired option below.\n"    
options = ["1. Check Cryptocurrency","2. Trade","3. Show Blotter", "4. Show P/L", "5. Quit"]
balance = 100000000

# I had a function to find the most valuable coins, but it was very slow so I used a Google Search
top_cryptos = ["BTC", "ETH", "LTC", "NEO", "XMR"]

# Now I am putting the data stored in my mongodb into a dataframe so that I can create the P/L dataframe
index = pd.Timestamp.now()
columns = ['Coin','Time_Executed', 'Transaction', "Volume", "Price", "Money_In\Out", "Cash"]
blotter_df = pd.DataFrame(index=[0],columns=columns)
blotter_df = pd.DataFrame(list(blotter.collection.find()))
blotter_df['Time_Executed'] = pd.to_datetime(blotter_df.Time_Executed)

#Dropping some comlums and rows from early tests
blotter_df = blotter_df.drop(['USD', '_id'],axis=1)
blotter_df = blotter_df[blotter_df.Transaction != 'Test']
#Stack Overflow claims that using NumPy 'isfinite' is faster than Pandas 'dropna'
blotter_df = blotter_df[np.isfinite(blotter_df['Cash'])]

#I want my cash balance to carryover from the last trade.
blotter_df = blotter_df.sort_values('Time_Executed', ascending = False)
balance  = blotter_df.iloc[0]['Cash']
"""
Below I initialize the Blotter and the P/L tables.

I used a Pandas Dataframe since I am already familiar with native python data structures
and I wanted some experience in subsetting and locating data in a dataframe using
Pandas.

I start by initializing a Pandas Dataframe.
There is an empty Initial row for each stock since the wap_calc and inv_calc
functions need initial zero values to work.

This is an ad hoc fix that I intend to improve upon in assignment 2
"""


pl_df = pd.DataFrame(columns = ['Time_Executed',"Coin", "Position", "Price", "RP/L" , "UP/L" , "Total P/L", "Allocation by Shares","Allocation by Dollars","WAP", "OLS Predicted Close", "ARIMA Predicted Close"])

for c in coin_list().index.values:
    pl_df = pl_df.append({'Time_Executed':pd.to_datetime('2001-01-01 12:00:00'),'Coin':c, "Position":0, "Price":0, "RP/L":0 , "UP/L":0 , "Total P/L":0,"Allocation by Shares":0,"Allocation by Dollars":0,"WAP":0,"OLS Predicted Close":0, "ARIMA Predicted Close":0}, ignore_index=True)

# This is to reconstruct previous P/L since that is not presisted into a db or .csv
coins = blotter_df.sort_values('Time_Executed', ascending = True).groupby('Coin')
for coin, coin_df in coins:
    mny = 0
    vol_t = 0
    rpl = 0
    upl = 0
    for index,row in coin_df.iterrows():
        if(row['Transaction']=='Buy'):
            mny = mny - row['Money_In\Out']
            vol_t = vol_t + row['Volume']
            wap = mny/vol_t
            upl = p_l_calc(wap,row['Price'],vol_t)
            tpl = upl + rpl
            time = row['Time_Executed']
            pl_df = pl_df.append({'Time_Executed':row['Time_Executed'],"Coin":coin, "Position":vol_t, "Price":row['Price'], "RP/L":0 , "UP/L":upl, "Total P/L":tpl,"Allocation by Shares":allocation_by_shares(coin,blotter_df),"Allocation by Dollars":allocation_by_dollars(coin,blotter_df),"WAP":wap,"OLS Predicted Close":0, "ARIMA Predicted Close":0}, ignore_index=True)
        elif(row['Transaction']=='Sell'):
            vol_t = vol_t + row['Volume']
            rpl= p_l_calc(wap,row['Price'],-row['Volume'])
            tpl = rpl + upl
            pl_df = pl_df.append({'Time_Executed':row['Time_Executed'],"Coin":coin, "Position":vol_t, "Price":row['Price'], "RP/L":rpl, "UP/L":0, "Total P/L":tpl,"Allocation by Shares":allocation_by_shares(coin,blotter_df),"Allocation by Dollars":allocation_by_dollars(coin,blotter_df),"WAP":wap,"OLS Predicted Close":0, "ARIMA Predicted Close":0}, ignore_index=True)

pl_df = pl_df.set_index('Time_Executed')
"""
Below is where the main part of the program begins.

Program will continue until user selects main menu option 5

The Blotter and P\L table will only update if a trade is confirmed. The user
will be given a price and asked if the wish to procede.
"""
#def trader():
print("Initilizting Predictive Models\n")

btc_df = daily_price_historical('BTC' ,'USD', all_data = False, limit=731)
btc_df= btc_df.set_index('timestamp')
btc_df['return'] = btc_df['close'].pct_change()
btc_df['diff_close'] = btc_df['close'].diff()
btc_df = btc_df.dropna()
print(btc_df.tail())
btc_df.plot(y='close')
btc_model = sm.formula.ols(formula = 'np.log(close) ~ I(time**3) + I(time**2) + time', data = btc_df).fit()
print(btc_model.summary())
sm.graphics.plot_fit(btc_model, 3)
plt.show()
nxt_day = btc_df['time'][730] + 86400
btc_prd_ols = np.exp(btc_model.params[0] + btc_model.params[1]*nxt_day**3 + btc_model.params[2]*nxt_day**2 + btc_model.params[3]*nxt_day)
print(btc_prd_ols)
result = adfuller(btc_df['close'])
print("The p-value for the ADF test is ", result[1])
#chg_bit = btc_df - btc_df.shift(1)
#chg_bit = chg_bit.dropna()
btc_df.plot(y='return')
plot_acf(btc_df['return'], lags = 60)
btc_df.plot(y='diff_close')
plot_acf(btc_df['diff_close'], lags = 60)
# Plot the ACF and PACF on the same page
fig, axes = plt.subplots(1,2)

# Plot the ACF
plot_acf(btc_df['close'], lags=20, ax=axes[0])

# Plot the PACF
plot_pacf(btc_df['close'], lags=20, ax=axes[1])
plt.show()


# Fit the data to an AR(1) model and print AIC:
mod = ARMA(btc_df['close'], order=(1,0))
res = mod.fit()
print("The AIC for an AR(1) is: ", res.aic)

# Fit the data to an AR(2) model and print AIC:
mod = ARMA(btc_df['close'], order=(2,0))
res = mod.fit()
print("The AIC for an AR(2) is: ", res.aic)

# Fit the data to an AR(2) model and print AIC:
mod = ARMA(btc_df['close'], order=(3,0))
res = mod.fit()
print("The AIC for an AR(3) is: ", res.aic)

# Fit the data to an MA(1) model and print AIC:
mod = ARMA(btc_df['close'], order=(0,1))
res = mod.fit()
print("The AIC for an MA(1) is: ", res.aic)

# Fit the data to an ARMA(1,1) model and print AIC:
mod = ARMA(btc_df['close'], order=(1,1))
res = mod.fit()
print("The AIC for an ARMA(1,1) is: ", res.aic)

# Import the ARIMA module from statsmodels

# Forecast interest rates using an AR(1) model
mod = ARIMA(btc_df['close'], order=(1,2,1))
res = mod.fit()
print("The AIC for an ARIMA(1,2,1) is: ", res.aic)
forecast = res.forecast()[0]
print('Today the close for Bit Coin is predcited to be: $', forecast)
# Plot the original series and the forecasted series
#res.plot_predict(start='2016-04-29 20:00:00', end='2018-04-30 20:00:00')
#plt.show()

lit_df = daily_price_historical('LTC' ,'USD', all_data = False, limit=731)
lit_df = lit_df.set_index('timestamp')
lit_df['return'] = lit_df['close'].pct_change()
lit_df['diff_close'] = lit_df['close'].diff()
lit_df = lit_df.dropna()
print(lit_df.tail())
lit_df.plot(y='close')
lit_model = sm.formula.ols(formula = 'np.log(close) ~ I(time**3) + I(time**2) + time', data = lit_df).fit()
print(lit_model.summary())
sm.graphics.plot_fit(lit_model, 3)
plt.show()
nxt_day = lit_df['time'][730] + 86400
lit_prd_ols = np.exp(lit_model.params[0] + lit_model.params[1]*nxt_day**3 + lit_model.params[2]*nxt_day**2 + lit_model.params[3]*nxt_day)
print(lit_prd_ols)
result = adfuller(lit_df['close'])
print("The p-value for the ADF test is ", result[1])

lit_df.plot(y='return')
plot_acf(lit_df['return'], lags = 60)
lit_df.plot(y='diff_close')
plot_acf(lit_df['diff_close'], lags = 60)
# Plot the ACF and PACF on the same page
fig, axes = plt.subplots(1,2)

# Plot the ACF
plot_acf(lit_df['close'], lags=20, ax=axes[0])

# Plot the PACF
plot_pacf(lit_df['close'], lags=20, ax=axes[1])
plt.show()


# Fit the data to an AR(1) model and print AIC:
mod = ARMA(lit_df['close'], order=(1,0))
res = mod.fit()
print("The AIC for an AR(1) is: ", res.aic)

# Fit the data to an AR(2) model and print AIC:
mod = ARMA(lit_df['close'], order=(2,0))
res = mod.fit()
print("The AIC for an AR(2) is: ", res.aic)

# Fit the data to an AR(2) model and print AIC:
mod = ARMA(lit_df['close'], order=(3,0))
res = mod.fit()
print("The AIC for an AR(3) is: ", res.aic)

# Fit the data to an MA(1) model and print AIC:
mod = ARMA(lit_df['close'], order=(0,1))
res = mod.fit()
print("The AIC for an MA(1) is: ", res.aic)

# Fit the data to an ARMA(1,1) model and print AIC:
mod = ARMA(lit_df['close'], order=(1,1))
res = mod.fit()
print("The AIC for an ARMA(1,1) is: ", res.aic)

# Import the ARIMA module from statsmodels

# Forecast interest rates using an AR(1) model
mod = ARIMA(lit_df['close'], order=(1,1,1))
res = mod.fit()
print("The AIC for an ARIMA(1,1,1) is: ", res.aic)
forecast = res.forecast()[0]
print('Today the close for Lite Coin is predcited to be: $', forecast)

main_menu = menu(greeting,options)

while(main_menu != 5):
    
    #cypto search
    if(main_menu ==1):
        crypt_greeting = "\nYou selected Crypto Check.\nMake your choice below."
        crypt_options = ["1. Full List (Warning! Over 2300 Cryptos!)", "2. Check vs. Symbol", "3. Check vs. Coin Name" ,"4. Main Menu"]
        crypt_menu = menu(crypt_greeting,crypt_options) 
        
        if(crypt_menu == 1):
            print(tabulate(coin_list()[['Symbol', 'CoinName']], headers='keys', showindex = False,tablefmt='grid'))
            continue
        elif(crypt_menu == 2):
            crypto = input_check("\nPlease enter the Symbol of the Cryptocurrency you would like to check:", 'ABV')
            print(coin_list().loc[crypto])
            continue
        elif(crypt_menu == 2):
            crypto = input_check("\nPlease enter the Coin Name of the Cryptocurrency you would like to check:", 'CN')
            print(tabulate(coin_list().loc[coin_list()['CoinName'] == crypto].transpose(),headers='keys', showindex = False,tablefmt='grid'))
            continue
        elif(crypt_menu == 4):
            print("\nBack to the Main Menu\n")
            main_menu = menu(greeting,options)
            continue
        
    #Trade Options 
    elif(main_menu == 2):
        trd_greet = "\nYou have selected Trade\nMake your choice below.\n"
        trd_options = ["1. Buy", "2. Sell","3. 20 Day Weighted Averages.","4. Main Menu"]
        trd_menu = menu(trd_greet,trd_options)
        
        #This is the Buy Stock Option
        if(trd_menu == 1):
            print("\nYou Selected Buy.\n These are the top 5 Cryptocurrencies:")
            for crp in top_cryptos:
                print(crp+"\n")
            crypt = input_check("Please enter your Crypto Symbol: ", 'ABV')
            plt.figure(figsize=(12,8))
            crypt_df = daily_price_historical(crypt,'USD',all_data=False,limit=731,exchange='')
            crypt_df = crypt_df.set_index('timestamp')
            crypt_df.plot(y='close')
            plt.xlabel('Last 731 Days')
            plt.ylabel('USD')
            plt.show(block=True)
            print(crypt+" average closing price in the last 24 hours: $" + str(hourly_price_historical(crypt,'USD',limit=24,aggregate=1)['close'].mean()))
            print(crypt+" maximum closing price in the last 24 hours: $" + str(hourly_price_historical(crypt,'USD',limit=24,aggregate=1)['close'].max()))
            print(crypt+" minimum closing price in the last 24 hours: $" + str(hourly_price_historical(crypt,'USD',limit=24,aggregate=1)['close'].min()))
            print(crypt+" standard deviation of closing price in the last 24 hours: $" + str(hourly_price_historical(crypt,'USD',limit=24,aggregate=1)['close'].std()))
            #print(stock + ' = $'+ str(buy_price))
            mod = ARIMA(crypt_df['close'], order=(1,1,1))
            res = mod.fit()
            forecast = res.forecast()[0]
            crypt_model = sm.formula.ols(formula = 'np.log(close) ~ I(time**3) + I(time**2) + time', data = crypt_df).fit()
            nxt_day = crypt_df['time'][731] + 86400
            crypt_prd_ols = np.exp(crypt_model.params[0] + crypt_model.params[1]*nxt_day**3 + crypt_model.params[2]*nxt_day**2 + crypt_model.params[3]*nxt_day)
            buy_price = price(crypt).iloc[0,0]
            buy_shares = input_check("Price is: $"+ str(buy_price) + ". Confirm number of Shares you want to buy: ", "B-S", buy_price)
            if(buy_shares > 0): #will only update if you confirm a trade
                time = pd.Timestamp.now()
                coin_pl_df = pl_df.loc[(pl_df['Coin']==crypt)]
                inv = inv_calc(coin_pl_df.iloc[-1]["Position"],buy_shares,"Buy")
                wap = wap_calc(coin_pl_df.iloc[-1]["WAP"],coin_pl_df.iloc[-1]["Position"],buy_price,buy_shares)
                upl = p_l_calc(wap,buy_price,inv)
                tpl = upl + coin_pl_df.iloc[-1]["RP/L"]
                blotter_dict = {'Coin':crypt, "Time_Executed":time,"Transaction":"Buy", "Volume":buy_shares, "Price":buy_price, "Money_In\Out":-buy_price*buy_shares, "Cash":ledger('Buy',balance,buy_shares*buy_price)}
                blotter.collection.insert_one(blotter_dict)
                blotter_df = blotter_df.append(blotter_dict,ignore_index=True)
                a_s = allocation_by_shares(crypt,blotter_df)
                a_d = allocation_by_dollars(crypt,blotter_df)
                pl_df = pl_df.append({'Time_Executed':time,"Coin":crypt, "Position":inv, "Price":buy_price, "RP/L":0 , "UP/L":upl, "Total P/L":tpl,"Allocation by Shares":a_s,"Allocation by Dollars":a_d,"WAP":wap,"OLS Predicted Close":crypt_prd_ols, "ARIMA Predicted Close":forecast}, ignore_index=True)
                balance = ledger('Buy',balance,buy_shares*buy_price)
                continue
            else:
                continue
        
        #This is the Sell Stock Option
        elif(trd_menu == 2):
            print("\nYou Selected Sell.\n These are the top 5 Cryptocurrencies:")
            for crp in top_cryptos:
                print(crp+"\n")
            crypt = input_check("Please enter your Crypto Symbol: ", 'ABV')
            plt.figure(figsize=(12,8))
            crypt_df = daily_price_historical(crypt,'USD',all_data=False,limit=731,exchange='')
            crypt_df = crypt_df.set_index('timestamp')
            crypt_df.plot(y='close')
            plt.xlabel('Last 731 Days')
            plt.ylabel('USD')
            plt.show(block=True)
            print(crypt+" average closing price in the last 24 hours: $" + str(hourly_price_historical(crypt,'USD',limit=24,aggregate=1)['close'].mean()))
            print(crypt+" maximum closing price in the last 24 hours: $" + str(hourly_price_historical(crypt,'USD',limit=24,aggregate=1)['close'].max()))
            print(crypt+" minimum closing price in the last 24 hours: $" + str(hourly_price_historical(crypt,'USD',limit=24,aggregate=1)['close'].min()))
            print(crypt+" standard deviation of closing price in the last 24 hours: $" + str(hourly_price_historical(crypt,'USD',limit=24,aggregate=1)['close'].std()))
            #print(stock + ' = $'+ str(buy_price))
            mod = ARIMA(crypt_df['close'], order=(1,1,1))
            res = mod.fit()
            forecast = res.forecast()[0]
            crypt_model = sm.formula.ols(formula = 'np.log(close) ~ I(time**3) + I(time**2) + time', data = crypt_df).fit()
            nxt_day = crypt_df['time'][731] + 86400
            crypt_prd_ols = np.exp(crypt_model.params[0] + crypt_model.params[1]*nxt_day**3 + crypt_model.params[2]*nxt_day**2 + crypt_model.params[3]*nxt_day)
            sell_price = price(crypt).iloc[0,0]
            sell_shares = input_check("Price is: $"+ str(sell_price) + ". Confirm number of Shares you want to sell: ", "B-S", sell_price)
            #print(stock + ' = $'+ str(buy_price))
            if(sell_shares > 0): #will only update if you confirm a trade
                time = pd.Timestamp.now()
                coin_pl_df = pl_df.loc[(pl_df['Coin']==crypt)]
                inv = inv_calc(coin_pl_df.iloc[-1]["Position"],sell_shares,"Sell")
                wap = coin_pl_df.iloc[-1]["WAP"]
                rpl = p_l_calc(wap,sell_price,inv)
                tpl = rpl + coin_pl_df.iloc[-1]["UP/L"]
                blotter_dict = {'Coin':crypt, "Time_Executed":time,"Transaction":"Sell", "Volume":-sell_shares, "Price":sell_price, "Money_In\Out":sell_price*sell_shares, "Cash":ledger('Sell',balance,sell_shares*sell_price)}
                blotter.collection.insert_one(blotter_dict)
                blotter_df = blotter_df.append(blotter_dict,ignore_index=True)
                a_s = allocation_by_shares(crypt,blotter_df)
                a_d = allocation_by_dollars(crypt,blotter_df)
                pl_df = pl_df.append({'Time_Executed':time,"Coin":crypt, "Position":inv, "Price":sell_price, "RP/L":rpl , "UP/L":0, "Total P/L":tpl,"Allocation by Shares":a_s,"Allocation by Dollars":a_d,"WAP":wap,"OLS Predicted Close":crypt_prd_ols, "ARIMA Predicted Close":forecast}, ignore_index=True)
                balance = ledger('Sell',balance,sell_shares*sell_price)
                continue
            else:
                continue
            
        elif(trd_menu == 3):
            print("\n20 Day Weighted Averages per Coin.\n")
            print("\nYou Selected Sell.\n These are the top 5 Cryptocurrencies:")
            for crp in top_cryptos:
                print(crp+"\n")
            crypt = input_check("Please enter your Crypto Symbol: ", 'ABV')
            daily200_df = daily_price_historical(crypt,'USD',all_data=False,limit=200,exchange='')
            daily200_df['Datetime'] = pd.to_datetime(daily200_df['timestamp'])
            daily200_df = daily200_df.set_index('Datetime')
            daily200_df = daily200_df.drop(columns = ['timestamp'])
            plt.figure(figsize=(12,8))
            daily200_df.resample('20D').mean().plot(subplots=True)
            plt.xlabel('20 Weighted Averages Last 200 Days')
            plt.ylabel('USD')
            plt.show(block=True)
            print(crypt+" average closing price in the last 20 days: $" + str(daily_price_historical(crypt,'USD',all_data=False,limit=20)['close'].mean()))
            print(crypt+" maximum closing price in the last 20 days: $" + str(daily_price_historical(crypt,'USD',all_data=False,limit=20)['close'].max()))
            print(crypt+" minimum closing price in the last 20 days: $" + str(daily_price_historical(crypt,'USD',all_data=False,limit=20)['close'].min()))
            print(crypt+" standard deviation of closing price in the last 20 days: $" + str(daily_price_historical(crypt,'USD',all_data=False,limit=20)['close'].std()))
            
        elif(trd_menu == 4):
            print("\nBack to the Main Menu\n")
            main_menu = menu(greeting,options)
            continue
        
    elif(main_menu ==3):
        print("Current Top 5 Coin Market Prices:\n")
        for c in top_cryptos:
            print("\n"+c +" $"+ str(price(c).iloc[0,0]))
        print("\nHere is the Blotter:\n")
        blotter_df = pd.DataFrame(list(blotter.collection.find({})))
        blotter_df['Time_Executed'] = pd.to_datetime(blotter_df.Time_Executed)
        blotter_df = blotter_df.drop(['USD', '_id'],axis=1)
        blotter_df = blotter_df[blotter_df.Transaction != 'Test']
        #Stack Overflow claims that using NumPy 'isfinite' is faster than Pandas 'dropna'
        blotter_df = blotter_df[np.isfinite(blotter_df['Cash'])]
        print(tabulate(blotter_df.sort_values('Time_Executed', ascending = False), headers='keys', tablefmt='grid'))
        print("\nCash is: $"+str(balance))
        main_menu = menu(greeting,options)
        continue
    
    elif(main_menu == 4):
        print("Current Top 5 Coin Market Prices:\n")
        for c in top_cryptos:
            print("\n"+c +" $"+ str(price(c).iloc[0,0]))
        print("\nHere is the P/L:\n")
        print(tabulate(pl_df[pl_df.Price != 0].sort_index(ascending = False), headers='keys', tablefmt='grid'))
        pl_df[pl_df.Price != 0].plot(y='Position')
        pl_df[pl_df.Price != 0].plot(y='Total P/L')
        pl_df[pl_df.Price != 0].plot(y='WAP')
        pl_df[pl_df.Price != 0].plot(y='Price')
        plt.show()
        print("\nCash is: $"+str(balance))
        main_menu = menu(greeting,options)
        continue
    
print("Good Bye!")

#if __name__ == '__main__':
 #   app.run(host='0.0.0.0')