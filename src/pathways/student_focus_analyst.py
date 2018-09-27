'''
Created on Sep 25, 2018

@author: paepcke
'''
import os

from pandas.core.frame import DataFrame

from course2vec.word2vec_model_creation import Word2VecModelCreator, Action
from pathways.student_query_engine import StudentQueryEngine


class StudentFocusAnalyst(object):
    '''
    classdocs
    '''
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
    # course_sds 
    #------------------
        
    def course_sds(self, student):
        
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
        
        std_vec = course_vectors.std(axis='index')
        return std_vec

    # ---------------------------------- Main ------------------------------
    
if __name__ == '__main__':
    
    analyst = StudentFocusAnalyst()
    vector_sds_list_stud1 = analyst.course_sds('$2a$15$/s/sUcLiiDWgLVZKf/cvyunB9knF7k2VpORq0SiOzkjm6Kc/iISfK')
    #vector_sds_normed_list = analyst.vector_sds_normed(student_list)
    #vector_angular_sums_list = analyst.vector_angular_sums(student_list)
    