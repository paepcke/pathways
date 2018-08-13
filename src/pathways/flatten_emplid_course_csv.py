#!/usr/bin/env python
'''
Created on Aug 9, 2018

@author: paepcke
'''
import csv
import os
import sys

class EmplidCourseFlattener(object):
    
    def __init__(self, infile, outfile):
        with open(outfile, 'w') as outFd:
            with open(infile, 'r') as inFd:
                reader = csv.reader(inFd)
                curr_emplid = None
                course_list = []
                processed   = 0
                for (emplid, course) in reader:
                    if emplid != curr_emplid:
                        outFd.write(','.join(course_list) + '\n')
                        curr_emplid = emplid
                        course_list = []
                        processed += 1
                    course_list.append(course)
        print('Processed %s lines.' % processed)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: %s infile, outfile' % os.path.basename(sys.argv[0]))
        sys.exit(1)
        
    (infile,outfile) = sys.argv[1:3]
    EmplidCourseFlattener(os.path.abspath(infile), os.path.abspath(outfile))