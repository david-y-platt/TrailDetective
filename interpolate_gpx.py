#std packages
import argparse
import datetime as dt
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import pylab
from sklearn import linear_model
from sklearn.metrics import r2_score


#local packages
import PointExtractor
import GPXWriter

#positions in point tuple
DATETIME = 0
LAT = 1
LON = 2
ELE = 3

# https://www.thoughtco.com/degree-of-latitude-and-longitude-distance-4070616
DEG_LAT_DIST = 111 * 10**3

def get_lon_width(lat):
    return haversine_dist(lat,lat,0,1)

def haversine_dist(lat1,lat2,lon1,lon2):
    
    #avg earth radius used for haversine dist formula
    R = 6371000
    
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(delta_lon/2)**2
    c = 2*math.asin(math.sqrt(a))
    
    return R * c

def calibrate_src(orig_src_df,orig_ref_df):

    src_df = orig_src_df.copy()
    orig_src_start = src_df.index.min()
    
    #create entries for missing seconds
    ref_df = orig_ref_df.resample('1S').first()
    #interpolate lat,lon,ele for newly created points
    ref_df.interpolate(method='time',inplace=True)

    min_offset = min(0,int((ref_df.index.min() - src_df.index.min()).total_seconds()))
    max_offset = max(0,int((ref_df.index.max() - src_df.index.max()).total_seconds()))
    
    merged_df = src_df.join(ref_df,how='outer',lsuffix='_src',rsuffix='_ref')
    src_cols = ['lat_src','lon_src','ele_src']
    
    print(f'Testing calibration range: [{min_offset}, {max_offset}] s')

    orig_err_df = get_err_df(merged_df)
    orig_l1_err = orig_err_df['l1_err'].mean()
        
    merged_df[src_cols] = merged_df[src_cols].shift(min_offset)
    
    MAX_ITR = merged_df.index[-1] - pd.Timedelta(src_df.index[-1] - src_df.index[0])
    mean_err_df = pd.DataFrame(columns=['l1_err','l2_err'])
    mean_err_df.index.name = 'datetime'
    

    for time_itr in merged_df.index[range(0, max_offset - min_offset)]:
        
        # full haversine dist not used for perf reasons. for calibration approx is fine
        err_df = get_err_df(merged_df)
        mean_err_df.loc[time_itr] = {'l1_err':err_df['l1_err'].mean(),'l2_err':err_df['l2_err'].mean()}
        merged_df[src_cols] = merged_df[src_cols].shift(1)
   
#     mean_err_df.dropna(inplace=True)
    best_l1_err = mean_err_df['l1_err'].min()
    best_idx = mean_err_df['l1_err'].values.argmin()
    best_datetime = mean_err_df.index[best_idx]   
    best_offset = int((best_datetime - orig_src_start).total_seconds())
    
    merged_df[src_cols] = merged_df[src_cols].shift(int(pd.Timedelta(best_datetime - MAX_ITR).total_seconds()))
    best_err_df = get_err_df(merged_df)
    
    print(
            f'Calibrated L1 err:   {round(best_l1_err,2)} ' \
            f'({round((best_l1_err - orig_l1_err) / orig_l1_err * 100,2)}%) reduction ' \
            f'from {round(orig_l1_err,2)} ' \
            f'@ offset {best_offset}'
        )
        
    return best_offset

        
def get_err_df(merged_df):
    
    #only calc once. change insignificant over course of single hike
    DEG_LON_DIST = get_lon_width(merged_df.loc[merged_df['lat_src'].first_valid_index(),
                                               'lat_src'])
    
    #taking sqrt for err than squaring for sq_err is extra work, but doing for clarity of metrics
    err_df = pd.DataFrame(index=merged_df.index)
    
    err_df['l1_err'] = (  np.sqrt(
                np.square((merged_df['lat_src'] - merged_df['lat_ref']) * DEG_LAT_DIST) +
                np.square((merged_df['lon_src'] - merged_df['lon_ref']) * DEG_LON_DIST)
            )
          )
    
    err_df['l2_err'] = np.square(err_df['l1_err'])
              
    return err_df

