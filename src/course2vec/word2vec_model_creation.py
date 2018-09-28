'''
Created on Aug 29, 2018

@author: paepcke
'''
import argparse
import csv
from enum import Enum
import gzip
import logging
import os
import sqlite3
import sys
import tempfile
import time

import gensim
from gensim.models import KeyedVectors
from gensim.models import Word2Vec

import numpy as np


class Action(Enum):
    LOAD_MODEL = 0
    LOAD_VECTORS = 1
    SAVE_MODEL = 2
    SAVE_WORD_VECTORS = 3
    CREATE_MODEL = 4
    CREATE_SENTENCES_FILE = 5
    EVALUATE = 6
    OPTIMIZE_MODEL = 7
    
class VerificationMethods(Enum):
    TOP_N = 1
    RANK = 2

class Word2VecModelCreator(gensim.models.Word2Vec):
    '''
    classdocs
    '''
    CROSS_REGISTRATION_FILENAME = 'cross_registered_courses.csv'
    
    # The enrollment data
    TRAINING_FILENAME  = 'emplid_crs_major_strm_gt10_2000plus.csv'
    TRAINING_SQLITE_DB = 'enrollment_tally.sqlite'

    #--------------------------
    # __init__ 
    #----------------

    def __init__(self, 
                 action=None, 
                 actionFileName=None, 
                 saveFileName=None, 
                 hasHeader=False, 
                 low_strm=None, 
                 high_strm=None):
        '''
        Constructor
        '''
        logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

        curr_dir = os.path.dirname(__file__)
        save_dir = os.path.join(curr_dir, '../data/Word2vec/')
        
        # Initialize self.cross_listings dict:
        cross_registered_course_filename = os.path.join(save_dir, 
                                                        Word2VecModelCreator.CROSS_REGISTRATION_FILENAME
                                                        )
        # The enrollment data, though can be over-ridden 
        # in actionFileName; see case statement below:
        self.training_filename  = os.path.join(save_dir, 
                                               Word2VecModelCreator.TRAINING_FILENAME
                                               )
    
        # The cross_lists_file must have information about which
        # courses are cross listed. Format: "course_name, evalunitid".
        self.cross_listings = self.cross_listings_from_file(cross_registered_course_filename, hasHeader=False)
        
        # self.sentences = self.create_course_sentences(self.training_filename, hasHeader=True)
        
        if action is None:
            # If nothing to do, just provide the instance
            # and let the caller call methods of choice: 
            return
        
        if action == Action.LOAD_MODEL:
            model_file = actionFileName
            self.model = self.load_model(model_file)
            return
        elif action == Action.LOAD_VECTORS:
            vector_file = actionFileName
            self.word_vectors = self.load_word_vectors(vector_file)
            return
        elif action == Action.CREATE_MODEL:
            id_strm_crse_filename = actionFileName
            self.sentences = self.create_course_sentences(id_strm_crse_filename,  # csv of sqlite3 filename 
                                                          hasHeader=hasHeader, 
                                                          low_strm=low_strm, 
                                                          high_strm=high_strm)
            self.model = self.create_model(self.sentences)
            (self.model_filename, self.wv_filename) = self.save(saveFileName)
        elif action == Action.EVALUATE:
            # Run the cross-registration verification prediction accuracy test:
            accuracy = self.verify_model()
            self.logInfo('Accuracy cross registration prediction: %s' % accuracy)
        elif action == Action.OPTIMIZE_MODEL:
            training_set_filename = actionFileName
            cross_lists_filename  = saveFileName 
            self.sentences = self.create_course_sentences(training_set_filename, hasHeader=hasHeader)            
            self.optimize_model(self.sentences, cross_lists_filename, hasHeader=hasHeader)
        elif action == Action.CREATE_SENTENCES_FILE:
            emplid_crs_major_strm_file = actionFileName
            sentences = self.create_course_sentences(emplid_crs_major_strm_file, hasHeader=hasHeader)
            with open(saveFileName, 'w') as fd:
                for sentence in sentences:
                    fd.write(','.join(sentence) + '\n')            
        else:
            raise ValueError("Bad action indicator: '%s' % action")
            
    #--------------------------
    # create_model 
    #----------------
        
    def create_model(self, training_set, vec_size=150, win_size=10, save_name_prefix=None):
        
        self.logInfo("Start creating model...")
        # build vocabulary and train model
        model = gensim.models.Word2Vec(
            training_set,
            size=vec_size,
            window=win_size,
            min_count=2,
            workers=10)
        model.train(training_set, total_examples=len(training_set), epochs=10)
        self.logInfo("Done creating model.")
        return model

    #--------------------------
    # save
    #----------------

    def save(self, saveFileName=None):
        '''
        Save the current model to the file. Will also save the 
        corresponding vectors in saveFileName with extension changed
        to '.vectors'. The vectors are of type KeyedVector and can
        be used for fast operations (see course_sim_analytics.py for
        examples). 
        
        @param saveFileName: name of file to save model to. If None, a temp file is used.
        @type saveFileName: str
        @return: tuple with names of files to which model and vectors were saved.
        @rtype: (str, str)
        '''
        if saveFileName is None:
            openFile = tempfile.NamedTemporaryFile('wb', suffix='.model', prefix='word2vec', dir='/tmp')
            saveFileName = openFile.name
            openFile.close()
        self.model.save(saveFileName)
        saveFileName_dir = os.path.dirname(saveFileName)
        # Create filename in same dir as model, but w/ extension .vectors:
        file_root, _ext   = os.path.splitext(os.path.basename(saveFileName))
        key_vec_filename = os.path.join(saveFileName_dir, file_root + '.vectors') 

        self.model.wv.save(key_vec_filename)
        self.logInfo("Model and word vectors saved in \n    %s and \n    %s, \n    respectively" % (saveFileName, key_vec_filename))
        return (saveFileName, key_vec_filename)

    #--------------------------
    # load_model
    #----------------
                
    def load_model(self, model_file):
        self.logInfo('Starting to load model...')
        model = Word2Vec.load(model_file)
        self.logInfo('Model loaded.')
        
        return model
        
    #--------------------------
    # load_word_vectors 
    #----------------
        
    def load_word_vectors(self, wv_file):
        self.logInfo('Starting to load word vectors...')        
        word_vector_obj = KeyedVectors.load(wv_file)
        self.logInfo('Done loading word vectors.')
        
        self.vectors     = word_vector_obj.vectors
        self.vocab       = word_vector_obj.vocab
        self.index2word  = word_vector_obj.index2word
        self.wv          = word_vector_obj
        
        return word_vector_obj
    
    #--------------------------
    # create_course_sentences 
    #----------------

    def create_course_sentences(self, id_strm_crse_filename, hasHeader=False, low_strm=None, high_strm=None):
        '''
        Given a course info file, create a list of lists that
        can be used as input sentences for word2vec. Input file
        expected:
        
			"emplid","coursename","major","acad_career","strm"
			"$2b$...1123","MED300A","MED-MD","MED","1016"
			"$2b$...Uq24","MED300A","MED-MD","MED","1014"
			"$2b$...Ux35","SURG300A","MED-MD","MED","1012"
			"$2b$...Urk3","PEDS300A","MED-MD","MED","1012"
			
		If the file has extension .sqlite it is assumed to be an
		sqlite file with the same schema as the csv file layout.
		In this case the hasHeader argument is ignored. Instead,
		the low_strm and high_strm args are considered. The low_strm
		is an optional lower bound (inclusive) of the strm(s) included.
		And high_strm is the upper (exclusive) bound. If either is None,
		no bound is imposed in the respective (or both) directions.  
			            
		Each sentences will be the concatenation of one student's 
		course names, and their major.	            
        
        @param id_strm_crse_filename: name of file with enrollment info
        @type id_strm_crse_filename: string
        @param hasHeader: whether or not .csv file as a column name header row.
        @type hasHeader: bool
        @param low_strm: lower inclusive bound of strm included.
        @type low_strm: int
        @param high_strm: upper exclusive bound of strm included.
        @type high_strm: int
        @return: array of array representing the training sentences
        @rtype: [[str,str,str,...],[str,str...]...] 
        '''
        csv_fd = None
        
        if id_strm_crse_filename.endswith('.sqlite'):
            try:
                conn = sqlite3.connect(id_strm_crse_filename)
            except Exception as e:
                raise ValueError("Could not open Sqlite3 db '%s' (%s)" % (id_strm_crse_filename, repr(e)))
            reader = conn.cursor()
            where_clause = '' if low_strm is None and high_strm is None else 'WHERE '
            if low_strm is not None:
                where_clause += "strm >= %s" % low_strm
                if high_strm is not None:
                    where_clause += ' and '
            if high_strm is not None:
                where_clause += 'strm < %s' % high_strm
            
            try:    
                reader.execute("SELECT * FROM EnrollmentTallyAllCols " + where_clause + ';')
            except Exception as e:
                reader.close()
                raise ValueError("Could not query Sqlite3 db '%s' (%s)" % (id_strm_crse_filename, repr(e)))                
        else:
            try:
                csv_fd = open(id_strm_crse_filename, 'r')
                reader = csv.reader(csv_fd)
            except Exception as e:
                raise ValueError("Could not open csv file '%s' (%s)" % (id_strm_crse_filename, repr(e)))                
        try:
            sentences = []
            curr_emplid   = None
            curr_sentence = None
            
            if hasHeader and not id_strm_crse_filename.endswith('.sqlite'):
                # Ignore header in CSV:
                next(reader)
                
            self.logInfo('Creating sentences from enrollments...')
            for emplid, coursename, major, career, strm in reader: #@UnusedVariable
                if emplid != curr_emplid:
                    # Starting a new student:
                    if curr_sentence is not None:
                        # Finished with one student, add finished sentence
                        # to sentences list:
                        sentences.append(curr_sentence)
                    # Start a new sentence with this student's
                    # first course:
                    curr_sentence = [major, coursename]
                    curr_emplid   = emplid
                else:
                    # More courses for current student:
                    curr_sentence.append(coursename)
        finally:
            try:
                # If reader is a db:
                reader.close()
            except AttributeError:
                try:
                    # Oh well, guess it wasn't a db. In that
                    # case close the file underlying the csv 
                    # reader:
                    csv_fd.close()
                except Exception:
                    pass
            
        self.logInfo('Done creating sentences from enrollments.')
        return sentences
    
    #--------------------------
    # optimize_model 
    #----------------
    
    def optimize_model(self, 
                       verification_method,
                       grid_results_save_file_name,
                       vector_sizes=None,
                       window_sizes=None,
                       topn = 4):
        '''
        Train with a variety of vector sizes and window
        combinations. Run the cross-list validation for
        each. Return an array of vectors:
           [['veclen1/win1', accuracy],
            ['veclen1/win2', accuracy],
                 ...
            ['veclenFinal/winFinal', accuracy]
            ]
            
        The topn parameter is relevant only for the top-n eval method. 
        The parameter controls how stringent the success test is
        to be. A topn == 1 means that a cross listed course must be
        the highest-probability co-course in the similarities list
        of the most_similar() result when compared to another cross
        list of the same course. A topn == 2 means that the course must
        be among the top 2, etc.
        
        Models are trained for all combinations of vector
        sizes, and window sizes as given in vec_sizes and win_sizes.
        
        @param verification_method: code of method to use for evaluationg the
            models that are created. Options are as in enum class: VerificationMethods.
        @type verification_method: int
        @param grid_results_save_file_name: name of file to which the results will be written
        @type grid_results_save_file_name: str
        @param vector_sizes: a list of vector dimension numbers to test.
        @type vector_sizes: [int]
        @param window_sizes: a list of window sizes to test.
        @type window_sizes: [int]
        @param topn: test stringency: only needed if verification method is topn-n
        @type topn: int
        @return: a list of result objects, one for each vector-size/window-size
            combination. The subclass of result objs is determined by the 
            verification_method.
        @rtype: [CrossRegistrationTestResult]
        '''

        if grid_results_save_file_name is None:

            # Get the name of a temp file with expressive name.
            # Yes, race condition; but we're alone in the universe:
            
            grid_results_save_fd = tempfile.NamedTemporaryFile(prefix='word2vec_grid_results', 
                                                               suffix='.txt', 
                                                               dir='/tmp', 
                                                               delete=False)
            grid_results_save_file_name = grid_results_save_fd.name
            grid_results_save_fd.close()
        
        # Compute number of pairs that will be compared:
        num_comparisons = 0
        for cross_course_list in self.cross_listings.values():
            num_comparisons += len(cross_course_list)
        num_of_cross_lists = len(self.cross_listings.keys())
        
        save_dir = os.path.dirname(self.training_filename)
        result_objects = []
        with open(grid_results_save_file_name, 'a') as grid_results_save_fd:
            # First, write one line with the number of cross list sets,
            # and the total number of course comparisons:
            grid_results_save_fd.write('Number of cross list sets: %s; Number of comparisons: %s\n' %\
                                       (num_of_cross_lists, num_comparisons)
                                       )
            grid_results_save_fd.flush()
             
            for vec_size in vector_sizes:
                for win_size in window_sizes:
                    #********
                    #*****self.model = self.create_model(self.sentences, vec_size=vec_size, win_size=win_size)
                    save_file = self.make_filename(save_dir, prefix='all_since2000', vec_size=vec_size, win_size=win_size, suffix_no_dot='model')
                    self.model = self.load_model(save_file)
                    #********
                    self.word_vectors = self.model.wv
                    self.vectors     = self.word_vectors.vectors
                    self.vocab       = self.word_vectors.vocab
                    self.index2word  = self.word_vectors.index2word
                    self.wv          = self.word_vectors
                    
                    # Save the model under an appropriate name:
                    save_file = self.make_filename(save_dir, prefix='all_since2000', vec_size=vec_size, win_size=win_size, suffix_no_dot='model')
                    #*********
                    #****self.save(save_file)
                    #*********                    
                    
                    if verification_method == VerificationMethods.TOP_N:
                        accuracy = self.verify_model(topn=topn)
                        # Create a test result object:
                        result = CrossRegistrationTopNResult(topn,
                                                             accuracy, 
                                                             vec_size, 
                                                             win_size, 
                                                             num_comparisons,
                                                             num_of_cross_lists
                                                             )
                    elif verification_method == VerificationMethods.RANK:
                        (mean_rank, median_rank, sd_rank) = self.verify_model(verification_method)
                        result = CrossRegistrationRankResult(mean_rank,
                                                             median_rank,
                                                             sd_rank,
                                                             vec_size, 
                                                             win_size, 
                                                             num_comparisons,
                                                             num_of_cross_lists
                                                             )
                    result_objects.append(result)
                    # Save this result to file:
                    grid_results_save_fd.write(str(result) + '\n')
                    grid_results_save_fd.flush()

        return result_objects
    
    #--------------------------
    # make_filename 
    #----------------
        
    def make_filename(self, the_dir, prefix, vec_size, win_size, suffix_no_dot):
        '''
        Make a filename for model or keyedvector files. The names will reflect the
        vector and window sizes. Example outputs:
                  /tmp/myModel_vec50_win10.model
                  /tmp/myModel_vec50_win10.vectors
        
        @param the_dir: directory where file is to be located
        @type the_dir: str
        @param prefix: prefix to identify the model in some recognizable way
        @type prefix: str
        @param vec_size: dimensionality of the vectors used
        @type vec_size: int
        @param win_size: window size of the model
        @type win_size: int
        @param suffix_no_dot: suffix without a dot. The dot is added.
        @type suffix_no_dot: str
        '''
        
        return os.path.join(the_dir, '%s_vec%s_win%s.%s' % (prefix, vec_size, win_size, suffix_no_dot))

