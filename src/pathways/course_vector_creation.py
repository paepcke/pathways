'''
Created on Aug 10, 2018

@author: paepcke

NOTE: This file is strongly associated with the TSNE viz. For the more
       general course2vec see course2vec_model_creation.py
'''

import gzip
import logging
from logging import info as logInfo
import os
import warnings
from gensim.models.deprecated.keyedvectors import KeyedVectors

with warnings.catch_warnings():
    import gensim
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

class CourseVectorsCreator(gensim.models.Word2Vec):
    '''
    classdocs
    '''

    #-----------------------------
    # Constructor
    #-------------------

    def __init__(self):
        '''
        Constructor
        '''
        
    #-----------------------------
    # load_word2vec_model 
    #-------------------
    
    def load_word2vec_model(self, model_file_name):
        logInfo('Loading course vector model from %s...' % model_file_name)
        self.word2vec_model = gensim.models.Word2Vec.load(model_file_name)
        logInfo('Model loaded.') 
        return self.word2vec_model
        
    #--------------------------
    # save_word_vectors_only 
    #----------------
    
    def save_word_vectors_only(self, filename):
        word_vectors = self.word2vec_model.wv
        word_vectors.save(filename)
        
    #--------------------------
    # load_word_vectors_only
    #----------------
    
    def load_word_vectors_only(self, filename):
        self.word_vectors = KeyedVectors.load(filename, mmap='r')
        return self.word_vectors
        
    #-----------------------------
    # train_word2vec_model 
    #-------------------
        
    def train_word2vec_model(self, sentencesInputFile, contextWindowSize=10, model_output_file=None):
        '''
        Train course vectors for a given sequence of course sets. Each
        set would typically be the courses taken by one student.
        NOTE: you can ignore the RuntimeWarning messages about binary incompatibilities.
        
        @param sentencesInputFile:
        @type sentencesInputFile:
        @param contextWindowSize:
        @type contextWindowSize:
        @param model_output_file:
        @type model_output_file:
        '''
        
        self.read_input(sentencesInputFile)
        
        # Get the 'sentences':
        documents = [course_list for course_list in self.read_input(sentencesInputFile)]
        
        # Build vocabulary and train course_vector_model
        logInfo('Building course vector model from student course sets...')
        self.word2vec_model = gensim.models.Word2Vec(
            documents,    # Sentences
            size=150,     # Number of elements in each word vector
            window=contextWindowSize,
            min_count=2,  # Only courses that occur at least this # of times
            workers=10    # Threads
            )
        logInfo('Done building course model from student course sets.')
        
        logInfo('Train course vecor  model...')
        self.word2vec_model.train(documents, total_examples=len(documents), epochs=10)
        logInfo('Done training course vecor  model.')        
        
        if model_output_file is not None:
            self.word2vec_model.save(model_output_file)
            
    #-----------------------------
    # wv wordvectors property  
    #-------------------
    
    @property
    def wv(self):
        return self.word2vec_model.wv
            
    @property
    def vector_size(self):
        return self.word2vec_model.vector_size

    #-----------------------------
    # find_courses_with_similar_context
    #-------------------
        
    def find_courses_with_similar_context(self, course_vector_model, course):
        # Find similar courses:
        course_vector_model.wv.most_similar(positive=course)        
        
        
    #-----------------------------
    #  read_input
    #-------------------
        
    def read_input(self, input_file):
        '''
        This method reads the input file which may be in gzip format
        as determined by presence of absence of .gz extension. Each row
        in the file is assumed to be all the courses taken by one student.
        
              MATH104, CS105A, ...
         '''
     
        logging.info("reading file {0}...this may take a while".format(input_file))
        try:
            if os.path.splitext(input_file) == '.gz':
                fd = gzip.open(input_file, 'rb')
            else:
                fd = open(input_file, 'rb')
                
            for i, line in enumerate(fd):
                if line == '':
                    continue
                if (i % 10000 == 0):
                    logInfo("read {0} course sequences".format(i))
                yield line.strip().split(',')
        finally:
            fd.close()
            logInfo('Read total of %s course sets.' % i)

    def filter_runtime_warning(self):
        warnings.warn("runtime", RuntimeWarning)
            
# ---------------------------------  Main ---------------------------              
        
if __name__ == '__main__':
    #student_course_sets_input_file = os.path.join(os.path.dirname(__file__), '../Data/Course2VecData/course2VecInput.txt'
    model_save_outfile = os.path.join(os.path.dirname(__file__), '../Data/course2vecModelWin10.vectors')
    vector_creator = CourseVectorsCreator()
#     vector_creator.train_word2vec_model(student_course_sets_input_file, 
#                                         contextWindowSize=10,
#                                         model_output_file=model_save_outfile)
    #vector_creator.load_word2vec_model('/users/Paepcke/Project/Pathways/Data/Course2VecData/course2vecModelWin10.model')
    #vector_creator.save_word_vectors_only(model_save_outfile)
    vector_creator.load_word_vectors_only(model_save_outfile)
