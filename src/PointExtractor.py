#std packages
import os
import xml.etree.ElementTree as ET
import re
import datetime as dt
import pandas as pd

#installed packages
import PIL.Image

#imports for google gcloud drive
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

#From EXIF standards page: https://www.exiv2.org/tags.html
GPS_GROUP_TAG = 34853
# TIME_ZONE_TAG = 34858 #not reliably populated
DATETIME_TAG  = 36867 # datetime for image

#these are all subgroup tags under the gps group tag
NORTH_SOUTH_TAG = 1
LATITUDE_TAG = 2
EAST_WEST_TAG = 3
LONGITUDE_TAG = 4
ALTITUDE_SIGN_TAG = 5
ALTITUDE_TAG = 6
TIMESTAMP_TAG = 7 # datetime for GPS data
SATELLITES_TAG = 8 #missing
GPS_STATUS_TAG = 9 #missing
GPS_MEASURE_MODE_TAG = 10 #missing
GPS_PRECISION_TAG = 11
GPS_SPEED_TAG = 13 #missing
GPS_MAP_TAG = 18 #missing
DATE_TAG = 29 # datetime for GPS data

#list of valid file extensions for photos
EXT_LIST = ('jpg','jpeg','gif','png','tiff','raw')

LAT = 'lat'
LON = 'lon'
ELE = 'ele'
DATETIME = 'datetime'
DOP = 'DOP'

