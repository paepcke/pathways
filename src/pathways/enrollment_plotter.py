'''
Created on Aug 28, 2018

@author: paepcke
'''
import os
import sqlite3
import numpy as np

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
        #****print(self.per_quarter_enrollment_sums)
        self.plot_enrollment_history(self.per_quarter_enrollment_sums)
        
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
    
    def plot_enrollment_history(self, data):
        
        quarters    = [int(strm_enrollment[0]) for strm_enrollment in data]
        enrollments = [strm_enrollment[1] for strm_enrollment in data]
        y_pos = np.arange(len(quarters))

        plt.bar(y_pos, enrollments, align='center', alpha=0.5)
        plt.xticks(y_pos, quarters)
        plt.ylabel('Enrollment')
        plt.title('Enrollment Since 2000')
 
        plt.show()


if __name__ == '__main__':
    #****EnrollmentPlotter(['CS106A', 'CS106B'])        
    #EnrollmentPlotter(['CS106A'])        
    EnrollmentPlotter(['MATH104'])