#********************    
#     #--------------------------
#     # cross_list_verification 
#     #----------------
#     
#     def verify_model(self, topn=1, cross_lists_dict=None, cross_lists_filename=None, hasHeader=False):
#         '''
#         Given filename to csv file:
#         
#            course_name, evalunitid
#         
#         that is ordered by evalunitid,    
#         return the percentage of times that the word vectors
#         computed cross listed courses as the most similar.
#         
#         The topn parameter controls how stringent the success test is
#         to be. A topn == 1 means that a cross listed course must be
#         the highest-probability co-course in the similarities list
#         of the most_similar() result when compared to another cross
#         list of the same course. A topn == 2 means that the course must
#         be among the top 2, etc.
#         
#         @param topn: test stringency
#         @type topn: int
#         @param cross_lists_dict: map course to its cross-registered siblings.
#             May be left null if unknown. In that case cross_lists_filename must
#             be provided.
#         @type cross_lists_dict: {str : [str]}
#         @param cross_lists_filename: file with cross listings. No csv header expected
#             If cross_lists_dict provided, no need for this arg, nor the headers arg.
#         @type cross_lists_filename: str
#         @param hasHeader: whether cross_lists_filename has a column header line.
#             Not needed if cross_lists_dict is provided.
#         @type hasHeader: bool
#         @return: accuracy as percentage, and a list of probabilities found for 
#             successful matches. The higher those probabilities, the better.
#         @rtype: (float, [float])
#         '''
#         
#         if cross_lists_dict is None:
#             cross_listings = self.cross_listings_from_file(cross_lists_filename, hasHeader)
#         else:
#             cross_listings = cross_lists_dict
#             
#         # Got the dict. Check similarities:
#         num_cases      = 0
#         num_successes  = 0
#         num_failures   = 0
#         # List of match probabilities of successful matches
#         # between courses and their cross-reg sibs:
#         match_success_probabilities = []
#         
#         for first_sib, other_sibs in cross_listings.items():
#             # Check each of the other_sibs against first_sib.
#             # each should have the first_sib as most similar:
#             for other_sib in other_sibs:
#                 num_cases += 1
#                 # Get single-element array of two-tuples, like
#                 #   [('Foo', 0.53), ('Bar', 0.3),...] in high-low 
#                 # sim order. So check name of first tuple:
# 
#                 try:
#                     # most_similar() returns: ((course1, probability1), (course2, probability2)...)
#                     # *zip(tuple-list) will return a list of the courses, and a list of
#                     # the probabilities:
#                     courses, probabilities = zip(*self.wv.most_similar(other_sib))
#                 except KeyError:
#                     # Course not in vocabulary. This happens if the class had
#                     # fewer than 10 students, or nobody ever got a grade.
#                     continue 
#                 # Check whether the first sibling is in the 
#                 # top-n most similar courses, and note the course's
#                 # probability if the course is within topn:
#                 try:
#                     topn_predictions = courses[:topn] 
#                     first_sib_position = topn_predictions.index(first_sib)
#                 except ValueError:
#                     # The cross listed course is not in the topn:
#                     num_failures += 1
#                     continue
#                 num_successes  += 1
#                 match_success_probabilities.append(probabilities[first_sib_position])
#                 
#         return (100 * num_successes / num_cases, match_success_probabilities)        
#********************

    #--------------------------
    # verify_model 
    #----------------

    def verify_model(self, verification_method, topn=4):
        '''
        
        @param verification_method: which of the VerificationMethod to use.
            Choices are TOP_N and RANK. 
        @type verification_method: int
        @param topn: Only needed for TOP_N method: rank within which 
            sibling must be found.
        @type topn: int
        @return: accuracy as measured by the requested verification method:
            TOP_N: accuracy percentage
            RANK: tuple of mean, median, sdev rank of siblings
        @rtype: {float if TOP_N | (float, float,float) if RANK
        '''
        
        if verification_method == VerificationMethods.TOP_N:
            self.topn = topn 
            # Got the dict. Check similarities:
            self.num_cases      = 0
            self.num_successes  = 0
            self.num_failures   = 0
            # List of match probabilities of successful matches
            # between courses and their cross-reg sibs:
            self.match_success_probabilities = []

            self._loop_through_cross_lists(self.cross_listings_verification_topn_method_helper)
      
            # Return the overall accuracy, a percentage of successes of cases:
            return (100 * self.num_successes / self.num_cases)

        elif verification_method == VerificationMethods.RANK:
            self.sibling_ranks = []
            self._loop_through_cross_lists(self.cross_listings_verification_rank_method_helper)
            return(np.mean(self.sibling_ranks), 
                   np.median(self.sibling_ranks),
                   np.std(self.sibling_ranks)
                   )
        
        else:
            raise ValueError("Verification method %s does not exist." % verification_method)        

    #--------------------------
    # cross_listings_verification_rank_method_helper 
    #----------------

    def cross_listings_verification_rank_method_helper (self, reference_sib, other_sib):
        rank_of_other_sib = self.wv.rank(reference_sib, other_sib)
        self.sibling_ranks.append(rank_of_other_sib)

    #--------------------------
    # cross_listings_verification_topn_method_helper 
    #----------------

    def cross_listings_verification_topn_method_helper(self, reference_sib, other_sib):
        
        # Method most_similar() returns: ((course1, probability1), (course2, probability2)...)
        # *zip(tuple-list) will return a list of the courses, and a list of
        # the probabilities:
        courses, _probabilities = zip(*self.wv.most_similar(other_sib))
        
        # Check whether the first sibling is in the 
        # top-n most similar courses, and note the course's
        # probability if the course is within topn:
        try:
            topn_predictions = courses[:self.topn] 
            topn_predictions.index(reference_sib)
        except ValueError:
            # The cross listed course is not in the topn:
            self.num_failures += 1
        else:
            self.num_successes  += 1

    #--------------------------
    # _loop_through_cross_lists
    #----------------

    def _loop_through_cross_lists(self, validation_callback):
        
        for first_sib, other_sibs in self.cross_listings.items():
            # Check each of the other_sibs against first_sib.
            # each should have the first_sib as most similar:
            for other_sib in other_sibs:
                try:
                    validation_callback(reference_sib=first_sib, other_sib=other_sib)
                except KeyError:
                    # Course not in vocabulary. This happens if the class had
                    # fewer than 10 students, or nobody ever got a grade.
                    continue 

    #--------------------------
    # cross_listings_from_file
    #----------------
        
    def cross_listings_from_file(self, cross_lists_filename, hasHeader=False):
        '''
        Return a dictionary of cross listings, like this:
        
             {course1 : [course2, course3],
              course4 : [course5, course6, course7],
                 ...
            }
            
        where the courses in the key+value list of courses are cross references.
        The given file must have the form:
        
			  "CEE 251","COU:1144:COMBO:202776:05265994"
			  "CEE 151","COU:1144:COMBO:202776:05265994"
			  "EARTHSCI 251","COU:1144:COMBO:202776:05265994"
			  "MS&E 240","CRS:1098:COMBO:0290:05163541"
			           ...        
			          
        @param cross_lists_filename: filename with cross list info
        @type cross_lists_filename: str
        @param hasHeader: whether a CSV column header is present
        @type hasHeader: boolean
        @return: dict with cross reg info
        @rtype: {str : [str]}
        '''
        with open(cross_lists_filename, 'r') as cross_lists_fd:
            csv_reader = csv.reader(cross_lists_fd)
            
            # Skip past header if any:
            if hasHeader:
                next(csv_reader)
            
            # Build a dict mapping one of each crosslisted courses
            # to its siblings. Ex. a crosslisting c1,c2,c3 => {c1 : [c2,c3]}
            
            prev_evalunitid       = None
            first_sibling_course = None    
            cross_listings = {}
            for course, evalunitid in csv_reader:
                # The tables where the course names come from
                # have spaces between course names and course
                # numbers. But the word vec tokens don't:
                course = course.replace(' ', '') 
                if evalunitid != prev_evalunitid:
                    # Done with one set of cross listings:
                    prev_evalunitid = evalunitid
                    first_sibling_course = course
                    # Prepare for the cross listings to follow:
                    cross_listings[first_sibling_course] = []
                else:
                    # Still collecting cross listings:
                    cross_listings[first_sibling_course].append(course)

        return cross_listings

    #--------------------------
    # read_file_input
    #----------------
    
    def read_file_input(self, input_file):
        '''This method reads the input file which is in gzip format'''
        
        with gzip.open(input_file, 'rb') as f:
            for i, line in enumerate(f):
                if line == '':
                    continue
                if (i % 10000 == 0):
                    logging.info("Read {0} course sequences".format(i))
                yield line.strip().split(',')
                
    #--------------------------
    # logging convenience methods 
    #----------------
                
    def logInfo(self, msg):
        logging.info(msg)
        
    def logWarn(self, msg):
        logging.warning(msg)
    
    def logDebug(self, msg):
        logging.debug(msg)
                
