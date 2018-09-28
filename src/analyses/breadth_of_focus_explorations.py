'''
Created on Sep 11, 2018

@author: paepcke
'''
import csv
import os

from gensim.models.keyedvectors import KeyedVectors

from course2vec.word2vec_model_creation import Word2VecModelCreator 
from pathways.student_focus_analyst import StudentFocusAnalyst


class StudentFocusExplorer(object):
    '''
    classdocs
    '''

    #--------------------------------
    # Constructor 
    #------------------


    def __init__(self,
                 sentences_filename=None,
                 id_strm_crse_filename=None,
                 model_vector_filename=None):
        '''
        Only one of sentences_filename and id_strm_crse_filename
        are needed. If both are provided, the sentences_filename
        is used.
        
        If provided, the sentences_filename is assumed to contain one row for
        each student:
        
               major, crs1, crs2, crs3,...
        
        Note that the sentences are not used to train a model. 
        They are used, for instance, in computing the SD of one
        student's course vectors.
        
        If the sentences_filename is not provided, the id_strm_crse_filename
        is assumed to contain rows with student ID, strm, and coursename, for
        each student and course. Absent the already computed sentences, the
        id_strm_crse_filename is used to ask a Word2VecModelCreator to compute
        the sentences and return them as a data structure.
        
        The model vector filename should be just the vectors part of
        the trained model.        

        @param sentences_filename: name of file containing the major/crse-name rows
        @type sentences_filename: str
        @param id_strm_crse_filename: alternative to sentences_filename: file with
            raw information from which the sentences will be constructed.
        @type id_strm_crse_filename: str
        @param model_vector_filename: name of file with vectors for all courses
        @type model_vector_filename: str
        '''
        self.sentences_filename = sentences_filename
        self.id_strm_crse_filename = id_strm_crse_filename
        self.model_vector_filename = model_vector_filename
        
        if model_vector_filename is not None and not os.path.exists(model_vector_filename):
            raise ValueError("Model vectors file does not exist: %s" % model_vector_filename)
        
        if sentences_filename is not None and not os.path.exists(sentences_filename):
            raise ValueError("Sentences filename file does not exist: %s" % sentences_filename)

        if id_strm_crse_filename is not None and not os.path.exists(id_strm_crse_filename):
            raise ValueError("File id_strm_crse_filename does not exist: %s" % id_strm_crse_filename)
        
        # Get the list of courses taken by each student:
        #   [[major1, course1, course2, ...],        <== student1
        #    [major1, course5, course1, ...],        <== student2
        #         ...
        #   ]
        # 
        # This structure either lives in the sentences_filename, if 
        # provided, or needs to be constructed:

        if sentences_filename is None:
            model_creator = Word2VecModelCreator()
            self.sentences = model_creator.create_course_sentences(sentences_filename, hasHeader=True)
        else:
            self.sentences = self.import_sentences(sentences_filename)
            
        # Get service instance that computes norms, etc.:
        self.student_vec_analyst = StudentFocusAnalyst()
        
    #--------------------------------
    # compute_students_breadths_l2 
    #------------------

    def compute_students_breadth_l2(self, student_list):
        '''
        Given some number of students, return an array of their
        L2-SD breadth. 
        
        Students can either be specified by a list of student
        IDs, or by an array of dataframes.
        
        Returns a Series of L2-collapsed
        course vector SDs: one SD per student. 
        
        For the dataframe option we expect:
        
        [DataFrame for student 1 who took three courses:
                             crs_vec_el1   crs_vec_el2   crs_vec_el3,...
                 course1                   ...
                 course2                   ...
                 course3                   ...,
                 
         DataFrame for student 2 who took 4 courses:
                             crs_vec_el1   crs_vec_el2   crs_vec_el3,...
                 course1                   ...
                 course2                   ...
                 course3                   ...
                 course4                   ...                            
        ] # End study sets for all students of interest to the caller
        
        Returns a 1d vector with the overall SDs of students. I.e. one
        SD across all a student's courses for each student. The vector
        length will thus be the length of the student_list, which 
        is the number of students of interest to the caller:
        
        @param student_list: array of one dataframe for each student.
            Each student_specification holds the vectors for the courses taken by that student.
        @type student_list: [DataFrame]
        @return: array of SDs, one for each student
        @rtype: [float]
        
        '''
        res_vec = []
        # Get one student's DF at a time:
        for student_specification in student_list:
            # Get a 1D of the SDs across the course vectors of
            # this student:
            course_sd_vec = self.student_vec_analyst.course_sds(student_specification)
            # Collapse the SD vector into an L2 norm:
            res_vec.append(self.student_vec_analyst.L2_norm(course_sd_vec))
            
        return res_vec
            
    #--------------------------------
    # compute_majors_breadths_l2 
    #------------------
        
    def compute_majors_breadths_l2(self):

        # Create dict:
        #    {major1 : [DataFrame_student1,
        #               DataFrame_student2,
        #                   ...
        #              ]
        #    {major2 : [[...],
        #               [...]
        vectors_by_majors = self.vectors_from_courses()
        #print(vectors_by_majors['CS-BS'][:6])
        #print(vectors_by_majors['CS-BS'][0])
        print('Num majors: %s' % len(vectors_by_majors.keys()))
        print('Num CS-BS students: %s' % len(vectors_by_majors['CS-BS']))
        print('Num courses of first CS student: %s' % len(vectors_by_majors['CS-BS'][0]))
        print('Num courses of second CS student: %s' % len(vectors_by_majors['CS-BS'][1]))
                
        
    #--------------------------------
    # course_vector_by_majors 
    #------------------
        
    def course_vectors_by_majors(self):
        '''
        Returns dictionary mapping majors to array of lists of
        course vectors. Each course list in the array contains KeyedVectors.
        Each list corresponds to one student. Each KeyedVector within a list
        corresponds to a course that the respective student took. Example, 
        two CS students and three bio students:
        
            {'CS' : [DataFrame for CS student 1 who took three courses:
                                        crs_vec_el1   crs_vec_el2   crs_vec_el3,...
                            course1                   ...
                            course2                   ...
                            course3                   ...,
                            
                    DataFrame for CS student 2 who took 4 courses:
                                        crs_vec_el1   crs_vec_el2   crs_vec_el3,...
                            course1                   ...
                            course2                   ...
                            course3                   ...
                            course4                   ...                            
                    ] # End study sets for all CS students
                    
             'BIO': [DataFrame for Bio student 1 who took three courses:
                                        crs_vec_el1   crs_vec_el2   crs_vec_el3,...
                            course1                   ...
                            course2                   ...
                            course3                   ...,
                            
                    DataFrame for Bio student 2 who took 1 course:
                                        crs_vec_el1   crs_vec_el2   crs_vec_el3,...
                            course1                   ...,

                    DataFrame for Bio student 3 who took 2 courses:
                                        crs_vec_el1   crs_vec_el2   crs_vec_el3,...
                            course1                   ...
                            course2                   ...                            
                            
                    ] # End study sets for all Bio students
            }
        
        @return: dictonary keyed by majors. The values are Dataframes
            holding the course vectors for one student. The returned
            quantity is suitable for passing to student_breadth_l2()
            in student_focus_analyst()
        @rtype: {str : DataFrame}
        
        '''
        # Load the key vectors computed by a previous procedure using
        # word2vec_model_creation.py:
        word_vectors = KeyedVectors.load(self.model_vector_filename, mmap='r')
                
        student_vectors = {}
        
        # Each sentence holds the major and courses of one
        # student. A sentence is a list beginning with with
        # major, followed by course names:
         
        for student_courses in self.sentences:
            # The first element is the student's major
            major = student_courses[0]

            # Get the vector arrays collected so far for this major:
            vectors_already_in_major = student_vectors.get(major, [])

            # Find vector of each course of the current student,
            # and add the resulting vector array to the major's
            # already existing array:
            this_student_course_vectors = []
            for student_course in student_courses[1:]:
                try:
                    this_student_course_vectors.append(word_vectors[student_course])
                except KeyError:
                    # Courses with fewer than 10 students aren't in the
                    # set for privacy preservation. Just go to next course.
                    continue
            vectors_already_in_major.append(this_student_course_vectors)
            
            # The append likely happens in place, but to be sure:
            student_vectors[major] = vectors_already_in_major
        return student_vectors

    # ---------------------------------- Utilities ----------
    #--------------------------------
    # import_sentences 
    #------------------
    
    def import_sentences(self, sentence_filename):

        res_arr_of_arr = []
        with open(sentence_filename, 'r') as sentence_fd:
            csv_reader = csv.reader(sentence_fd)
            for sentence in csv_reader:
                res_arr_of_arr.append(sentence.split(','))
        return res_arr_of_arr
    #---------------------------------- Class Student --------------
    