class PointExtractor:
    
    def __init__(self,stringify=False):
        self.stringify = stringify

    def standardize_exif_lat(self,exif_lat,dir):
        
        deg, min, sec = exif_lat
        lat = ( deg[0] / deg[1]
              + min[0] / min[1] / 60
              + sec[0] / sec[1] / 3600 )
        if dir == 'S':
            lat *= -1
        elif dir != 'N':
            raise Exception('Invalid N/S: ' + dir)
        
        if self.stringify:
            lat = str(lat)
        return lat
    
    def standardize_exif_lon(self,exif_lon,dir):
        
        deg, min, sec = exif_lon
        lon = ( deg[0] / deg[1]
              + min[0] / min[1] / 60
              + sec[0] / sec[1] / 3600 )
        if dir == 'W':
            lon *= -1
        elif dir != 'E':
            raise Exception('Invalid E/W: ' + dir)
        
        if self.stringify:
            lon = str(lon)
        return lon  
      
    def standardize_exif_ele(self,exif_ele,exif_ele_sign):
        if exif_ele is None:
             return None
        ele = exif_ele[0] / exif_ele[1]
        
        if exif_ele_sign == b'\x01':
            ele *= -1
        elif exif_ele_sign != b'\x00':
            raise Exception('Invalid ele sign (expected 0 or 1): ' + exif_ele_sign)
        
        if self.stringify:
            ele = str(ele)
        return ele
    
    def standardize_exif_dilution_of_precision(self,exif_dilution_of_precision):
        if exif_dilution_of_precision is None:
             return None
        dilution_of_precision = exif_dilution_of_precision[0] / exif_dilution_of_precision[1]
        
        if self.stringify:
            dilution_of_precision = str(dilution_of_precision)
        
        print(dilution_of_precision)
        return dilution_of_precision
        
    def standardize_exif_datetime(self,exif_datetime,utc_zone):
        
        if utc_zone == 0:
            date, time = exif_datetime.split(' ')
            date = date.replace(':','-')
            return date + 'T' + time + '.000Z'
        
        date, time = exif_datetime.split(' ')
        year, month, day = date.split(':')
        time = time.split('.')[0]
        hour, minute, sec = time.split(':')
        
        datetime = dt.datetime(int(year),int(month),int(day),int(hour),int(minute),int(sec))
        datetime += dt.timedelta(hours=-utc_zone)
        
        if self.stringify:
            return ( str(datetime.year).zfill(2)   + '-'+
                     str(datetime.month).zfill(2)  + '-'+
                     str(datetime.day).zfill(2)    + 'T' +
                     str(datetime.hour).zfill(2)   + ':'+
                     str(datetime.minute).zfill(2) + ':'+
                     str(datetime.second).zfill(2) +
                     '.000Z' )
        else:
            return datetime
    
    def standardize_gcloud_lat(self,lat):
        
        if self.stringify:
            lat = str(lat)
        return lat
    
    def standardize_gcloud_lon(self,lon):
        
        if self.stringify:
            lon = str(lon)
        return lon    
    
    def standardize_gcloud_ele(self,ele):
        
        if self.stringify:
            ele = str(ele)
        return ele
    
    def standardize_gcloud_datetime(self,gcloud_datetime,utc_zone):
    
        if utc_zone == 0:
            date, time = gcloud_datetime.split(' ')
            date = date.replace(':','-')
            return date + 'T' + time + '.000Z'
        
        date, time = gcloud_datetime.split(' ')
        year, month, day = date.split('-')
        time = time.split('.')[0]
        hour, minute, sec = time.split(':')
        
        datetime = dt.datetime(int(year),int(month),int(day),int(hour),int(minute),int(sec))
        datetime += dt.timedelta(hours=-utc_zone)
        
        if self.stringify:
            return ( str(datetime.year).zfill(2)   + '-'+
                     str(datetime.month).zfill(2)  + '-'+
                     str(datetime.day).zfill(2)    + 'T' +
                     str(datetime.hour).zfill(2)   + ':'+
                     str(datetime.minute).zfill(2) + ':'+
                     str(datetime.second).zfill(2) +
                     '.000Z' )
        else:
            return datetime 
    
    def standardize_gpx_lat(self,lat):

        if not self.stringify:
            lat = float(lat)
        return lat
    
    def standardize_gpx_lon(self,lon):

        if not self.stringify:
            lon = float(lon)
        return lon
    
    def standardize_gpx_ele(self,ele):

        if not self.stringify:
            ele = float(ele)
        return ele
    
    def standardize_gpx_datetime(self,gpx_datetime):
        
        #expected format: '2019-02-14T06:28:54.000Z'
     
        if self.stringify:
            return datetime
        else:         
            date, time = gpx_datetime.split('T')
            year, month, day = date.split('-')
            time = time.split('.')[0]
            hour, minute, sec = time.split(':')
             
            datetime = dt.datetime(int(year),int(month),int(day),int(hour),int(minute),int(sec))
            return datetime
        
    def standardize_gpx_DOP(self,dilution_of_precision):

        if not self.stringify:
            dilution_of_precision = float(dilution_of_precision)
        return dilution_of_precision
          
    def get_points_local(self,dir,utc_zone):
        
        print(f'Extracting points from local <{dir}>')
        
        #track stats
        used_photo_ctr = 0
        skipped_photo_ctr = 0
        
        #list of points to return
        point_list = []
        
        #list of photo names
        photo_list = [dir + "/" + fname for fname in os.listdir(dir) if fname.split('.')[-1] in EXT_LIST]
        if len(photo_list) == 0:
            raise Exception("No photos in directory:", dir)
        
        for photo in photo_list:
            photo_image = PIL.Image.open(photo)
            exif_data = photo_image._getexif()
        
            if exif_data is None:
                print("WARNING: skipping photo with no exif data:", photo)
                skipped_photo_ctr += 1
                photo_image.close()
                continue
            
            if exif_data.get(GPS_GROUP_TAG) is None:
                print("WARNING: skipping photo with no GPS data:", photo)
                skipped_photo_ctr += 1
                photo_image.close()
                continue
                        
            try:       
                lat = self.standardize_exif_lat(exif_data[GPS_GROUP_TAG][LATITUDE_TAG], exif_data[GPS_GROUP_TAG][NORTH_SOUTH_TAG])
            except:
                print("WARNING: skipping photo with missing or invalid latitude data:", photo)
                skipped_photo_ctr += 1
                photo_image.close()
                continue
            
            try:
                lon = self.standardize_exif_lon(exif_data[GPS_GROUP_TAG][LONGITUDE_TAG], exif_data[GPS_GROUP_TAG][EAST_WEST_TAG])
            except:
                print("WARNING: skipping photo with missing or invalid longitude data:", photo) 
                skipped_photo_ctr += 1
                photo_image.close()
                continue     
            
            try:
                datetime = self.standardize_exif_datetime(exif_data[DATETIME_TAG],utc_zone)
            except:
                print("WARNING: skipping photo with missing or invalid datetime data:", photo) 
                skipped_photo_ctr += 1
                photo_image.close()
                continue    
            
            try:   
                ele = self.standardize_exif_ele(exif_data[GPS_GROUP_TAG].get(ALTITUDE_TAG),exif_data[GPS_GROUP_TAG].get(ALTITUDE_SIGN_TAG))
            except:
                print("WARNING: skipping photo with invalid ele data:", photo) 
                skipped_photo_ctr += 1
                photo_image.close()
                continue
            
            try:   
                dilution_of_precision = self.standardize_exif_dilution_of_precision(exif_data[GPS_GROUP_TAG].get(GPS_PRECISION_TAG))
            except:
                print("WARNING: skipping photo with invalid dilution_of_precision data:", photo) 
                skipped_photo_ctr += 1
                photo_image.close()
                continue  
    
            point_list.append((datetime,lat,lon,ele,dilution_of_precision))
            used_photo_ctr += 1
            photo_image.close()
            
        tot_photos = used_photo_ctr + skipped_photo_ctr 
        print ("\n***** ANALYSIS COMPLETED *****\n")
        print (f'total photos analyzed in <{dir}> : {tot_photos}')
        print (f'analyzed photos missing GPS data: {skipped_photo_ctr} ({round(skipped_photo_ctr / tot_photos * 100,2)}%)')
            
        return point_list
    
    def get_points_gcloud(self,dir,utc_zone):
        
        print(f'Extracting points from gcloud <{dir}>')
        
        #track stats
        used_photo_ctr = 0
        skipped_photo_ctr = 0
    
        # gcloud api docs: https://developers.google.com/drive/api/v3/reference/files#resource
        # seed code: https://developers.google.com/drive/api/v3/quickstart/python?authuser=1
        
        # If modifying these scopes, delete the file token.pickle.
        SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
    
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
    
        service = build('drive', 'v3', credentials=creds)
        
        # Call the Drive v3 API
        files = service.files()
        
        folder_request = files.list(q="name='" + dir + "'")
        folder_result = folder_request.execute()
        folder_items = folder_result.get('files', [])
        if len(folder_items) == 0:
            raise Exception("Folder not found: " + dir)
        if len(folder_items) > 1:
            raise Exception("Multiple folders with the same name found (a unique name is needed): " + dir)
        folder_id = folder_items[0]['id']
        
        request = files.list(q="mimeType != 'application/vnd.google-apps.folder'" \
                               " and '" + folder_id + "' in parents",
                             pageSize=100,
                             fields="nextPageToken, files(id, name,imageMediaMetadata,createdTime)")
        result = request.execute()
        photos = result.get('files', [])
        if len(photos) == 0:
            raise Exception('No files found in directory: ' + dir)
    
        point_list.sort()    
        point_list = []
        
        while(True):
    
            for photo in photos:
                if photo['name'].split('.')[-1] not in EXT_LIST:
                    continue
                            
                try:
                    datetime = self.standardize_gcloud_datetime(photo['imageMediaMetadata']['time'],utc_zone)
                except:
                    print("WARNING: skipping photo with missing or invalid datetime data:", photo['name']) 
                    skipped_photo_ctr += 1
                    continue    
                
                try:
                    loc_data = photo['imageMediaMetadata']['location']
                except:
                    print("WARNING: skipping photo with no GPS data:", photo['name'])
                    skipped_photo_ctr += 1
                    continue
                
                try:       
                    lat = self.standardize_gcloud_lat(loc_data['latitude'])
                except:
                    print("WARNING: skipping photo with missing or invalid latitude data:", photo['name'])
                    skipped_photo_ctr += 1
                    continue
                
                try:
                    lon = self.standardize_gcloud_lon(loc_data['longitude'])
                except:
                    print("WARNING: skipping photo with missing or invalid longitude data:", photo['name']) 
                    skipped_photo_ctr += 1
                    continue   
                
                try:   
                    ele = self.standardize_gcloud_ele(loc_data['altitude'])
                except:
                    print("WARNING: skipping photo with invalid altitude data:", photo['name']) 
                    skipped_photo_ctr += 1
                    continue
    
                point_list.append((datetime,lat,lon,ele))
                used_photo_ctr += 1
            
            request = files.list_next(request,result)
            if request is None:
                break
            result = request.execute()
            photos = result.get('files', [])
        
        tot_photos = used_photo_ctr + skipped_photo_ctr 
        print ("\n***** ANALYSIS COMPLETED *****\n")
        print ("total photos processed:", tot_photos)
        print ("photos missing GPS data:", skipped_photo_ctr , "(" +str(round(skipped_photo_ctr / tot_photos * 100,2)) + "%)")
    
        point_list.sort()    
        return point_list
    
    def get_points_gpx(self,gpx_file):
        
        if not os.path.exists(gpx_file):
            raise Exception(f'file not found: {gpx_file}')
        
        print(f'Extracting points from gpx file <{gpx_file}>')
    
        tree = ET.parse(gpx_file)
        root = tree.getroot()
        
        #get namespace which is needed to check name of later child nodes
        ns = re.match(r'{.*}', root.tag).group(0)
    
        point_df = pd.DataFrame(columns=[LAT,LON,ELE,DOP])
        point_df.index.name = DATETIME
      
        for track in root:
            #skip non-track top-level children, e.g. metadata
            if track.tag != ns + 'trk':
                continue
            for segment in track:
                for point in segment:
                    lat = self.standardize_gpx_lat(point.attrib['lat'])
                    lon = self.standardize_gpx_lon(point.attrib['lon'])
                    ele = None
                    datetime = None
                    dilution_of_precision = None
                    for opt_data in point:
                        if opt_data.tag == ns + 'ele':
                            ele = self.standardize_gpx_ele(opt_data.text)
                        elif opt_data.tag == ns + 'time':
                            datetime = self.standardize_gpx_datetime(opt_data.text)
                        elif opt_data.tag == ns + 'DOP':
                            dilution_of_precision = self.standardize_gpx_DOP(opt_data.text)
                    point_df.loc[pd.to_datetime(datetime)] = {LAT:lat, LON:lon, ELE:ele, DOP:dilution_of_precision}
    
        point_df.sort_index(inplace=True)
        return point_df