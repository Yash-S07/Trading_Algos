# -*- coding: utf-8 -*-
"""
Created on Mon Jun  9 20:32:21 2025

@author: Yash Singhal
"""

#_________________________Greenblatt's Magic Formula Implementation_________________

import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import copy
import pickle # To save data since requires a lot of time to scrap data
path  = r"C:\Users\Yash Singhal\Desktop\trading_1\chromedriver-win64\chromedriver.exe"

tickers = ["MMM","AXP","AAPL","BA","CAT","CVX","CSCO","KO","DIS",
           "XOM","GE","GS","HD","IBM","INTC","JNJ","JPM","MCD","MRK",
           "MSFT","NKE","PFE","PG","TRV","UNH","VZ","V","WMT"]

def get_fin_stat(ticker, type_of_stat="income_statement"):
    """
    Parameters
    ----------
    ticker : str
    type_of_stat : str
        Either of "income_statement", "balance_sheet", and "Cash_Flow". Default is "income_statement".
    
    Returns
    -------
    df : dataframe
        Financial statement data
    """
    # URL setup
    url_map = {
        "income_statement": f"https://finance.yahoo.com/quote/{ticker}/financials/",
        "balance_sheet": f"https://finance.yahoo.com/quote/{ticker}/balance-sheet/",
        "Cash_Flow": f"https://finance.yahoo.com/quote/{ticker}/cash-flow/"
    }
    url = url_map.get(type_of_stat, url_map["income_statement"])
    
    # Chrome options setup
    service = webdriver.chrome.service.Service(path)
    service.start()
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    
    try:
        # Handle potential toast dialog
        try:
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="dialog"][contains(@class, "toast")]'))
            )
            # If toast exists, wait for it to disappear or click it away
            WebDriverWait(driver, 2).until(
                EC.invisibility_of_element_located((By.XPATH, '//div[@role="dialog"][contains(@class, "toast")]'))
            )
        except:
            pass  # No toast appeared or it disappeared quickly
        
        # Find and click the expand button with robust waiting
        expand_button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@class="link2-btn fin-size-small rounded yf-y8kifl"]'))
        )
        
        # Scroll to button and click using JavaScript as fallback
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", expand_button)
        try:
            expand_button.click()
        except:
            driver.execute_script("arguments[0].click();", expand_button)
        
        # Wait for data to load
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, '//div[@class="tableBody yf-9ft13"]'))
        )
        
        # Extract table data
        temp = {}
        table = driver.find_elements(By.XPATH, '//div[@class="tableBody yf-9ft13"]')
        table_heading = driver.find_elements(By.XPATH, '//div[@class="tableHeader yf-9ft13"]')
        
        for cell in table_heading:
            headings = cell.text.split(' ')
        
        for cell in table:
            vals = cell.text.split('\n')
            for count, element in enumerate(vals):
                if count % len(headings) == 0:
                    key = element
                    temp[key] = []
                else:
                    temp[key].append(element)
        
        # Create and clean dataframe
        df = pd.DataFrame(temp).T
        df.columns = headings[1:]
        for col in df.columns:
            df[col] = df[col].str.replace(',', '')
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
    except Exception as e:
        print(f"Error occurred: {e}")
        driver.save_screenshot('error_screenshot.png')
        raise
    finally:
        driver.close()
    
    return df


