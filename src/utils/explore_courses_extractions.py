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

    # Some courses have 50 and more instructors (e.g. MED courses).
    # Set this number to the upper limit, or None if no limit:
    MAX_INSTRUCTORS = 20

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

        course_info_arr = []

        for school in self.connection.get_schools(year):
            for dept in school.departments:
                courses = self.connection.get_courses_by_department(dept.code, year=year)
                for course in courses:
                    course_info = CourseInfo(year, course.subject + course.code, course.course_id, self.course_instructors(course))
                    course_info_arr.append(course_info)
                    
        return course_info_arr
        
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

# ---------------------------------- Class CourseInfo -------------------------

class CourseInfo(object):
    
    def __init__(self, year, course_code, course_id, instructors):
        self.course_code = course_code
        self.course_id = course_id
        if ExploreCoursesGetter.MAX_INSTRUCTORS is None:
            self.instructors = ','.join(instructors)
        else:
            self.instructors = ','.join(instructors[:ExploreCoursesGetter.MAX_INSTRUCTORS])
        
        # Make the year more readable: From 20132014 ==> 2013-2014
        self.year = year[:4] + '-' + year[4:]
        
    def as_array(self):
        return [self.year, self.course_code, self.course_id, self.instructors] 
        
# --------------------------------------------- Main --------------------------        
if __name__ == '__main__':
    ec_conn = ExploreCoursesGetter()
    
    years = ['20122013', '20132014', '20142015', '20162017', '20172018', '20182019']
    
    with open('/tmp/course_instructors.tsv', 'w') as out_fd:
        csv_writer = csv.writer(out_fd, delimiter='\t') 
        # Column header:
        csv_writer.writerow(['year', 'course_code', 'course_id', 'instructors'])
         
        for year in years:
            print('Retrieving year %s...' % year)
            course_info_objs = ec_conn.get_all_instructors(year)
            print('Retrieved all for year %s.' % year)
            print('Start writing year %s to .csv...' % year)
    
            for course_info_obj in course_info_objs:
                row = course_info_obj.as_array()
                csv_writer.writerow(row)
