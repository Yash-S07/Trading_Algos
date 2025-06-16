# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 18:05:40 2025

@author: Yash Singhal
"""

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
            WebDriverWait(driver, 0.2).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="dialog"][contains(@class, "toast")]'))
            )
            # If toast exists, wait for it to disappear or click it away
            WebDriverWait(driver, 2).until(
                EC.invisibility_of_element_located((By.XPATH, '//div[@role="dialog"][contains(@class, "toast")]'))
            )
        except:
            pass  # No toast appeared or it disappeared quickly
        
        # Find and click the expand button with robust waiting
        expand_button = WebDriverWait(driver, 0.2).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@class="link2-btn fin-size-small rounded yf-y8kifl"]'))
        )
        
        # Scroll to button and click using JavaScript as fallback
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", expand_button)
        try:
            expand_button.click()
        except:
            driver.execute_script("arguments[0].click();", expand_button)
        
        # Wait for data to load
        WebDriverWait(driver, 0.2).until(
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
        if df.columns[0] == "TTM": #delete TTM column from income statement and cashfow statement to make it consistent with balance sheet
            df.drop("TTM",axis=1,inplace=True)
        driver.close()
    
    return df



financial_dir = {}
for ticker in tickers:
    try:
        df1 = get_fin_stat(ticker,"income_statement")
        df1 = df1.iloc[:,:3]
        df2 = get_fin_stat(ticker,"balance_sheet")
        df2 = df2.iloc[:,:3]
        df3 = get_fin_stat(ticker,"Cash_Flow")
        df3 = df3.iloc[:,:3]
        df = pd.concat([df1,df2,df3])
        financial_dir[ticker] = df
        print("data extracted for ",ticker)
        financial_dir[ticker] = df
    except Exception as e:
        print(ticker,":", e)


### Currently using the value investing one only since need to get rid of a few columns only. Extra columns are not a problem
### Cant use that. It only has current years values previous uda di thi


# selecting relevant financial information for each stock using fundamental data
stats = ["Net Income from Continuing Operations",
         "Total Assets",
         "Operating Cash Flow",
         "Long Term Debt And Capital Lease Obligation",
         "Total Non Current Liabilities Net Minority Interest",
         "Current Assets",
         "Current Liabilities",
         "Stockholders' Equity",
         "Total Revenue",
         "Gross Profit"] # change as required

indx = ["NetIncome","TotAssets","CashFlowOps","LTDebt","TotLTLiab",
        "CurrAssets","CurrLiab","CommStock","TotRevenue","GrossProfit"]


def info_filter(df,stats,indx,lookback):
    """function to filter relevant financial information
       df = dataframe to be filtered
       stats = headings to filter
       indx = rename long headings
       lookback = number of years of data to be retained"""
    for stat in stats:
        if stat not in df.index:
            print("unable to find {} in {}".format(stat,df.columns[0]))
            return
    df_new = df.loc[stats,df.columns[:3]]
    df_new.rename(dict(zip(stats,indx)),inplace=True)
    df_new.loc["OtherLTDebt",:] = df_new.loc["TotLTLiab",:] - df_new.loc["LTDebt",:]
    return df_new

#applying filtering to the finacials
t_df = {}
for ticker in financial_dir:
    t_df[ticker] = info_filter(financial_dir[ticker],stats,indx,3)


def piotroski_f(df_dict):
    """function to calculate f score of each stock and output information as dataframe"""
    f_score = {}
    for ticker in df_dict:
        columns = df_dict[ticker].columns
        ROA_FS = int(df_dict[ticker].loc["NetIncome",columns[0]]/((df_dict[ticker].loc["TotAssets",columns[0]] + df_dict[ticker].loc["TotAssets",columns[1]])/2) > 0)
        CFO_FS = int(df_dict[ticker].loc["CashFlowOps",columns[0]] > 0)
        ROA_D_FS = int((df_dict[ticker].loc["NetIncome",columns[0]]/((df_dict[ticker].loc["TotAssets",columns[0]] + df_dict[ticker].loc["TotAssets",columns[1]])/2)) > (df_dict[ticker].loc["NetIncome",columns[1]]/((df_dict[ticker].loc["TotAssets",columns[1]] + df_dict[ticker].loc["TotAssets",columns[2]])/2)))
        CFO_ROA_FS = int(df_dict[ticker].loc["CashFlowOps",columns[0]]/df_dict[ticker].loc["TotAssets",columns[0]] > df_dict[ticker].loc["NetIncome",columns[0]]/((df_dict[ticker].loc["TotAssets",columns[0]] + df_dict[ticker].loc["TotAssets",columns[1]])/2))
        LTD_FS = int((df_dict[ticker].loc["LTDebt",columns[0]] + df_dict[ticker].loc["OtherLTDebt",columns[0]]) < (df_dict[ticker].loc["LTDebt",columns[1]] + df_dict[ticker].loc["OtherLTDebt",columns[1]]))
        CR_FS = int((df_dict[ticker].loc["CurrAssets",columns[0]] / df_dict[ticker].loc["CurrLiab",columns[0]]) > (df_dict[ticker].loc["CurrAssets",columns[1]] / df_dict[ticker].loc["CurrLiab",columns[1]]))
        DILUTION_FS = int(df_dict[ticker].loc["CommStock",columns[0]] <= df_dict[ticker].loc["CommStock",columns[1]])
        GM_FS = int((df_dict[ticker].loc["GrossProfit",columns[0]]/df_dict[ticker].loc["TotRevenue",columns[0]]) > (df_dict[ticker].loc["GrossProfit",columns[1]]/df_dict[ticker].loc["TotRevenue",columns[1]]))
        ATO_FS = int((df_dict[ticker].loc["TotRevenue",columns[0]]/((df_dict[ticker].loc["TotAssets",columns[0]] + df_dict[ticker].loc["TotAssets",columns[1]])/2)) > (df_dict[ticker].loc["TotRevenue",columns[1]]/((df_dict[ticker].loc["TotAssets",columns[1]] + df_dict[ticker].loc["TotAssets",columns[2]])/2)))
        f_score[ticker] = [ROA_FS,CFO_FS,ROA_D_FS,CFO_ROA_FS,LTD_FS,CR_FS,DILUTION_FS,GM_FS,ATO_FS]
    f_score_df = pd.DataFrame(f_score,index=["PosROA","PosCFO","ROAChange","Accruals","Leverage","Liquidity","Dilution","GM","ATO"])
    return f_score_df

# sorting stocks with highest Piotroski f score to lowest
f_score_df = piotroski_f(t_df)
f_score_df.sum().sort_values(ascending=False)














