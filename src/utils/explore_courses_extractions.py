'''
Created on Feb 18, 2019

@author: paepcke
'''

import csv
import itertools

from explorecourses import CourseConnection
#from explorecourses import filters


class ExploreCoursesGetter(object):
    '''
    Creates CSV file with all instructors for every course
    since 2013/2014. This is just one example for how to use
    the Explore-Courses-API program from Github.
    
    Since I had to modify Explore-Courses-API to have its
    URL use "https" instead of "http" I make the Explore-Courses-API
    project referenced from this one. 
    '''

    #------------------------------------
    # Constructor 
    #-------------------    

    def __init__(self):
        '''
        Constructor
        '''
        
        self.connection = CourseConnection()
        
        
    #------------------------------------
    # get_all_instructors 
    #-------------------    
    
    def get_all_instructors(self, year):

        course_instr_dict = {}

        for school in self.connection.get_schools(year):
            for dept in school.departments:
                courses = self.connection.get_courses_by_department(dept.code, year=year)
                for course in courses:
                    course_instr_dict[course.subject + course.code] = self.course_instructors(course)
                    
        return course_instr_dict
        
    #------------------------------------
    # course_instructors 
    #-------------------    

    
    def course_instructors(self, course):
        '''
        Given a course object, return a list of all instructors,
        including for all sections.
        
        @param course: course object
        @type course: Course
        @return list of instructor sunet IDs
        @rtype [str]
        '''

        sections    = course.sections
        schedules   = [section.schedules for section in sections]
        
        # schedules is now an array of tuples. Concat the tuples to get
        # a simple list of schedules:
        schedules   = list(itertools.chain(*schedules))
        
        instructors = [schedule.instructors for schedule in schedules]
        
        # Same flattening for the instructors:
        instructors = list(itertools.chain(*instructors))
        sunet_ids   = [instructor.sunet_id for instructor in instructors]
        return sunet_ids 
        
    #------------------------------------
    # example 
    #-------------------    
        
    def example_query(self):

        # Print out all courses for 2017-2018.
        year = "2017-2018"
        for school in self.connection.get_schools(year):
            for dept in school.departments:
                courses = self.connection.get_courses_by_department(dept.code, year=year)
                for course in courses:
                    print(course)
        
if __name__ == '__main__':
    ec_conn = ExploreCoursesGetter()
    
    years = ['2012-2013', '2013-2014', '2014-2015', '2016-2017', '2017-2018', '2018-2019']
    
    with open('/tmp/course_instructors.csv', 'w') as out_fd:
        csv_writer = csv.writer(out_fd) 
        # Column header:
        csv_writer.writerow(['year', 'course_code', 'instructors'])
         
        for year in years:
            print('Retrieving year %s...' % year)
            course_dict = ec_conn.get_all_instructors(year)
            print('Retrieved all for year %s.' % year)
            print('Start writing year %s to .csv...' % year)
    
            for course_code in course_dict.keys():
                row = [year, course_code, ','.join(course_dict[course_code])]
                csv_writer.writerow(row)