class Student(object):
    
    NP_CORRESPONDING_ELEMENTS_AXIS = 0
    
    def __init__(self, major):
        self.major = major
        self.course_vectors = []
        self.courses = []
        
    def add_course(self, course_name, crse_vec):
        '''
        
        @param course_name:
        @type course_name:
        @param crse_vec:
        @type crse_vec:
        '''
        self.course_vectors.append(crse_vec)
        self.courses.append(course_name)
        
    def num_vectors(self):
        return len(self.course_vectors)
    

if __name__ == '__main__':
    
    # Test IDs of 20 students:
    test_ids = [
                '$2b$15$CDsZ1FN2duAmJSNQWMgUoecvcraUwYuRWpxOUM1EBmib4JCMHUxqq',
                '$2b$15$0FI1Dm8nyfrbDbL6HX5XNui41cqM48EEpJ0deqikq4jaQyfh1Na8.',
                '$2b$15$jDMQFgaTO4YW.saEwvWm7./yCB./attA3PCEz8QAoNSROxCAQLBjm',
                '$2b$15$toydgDvebRVo.IHNesrx7u9m9XidcCwsOUcfgO9DC8A5Ch8VQpMpG',
                '$2b$15$TWK.su2jX5x5PJs4Ky25uuEOhJCtB8G1jzfC8X0tSo0azeeGECWqy',
                '$2b$15$Q5nnEU..JzR7M4UG1Dx6sOAzKjgHaQebAnkIa.IxaeI0XJ9DSRnLC',
                '$2b$15$EFAXEr/X/NST9tB6D6A3Eehj085YFY7oRyjZ6myQITx6R53v5udT6',
                '$2b$15$zeD0/FfVR87ZIewKphM3Zu/Xj4vw4.IZuJILedCzdvPSYq1lTBdRi',
                '$2b$15$/LwePtb3PMqkl0/p3nkU/evJZ92ahPzrS726Thejvpd0jiFEkohmK',
                '$2b$15$6di3VOeCW6mW6kf1mzgXU.gukM7YKRkrKoL//1RKiYsJ55YQdcr9G',
                '$2b$15$kGLUl1W/9NjH2O7WGg7WL.KFaTQqe/5eBuYRWJi1Hk3u4/lEgd/py',
                '$2b$15$iwJOkr807bdE3Wl52B3U7OgK3IkcKiPvNgF05P6x1qqFERw7.Xoj2',
                '$2b$15$4sXQ/ivtodFGt44oZlnKbuadr8YAUcIJNv7nb3WC0ob73.Xfc4RTC',
                '$2b$15$x2v8t6TNPvEtKf5kZNtOR.MAACkad58.3S4eX2D4lRMHQYOikfEna',
                '$2b$15$agPd01KuHh.iu2monC65..dKG43ZBNwo5aFNYXpwAfQNEh56nEWDi',
                '$2b$15$SPWY3c0w3AmRVQM7h7kvWeUiS/W.15LwP.LJlnoLJIRpEIK2YSTPy',
                '$2b$15$D5R5lIWq/AoNd3ElqY1cNO6xj91k6P9sUo/8OX03WXRAkFcXc0Zzu',
                '$2b$15$3CF37AfoRkDzm5yj5tpifORC3n6RN.maxHnb1h5Rhfo3RLbRO.moS',
                '$2b$15$UhY288tdIX.Y5AyqBvNjvuqVfClViJMG4vBq3UwekcZ7IxLo4mwFS',
                '$2b$15$zuUVsUfThqAGfsBvdHJPWOPL/gDO5U.oC83.hR.zb9Zht2P6/33pC',
                ]    
    curr_dir = os.path.dirname(__file__)
    save_dir = os.path.join(curr_dir, '../data/Word2vec/')
    
    # The enrollment data:
    # training_filename      = os.path.join(save_dir, 'emplid_crs_major_strm_gt10_2000plus.csv')
    sentences_filename     = os.path.join(save_dir, 'sentences.txt')
    model_vector_filename  = os.path.join(save_dir, 'winning_model.vectors')

    explorer = StudentFocusExplorer(sentences_filename=sentences_filename, 
                                    model_vector_filename=model_vector_filename)
    
    # Test1:
    breadth_20_students = explorer.compute_majors_breadths_l2()
    majors_vectors = explorer.course_vectors_by_majors()     
    print(majors_vectors)