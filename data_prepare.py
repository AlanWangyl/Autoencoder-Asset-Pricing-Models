import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None
from tqdm import tqdm
from joblib import delayed, Parallel
from itertools import product

import os

import warnings
warnings.filterwarnings('ignore')



if 'data' not in os.listdir():
    os.system('wget https://cloud.tsinghua.edu.cn/f/001a8f8ba2ba4cad9bf8/?dl=1 -O data.zip')
    os.system('unzip data.zip')
    

datashare = pd.read_csv('data/datashare.csv')
mon_ret = pd.read_csv('data/month_return.csv')

# stock-level characteristics with index corresponding to original paper
annual_chara = {
    'absacc': 1, 'acc': 2, 'age': 4, 'agr': 5, 'bm': 9,
    'bm_ia': 10, 'cashdebt': 12, 'cashpr': 13, 'cfp': 14, 'cfp_ia': 15,  
    'chatoia': 16, 'chcsho': 17, 'chempia': 18, 'chinv': 19, 'chpmia': 21,
    'convind': 24, 'currat': 25, 'depr': 26, 'divi': 27, 'divo': 28,
    'dy': 30, 'egr': 32, 'ep': 33, 'gma': 34, 'grcapx': 35,
    'grltnoa': 36, 'herf': 37, 'hire': 38, 'invest': 42, 'lev': 43,
    'lgr': 44, 'mve_ia': 52, 'operprof': 54, 'orgcap': 55, 'pchcapx_ia': 56,
    'pchcurrat': 57, 'pchdepr': 58, 'pchgm_pchsale': 59, 'pchquick': 60, 'pchsale_pchinvt': 61,
    'pchsale_pchrect': 62, 'pchsale_pchxsga': 63, 'pchsaleinv': 64, 'pctacc': 65, 'ps': 67, 
    'quick': 68, 'rd': 69, 'rd_mve': 70, 'rd_sale': 71, 'realestate': 72, 
    'roic': 77, 'salecash': 79, 'saleinv': 80, 'salerec': 81, 'secured': 82, 
    'securedind': 83, 'sgr': 84, 'sin': 85, 'sp': 86, 'tang': 91, 'tb': 92
}

quarter_chara = {
    'aeavol': 3, 'cash': 11, 'chtx': 22, 'cinvest': 23,
    'ear': 31, 'ms': 50, 'nincr': 53, 'roaq': 74,
    'roavol': 75, 'roeq': 76, 'rsup': 78, 'stdacc': 89, 'stdcf': 90
}

month_chara = {
    'baspread': 6, 'beta': 7, 'betasq': 8, 'chmom': 20,
    'dolvol': 29, 'idiovol': 39, 'ill': 40, 'indmom': 41,
    'maxret': 45, 'mom12m': 46, 'mom1m': 47, 'mom36m': 48,
    'mom6m': 49, 'mvel1': 51, 'pricedelay': 66, 'retvol': 73,
    'std_dolvol': 87, 'std_turn': 88, 'turn': 93, 'zerotrade': 94
}

charas = list(annual_chara.keys()) + list(quarter_chara.keys()) + list(month_chara.keys())



def pre_process(date):
    cross_slice = datashare.loc[datashare.DATE == date].copy(deep=False)
    
    omitted_mask = 1.0 * np.isnan(cross_slice.loc[cross_slice['DATE'] == date])
    # fill nan values with each factors median
    cross_slice.loc[cross_slice.DATE == date] = cross_slice.fillna(0) + omitted_mask * cross_slice.median()
    # if all stocks' factor is nan, fill by zero
    cross_slice.loc[cross_slice.DATE == date] = cross_slice.fillna(0)
    # rank-normalize all characteristics into the interval [-1, 1]
    cross_slice.loc[cross_slice.DATE == date, charas] = ((cross_slice - cross_slice.min()) / (cross_slice.max() - cross_slice.min()))[charas].fillna(0.5) * 2 - 1
    
    return cross_slice


def cal_portfolio_ret(it, df):
    d, f = it[0], it[1]
    # long portfolio, qunatile 0.0~0.1; short portfolio, qunatile 0.9~1.0
    long_portfolio = df.loc[df.DATE == d][['permno', f]].sort_values(by=f, ascending=False)[:df.loc[df.DATE == d].shape[0]//10]['permno'].to_list()
    short_portfolio = df.loc[df.DATE == d][['permno', f]].sort_values(by=f, ascending=False)[-df.loc[df.DATE == d].shape[0]//10:]['permno'].to_list()
    # long-short portfolio return
    long_ret = mon_ret.loc[mon_ret.date == d].drop_duplicates('permno').set_index('permno').reindex(long_portfolio)['ret-rf'].dropna().mean()
    short_ret = mon_ret.loc[mon_ret.date == d].drop_duplicates('permno').set_index('permno').reindex(short_portfolio)['ret-rf'].dropna().mean()
    chara_ret = 0.5*(long_ret - short_ret)
    
    return chara_ret



if __name__ == '__main__':
    # pre-process share data
    processed_df = Parallel(n_jobs=-1)(delayed(pre_process)(d) for d in tqdm(datashare.DATE.drop_duplicates().to_list(), colour='green', desc='Processing'))
    processed_df = pd.concat(processed_df)
    processed_df[['permno', 'DATE']] = processed_df[['permno', 'DATE']].astype(int)

    # calculate portfolio returns
    iter_list = list(product(datashare.DATE.drop_duplicates(), charas))
    portfolio_rets = Parallel(n_jobs=-1)(delayed(cal_portfolio_ret)(it, df=processed_df) for it in tqdm(iter_list, colour='green', desc='Calculating'))
    portfolio_rets = pd.DataFrame(np.array(portfolio_rets).reshape(-1, 94), index=datashare.DATE.drop_duplicates(), columns=charas).reset_index()
    
    processed_df.to_csv('data/datashare_re.csv')
    portfolio_rets.to_csv('data/portfolio_rets.csv')