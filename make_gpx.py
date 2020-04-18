#std packages
import argparse

#local packages
import GPXWriter
import PointExtractor

LOCAL = 'local'
GCLOUD = 'gcloud'

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('dir_type',    choices={LOCAL, GCLOUD}, help='type of storage directory: local or gcloud')
    parser.add_argument('input_dir',                            help='input directory name')
    parser.add_argument('output_file',                          help="output file name for GPX file, e.g. mytrail.gpx")
    parser.add_argument('--utc_zone',  type=int, default=0,     help="UTC timezone as an int offset from GMT, e.g. -4 or 3")
    
    args = parser.parse_args()
    
    pe = PointExtractor.PointExtractor(stringify=True)
    point_list = []
    if args.dir_type == LOCAL:
        point_list = pe.get_points_local(args.input_dir,args.utc_zone)
    elif args.dir_type == GCLOUD:
        point_list = pe.get_points_gcloud(args.input_dir,args.utc_zone)
    else:
        #shouldn't get here since argparser enforces enums, but just in case...
        raise Exception("Invalid dir_type: " + dir_type)

    GPXWriter.create_gpx_file(args.output_file,point_list)