if __name__ == '__main__':

    for src_file, ref_file in [
            ('clark-local.gpx','clark-watch.gpx'),
            ('great_dune-local.gpx','great_dune-watch.gpx'),
            ('mesquite-local.gpx','mesquite-watch.gpx'),
            ('ncrater-local.gpx','ncrater-watch.gpx'),
            ('wasson-local.gpx','wasson-watch.gpx')
        ]:
        
            pe = PointExtractor.PointExtractor(stringify=False)
            
            orig_src_df = pe.get_points_gpx(src_file) 
            if len(orig_src_df.index) < 2:
                raise Exception(f'<2 points detected in src file (at least 2 are needed): {src_file}')
        
            orig_ref_df = pe.get_points_gpx(ref_file)
            if len(orig_ref_df.index) == 0:
                raise Exception(f'0 points detected in ref file: {ref_file}')
            
            offset = calibrate_src(orig_src_df,orig_ref_df)
                        
            #interpolate src_df
            #create entries for missing seconds
            orig_src_df['nearest_pt_idx'] = range(len(orig_src_df.index))
            src_df = orig_src_df.resample('1S').first()
            #interpolate lat,lon,ele for newly created points
            src_df[['lat','lon','ele']] = src_df[['lat','lon','ele']].interpolate(method='time',inplace=False)
            src_df['nearest_pt_idx'] = src_df['nearest_pt_idx'].interpolate(method='nearest',inplace=False).astype('int64')
            src_df['s_nearest_src'] = np.abs((orig_src_df.index[src_df['nearest_pt_idx'].values] - src_df.index).total_seconds())
            src_df.drop(columns='nearest_pt_idx',inplace=True)

            #interpolate ref_df
            #create entries for missing seconds
            orig_ref_df['nearest_pt_idx'] = range(len(orig_ref_df.index))
            ref_df = orig_ref_df.resample('1S').first()
            #interpolate lat,lon,ele for newly created points
            ref_df[['lat','lon','ele']] = ref_df[['lat','lon','ele']].interpolate(method='time',inplace=False)
            ref_df['nearest_pt_idx'] = ref_df['nearest_pt_idx'].interpolate(method='nearest',inplace=False).astype('int64')
            ref_df['s_nearest_ref'] = np.abs((orig_ref_df.index[ref_df['nearest_pt_idx'].values] - ref_df.index).total_seconds())
            ref_df.drop(columns='nearest_pt_idx',inplace=True)        
            
            merged_df = src_df.join(ref_df,how='outer',lsuffix='_src',rsuffix='_ref')
            src_cols = ['lat_src','lon_src','ele_src','s_nearest_src']
            merged_df[src_cols] = merged_df[src_cols].shift(offset)
            merged_df.dropna(inplace=True)

    
            err_df = get_err_df(merged_df)
            
            print(f"Interpolated L1 err: {round(err_df['l1_err'].mean(),2)}")                 
                        
            X_s_nearest_src = merged_df.loc[err_df.index,'s_nearest_src'].to_frame()

            X_ele_raw_src = merged_df['ele_src'].to_frame()
            X_ele_rel_src = (merged_df['ele_src'] - np.mean(merged_df['ele_src'])).to_frame()
            X_ele_relabs_src = (np.abs(merged_df['ele_src'] - np.mean(merged_df['ele_src']))).to_frame()
            
            X_list = [X_ele_raw_src,
                      X_ele_rel_src,
                      X_ele_relabs_src]
            
            print (' R2 |  b  | coef')

            reg = linear_model.LinearRegression()
            reg.fit(X_s_nearest_src, err_df['l1_err'])
            print (round(reg.score(X_s_nearest_src, err_df['l1_err']),2),round(reg.intercept_,2), np.round(reg.coef_,2))
                
            for X in X_list:
                
                df_comb = pd.concat([X,X_s_nearest_src],axis=1)
                reg2 = linear_model.LinearRegression()
                reg2.fit(df_comb, err_df['l1_err'])
                print (round(reg2.score(df_comb, err_df['l1_err']),2),round(reg2.intercept_,2), np.round(reg2.coef_,2))
                            
            f, (ax1,ax2) = plt.subplots(nrows=2, ncols=1)
            default_x_size, default_y_size = pylab.gcf().get_size_inches()
            pylab.gcf().set_size_inches( (default_x_size * 2.75, default_y_size * 1.5) )
            
            ax1.scatter(merged_df.loc[err_df.index,'s_nearest_src'],err_df['l1_err'],s=1)  
#             ax2.scatter(merged_df.loc[err_df.index,'s_nearest_ref'],err_df['l1_err'],s=1)  
            
#             ax1.scatter(err_df.index,err_df['l1_err'])   
#             ax1.set_xlim(err_df.index[0],err_df.index[-1])
#             for pt in orig_src_df.index:
#                 ax1.axvline(x=pt, color='orange', linestyle='dashed')
            
#             plt.show()   
                
            
#             plt.hist(err_df['l1_err'],bins=20)
#             #set y-axis as pct tot
#             plt.gca().yaxis.set_major_formatter(PercentFormatter(len(err_df.index)))
#             plt.show()
            
    
    