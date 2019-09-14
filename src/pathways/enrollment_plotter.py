'''
Created on Aug 28, 2018

@author: paepcke
'''
import os
import sqlite3
import numpy as np

import matplotlib.pyplot as plt

from strmComputer import StrmComputer 


class EnrollmentPlotter(object):
    '''
    classdocs
    '''

    def __init__(self, parent, course_list, block=True):
        '''
        Constructor
        '''
        
        self.db_file = os.path.join(os.path.dirname(__file__), '../data/enrollment_tally.sqlite')
        self.per_quarter_enrollment_sums = self.get_sums(course_list)
        self.strm_computer = StrmComputer()
        self.plot_enrollment_history(self.per_quarter_enrollment_sums, course_list)
        plt.tight_layout()
        
        # Let parent know if user closes the enrollment
        # history window:
        
        self.fig.canvas.mpl_connect("close_event", parent.on_enroll_history_close)
        
        plt.show(block=block)
        
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
    
    def plot_enrollment_history(self, data, course_list):
        
        quarters    = [int(strm_enrollment[0]) for strm_enrollment in data]
        enrollments = [strm_enrollment[1] for strm_enrollment in data]
        y_pos = np.arange(len(quarters))

        self.fig, ax = plt.subplots() #@UnusedVariable
        ax.bar(y_pos, enrollments, align='center', alpha=0.5)
        self.set_xticks(quarters, ax)
        partial_course_str = self.get_partial_course_list(course_list, 3)
        ax.set_ylabel('Enrollment')
        title = 'Quarterly Enrollment %s Since 2000' % partial_course_str
        ax.set_title(title)
        self.fig.canvas.set_window_title(title)
        
    def set_xticks(self, quarters, ax):
        '''
        Given a list of strm, create X-axis labels for just the
        Fall quarter of each year. Have them show an an angle.
        
        @param quarters: quarter codes (strms)
        @type quarters: [int]
        '''
        ax.set_xlim(1,len(quarters))
        indices_of_fall_quarters = []
        xtick_labels = []
        # First of the years in the strms: 
        # For 1182 that's 118:
        curr_year = int(quarters[0] / 10)
        
        for quarter_num, strm in enumerate(quarters):
            #if strm % 10 == 2:
            year = int(strm / 10) 
            if year != curr_year:
                # It's the first quarter in a new year. Populate the xticks:
                (strm_year, quarter_name) =  self.year_from_strm(strm)
                xtick_labels.append('%s %s' % (quarter_name, strm_year))
                indices_of_fall_quarters.append(quarter_num)
                curr_year = year
        ax.set_xticks(indices_of_fall_quarters)
        ax.set_xticklabels(xtick_labels, rotation='45')
        
    def year_from_strm(self, strm):
        return self.strm_computer.strm2AcadPeriod(strm)

    def get_partial_course_list(self, course_list, max_num_courses):
        '''
        Given course name list, return a string listing the first few
        names, adding ellipses if needed. Example: return 'Math104,CS105,CS107...'
        
        @param course_list: list of course names
        @type course_list: [str]
        @param max_num_courses: maximum number of courses to list
        @type max_num_courses: int
        '''
        partial_course_list = course_list[:min(max_num_courses,len(course_list))]
        partial_courses_str = ','.join(partial_course_list)
        # Add ellipses if needed:
        if len(course_list) > len(partial_course_list):
            partial_courses_str += '...'
        return partial_courses_str
        

if __name__ == '__main__':
    EnrollmentPlotter(['CS106A', 'CS106B'])        
    #EnrollmentPlotter(['CS106A'])
    #EnrollmentPlotter(['MATH104'])
