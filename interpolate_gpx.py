#std packages
import argparse
import datetime as dt
import math
import numpy as np
import pandas as pd

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

def calibrate_time_df(src_df,ref_df):

    orig_datetime = src_df.index.min()

    src_len = len(src_df.index)
    min_offset = int((ref_df.index.min() - src_df.index.min()).total_seconds())
    max_offset = int((ref_df.index.max() - src_df.index.max()).total_seconds())
    
    print(f'Testing calibration range: [{min_offset}, {max_offset}] sec')
    src_df.index = src_df.index + pd.Timedelta(min_offset,unit='s')
    
    merged_df = src_df.join(ref_df,how='outer',lsuffix='_src',rsuffix='_ref')
    src_cols = ['lat_src','lon_src','ele_src']
    merged_df[src_cols] = merged_df[src_cols].shift(min_offset)
    orig_err = calc_avg_err(merged_df)
    
    time_itr = merged_df.index[0]
    MAX_ITR = merged_df.index[-1] - pd.Timedelta(src_len,unit='s')
    err_df = pd.DataFrame(columns=['err'])
    err_df.index.name = 'offset'
    
    while time_itr <= MAX_ITR:
        # full haversine dist not used for perf reasons. for calibration approx is fine

        err = calc_avg_err(merged_df)
        err_df.loc[time_itr] = {'err':err}
        merged_df[src_cols] = merged_df[src_cols].shift(1)
        time_itr = time_itr + pd.Timedelta(1,unit='s')
    
    best_idx = err_df['err'].values.argmin()
    best_datetime = err_df.index[best_idx]
    best_offset = (best_datetime - orig_datetime).total_seconds()
    best_err = err_df['err'].iloc[best_idx]
    print(f'offset:    {best_offset}')
    print(f'avg_err:   {round(best_err,2)}')
    print(f'reduction: {round((best_err - orig_err) / orig_err * 100,2)}%')
    
    return err_df

        
def calc_avg_err(merged_df):
    
    #only calc once. change insignificant over course of single hike
    DEG_LON_DIST = get_lon_width(src_df.iloc[0]['lat'])
    
    err = (  np.sqrt(
                np.square((merged_df['lat_src'] - merged_df['lat_ref']) * DEG_LAT_DIST) +
                np.square((merged_df['lon_src'] - merged_df['lon_ref']) * DEG_LON_DIST)
            )
          ).mean()
          
    return err

if __name__ == '__main__':
    
    source_file = None
    
    #local shortcut for local testing
    source_file = 'great_dune-local.gpx'
    ref_file ='great_dune-watch.gpx'
    
    if source_file is None:
    
        parser = argparse.ArgumentParser()
        parser.add_argument('source_file',  help='reconstructed file')
        parser.add_argument('ref_file',     help='golden source file')
    #     parser.add_argument('output_file',  help="output file name for GPX file, e.g. mytrail.gpx")
    
        args = parser.parse_args()
        
        source_file = args.source_file
        ref_file = args.ref_file

    pe = PointExtractor.PointExtractor(stringify=False)
    
    src_df = pe.get_points_gpx(source_file) 
    if len(src_df.index) < 2:
        raise Exception(f'<2 points detected in source file (at least 2 are needed): {source_file}')
    #create entries for missing seconds
    src_df = src_df.resample('1S').mean()
    #interpolate lat,lon,ele for newly created points
    src_df.interpolate(method='time',inplace=True)

    ref_df = pe.get_points_gpx(ref_file)
    if len(ref_df.index) == 0:
        raise Exception(f'0 points detected in ref file: {ref_file}')
    #create entries for missing seconds
    ref_df = ref_df.resample('1S').mean()
    #interpolate lat,lon,ele for newly created points
    ref_df.interpolate(method='time',inplace=True)
    
    calibrate_time_df(src_df,ref_df)
    
#     ref_df_calibrated = calibrate_time(src_df,ref_df)
#     err_distribution = calc_err_distribution(calibrated_source_point_list,ref_point_list_interpolated)
# #     err_distribution = calc_err_distribution(source_point_list,ref_point_list_interpolated)
#     print(err_distribution)
#     print(np.mean(err_distribution),np.median(err_distribution))
    
    