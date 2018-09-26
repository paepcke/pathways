'''
Created on Sep 25, 2018

@author: paepcke
'''
from _datetime import date
import os
import sqlite3

from pathways.strmComputer import StrmComputer
from matplotlib._cm import _summer_data


class StudentQueryEngine(object):

    #--------------------------------
    # Constructor 
    #------------------
    
    def __init__(self):

        self.db_file = os.path.join(os.path.dirname(__file__), '../data/enrollment_tally.sqlite')
        try:
            self.sqlite_db_conn = sqlite3.connect(self.db_file)
        except Exception as e:
            raise ValueError("Could not connect ot Sqlite3 db at '%s' (%s)" % (self.db_file, repr(e)))
        
        # Utility instance for manipulating strms:
        self.strm_computer = StrmComputer()
        
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
        return self.run_query(query)
    
    #--------------------------------
    # stud_crse_lists 
    #------------------

    def stud_crse_lists(self, emplid_list):
        '''
        Return an iterator for query results:
        
            emplid, course_name, strm
            
        for a given list of students.

        Caller should close the iterator if no more
        data is to be extracted from it.
        
        @return: iterator over db rows
        @rtype: [str,str,int]
        '''
        # The funky format statement creates the
        # quoted list of emplids: ('emplid1', 'emplid2',...):
        
        query = '''
                SELECT emplid,coursename,strm
                  FROM EnrollmentTallyAllCols
                 WHERE emplid IN (%s)
                 ORDER BY emplid, coursename, strm
                 ''' % ("'" + "','".join(emplid_list) + "'")

        return self.run_query(query)
    
    #--------------------------------
    # all_given_year 
    #------------------
    
    def all_given_year(self, year):
        
        # Find low and high strm for given year.
        # Earliest is Fall quarter:
        acad_year = year - 1
        fall_quarter_date = date('%s-9-28' % acad_year)
        fall_quarter_next_year = date('%s-9-28' % acad_year + 1)
        low_strm  = self.strm_computer.strm_from_date(fall_quarter_date)
        high_strm = self.strm_computer.strm_from_date(fall_quarter_next_year)
        
        query = '''
                SELECT emplid, coursename
                  FROM EnrollmentTallyAllCols
                 WHERE strm >= %s and strm < %s
                  ORDER BY emplid;
                ''' % (low_strm, high_strm)
                
        return self.run_query(query)
    
    
    #----------------------- Utilities -------------
    
    #--------------------------------
    # run_query 
    #------------------

    def run_query(self, query_str):
        '''
        Return an iterator for query results
        
        @return: iterator over db rows
        @rtype: [str,str,int]
        '''
        try:
            cur = self.sqlite_db_conn.cursor()
            cur.execute(query_str)
        except Exception as e:
            raise IOError("Query failure: '%s' (%s)" % (query_str, repr(e)))
        return cur
    
    #---------------------- DbIterator -------
    
class DbIterator(sqlite3.Cursor):
    
    def next(self):
        return self.fetchone()
        
    #---------------------- Main ------------
    
if __name__ == '__main__':
    
    qe = StudentQueryEngine()
    res_it = qe.all_stud_crses_strms()
    for row_num in range(3):
        row = res_it.fetchone()
        #print(row)
        