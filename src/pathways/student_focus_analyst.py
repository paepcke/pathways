'''
Created on Sep 25, 2018

@author: paepcke
'''
import os

import numpy as np
import pandas as pd
from pandas.core.frame import DataFrame

from course2vec.word2vec_model_creation import Word2VecModelCreator, Action
from pathways.student_query_engine import StudentQueryEngine


class StudentFocusAnalyst(object):
    '''
    Class for computing student breadth related 
    primitives. This is a service class. For the
    place where the breadths of different student 
    groups are examined and/or plotted, see 
    breadth_of_focus_explorations.py.
    
    The class does go to the database, extracting
    a given studentid's courses.
    '''
    
    #--------------------------------
    # Constructor 
    #------------------
    
    def __init__(self):
        '''
        Constructor
        '''
        vector_model_filepath = os.path.join(os.path.dirname(__file__),
                                             '../data/Word2vec/winning_model.vectors')
                                             
        self.vectors = Word2VecModelCreator(action=Action.LOAD_VECTORS, 
                                            actionFileName=vector_model_filepath)
        
        self.student_db = StudentQueryEngine()

    #--------------------------------
    # student_group_breadth_l2 
    #------------------

    def student_group_breadth_l2(self, student_list):
        
        # Get a list of the L2 norms that summary 
        # each student's course breadth:
        
        l2_sd_norms = [self.student_breadth_l2(student) for student in student_list]
        return l2_sd_norms
        
    #--------------------------------
    # course_sds 
    #------------------
        
    def course_sds(self, student):
        '''
        Given the emplid of one student:
            o find his/her courses,
            o look up each course's course vector
            o compute the element-wise standard deviations
                of all vectors
            o return Pandas Series instance of the SDs. The length of
              the series will be equal to the number courses
              the student took.
               
        @param student: identifier of student
        @type student: str
        @return: vector of element-wise standard deviations
        @rtype: pandas.Series
        '''
        
        # Method stud_crse_lists() returns rows of the form:
        #    emplid, course_name, strm
        # Get all the student's courses in one array:
        
        course_names = [row[1] for row in self.student_db.stud_crse_lists([student]).fetchall()]
        # Create a 2D df:
        #                    vecDim1    vecDim2  ... vedDim200
        #    course_name1
        #    course_name        ...         ...
        course_vectors = DataFrame([self.vectors[course_name] for course_name in course_names],
                                   index=course_names
                                   )
        # Get a vector in which each of the 200 elements
        # is the standard deviation of one column. I.e.
        # [(std of vecDim1), (std of vecDim2), etc. ]
        
        sd_series = course_vectors.std(axis='index')
        return sd_series

    #--------------------------------
    # L2_norm 
    #------------------

    def L2_norm(self, vector):
        '''
        Given either a Python vector, or a pandas Series,
        return the vector's L2 norm: sqrt(sum(squares-over-elements))
        
        @param vector: vector over which L2 norm is to be computed
        @type vector: { list | pandas.Series }
        '''
        if isinstance(vector, list):
            vector = pd.Series(vector)
        return np.sqrt(np.square(vector).sum())

    #--------------------------------
    # student_breadth_l2 
    #------------------

    def student_breadth_l2(self, student):
        return self.L2_norm(self.course_sds(student))

    # ---------------------------------- Main ------------------------------
    
if __name__ == '__main__':
    
    analyst = StudentFocusAnalyst()
#     vector_sds_list_stud1 = analyst.course_sds('$2a$15$/s/sUcLiiDWgLVZKf/cvyunB9knF7k2VpORq0SiOzkjm6Kc/iISfK')
#     vector_sds_normed_list = analyst.vector_sds_normed(student_list)
#     vector_angular_sums_list = analyst.vector_angular_sums(student_list)
#     assert(analyst.L2_norm([1,2,3]) == 3.7416573867739413)
#     assert(analyst.L2_norm(pd.Series([1,2,3])) == 3.7416573867739413)
#     print("L2 norm computation OK")
    
#     l2_breadth = analyst.student_breadth_l2('$2a$15$/s/sUcLiiDWgLVZKf/cvyunB9knF7k2VpORq0SiOzkjm6Kc/iISfK')
#     # Check l2_breadth more manually: get vector of SDs 
#     # of one student's course vectors:
#     sd_vec = analyst.course_sds('$2a$15$/s/sUcLiiDWgLVZKf/cvyunB9knF7k2VpORq0SiOzkjm6Kc/iISfK')
#     # Compute the L2 norm:
#     manual_l2_breadth = np.linalg.norm(sd_vec)
#     assert(l2_breadth == manual_l2_breadth)
    
    
    