#std packages
import argparse

#local packages
import PointExtractor

LOCAL  = 'local'
GCLOUD = 'gcloud'

class GPXWriter:

    #######################################################################
    # These 3 instance methods allow for flexible construction of GPX file
    #######################################################################
    
    ###### #1 #####       
    def __init__(self, name):
        
        self.name = name
        
        #header formalities
        self.f = open(self.name, "w+")
        self.f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.f.write('<gpx creator="GPXWriter" version="1.1"\n')
        self.f.write('  xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/11.xsd"\n')
        self.f.write('  xmlns="http://www.topografix.com/GPX/1/1"\n')
        self.f.write('  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')
        self.f.write('  <trk>\n')
        self.f.write('    <trkseg>\n')

    ###### #2 #####           
    def add_point(self, lat, lon, ele=None, datetime=None):
        
        self.f.write('      <trkpt lat="' + lat + '" lon="' + lon + '">\n')
        if ele is not None:
            self.f.write('        <ele>'  + ele  + '</ele>\n')
        if datetime is not None:
            self.f.write('        <time>' + datetime + '</time>\n')
        self.f.write('      </trkpt>\n')
        
    ###### #2a #####           
    def add_point_list(self, point_list):
        
        for point in point_list:
            datetime, lat,lon,ele = point
            self.add_point(lat,lon,ele,datetime)
    
    ###### #3 #####               
    def finalize(self):
        
        #trailer formalities 
        self.f.write('    </trkseg>\n')
        self.f.write('  </trk>\n')
        self.f.write('</gpx>\n')
        
        self.f.close()

##################################################################
# This static method constructs the GPX file in one go
################################################################## 
        
def make_gpx(dir_type,input_dir,utc_zone=0):
    
    pe = PointExtractor.PointExtractor(stringify=True)
    point_list = []
    if dir_type == LOCAL:
        point_list = pe.get_points_local(input_dir,utc_zone)
    elif dir_type == GCLOUD:
        point_list = pe.get_points_gcloud(input_dir,utc_zone)
    else:
        raise Exception("Invalid dir_type: " + dir_type)

    name = f'{input_dir}-{dir_type}.gpx'.lower()
    
    gpxw = GPXWriter(name)
    gpxw.add_point_list(point_list)
    gpxw.finalize()
    
    print('GPX file created:', name)  
    
    
if __name__ == '__main__':
    
    dir_type = None
    
    #local shortcut for local testing
    dir_type = LOCAL
    input_dir = 'clark'
    utc_zone = -4
    
    if dir_type is None:
        parser = argparse.ArgumentParser()
        parser.add_argument('dir_type',    choices={LOCAL, GCLOUD}, help='type of storage directory: local or gcloud')
        parser.add_argument('input_dir',                            help='input directory name')
        parser.add_argument('--utc_zone',  type=int, default=0,     help="UTC timezone as an int offset from GMT, e.g. -4 or 3")
        
        args = parser.parse_args()
        
        dir_type  = args.dir_type
        input_dir = args.input_dir
        utc_zone  = args.utc_zone
            
    make_gpx(dir_type, input_dir, utc_zone)