def get_key_stat(ticker):
    temp_dir = {}
    
    url = f'https://finance.yahoo.com/quote/{ticker}/key-statistics/'
    
    service = webdriver.chrome.service.Service(path)
    service.start()
    options = Options()
    options.add_argument("--headless")
    
    driver = webdriver.Chrome(service = service,options = options)
    driver.get(url)
    driver.implicitly_wait(0.2)
    
    table = driver.find_element(By.XPATH,'//div[@class = "table-container yf-kbx2lo"]')
    cells = table.text.split('\n')
    
    for c in cells:
        #We only need the current values. The older values are of no use to use so we leave them
        vals = c.split(' ')
        if vals[0] == "Current":
            pass
        else:
            temp_dir[" ".join(vals[:-6])] = vals[-6]
    
    table = driver.find_element(By.XPATH,'//div[@class = "column yf-14j5zka"]')
    not_req = ['Fiscal Year','Profitability','Management Effectiveness','Income Statement','Balance Sheet','Cash Flow Statement']
    
    cells = table.text.split('\n')
    for i in range(len(cells)):
        if cells[i] not in not_req:
            vals = cells[i].split(" ")
            temp_dir[" ".join(vals[:-1])] = vals[-1]
        
        
    df = pd.DataFrame(temp_dir.values(),index = temp_dir.keys(),columns = ['values'])
    df.iloc[:,0] = df.iloc[:,0].replace({'M':'E+03','B':'E+06','T':'E+09','%':'E-02'},regex = True)
    df.iloc[:,0] = pd.to_numeric(df.iloc[:,0],errors='coerce')
    driver.close()
    return df

def get_more_data(ticker):
    temp_dir = {}
    
    url = f'https://finance.yahoo.com/quote/{ticker}/key-statistics/'
    
    service = webdriver.chrome.service.Service(path)
    service.start()
    options = Options()
    options.add_argument("--headless")
    
    driver = webdriver.Chrome(service = service,options = options)
    driver.get(url)
    driver.implicitly_wait(0.2)
    
    table = driver.find_elements(By.XPATH,'//div[@class = "column yf-14j5zka"]')
    not_req = ['Stock Price History','Share Statistics','Dividends & Splits']
    
    cell = table[1]
    cells=cell.text.split('\n')
    for i in range(len(cells)):
        if cells[i] not in not_req:
            vals = cells[i].split(" ")
            #print(vals)
            temp_dir[" ".join(vals[:-1])] = vals[-1]
        
        
    df = pd.DataFrame(temp_dir.values(),index = temp_dir.keys(),columns = ['values'])
    df.iloc[:,0] = df.iloc[:,0].replace({'M':'E+03','B':'E+06','T':'E+09','%':'E-02'},regex = True)
    df.iloc[:,0] = pd.to_numeric(df.iloc[:,0],errors='coerce')
    driver.close()
    return df
                                                                           

financial_dir = {}
for ticker in tickers:
    try:
        df1 = get_fin_stat(ticker,'income_statement')
        df1 = df1.iloc[:,[0]]
        df1.columns= [ticker]
        df2 = get_fin_stat(ticker,'balance_sheet')
        df2 = df2.iloc[:,[0]]
        df2.columns= [ticker]
        df3 = get_fin_stat(ticker,'Cash_Flow')
        df3 = df3.iloc[:,[0]]
        df3.columns= [ticker]
        df4 = get_key_stat(ticker)
        df4 = df4.iloc[:,[0]]
        df4.columns = [ticker]
        df5 = get_more_data(ticker)
        df5 = df5.iloc[:,[0]]
        df5.columns = [ticker]
        df = pd.concat([df1,df2,df3,df4,df5])
        financial_dir[ticker] = df
        print(f'Data extracted for {ticker}')
    except Exception as e:
        print(ticker,':',e)
    
    
tickers = financial_dir.keys()

#Save the file
with open("financial_data.pkl", "wb") as f:
    pickle.dump(financial_dir, f)

# Load it back later
with open("financial_data.pkl", "rb") as f:
    financial_dir = pickle.load(f)    

# Creating dataframe with relevant financial information for each stock using fundamental data
stats = ["EBITDA",
         "Depreciation Amortization Depletion",
         "Market Cap",
         "Net Income",
         "Operating Cash Flow",
         "Capital Expenditure",
         "Current Assets",
         "Current Liabilities",
         "Net PPE Purchase And Sale",
         "Stockholders' Equity",
         "Long Term Debt And Capital Lease Obligation",
         "Forward Annual Dividend Yield 4"] # change as required

