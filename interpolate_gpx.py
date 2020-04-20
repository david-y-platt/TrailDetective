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

def haversine_dist(lat1,lat2,lon1,lon2):
    
    # avg radius of eawrth in meters
    R = 6371000
    
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(delta_lon/2)**2
    c = 2*math.asin(math.sqrt(a))
    
    return R * c


# 
# def datetime_to_str(dt):
#     return ( str(dt.year)   + '-'+
#                  str(dt.month).zfill(2)  + '-'+
#                  str(dt.day).zfill(2)    + 'T' +
#                  str(dt.hour).zfill(2)   + ':'+
#                  str(dt.minute).zfill(2) + ':'+
#                  str(dt.second).zfill(2) +
#                  '.000Z' )

def interpolate_pt(src_pt1,src_pt2,dt_ref):
       
    scale_factor = (dt_ref - src_pt1[DATETIME]) / (src_pt2[DATETIME] - src_pt1[DATETIME])
    
    lat = src_pt1[LAT] + scale_factor * (src_pt2[LAT] - src_pt1[LAT])
    lon = src_pt1[LON] + scale_factor * (src_pt2[LON] - src_pt1[LON])
    ele = src_pt1[ELE] + scale_factor * (src_pt2[ELE] - src_pt1[ELE])
    
    return (dt_ref,lat,lon,ele)

def interpolate_range(src_pt1,src_pt2):
    
    interpolated_point_list = []
        
    sec_range = (src_pt2[DATETIME] - src_pt1[DATETIME]).seconds
    for sec_offset in range(1,sec_range):
        interpolated_point_list.append(interpolate_pt(src_pt1,src_pt2, src_pt1[DATETIME] + dt.timedelta(seconds=sec_offset)))

    return interpolated_point_list

def interpolate_list(point_list):
    
    if len(point_list) < 2:
        raise Exception('point_list is < 2 points and cannot be interpolated')
    
    interpolated_list = []
    for i in range(len(point_list) -1):
        interpolated_list.append(point_list[i])
        interpolated_list.extend(interpolate_range(point_list[i],point_list[i+1]))
    interpolated_list.append(point_list[-1])
    
    return interpolated_list

def dictify_list(point_list):

    d = dict()
    for point in point_list:
        d[str(point[DATETIME])] = point
        
    return d

def calibrate_time(photo_point_list, ref_point_list):
    
    min_photo_dt = photo_point_list[0][DATETIME]
    min_ref_dt = ref_point_list_interpolated[0][DATETIME]
    min_offset = int((min_ref_dt - min_photo_dt).total_seconds())
    
    max_photo_dt = photo_point_list[-1][DATETIME]
    max_ref_dt = ref_point_list_interpolated[-1][DATETIME]
    max_offset = int((max_ref_dt - max_photo_dt).total_seconds())
    
    print(f'Testing calibration range: [{min_offset}, {max_offset}] sec')
    
    lo_err = float('inf')
    best_offset = None
    best_offset_point_list = None
    
    for offset in range(min_offset,max_offset+1):
        offset_point_list = []
        for i in range(len(photo_point_list)):
            offset_point_list.append ( (photo_point_list[i][DATETIME] + dt.timedelta(seconds=offset),photo_point_list[i][LAT],photo_point_list[i][LON],photo_point_list[i][ELE] ))
        err = calc_avg_err(offset_point_list,ref_point_list_interpolated)
#         print(offset,err)
        if err < lo_err:
            lo_err = err
            best_offset = offset    
            best_offset_point_list = offset_point_list.copy()
    
    err_no_calibration = calc_avg_err(photo_point_list,ref_point_list_interpolated)
    pct_reduction = (err_no_calibration - lo_err) / err_no_calibration * 100

    print (f'calibration:\n'\
           f'  uncalibrated_err:   {round(err_no_calibration,2)} m/point\n' \
           f'  calibrated_err:     {round(lo_err,2)} m/point ({round(pct_reduction,2)}% reduction)\n' \
           f'  calibration offset: {best_offset} sec')
    
    return best_offset_point_list
    
def calc_avg_err(photo_point_list, ref_point_list):
    
    ref_point_dict = dictify_list(ref_point_list)
    
    err = 0
    skipped_ctr = 0
            
    for photo_point in photo_point_list:
        ref_point = ref_point_dict.get(str(photo_point[DATETIME]))
        if ref_point is None:
            print('WARNING: photo datetime not found in interpolated datetime:', photo_point[DATETIME])
            skipped_ctr += 1
            continue
        err += haversine_dist(photo_point[LAT],ref_point[LAT],photo_point[LON],ref_point[LON])
                
    return err / (len(photo_point_list) - skipped_ctr)

def calc_err_distribution(photo_point_list, ref_point_list):
    
    ref_point_dict = dictify_list(ref_point_list)
    ret = np.empty(shape=(len(photo_point_list)))

    for i in range(len(photo_point_list)):
        photo_point = photo_point_list[i]
        ref_point = ref_point_dict.get(str(photo_point[DATETIME]))
        if ref_point is None:
            ret[i] = np.nan
        else:            
            ret[i] = haversine_dist(photo_point[LAT],ref_point[LAT],photo_point[LON],ref_point[LON])
            print(round(ret[i],1),str(photo_point[DATETIME]))
            print('  ',photo_point[LAT],ref_point[LAT])
            print('  ',photo_point[LON],ref_point[LON])

    return ret   

if __name__ == '__main__':
    
    source_file = None
    
    #local shortcut for local testing
    source_file = 'wasson-local.gpx'
    ref_file ='wasson-watch.gpx'
    
    if source_file is None:
    
        parser = argparse.ArgumentParser()
        parser.add_argument('source_file',  help='reconstructed file')
        parser.add_argument('ref_file',     help='golden source file')
    #     parser.add_argument('output_file',  help="output file name for GPX file, e.g. mytrail.gpx")
    
        args = parser.parse_args()
        
        source_file = args.source_file
        ref_file = args.ref_file

    
    
    pe = PointExtractor.PointExtractor(stringify=False)
    source_point_list = pe.get_points_gpx(source_file)
    if len(source_point_list) < 2:
        raise Exception('<2 points detected in source file (at least 2 are needed): ' + source_file)

    ref_point_list = pe.get_points_gpx(ref_file)
    if len(ref_point_list) == 0:
        raise Exception('0 points detected in ref file: ' + ref_file)
    
    ref_point_list_interpolated = interpolate_list(ref_point_list)
    calibrated_source_point_list = calibrate_time(source_point_list,ref_point_list_interpolated)
    err_distribution = calc_err_distribution(calibrated_source_point_list,ref_point_list_interpolated)
#     err_distribution = calc_err_distribution(source_point_list,ref_point_list_interpolated)
    print(err_distribution)
    print(np.mean(err_distribution),np.median(err_distribution))
    
    