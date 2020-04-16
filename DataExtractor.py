#std packages
import os

#installed packages
import PIL.Image

#imports for google gcloud drive
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

#From EXIF standards page: https://www.exiv2.org/tags.html
GPS_GROUP_TAG = 34853
NORTH_SOUTH_TAG = 1
LATITUDE_TAG = 2
EAST_WEST_TAG = 3
LONGITUDE_TAG = 4
ALTITUDE_TAG = 6
TIMESTAMP_TAG = 7
DATE_TAG = 29

#list of valid file extensions for photos
EXT_LIST = ('jpg','jpeg','gif','png','tiff','raw')

def standardize_exif_lat(exif_lat,dir):
    
    deg, min, sec = exif_lat
    lat = ( deg[0] / deg[1]
          + min[0] / min[1] / 60
          + sec[0] / sec[1] / 3600 )
    if dir == 'S':
        lat *= -1
    elif dir != 'N':
        raise Exception('Invalid N/S: ' + dir)
    return str(lat)

def standardize_exif_lon(exif_lon,dir):
    
    deg, min, sec = exif_lon
    lon = ( deg[0] / deg[1]
          + min[0] / min[1] / 60
          + sec[0] / sec[1] / 3600 )
    if dir == 'W':
        lon *= -1
    elif dir != 'E':
        raise Exception('Invalid E/W: ' + dir)
    return str(lon)

def standardize_exif_ele(exif_ele):
    
    if exif_ele is None:
         return None
    return str(exif_ele[0] / exif_ele[1])

def standardize_exif_datetime(exif_date,exif_time):
    
    year, month, date = exif_date.split(':')
    
    hour, min, sec = exif_time
    hour = int(hour[0] / hour[1])
    min =  int(min[0]  / min[1])
    sec =  int(sec[0]  / sec[1])
                
    return str(year).zfill(2) + '-' + str(month).zfill(2) + '-' + str(date).zfill(2) + 'T' + str(hour).zfill(2) + ':' + str(min).zfill(2) + ':' + str(sec).zfill(2) + '.000Z'

def standardize_gcloud_datetime(gcloud_datetime):
    date, time = gcloud_datetime.split(' ')
    date.replace(':','-')
    return date + 'T' + time + '.000Z'

def standardize_gcloud_lat(lat):
    return str(lat)

def standardize_gcloud_lon(lon):
    return str(lon)

def standardize_gcloud_ele(ele):
    return str(ele)

def get_points_local(dir):
    
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
            lat = standardize_exif_lat(exif_data[GPS_GROUP_TAG][LATITUDE_TAG], exif_data[GPS_GROUP_TAG][NORTH_SOUTH_TAG])
        except:
            print("WARNING: skipping photo with missing or invalid latitude data:", photo)
            skipped_photo_ctr += 1
            photo_image.close()
            continue
        
        try:
            lon = standardize_exif_lon(exif_data[GPS_GROUP_TAG][LONGITUDE_TAG], exif_data[GPS_GROUP_TAG][EAST_WEST_TAG])
        except:
            print("WARNING: skipping photo with missing or invalid longitude data:", photo) 
            skipped_photo_ctr += 1
            photo_image.close()
            continue     
        
        try:
            datetime = standardize_exif_datetime(exif_data[GPS_GROUP_TAG][DATE_TAG],exif_data[GPS_GROUP_TAG][TIMESTAMP_TAG])
        except:
            print("WARNING: skipping photo with missing or invalid datetime data:", photo) 
            skipped_photo_ctr += 1
            photo_image.close()
            continue    
        
        try:   
            ele = standardize_exif_ele(exif_data[GPS_GROUP_TAG].get(ALTITUDE_TAG))
        except:
            print("WARNING: skipping photo with invalid ele data:", photo) 
            skipped_photo_ctr += 1
            photo_image.close()
            continue  

        point_list.append((datetime,lat,lon,ele))
        used_photo_ctr += 1
        photo_image.close()
        
    tot_photos = used_photo_ctr + skipped_photo_ctr 
    print ("\n***** ANALYSIS COMPLETED *****\n")
    print ("total photos processed:", tot_photos)
    print ("photos missing GPS data:", skipped_photo_ctr , "(" +str(round(skipped_photo_ctr / tot_photos * 100,2)) + "%)")
        
    return point_list

def get_points_gcloud(dir):
    
    #track stats
    used_photo_ctr = 0
    skipped_photo_ctr = 0

    # Seed Code from: https://developers.google.com/drive/api/v3/quickstart/python?authuser=1
    
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
                         fields="nextPageToken, files(id, name,imageMediaMetadata)")
    if request is None:
        raise Exception('No files found in directory: ' + dir)
    
    point_list = []
    while(request is not None):
        result = request.execute()
        photos = result.get('files', [])
        for photo in photos:
            
            try:
                datetime = standardize_gcloud_datetime(photo['imageMediaMetadata']['time'])
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
                lat = standardize_gcloud_lat(loc_data['latitude'])
            except:
                print("WARNING: skipping photo with missing or invalid latitude data:", photo['name'])
                skipped_photo_ctr += 1
                continue
            
            try:
                lon = standardize_gcloud_lon(loc_data['longitude'])
            except:
                print("WARNING: skipping photo with missing or invalid longitude data:", photo['name']) 
                skipped_photo_ctr += 1
                continue   
            
            try:   
                ele = standardize_gcloud_ele(loc_data['altitude'])
            except:
                print("WARNING: skipping photo with invalid altitude data:", photo['name']) 
                skipped_photo_ctr += 1
                continue

            point_list.append((datetime,lat,lon,ele))
            used_photo_ctr += 1
        
        request = files.list_next(request,result)
    
    tot_photos = used_photo_ctr + skipped_photo_ctr 
    print ("\n***** ANALYSIS COMPLETED *****\n")
    print ("total photos processed:", tot_photos)
    print ("photos missing GPS data:", skipped_photo_ctr , "(" +str(round(skipped_photo_ctr / tot_photos * 100,2)) + "%)")
        
    return point_list