indx = ["EBITDA","D&A","MarketCap","NetIncome","CashFlowOps","Capex","CurrAsset",
        "CurrLiab","PPE","BookValue","TotDebt","DivYield"]

def info_filter(df,stats,indx):
    """function to filter relevant financial information
       df = dataframe to be filtered
       stats = headings to filter
       indx = rename long headings
       lookback = number of years of data to be retained"""
    for stat in stats:
        if stat not in df.index:
            print("unable to find {} in {}".format(stat,df.columns[0]))
            return
    df_new = df.loc[stats]
    df_new = df_new[~df_new.index.duplicated(keep='first')]
    df_new.rename(dict(zip(stats,indx)),inplace=True)
    return df_new

#applying filtering to the finacials and calculating relevant financial metrics for each stock
t_df = {} 
for ticker in financial_dir:
    t_df[ticker] = info_filter(financial_dir[ticker],stats,indx)
    if t_df[ticker] is None:
        del t_df[ticker]
        continue
    t_df[ticker].loc["EBIT",:] = t_df[ticker].loc["EBITDA",:] - t_df[ticker].loc["D&A",:]
    t_df[ticker].loc["TEV",:] =  t_df[ticker].loc["MarketCap",:] + \
                                           t_df[ticker].loc["TotDebt",:] - \
                                           (t_df[ticker].loc["CurrAsset",:]-t_df[ticker].loc["CurrLiab",:])
    t_df[ticker].loc["EarningYield",:] =  t_df[ticker].loc["EBIT",:]/t_df[ticker].loc["TEV",:]
    t_df[ticker].loc["FCFYield",:] = (t_df[ticker].loc["CashFlowOps",:]-t_df[ticker].loc["Capex",:])/t_df[ticker].loc["MarketCap",:]
    t_df[ticker].loc["ROC",:]  = (t_df[ticker].loc["EBITDA",:] - t_df[ticker].loc["D&A",:])/(t_df[ticker].loc["PPE",:]+t_df[ticker].loc["CurrAsset",:]-t_df[ticker].loc["CurrLiab",:])
    t_df[ticker].loc["BookToMkt",:] = t_df[ticker].loc["BookValue",:]/t_df[ticker].loc["MarketCap",:]
    
    

# Create DataFrame using the first key's index (assuming all have same index)
final_stats_val_df = pd.DataFrame(index=t_df[next(iter(t_df.keys()))].index)

# Add each column from t_df
for key in t_df:
    final_stats_val_df[key] = t_df[key].values.flatten()
    


# Calculate ranks
final_stats_val_df.loc["Comb_Rank"] = final_stats_val_df.loc["EarningYield",:].rank(ascending=False,na_option='bottom') + final_stats_val_df.loc["ROC",:].rank(ascending=False,na_option='bottom')
final_stats_val_df.loc["MagicFormulaRank"] = final_stats_val_df.loc["Comb_Rank",:].rank(method='first')      



value_stocks = final_stats_val_df.loc["MagicFormulaRank",:].sort_values()
print("------------------------------------------------")
print("Value stocks based on Greenblatt's Magic Formula")
print(value_stocks)



# finding highest dividend yield stocks
high_dividend_stocks = final_stats_val_df.loc["DivYield",:].sort_values(ascending=False)
print("------------------------------------------------")
print("Highest dividend paying stocks")
print(high_dividend_stocks)

# # Magic Formula & Dividend yield combined
final_stats_val_df.loc["CombinedRank",:] =  final_stats_val_df.loc["EarningYield",:].rank(ascending=False,method='first') \
                                        +final_stats_val_df.loc["ROC",:].rank(ascending=False,method='first')  \
                                        +final_stats_val_df.loc["DivYield",:].rank(ascending=False,method='first')
value_high_div_stocks = final_stats_val_df.T.sort_values("CombinedRank").loc[:,["EarningYield","ROC","DivYield","CombinedRank"]]
print("------------------------------------------------")
print("Magic Formula and Dividend Yield combined")
print(value_high_div_stocks)


        
        
        
    
    
