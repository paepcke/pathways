#!/usr/bin/env python
import argparse
import csv
import os
import sys
import zlib


class Obfuscator(object):
    '''
    Given: one or more column numbers, orgin 0. Reads lines
    of TAB-separated values from stdin. Each referenced column
    may contain either one or several comma-separated strings. 
    Each of these strings is deterministically converted to 
    a 32bit integer using zlip.adler32().
    
    For example:
    
       20122013        ACCT541 clee8
       
    ==> 20122013        ACCT541 2565454
    
    Or:
       20122013        ACCT340 clee8,chaga,clee8,chaga
       
    ==> 20122013        ACCT340 145634,245656,3877,44689
       
    Useful to anonymize comma-separated sunet ids while
    preserving identity.
    
    Usage:
      For Left-most column to be converted:
         cat myFile.tsv | student_id_shortener.py 0
      Left-most col and column 4 (i.e. 5th col):
         cat myFile.tsv | student_id_shortener.py 0 4
      For Left-most column to be converted and skip one header line:
         cat myFile.tsv | student_id_shortener.py -s 1 0
    
    '''

    def __init__(self, cols_to_convert, in_file=None, skip=0):
        '''
        Constructor
        
        @param cols_to_convert: column number, or list of column numbers to convert
        @type cols_to_convert: {int | [int]}
        @param skip: number of lines to skip; use for preserving column header line.
        @type skip: int
        '''

        try:
            if in_file is None:
                in_fd = sys.stdin
            else:
                in_fd = open(in_file, 'r')
                
            csv_reader = csv.reader(in_fd, delimiter='\t')
            csv_writer = csv.writer(sys.stdout, delimiter='\t')
            if type(cols_to_convert) != list:
                cols_to_convert = [cols_to_convert]
    
            # Skip lines if requested:
            for _i in range(skip):
                line = next(csv_reader)
                csv_writer.writerow(line)
            
            for line_arr in csv_reader:
                for col_num in cols_to_convert:
                    col_csv_str = line_arr[col_num]
                    # Split the csv list into an array:
                    col_csv_list = col_csv_str.split(',')
                    col_obfuscated = []
                    for val_to_obfuscate in col_csv_list:
                        obfuscation = zlib.adler32(val_to_obfuscate.encode())
                        col_obfuscated.append(str(obfuscation))
                        
                    # col_obfuscated now has an int for every value in the csv
                    # column. Turn into a csv list, and replace as the new
                    # value for the current column:
                    line_arr[col_num] = ','.join(col_obfuscated)
                csv_writer.writerow(line_arr)
        finally:
            # If input was from a file (as opposed to stdin), then close the fd:
            if in_file is not None:
                in_fd.close()
            
if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description="Deterministically replaces columns in csv files with 32bit ints."
                                     )

    parser.add_argument('-f', '--file',
                        help='Path to file to convert. Default: stdin',
                        default=None
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
    
    Obfuscator(args.columns, in_file=args.file, skip=args.skip)
