#!/usr/bin/env python
'''
Created on Feb 4, 2019

@author: paepcke
'''
import argparse
import csv
import os
import random
import subprocess
import sys


class SampleGenerator(object):
    '''
    Takes a csv file, a distribution of values, and changes the
    values in a given column to samples from the distribution. 
    Example:
       mod_csv_col_from_distribution --skip 1    # skip column name header
                                     --weight 45 # sample first member of pop at 45%
                                     --weight 55 # sample second member of pop at 55%
                                     --column 2  # column to modify in the csv file
                                     myFile.csv  # input file
                                     F           # first member of population
                                     M           # second member of population
                                     
    If weights are provided: one weight for each population member.
    
    Modified csv written to stdout.
    
    '''

    # ------------------------------
    # constructor
    # --------------------

    def __init__(self, csv_file, column, population, weights=None, skip=0):
        '''
        Constructor
        '''
        
        csv_resolved_file = os.path.realpath(csv_file)
        if not os.access(csv_resolved_file, os.R_OK):
            print("File %s does not exist or not readable." % csv_resolved_file)
            sys.exit(1) 
        
        # How many csv rows (wityhout the ones to skip) will we have?
        num_lines_to_modify = self.get_num_csv_lines(csv_resolved_file, skip)
        
        # Get the precomputed sequence of randomn samples:
        if weights is not None:
            samples = random.choices(population, weights, k=num_lines_to_modify)
        else:
            samples = random.choices(population)
        
        with open(csv_resolved_file, 'r') as csv_fd:
            csv_reader = csv.reader(csv_fd)
            csv_writer = csv.writer(sys.stdout)
    
            # Skip lines if requested:
            for _i in range(skip):
                line = next(csv_reader)
                csv_writer.writerow(line)
            
            for (line_arr, sample) in self.line_sample_it(csv_reader, samples):
                line_arr[column] =  sample
                csv_writer.writerow(line_arr)
            
    # ------------------------------
    # line_sample_it 
    # --------------------
    
    def line_sample_it(self, csv_reader, samples):
        for csv_line, sample in zip(csv_reader, samples):
            yield (csv_line, sample) 
            
    # ------------------------------
    # get_num_csv_lines 
    # --------------------
            
    def get_num_csv_lines(self, csv_file, skip):
        proc = subprocess.run(["wc", "-l", csv_file], capture_output=True)
        
        res = proc.stdout
        
        # Get something like: b'     713 /tmp/amt3.log\n'. 
        # Pull out the first int, which is the num of lines:
        num_lines = [int(res) for res in res.split() if res.isdigit()][0]
        
        # Subtract the number of lines that are to be skipped
        # e.g. the column name header:
        
        return num_lines - skip
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description="Replaces columns in csv files with values from a distribution."
                                     )

    parser.add_argument('-s', '--skip',
                        help='Number of lines to leave alone (Default: 0).',
                        type=int,
                        default=0
                        )

    parser.add_argument('-w', '--weight',
                        help='Weight for each member of population; repeatable; default: equal weights.',
                        type=int,
                        action='append',
                        default=None
                        )
    
    parser.add_argument('-c', '--column',
                        help='Column whose values to replace; zero-origin',
                        type=int,
                        default=None
                        )
    
    parser.add_argument('in_file',
                        help='CSV file to process',
                        )
    
    parser.add_argument('population',
                        help='Column whose values to replace; zero-origin',
                        nargs='+',
                        )
    
    
    args = parser.parse_args()
    
    # Column is manadory. It's only syntactically
    # an option to make the CLI invokation more readable:
    if args.column is None:
        print('Must provide a --column value.')
        sys.exit(1)
    
    
    # If weights given, must be same length as population
    weights = args.weight
    population = args.population
    if len(weights) > 0:
        if len(weights) != len(population):
            print('**** Error: if weigths are provided, num of weights must equal num of population.')
            sys.exit(1)
            
    # argparse adds (may sometimes?) a space to to the last element of the population.
    population_clean = [pop_member.strip() for pop_member in population]
    
    SampleGenerator(args.in_file,
                    args.column, 
                    population_clean, 
                    weights, 
                    args.skip)
    
        
        
    

    