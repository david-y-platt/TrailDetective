# originally TrailDetective instantiated a GPXManager object...
# ... but this required TrailDetective __main__ to know aboutGPXManager __init__, add_point, and finalize methods
# for better decoupling, switched to a single create_gpx_file call
class GPXManager:
        
    def __init__(self, name):
        
        self.name = name
        
        #header formalities
        self.f = open(self.name, "w+")
        self.f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.f.write('<gpx creator="GPXManager" version="1.1"\n')
        self.f.write('  xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/11.xsd"\n')
        self.f.write('  xmlns="http://www.topografix.com/GPX/1/1"\n')
        self.f.write('  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')
        self.f.write('  <trk>\n')
        self.f.write('    <trkseg>\n')

    def add_point(self, lat, lon, ele=None, datetime=None):
        
        self.f.write('      <trkpt lat="' + lat + '" lon="' + lon + '">\n')
        if ele is not None:
            self.f.write('        <ele>'  + ele  + '</ele>\n')
        if datetime is not None:
            self.f.write('        <time>' + datetime + '</time>\n')
        self.f.write('      </trkpt>\n')
    
    def finalize(self):
        
        #trailer formalities 
        self.f.write('    </trkseg>\n')
        self.f.write('  </trk>\n')
        self.f.write('</gpx>\n')
        
        self.f.close()
        
def create_gpx_file(name,point_list):
    
    #header formalities
    f = open(name, "w+")
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<gpx creator="GPXManager" version="1.1"\n')
    f.write('  xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/11.xsd"\n')
    f.write('  xmlns="http://www.topografix.com/GPX/1/1"\n')
    f.write('  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')
    f.write('  <trk>\n')
    f.write('    <trkseg>\n')
    
    #add points to GPX file
    while len(point_list) > 0:
        
        datetime,lat,lon,ele = point_list.pop(0)
        
        f.write('      <trkpt lat="' + lat + '" lon="' + lon + '">\n')
        if ele is not None:
            f.write('        <ele>'  + ele  + '</ele>\n')
        if datetime is not None:
            f.write('        <time>' + datetime + '</time>\n')
        f.write('      </trkpt>\n')

    #trailer formalities        
    f.write('    </trkseg>\n')
    f.write('  </trk>\n')
    f.write('</gpx>\n')
    
    f.close()
    
    print('GPX file created:', name)  