'''
Created on Aug 28, 2018

@author: paepcke
'''
import os
import sqlite3

import matplotlib.pyplot as plt


class EnrollmentPlotter(object):
    '''
    classdocs
    '''

    def __init__(self, course_list):
        '''
        Constructor
        '''
        self.db_file = os.path.join(os.path.dirname(__file__), '../data/enrollment_tally.sqlite')
        self.per_quarter_enrollment_sums = self.get_sums(course_list)
        print(self.per_quarter_enrollment_sums)
        
    def get_sums(self, course_list):
        conn = sqlite3.connect(self.db_file)
        cur  = conn.cursor()
        query = '''SELECT strm, SUM(enrollment) 
                      FROM enrollment_tally 
                     WHERE coursename IN (%s)
                     GROUP BY strm;
                     ''' % ','.join("'{0}'".format(x) for x in course_list)
        cur.execute(query)
        strm_sum_list = cur.fetchall()
        return strm_sum_list


if __name__ == '__main__':
    EnrollmentPlotter(['CS106A', 'CS106B'])        