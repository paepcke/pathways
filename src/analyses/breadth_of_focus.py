'''
Created on Sep 11, 2018

@author: paepcke
'''
import os

from gensim.models.keyedvectors import KeyedVectors

from course2vec.word2vec_model_creation import Word2VecModelCreator 


class StudentFocusAnalyzer(object):
    '''
    classdocs
    '''


    def __init__(self, training_filename, model_vector_filename):
        '''
        Constructor
        '''
        self.training_filename = training_filename
        self.model_vector_filename = model_vector_filename
        
        if not os.path.exists(model_vector_filename):
            raise ValueError("Model vectors file does not exist: %s" % model_vector_filename)
        if not os.path.exists(training_filename):
            raise ValueError("Training filename file does not exist: %s" % training_filename)
        
        # Get the list of courses taken by each student:
        #   [[major1, course1, course2, ...],        <== student1
        #    [major1, course5, course1, ...],        <== student2
        #         ...
        #   ]
        

        model_creator = Word2VecModelCreator()
        self.sentences = model_creator.create_course_sentences(training_filename, hasHeader=True)
        self.vector_sds = self.compute_sds()
        
    def compute_sds(self):

        # Create dict:
        #    {major1 : [[crsVec1,crsVec2,...],
        #               [crsVec3,crsVec1,...],
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
                
        
    def vectors_from_courses(self):
        '''
        Returns dictionary mapping majors to array of lists of
        course vectors. Each course list in the array contains KeyedVectors.
        Each list corresponds to one student. Each KeyedVector within a list
        corresponds to a course that the respective student took. Example, 
        two CS students and three bio students:
        
            {'CS' : [[vec1, vec2, vec3],
                     [vec5, vec1, vec4]
                    ]
             'BIO': [[vec10, vec4, vec11, vec1],
                     [vec4, vec11],
                     [vec11, vec15, vec4]
                    ]
            }
        
        @return: {str : [[KeyedVector]]
        @rtype: dict
        
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

if __name__ == '__main__':
    
    curr_dir = os.path.dirname(__file__)
    save_dir = os.path.join(curr_dir, '../data/Word2vec/')
    
    # The enrollment data:
    training_filename      = os.path.join(save_dir, 'emplid_crs_major_strm_gt10_2000plus.csv')
    model_vector_filename  = os.path.join(save_dir, 'all_since2000_vec300_win5_.vectors')
    analyzer = StudentFocusAnalyzer(training_filename, model_vector_filename)     
    print(analyzer)