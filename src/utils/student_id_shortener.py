#!/usr/bin/env python
import argparse
import csv
import os
import sys
import zlib


class StudentIdShortener(object):
    '''
    Given: one or more column numbers, orgin 0. Reads lines
    of comma-separated values from stdin. Each referenced column
    is deterministically converted to a 32bit integer using zlip.adler32().
    
    For example:
       "$2b$15$HezqO8vbpA11qCYOaoNNmu0czi7A2tqgv.cI5X3rZZgwbQ1bw7O6S" ===> 1030820711
       
    Useful to turn long, cumbersome hashes into easier ints, while
    preserving identity.
    
    Usage:
      For Left-most column to be converted:
         cat myFile.csv | student_id_shortener.py 0
      Left-most col and column 4 (i.e. 5th col):
         cat myFile.csv | student_id_shortener.py 0 4
      For Left-most column to be converted and skip one header line:
         cat myFile.csv | student_id_shortener.py -s 1 0

    
    '''
    
    def __init__(self, cols_to_convert, skip=0):
        '''
        Constructor
        
        @param cols_to_convert: column number, or list of column numbers to convert
        @type cols_to_convert: {int | [int]}
        @param skip: number of lines to skip; use for preserving column header line.
        @type skip: int
        '''
        
        csv_reader = csv.reader(sys.stdin)
        csv_writer = csv.writer(sys.stdout)
        if type(cols_to_convert) != list:
            cols_to_convert = [cols_to_convert]

        # Skip lines if requested:
        for _i in range(skip):
            line = next(csv_reader)
            csv_writer.writerow(line)
        
        for line_arr in csv_reader:
            for col_num in cols_to_convert:
                line_arr[col_num] = zlib.adler32(line_arr[col_num].encode())
            csv_writer.writerow(line_arr)
            
if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description="Deterministically replaces columns in csv files with 32bit ints."
                                     )

    parser.add_argument('-s', '--skip',
                        help='Number of lines to leave alone (Default: 0).',
                        type=int,
                        default=0
                        )

    parser.add_argument('columns',
                        help='Columns whose values to replace; repeatable.',
                        type=int,
                        nargs='+'
                        )
    
    args = parser.parse_args()
    
    StudentIdShortener(args.columns, args.skip)
                
            
            
        