# -------------------------------------------- CrossRegistrationTestResult Classes and Subclasses ------------                
                
class CrossRegistrationTestResult(object):
    
    def __init__(self, vec_size, win_size, num_comparisons, num_cross_list_sets):
        '''
        Instances encapsulate the result of one test for predicting
        cross registered courses.  
        
        Success probabilities is a list of the probabilities at which
        most_similar() estimated the successfully found sibling.
        
        @param vec_size: vector size used in the test
        @type vec_size: int
        @param win_size: window size of the test
        @type win_size: int
        @param num_comparisons: number of pairwise sibling comparisons
        @type num_comparisons: int
        @param num_cross_list_sets: how many sets of cross registered siblings
            were involved in the test
        @type num_cross_list_sets: int
        '''
        self.vec_size = vec_size
        self.win_size = win_size
        self.num_comparisons = num_comparisons
        self.num_cross_registrations = num_cross_list_sets

class CrossRegistrationTopNResult(CrossRegistrationTestResult):
        
    # All the args of the parent init, plus the topn number:    
    def __init__(self, topn, accuracy, *args):
        '''
        Create a result of a top-n method model evaluation.
        The accuracy is the percentage of time
        that a cross-registration sibling was in the topn most similar 
        course list as found by the most_similar() method.
        
        @param topn: where in the list of most similar courses a cross registered
            sibling had to appear.
        @type topn: int
        '''
        super(CrossRegistrationTestResult).__init__(*args)
        self.topn = topn
        self.accuracy = accuracy
        
    def __str__(self):
        printable = 'Test: topn-%s, vec-%s, win-%s, accuracy-%s num-compares-%s, num-registrations-%s\nprob-when_successful-%s' %\
            (self.topn, self.vec_size, self.win_size, self.accuracy, self.num_comparisons, self.num_cross_list_sets,
             self.success_probabilities)
        return printable
        
