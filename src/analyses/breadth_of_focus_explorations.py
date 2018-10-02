'''
Created on Sep 11, 2018

@author: paepcke
'''
import argparse
import csv
import logging
import os
import pickle
import sys

from gensim.models.keyedvectors import KeyedVectors
from pandas.core.frame import DataFrame
from pandas.core.series import Series

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
        
        logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

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
        
        # Dict mapping majors to data frames. Each df holds
        # one student's vectors for each of their courses:
        # a course_name x vector matrix:
        self._majors_student_dfs_dict = None
        
        # Dict mapping each major to a 1D array of SDs.
        # Each SD is the breadth of one student in that major:
        self._majors_sds_dict         = None
        
        # Used for arbitrary set of students' list of SDs.
        self._curr_student_sds        = None

    # ----------------------------------------- Properties -----------------------
    
    
    #--------------------------------
    # majors_student_dfs_dict 
    #------------------
    
    @property
    def majors_student_dfs_dict(self):
        return self._majors_student_dfs_dict
    
    #--------------------------------
    # majors_sds_dict 
    #------------------
    
    @property
    def majors_sds_dict(self):
        return self._majors_sds_dict
    
    
    #--------------------------------
    # curr_student_sds 
    #------------------
    
    @property
    def curr_student_sds(self):
        return self._curr_student_sds
    
    # ----------------------------------------- Loading Pre-Computed Data Structures ----------
    
    #--------------------------------
    # load_majors_student_dfs 
    #------------------
    
    def load_majors_student_dfs(self, loadfile):
        '''
        Given the path to a pickle file that was created by 
        the course_vectors_by_majors() method, recover the
        data structure into instance var self._majors_student_dfs_dict.
        
        For the structure details, see course_vectors_by_majors()

        @param loadfile: path to pickle file to load from
        @type loadfile: str
        '''
        
        try:
            with open(loadfile, 'rb') as pickle_fd:
                self.logInfo('Loading majors->student course vectors from file...')
                self._majors_student_dfs_dict = pickle.load(pickle_fd)
                self.logInfo('Done loading majors->student course vectors from file...')
        except Exception as e:
            raise IOError("Could not load majors-to-student-DFs file '%s' (%s)" %\
                          (loadfile, repr(e))
                          )

    #--------------------------------
    # load_majors_sds 
    #------------------
    
    def load_majors_sds(self, loadfile):
        '''
        Given the path to a pickle file that was created by 
        the compute_majors_sds() method, recover the
        data structure into instance var self._majors_sds_dict.
        
        For the structure details, see compute_majors_sds()
        
        @param loadfile: path to pickle file to load from
        @type loadfile: str
        '''
        
        try:
            with open(loadfile, 'rb') as pickle_fd:
                self.logInfo('Loading majors->student-SDs from file...')
                self._majors_sds_dict = pickle.load(pickle_fd)
                self.logInfo('Done loading majors->student-SDs from file...')
        except Exception as e:
            raise IOError("Could not load majors-SDs file '%s' (%s)" %\
                          (loadfile, repr(e))
                          )

    # ------------------------------------------ Computing Data Structures --------------
        
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
        
        In addition to returning the result, saves result into instance
        var self._curr_student_sds
        
        @param student_list: array of one dataframe for each student.
            Each student_specification holds the vectors for the courses taken by that student.
        @type student_list: [DataFrame]
        @return: array of SDs, one for each student
        @rtype: [float]
        
        '''
        res_vec = []
        num_students = len(student_list)
        self.logInfo("Computing each of %d students' SD..." % num_students) 
        # Get one student's DF at a time:
        for student_specification in student_list:
            # Get a 1D of the SDs across the course vectors of
            # this student:
            course_sd_vec = self.student_vec_analyst.course_sds(student_specification)
            # Collapse the SD vector into an L2 norm:
            res_vec.append(self.student_vec_analyst.L2_norm(course_sd_vec))
        
        self.logInfo("Done computing each of %d students' SD..." % num_students)
        
        self._curr_student_sds = res_vec             
        return res_vec
            
    #--------------------------------
    # compute_majors_breadths_l2 
    #------------------
        
    def compute_majors_breadths_l2(self):
        '''
        Create dict:
           {major1 : Series([SD_Student1, SD_Student2, ...])
            major2 : Series([SD_Student3, SD_Student4, SD_Student5...])
                   ...
           }
           
        In addition to returning the resulting data structure, saves 
        the structure in self._majors_sds_dict.
        
        Method first checks whether self._majors_student_dfs_dict is
        set. If not, self.course_vectors_by_majors() is called (about 10mins).
        The instance var can be set by first calling load_majors_student_dfs()
        with the path to a previously pickled result of what course_vectors_by_majors()
        produces.
        
        @return: dict mapping majors to lists of student-SDs
        @rtype: {str : Series(float)}
              
        '''
        
        # Get dict major ==> DataFrame([courses x course_vectors]):
        if self._majors_student_dfs_dict is None:
            vectors_by_majors = self.course_vectors_by_majors()
        else:
            vectors_by_majors = self._majors_student_dfs_dict
        
        majors_SDs = {}
        self.logInfo("Computing each major's SD for each student in that major...")
        for major in vectors_by_majors.keys():

            self.logDebug("   ...major %s..." % major)
            
            student_sd_array = []
            # Get this major's array of student DFs.
            # Each df has one student's course x course_vector:
            for student_course_df in vectors_by_majors[major]:
                # Get one student's SD from their DF:
                student_sd = self.student_vec_analyst.course_sds(student_course_df)
                # And add to the SDs of students in the current major:
                student_sd_array.append(student_sd)
            # Make a 1D array (i.e. Series). Name the series
            # the name of the major, just so it can be identified
            # as reflecting the current major's SDs. Add to the result:
            majors_SDs[major] = Series(student_sd_array).rename(major)
            
        self.logInfo("Done computing each major's SD for each student in that major.")
        self._majors_sds_dict = majors_SDs
        return majors_SDs
                
        
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
        
        In addition to returning the resulting data structure, saves 
        the structure in self._majors_student_dfs_dict.
        
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
        
        # Each sentence (i.e. row in self.sentences) holds 
        # the major and courses of one student. A sentence 
        # is a list beginning with with major, followed by 
        # course names:
        
        self.logInfo("Gathering course vectors for each student in each major...")
        for student_courses in self.sentences:
            # The first element is the student's major
            major = student_courses[0]
            
            self.logDebug("   ...major: %s" % major)

            # Get the list of student-dfs collected so far for this major,
            # starting a new list if this is the first time we see
            # this major:
            student_dfs_already_in_major = student_vectors.get(major, [])
            if len(student_dfs_already_in_major) == 0:
                student_vectors[major] = student_dfs_already_in_major

            # Find vector of each course of the current student,
            # and add the resulting vector array to the student's
            # dataframe:
            this_student_course_vec = []
            this_student_included_courses = []
            for student_course in student_courses[1:]:
                try:
                    # word_vectors[course_name] returns a 1d array,
                    # which is that course's vector:
                    this_student_course_vec.append(word_vectors[student_course])
                    this_student_included_courses.append(student_course)
                except KeyError:
                    # Courses with fewer than 10 students aren't in the
                    # vectors for privacy preservation. Just go to next course.
                    continue
            # Done with all courses of one student: append
            # the df to the Python array of this major:
            this_student_course_df = DataFrame.from_records(this_student_course_vec, 
                                                            index=this_student_included_courses)
            
            # Set a name for what each row represents: the
            # vector for of one student's courses. The rows
            # will be auto-numbered:
            
            this_student_course_df.index.name = 'CourseVector'
            student_dfs_already_in_major.append(this_student_course_df)

        self.logInfo("Done gathering course vectors for each student in each major.")
        
        self._majors_student_dfs_dict = student_vectors        
        return student_vectors

    # ---------------------------------- Utilities ----------
    #--------------------------------
    # import_sentences 
    #------------------
    
    def import_sentences(self, sentence_filename, hasHeader=True):

        res_arr_of_arr = []
        with open(sentence_filename, 'r') as sentence_fd:
            csv_reader = csv.reader(sentence_fd)
            if hasHeader:
                # Throw out the column name header:
                next(csv_reader)
            self.logInfo("Loading sentences (i.e. training vectors)...")
            for sentence in csv_reader:
                res_arr_of_arr.append(sentence)
                
        self.logInfo("Done loading sentences (i.e. training vectors).")                
        return res_arr_of_arr
    
    #--------------------------
    # logging convenience methods 
    #----------------
                
    def logInfo(self, msg):
        logging.info(msg)
        
    def logWarn(self, msg):
        logging.warning(msg)
    
    def logDebug(self, msg):
        logging.debug(msg)
    
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
    
    curr_dir = os.path.dirname(__file__)
    
    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument('-a', '--action',
                        type=str,
                        choices=['create_majors_vectors',
                                 'create_majors_sds', 
                                 'test'
                                 ],
                        nargs='*',
                        help="what you want the program to do.", 
                        default=None);
    parser.add_argument('-f', '--file',
                        help='fully qualified path to majors vectors/SDs load file, depending on requested action',
                        default=None);
    parser.add_argument('-s', '--savefile',
                        help='fully qualified path to file for saving result depending on requested action',
                        default=None);
    
    args = parser.parse_args();
    
    curr_dir = os.path.dirname(__file__)
    save_dir = os.path.join(curr_dir, '../data/Word2vec/')
    
    # The enrollment data:
    # training_filename      = os.path.join(save_dir, 'emplid_crs_major_strm_gt10_2000plus.csv')
    sentences_filename     = os.path.join(save_dir, 'sentences.txt')
    model_vector_filename  = os.path.join(save_dir, 'winning_model.vectors')

    explorer = StudentFocusExplorer(sentences_filename=sentences_filename, 
                                    model_vector_filename=model_vector_filename)
    
    if 'create_majors_vectors' in args.action:
        # Make sure caller got us a file name to save to:
        if args.savefile is None:
            raise ValueError("Must provide a file name for the computed majors vectors.")
        
        # Make sure the file name has a .pickle extension:
        (name_root, ext) = os.path.splitext(args.savefile)
        if ext != '.pickle':
            savefile = args.safefile + '.pickle'
        else:
            savefile = args.savefile
        
        # Get dict majors --> array of DataFrames (course x vectors),
        # each DF for one student:
        explorer._majors_student_dfs_dict = explorer.course_vectors_by_majors()
        
        with open(savefile, 'wb') as fd:
            pickle.dump(explorer.majors_student_dfs_dict, fd)
        print("Majors student DFs are in %s" % savefile)
        
    elif 'create_majors_sds' in args.action:
        # Make sure there is a savefile specified, else the whole
        # computation happens, but is not saved
        if args.savefile is None:
            raise ValueError("Must provide a file name for the computed majors SDs.")
         
        # Have we already computed the majors-->course-vector-DFs?
        if explorer._majors_student_dfs_dict is None:
            # No, but did user provide a load file for the majors-->student-DFs?
            if args.file is not None:
                explorer.load_majors_student_dfs(args.file)
            else:
                # Bite the bullet and spend 10 minutes on a coffee:
                explorer._majors_student_dfs_dict = explorer.course_vectors_by_majors()
        
        explorer._majors_sds_dict = explorer.compute_majors_breadths_l2()

        with open(args.savefile, 'wb') as fd:
            pickle.dump(explorer.majors_sds_dict, fd)
            
        print("Majors student SDs are in %s" % args.savefile)


    elif 'test' in args.action:
        pass
        
        
        
    
#     
#     # Test IDs of 20 students:
#     test_ids = [
#                 '$2b$15$CDsZ1FN2duAmJSNQWMgUoecvcraUwYuRWpxOUM1EBmib4JCMHUxqq',
#                 '$2b$15$0FI1Dm8nyfrbDbL6HX5XNui41cqM48EEpJ0deqikq4jaQyfh1Na8.',
#                 '$2b$15$jDMQFgaTO4YW.saEwvWm7./yCB./attA3PCEz8QAoNSROxCAQLBjm',
#                 '$2b$15$toydgDvebRVo.IHNesrx7u9m9XidcCwsOUcfgO9DC8A5Ch8VQpMpG',
#                 '$2b$15$TWK.su2jX5x5PJs4Ky25uuEOhJCtB8G1jzfC8X0tSo0azeeGECWqy',
#                 '$2b$15$Q5nnEU..JzR7M4UG1Dx6sOAzKjgHaQebAnkIa.IxaeI0XJ9DSRnLC',
#                 '$2b$15$EFAXEr/X/NST9tB6D6A3Eehj085YFY7oRyjZ6myQITx6R53v5udT6',
#                 '$2b$15$zeD0/FfVR87ZIewKphM3Zu/Xj4vw4.IZuJILedCzdvPSYq1lTBdRi',
#                 '$2b$15$/LwePtb3PMqkl0/p3nkU/evJZ92ahPzrS726Thejvpd0jiFEkohmK',
#                 '$2b$15$6di3VOeCW6mW6kf1mzgXU.gukM7YKRkrKoL//1RKiYsJ55YQdcr9G',
#                 '$2b$15$kGLUl1W/9NjH2O7WGg7WL.KFaTQqe/5eBuYRWJi1Hk3u4/lEgd/py',
#                 '$2b$15$iwJOkr807bdE3Wl52B3U7OgK3IkcKiPvNgF05P6x1qqFERw7.Xoj2',
#                 '$2b$15$4sXQ/ivtodFGt44oZlnKbuadr8YAUcIJNv7nb3WC0ob73.Xfc4RTC',
#                 '$2b$15$x2v8t6TNPvEtKf5kZNtOR.MAACkad58.3S4eX2D4lRMHQYOikfEna',
#                 '$2b$15$agPd01KuHh.iu2monC65..dKG43ZBNwo5aFNYXpwAfQNEh56nEWDi',
#                 '$2b$15$SPWY3c0w3AmRVQM7h7kvWeUiS/W.15LwP.LJlnoLJIRpEIK2YSTPy',
#                 '$2b$15$D5R5lIWq/AoNd3ElqY1cNO6xj91k6P9sUo/8OX03WXRAkFcXc0Zzu',
#                 '$2b$15$3CF37AfoRkDzm5yj5tpifORC3n6RN.maxHnb1h5Rhfo3RLbRO.moS',
#                 '$2b$15$UhY288tdIX.Y5AyqBvNjvuqVfClViJMG4vBq3UwekcZ7IxLo4mwFS',
#                 '$2b$15$zuUVsUfThqAGfsBvdHJPWOPL/gDO5U.oC83.hR.zb9Zht2P6/33pC',
#                 ]    
#      
#     # Test1:
#     breadth_20_students = explorer.compute_majors_breadths_l2()
#     with open('/Users/paepcke/EclipseWorkspacesNew/pathways/src/data/Word2vec/TestData/breadth_20_students.pickle', 'wb') as fd:
#         pickle.dump(breadth_20_students, fd)
        