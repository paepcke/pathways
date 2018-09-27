'''
Created on Sep 25, 2018

@author: paepcke
'''
import datetime
import os
import sqlite3

from pathways.strmComputer import StrmComputer


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
        '''
        Given an academic year, find all students and their courses
        in that academic year. For 2018/19, use 2019!
        
        @param year: yr2 calendar year of the yr1/yr2 academic-year 
        @type year: integer
        '''
        
        # Find low and high strm for given year.
        # Earliest is Fall quarter:
        acad_year = year - 1
        
        fall_quarter_date = datetime.date(acad_year, 9, 29) 
        fall_quarter_next_year = datetime.date(acad_year + 1, 9, 29)
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
    
    #---------------------- Main ------------
    
if __name__ == '__main__':
    
    qe = StudentQueryEngine()
    res_it = qe.all_stud_crses_strms()
    for row_num in range(2):
        row = res_it.fetchone()
        if row_num == 0:
            assert(row == ('$2a$15$.bENtpoUdOJRTw7Kg/Bjr.qlKv0FwR9k5OMLrNjaN6MlBi3sTxBj6', 'CME211', '1182'))
        elif row_num == 1:
            assert(row == ('$2a$15$.bENtpoUdOJRTw7Kg/Bjr.qlKv0FwR9k5OMLrNjaN6MlBi3sTxBj6', 'CME212', '1184'))
    print("All student courses: Passed")
    
    res_it = qe.stud_crse_lists(['$2a$15$.bENtpoUdOJRTw7Kg/Bjr.qlKv0FwR9k5OMLrNjaN6MlBi3sTxBj6'])
    assert(res_it.fetchone() == ('$2a$15$.bENtpoUdOJRTw7Kg/Bjr.qlKv0FwR9k5OMLrNjaN6MlBi3sTxBj6', 'CME211', '1182'))
    print("Courses for one student list: Passed")
    
    res_it = qe.stud_crse_lists(['$2a$15$.bENtpoUdOJRTw7Kg/Bjr.qlKv0FwR9k5OMLrNjaN6MlBi3sTxBj6',
                                 '$2a$15$.iQPCHeeuyLD3TIqJRk4j.LU0IjGYumSdFkAEUfOoKEtk2jT/bFoi'
                                 ])
    #for row in res_it:
    #    print(row)
    
    res_it = qe.all_given_year(2017)
    for row_num in range(2):
        row = res_it.fetchone()
        if row_num == 0:
            assert(row ==  ('$2a$15$/s/sUcLiiDWgLVZKf/cvyunB9knF7k2VpORq0SiOzkjm6Kc/iISfK', 'BIOE300B')) 
        elif row_num == 1:
            assert(row == ('$2a$15$/s/sUcLiiDWgLVZKf/cvyunB9knF7k2VpORq0SiOzkjm6Kc/iISfK', 'BIOE301A'))
    print("All student given year: Passed")

        