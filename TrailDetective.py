#std packages
import argparse

#local packages
import GPXManager
import DataExtractor

LOCAL = 'local'
GCLOUD = 'gcloud'

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('dir_type',   help='type of storage directory: local or gcloud', choices={LOCAL, GCLOUD})
    parser.add_argument('input_dir',  help='input directory name')
    parser.add_argument('output_file', help="output file name for GPX file, e.g. mytrail.gpx")
    
    args = parser.parse_args()
    
    #store tuples of GPS data from each photo. Sort by GPS timestamp after they're all extracted
    point_list = []
    if args.dir_type == LOCAL:
        point_list = DataExtractor.get_points_local(args.input_dir)
    elif args.dir_type == GCLOUD:
        point_list = DataExtractor.get_points_gcloud(args.input_dir)
    else:
        #shouldn't get here since argparser enforces enums, but just in case...
        raise Exception("Invalid dir_type: " + dir_type)

    #datetime is first item in tuples returned by DataExtractor, so this chronologically sorts tuples before creating GPX file          
    point_list.sort()
    GPXManager.create_gpx_file(args.output_file,point_list)