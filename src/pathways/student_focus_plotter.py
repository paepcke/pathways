'''
Created on Sep 25, 2018

@author: paepcke
'''
import os
import sqlite3


class StudentFocusPlotter(object):
    '''
    classdocs
    '''


    def __init__(self, student_list):
        '''
        Constructor
        '''

class StudentComputer(object):
    
    def __init__(self):

        self.db_file = os.path.join(os.path.dirname(__file__), '../data/enrollment_tally.sqlite')
        try:
            self.sqlite_db_conn = sqlite3.connect(self.db_file)
        except Exception as e:
            raise ValueError("Could not connect ot Sqlite3 db at '%s' (%s)" % (self.db_file, repr(e)))
        
    #--------------------------------
    # all_stud_crses_strms 
    #------------------
    
    def all_stud_crses_strms(self):
        '''
        Return an iterator for query results:
            emplid, course_name, strm
        over all years.
        Caller should close the iterator if no more
        data is to be extracted from it.
        
        @return: iterator over db rows
        @rtype: [str,str,int]
        '''
        query = '''
                SELECT emplid,coursename,strm
                  FROM EnrollmentTallyAllCols
                 ORDER BY emplid, coursename, strm;
                 '''
        try:
            cur = self.sqlite_db_conn.cursor()
            cur.execute(query)
        except Exception as e:
            raise IOError("Cannot query for all students (%s)" % repr(e))
        return cur
    