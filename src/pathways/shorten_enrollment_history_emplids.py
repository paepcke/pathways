'''
Created on Nov 13, 2018

@author: paepcke
'''
import argparse
import csv
import json
import os
import sys


class EmplidShortener(object):
    '''
    Given a path to a json-encoded emplid-->shortStudentId dict,
    import enrollmentHistory.csv, replace all the emplids with
    their corresponding short student IDs that were constructed
    by create_sentences.py. 
    '''


    def __init__(self, 
                 enrollment_history_path,
                 emplid_map_json_file,
                 output_file
                 ):
        '''
        Do all the work here.
        
        @param enrollment_history_path: the file with enrollment records, emplid always first in line
        @type enrollment_history_path: str
        @param emplid_map_json_file: the json-encoded dict file mapping emplids to shorter strings.
        @type emplid_map_json_file: str
        @param output_file: where to place the new enrollment history file with emplids replaced
        @type output_file: str
        '''

        with open(emplid_map_json_file, 'r') as json_dict_fd:
            emplid_map = json.load(json_dict_fd)
        with open(enrollment_history_path, 'r') as history_fd:
            csv_reader = csv.reader(history_fd)
            with open(output_file, 'w') as out_fd:
                result_writer = csv.writer(out_fd)
                # Transfer column header line unchanged:
                header_line = next(csv_reader)
                result_writer.writerow(header_line)
                
                for enrollment_record in csv_reader:
                    try:
                        short_name = emplid_map[enrollment_record[0]]
                    except KeyError:
                        print('Warning: one emplid not found in mapping dict.')
                        # Transfer the record unchanged:
                        result_writer.writerow(enrollment_record)
                        continue
                    enrollment_record[0] = short_name
                    result_writer.writerow(enrollment_record)
                    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--include',
                        help='include the shortened student ID at the start of each sentence',
                        default=False
                        )
    parser.add_argument('infile',
                        help='fully qualified path to enrollment history with long emplids\n'
                        )
    
    parser.add_argument('outfile',
                        help='fully qualified path where result records be placed \n'
                        )
    parser.add_argument('dictfile',
                        help='file path where emplid-->shortStudentId JSON encoded dict is stored'
                        )

    args = parser.parse_args();
    
    EmplidShortener(args.infile,
                    args.outfile, 
                    args.dictfile
                    ) 
                    
                    
                