class CrossRegistrationRankResult(CrossRegistrationTestResult):
    
    def __init__(self, mean_rank, median_rank, sd_rank, *args ):
        
        super().__init__(*args)
        self.mean_rank = mean_rank
        self.median_rank = median_rank
        self.sd_rank = sd_rank
        self.args = args
        
    def __str__(self):
        printable = 'vecdim,winsize,mean_rank,median_rank,sd_rank\n'
        printable += '%d,%d,%.1f,%.1f,%.1f' % (self.vec_size, 
                                               self.win_size, 
                                               self.mean_rank,
                                               self.median_rank,
                                               self.sd_rank)
        return printable
    
# -------------------------------------------- Main -------------------------

if __name__ == '__main__':

    curr_dir = os.path.dirname(__file__)
    
    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-a', '--action',
                        type=str,
                        choices=['create_model', 'load_model', 'load_vectors', 'save_model', 'evaluate', 'optimize_model', 'create_sentences_file'],
                        help="what you want the program to do.", 
                        default=None);
    parser.add_argument('-f', '--file',
                        help='fully qualified path to model/vector load file, depending on requested action',
                        default=None);
    parser.add_argument('-s', '--savefile',
                        help='fully qualified path to file for saving result depending on requested action',
                        default=None);
    parser.add_argument('--low_strm',
                        type=int,
                        help='lowest integer strm (inclusive) to use during model training. Only used for create_model',
                        default=None);
    parser.add_argument('--high_strm',
                        type=int,                        
                        help='highest integer strm (exclusive) to use during model training. Only used for create_model',
                        default=None);
                        
                        
    args = parser.parse_args();

    save_dir = os.path.join(curr_dir, '../data/Word2vec/')
    
    # Output filename for the trained course vector full model:
    if args.file is None:
        model_filename   = os.path.join(save_dir, 'all_since_2000_plus_majors_veclen150_win10.model')
    else:
        model_filename   = args.file
    
    # Be on the save side: if the requested save destination
    # exists and is not empty, balk:
    if os.path.exists(args.savefile) and os.stat(args.savefile).st_size > 0:
        raise ValueError("Savefile '%s' exists; please remove it first." % args.savefile)
    
    # Create filename in same dir as model, but w/ extension .vectors:
    file_root, _ext   = os.path.splitext(os.path.basename(model_filename))
    key_vec_filename = os.path.join(save_dir, file_root + '.vectors')
    
    # Get an instance without doing anything yet.
    # Might get overridden below:
    wordvec_creator = Word2VecModelCreator(action=None)
    
    if args.action == 'create_model':    
    
        if args.file is None or not os.path.exists(args.file):
            raise ValueError("Must provide .csv or .sqlite file with enrollment numbers for model creation.")
        if args.savefile is None:
            raise ValueError("Must provide filename for saving the model model creation.")
        
        wordvec_creator = Word2VecModelCreator(
            action=Action.CREATE_MODEL, 
            actionFileName=args.file,
            saveFileName=args.savefile,
            hasHeader=True if not args.file.endswith('.sqlite') else False,
            low_strm=args.low_strm,
            high_strm=args.high_strm
            )
        print("Model file: '%s';\nVector file: '%s'" % (wordvec_creator.model_filename,
                                                        wordvec_creator.wv_filename)
                                                        )
    elif args.action == 'load_model':
        wordvec_creator = Word2VecModelCreator(
            action=Action.LOAD_MODEL, 
            actionFileName=args.file
            )
    elif args.action == 'load_vectors':
        wv_file = wordvec_creator.wv_filename if args.file is None else args.file
        wordvec_creator.load_word_vectors(wv_file)
        
    elif args.action == 'optimize_model':
    
        if args.savefile is None:
            raise ValueError("Must provide save filename for optimization result.")
        # Now we have a wordvec_creator with a model in
        # in, or with some model's vectors.
        timestr = time.strftime("%Y-%m-%d_%H_%M_%S")
        test_results_file = os.path.join(save_dir, 'cross_reg_test_res_%s.txt' % timestr)
        res_objs = wordvec_creator.optimize_model(VerificationMethods.RANK,
                                                  grid_results_save_file_name=args.savefile,
                                                  vector_sizes = [50, 100, 150, 200, 300, 400, 500, 600],
                                                  window_sizes = [2, 5, 10, 15, 20, 25]
                                                  )
    
    
        print('Results are in %s' % args.savefile)

    elif args.action == 'create_sentences_file':
        if args.file is None or not os.path.exists(args.file):
            raise ValueError("Must provide .csv with student ID, course, major, and strm.")
        if args.savefile is None:
            raise ValueError("Must provide filename for to save sentences to.")
        
        wordvec_creator = Word2VecModelCreator(
            action=Action.CREATE_SENTENCES_FILE,
            actionFileName=args.file,
            saveFileName=args.savefile
            )
        print('Sentences (i.e. training set) are in %s' % args.savefile)
        
    