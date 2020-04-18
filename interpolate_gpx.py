#std packages
import argparse
import datetime as dt
import math

#local packages
import PointExtractor

DATETIME = 0
LAT = 1
LON = 2
ELE = 3


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
    pass
    
    
def calc_avg_err(photo_point_list, ref_point_list):
    
    ref_point_list = interpolate_list(ref_point_list)
    ref_point_dict = dictify_list(ref_point_list)
    
    err = 0
            
    for photo_point in photo_point_list:
        ref_point = ref_point_dict.get(str(photo_point[DATETIME]))
        if ref_point is None:
            print('WARNING: photo datetime not found in interpolated datetime:', photo_point[DATETIME])
            continue
        err += math.sqrt( ( float(photo_point[LAT]) - float(ref_point[LAT]) ) ** 2 + ( float(photo_point[LON]) - float(ref_point[LON]) ) ** 2)
        
    print(err / len(photo_point_list))
    

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('source_file',  help='file to be interpolated')
    parser.add_argument('ref_file',     help='file containing points that source will interpolate to')
#     parser.add_argument('output_file',  help="output file name for GPX file, e.g. mytrail.gpx")

    args = parser.parse_args()

    
    # first extract all date pts from ref_file and store in ordered list
    # next extract all points from source file. if < 2 points throw err
    # for ref pts < first source point, extrapolate
    # interpolate
    # for points > last ref point, extrapolate
    
    # create element tree object 
    pe = PointExtractor.PointExtractor(stringify=False)
    source_point_list = pe.get_points_gpx(args.source_file)
    if len(source_point_list) < 2:
        raise Exception('<2 points detected in source file (at least 2 are needed): ' + args.source_file)

    ref_point_list = pe.get_points_gpx(args.ref_file)
    if len(ref_point_list) == 0:
        raise Exception('0 points detected in ref file: ' + args.ref_file)
    
    calc_avg_err(source_point_list,ref_point_list)
            
    
    