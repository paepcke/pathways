'''
Created on Aug 29, 2018

@author: paepcke
'''
import csv
import gzip
import logging
import os
import tempfile
import time

import gensim
from gensim.models import KeyedVectors
from gensim.models import Word2Vec
from scipy.optimize.zeros import results_c


class Action():
    LOAD_MODEL = 0,
    LOAD_VECTORS = 1,
    SAVE_MODEL = 2,
    SAVE_WORD_VECTORS = 3,
    CREATE_MODEL = 4,
    CREATE_SENTENCES = 5,
    EVALUATE = 6
    OPTIMIZE_MODEL = 7

class Word2VecModelCreator(gensim.models.Word2Vec):
    '''
    classdocs
    '''

    #--------------------------
    # __init__ 
    #----------------

    def __init__(self, action=None, actionFileName=None, saveFileName=None, hasHeader=False):
        '''
        Constructor
        '''
        logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
        
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
            self.sentences = self.create_course_sentences(id_strm_crse_filename, hasHeader=hasHeader)
            self.model = self.create_model(self.sentences)
            (self.model_filename, self.wv_filename) = self.save(saveFileName)
        elif action == Action.EVALUATE:
            # Run the cross-registration verification prediction accuracy test:
            accuracy = self.cross_listings_verification()
            self.logInfo('Accuracy cross registration prediction: %s' % accuracy)
        elif action == Action.OPTIMIZE_MODEL:
            training_set_filename = actionFileName
            cross_lists_filename  = saveFileName 
            self.sentences = self.create_course_sentences(training_set_filename, hasHeader=hasHeader)            
            self.optimize_model(self.sentences, cross_lists_filename, hasHeader=hasHeader)
            
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

    def create_course_sentences(self, id_strm_crse_filename, hasHeader=False):
        '''
        Given a course info file, create a list of lists that
        can be used as input sentences for word2vec. Input file
        expected:
        
			"emplid","coursename","major","acad_career","strm"
			"$2b$...1123","MED300A","MED-MD","MED","1016"
			"$2b$...Uq24","MED300A","MED-MD","MED","1014"
			"$2b$...Ux35","SURG300A","MED-MD","MED","1012"
			"$2b$...Urk3","PEDS300A","MED-MD","MED","1012"
			            
		Each sentences will be the concatenation of one student's 
		course names, and their major.	            
        
        @param id_strm_crse_filename: name of file with enrollment info
        @type id_strm_crse_filename: string
        @return: array of array representing the training sentences
        @rtype: [[str,str,str,...],[str,str...]...] 
        '''
        with open(id_strm_crse_filename, 'r') as fd:
            sentences = []
            csv_reader    = csv.reader(fd)
            curr_emplid   = None
            curr_sentence = None
            
            if hasHeader:
                # Ignore header in CSV:
                next(csv_reader)
                
            self.logInfo('Creating sentences from enrollments...')
            for emplid, coursename, major, career, strm in csv_reader: #@UnusedVariable
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
        self.logInfo('Done creating sentences from enrollments.')
        return sentences
    
    #--------------------------
    # optimize_model 
    #----------------
    
    def optimize_model(self, 
                       topn=1, 
                       sentences=None, 
                       cross_lists_file=None, 
                       hasHeader=False,
                       grid_results_save_file_name=None):
        '''
        Train with a variety of vector sizes and window
        combinations. Run the cross-list validation for
        each. Return an array of vectors:
           [['veclen1/win1', accuracy],
            ['veclen1/win2', accuracy],
                 ...
            ['veclenFinal/winFinal', accuracy]
            ]
            
        The cross_lists_file must have information about which
        courses are cross listed. Format: "course_name, evalunitid".
        The sentences training dict must be of the form expected by
        method create_course_sentences().
        
        The topn parameter controls how stringent the success test is
        to be. A topn == 1 means that a cross listed course must be
        the highest-probability co-course in the similarities list
        of the most_similar() result when compared to another cross
        list of the same course. A topn == 2 means that the course must
        be among the top 2, etc.
        
        The method returns a triplet: the number of course comparisons
        made, the number of cross-listed course sets, and a 2D matrix
        of results. Models are trained for all combinations of 6 vector
        sizes, and 2 window sizes. Each row in the result matrix contains
        a two-tuple, an experiment condition, such as '50/2', and the accuracy
        for that setting of vector length 50, and window size 2. 
        
        @param topn: test stringency
        @type topn: int
        @param sentences: list of course sets
        @type sentences: [str]
        @param cross_lists_file: csv file of cross listed courses.  
        @type cross_lists_file: str
        @param hasHeader: whether the cross_lists_file has a column header name row
        @type hasHeader: bool
        @return: a list of result objects, one for each vector-size/window-size
            combination
        @rtype: CrossRegistrationTestResult
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
        
        #************
#         vector_sizes = [50, 100, 150, 200, 250, 300]
#         window_sizes = [2, 5, 10]

#         vector_sizes = [50, 100, 150, 200, 250, 300]
#         window_sizes = [15, 20, 25]

        vector_sizes = [350, 400,450, 500, 550, 600]
        window_sizes = [2, 5, 10, 15, 20, 25]
        #************
        
        # Get a dict of cross listings as required by the cross list val:
        cross_lists_dict = self.cross_listings_from_file(cross_lists_file, hasHeader)
        # Compute number of pairs that will be compared:
        num_comparisons = 0
        for cross_course_list in cross_lists_dict.values():
            num_comparisons += len(cross_course_list)
        num_of_cross_lists = len(cross_lists_dict.keys())
        
        save_dir = os.path.dirname(training_filename)
        result_objects = []
        with open(grid_results_save_file_name, 'a') as grid_results_save_fd:
            for vec_size in vector_sizes:
                for win_size in window_sizes:
                    self.model = self.create_model(sentences, vec_size=vec_size, win_size=win_size)
                    self.word_vectors = self.model.wv
                    self.vectors     = self.word_vectors.vectors
                    self.vocab       = self.word_vectors.vocab
                    self.index2word  = self.word_vectors.index2word
                    self.wv          = self.word_vectors
                    
                    # Save the model under an appropriate name:
                    save_file = self.make_filename(save_dir, prefix='all_since2000', vec_size=vec_size, win_size=win_size, suffix_no_dot='model')
                    self.save(save_file)
                    (accuracy,match_probabilities) = self.cross_listings_verification(topn=topn, cross_lists_dict=cross_lists_dict)
                    # Create a test result object:
                    result = CrossRegistrationTestResult(topn, 
                                                         vec_size, 
                                                         win_size, 
                                                         accuracy,
                                                         num_comparisons,
                                                         num_of_cross_lists,
                                                         match_probabilities)
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
    
    #--------------------------
    # cross_list_verification 
    #----------------
    
    def cross_listings_verification(self, topn=1, cross_lists_dict=None, cross_lists_filename=None, hasHeader=False):
        '''
        Given filename to csv file:
        
           course_name, evalunitid
        
        that is ordered by evalunitid,    
        return the percentage of times that the word vectors
        computed cross listed courses as the most similar.
        
        The topn parameter controls how stringent the success test is
        to be. A topn == 1 means that a cross listed course must be
        the highest-probability co-course in the similarities list
        of the most_similar() result when compared to another cross
        list of the same course. A topn == 2 means that the course must
        be among the top 2, etc.
        
        @param topn: test stringency
        @type topn: int
        @param cross_lists_filename: file with cross listings. No csv header expected
        @return: accuracy as percentage, and a list of probabilities found for 
            successful matches. The higher those probabilities, the better.
        @rtype: (float, [float])
        '''
        
        if cross_lists_dict is None:
            cross_listings = self.cross_listings_from_file(cross_lists_filename, hasHeader)
        else:
            cross_listings = cross_lists_dict
            
        # Got the dict. Check similarities:
        num_cases      = 0
        num_successes  = 0
        num_failures   = 0
        # List of match probabilities of successful matches
        # between courses and their cross-reg sibs:
        match_success_probabilities = []
        
        for first_sib, other_sibs in cross_listings.items():
            # Check each of the other_sibs against first_sib.
            # each should have the first_sib as most similar:
            for other_sib in other_sibs:
                num_cases += 1
                # Get single-element array of two-tuples, like
                #   [('Foo', 0.53), ('Bar', 0.3),...] in high-low 
                # sim order. So check name of first tuple:

                try:
                    # most_similar() returns: ((course1, probability1), (course2, probability2)...)
                    # *zip(tuple-list) will return a list of the courses, and a list of
                    # the probabilities:
                    courses, probabilities = zip(*self.wv.most_similar(other_sib))
                except KeyError:
                    # Course not in vocabulary. This happens if the class had
                    # fewer than 10 students, or nobody ever got a grade.
                    continue 
                # Check whether the first sibling is in the 
                # top-n most similar courses, and note the course's
                # probability if the course is within topn:
                try:
                    topn_predictions = courses[:topn] 
                    first_sib_position = topn_predictions.index(first_sib)
                except ValueError:
                    # The cross listed course is not in the topn:
                    num_failures += 1
                    continue
                num_successes  += 1
                match_success_probabilities.append(probabilities[first_sib_position])
                
        return (100 * num_successes / num_cases, match_success_probabilities)        

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
                
# -------------------------------------------- CrossRegistrationTestResult ------------                
                
class CrossRegistrationTestResult(object):
    
    def __init__(self, topn, vec_size, win_size, accuracy, num_comparisons, num_cross_registrations, success_probabilities):
        '''
        Instances encapsulate the result of one test for predicting
        cross registered courses. The accuracy is the percentage of time
        that a cross-registration sibling was in the topn most similar 
        course list as found by the most_similar() method. 
        
        Success probabilities is a list of the probabilities at which
        most_similar() estimated the successfully found sibling.
        
        @param topn: where in the list of most similar courses a cross registered
            sibling had to appear.
        @type topn: int
        @param vec_size: vector size used in the test
        @type vec_size: int
        @param win_size: window size of the test
        @type win_size: int
        @param accuracy: percentage of time cross registered courses were
            found to be most similar with topn
        @type accuracy: float
        @param num_comparisons: number of pairwise sibling comparisons
        @type num_comparisons: int
        @param num_cross_registrations: how many sets of cross registered siblings
            were involved in the test
        @type num_cross_registrations: int
        @param success_probabilities: list of the probabilities at which siblings in 
            the test who were within topn similar were estimated to be close by.
        @type success_probabilities: [float]
        '''
        self.topn = topn
        self.vec_size = vec_size
        self.win_size = win_size
        self.accuracy = accuracy
        self.num_comparisons = num_comparisons
        self.num_cross_registrations = num_cross_registrations
        self.success_probabilities = success_probabilities
        
    def __str__(self):
        printable = 'Test: topn-%s, vec-%s, win-%s, accuracy-%s num-compares-%s, num-registrations-%s\nprob-when_successful-%s' %\
            (self.topn, self.vec_size, self.win_size, self.accuracy, self.num_comparisons, self.num_cross_registrations,
             self.success_probabilities)
        return printable
        

# -------------------------------------------- Main -------------------------

if __name__ == '__main__':
    curr_dir = os.path.dirname(__file__)
    save_dir = os.path.join(curr_dir, '../data/Word2vec/')
    
    # The enrollment data:
    training_filename  = os.path.join(save_dir, 'emplid_crs_major_strm_gt10_2000plus.csv')
    
    # Output filename for the trained course vector full model:
    model_filename   = os.path.join(save_dir, 'all_since_2000_plus_majors_veclen150_win10.model')
    # Create filename in same dir as model, but w/ extension .vectors:
    file_root, _ext   = os.path.splitext(os.path.basename(model_filename))
    key_vec_filename = os.path.join(save_dir, file_root + '.vectors')
    
    cross_registered_course_filename = os.path.join(save_dir, 'cross_registered_courses.csv') 
    
    wordvec_creator = None    
    # Create a model:
#     wordvec_creator = Word2VecModelCreator(action=Action.CREATE_MODEL, 
#                                            actionFileName=training_filename, 
#                                            saveFileName='allSince2000PlusMajors',
#                                            hasHeader=True)
#     if wordvec_creator is not None:
#         wordvec_creator = Word2VecModelCreator(action=Action.LOAD_VECTORS, 
#                                                actionFileName=wordvec_creator.wv_filename
#                                                )
#     else:
#         wordvec_creator = Word2VecModelCreator(action=Action.LOAD_VECTORS, 
#                                                actionFileName=key_vec_filename
#                                                )
#wordvec_creator.cross_listings_verification(cross_registered_course_filename)

    timestr = time.strftime("%Y-%m-%d_%H_%M_%S")
    test_results_file = os.path.join(save_dir, 'cross_reg_test_res_%s.txt' % timestr)
                                      
    # Run through many vector and window sizes and see which course cross listings
    # are best predicted: 
    # Get an instance without doing anything yet:
    
    wordvec_creator = Word2VecModelCreator(action=None)
    sentences = wordvec_creator.create_course_sentences(training_filename, hasHeader=True)
    
    # Try models for course siblings being the 1st, 2nd, 3rd, and 4th 
    # most likely neighbor course: 
    for topn in range(1,5):
        res_objs = wordvec_creator.optimize_model(topn, 
                                                  sentences, 
                                                  cross_registered_course_filename, 
                                                  hasHeader=False,
                                                  grid_results_save_file_name=test_results_file)
    print('Results are in %s' % test_results_file)
    
