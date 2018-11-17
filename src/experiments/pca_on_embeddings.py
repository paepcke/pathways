'''
Created on Oct 30, 2018

@author: paepcke
'''

import argparse
import logging
import os
import re
import sys

from gensim.models.deprecated.word2vec import Word2Vec
from gensim.models.keyedvectors import KeyedVectors
from sklearn import preprocessing
from sklearn.decomposition import PCA

import numpy as np
import pandas as pd
from utils.constants import majors
from utils.course_info_collector import CourseInfoCollector


# List of all majors:
class DimReducer(object):
    '''
    Given a vector file as exported from a gensim model, 
    compute the top p PCA components from the n-dimensional 
    vectors. Usually p == 2 to allow planar plotting. But the
    number of dimensions can be set during instance creation.
    CSV output can be to stdout, or a file.
    
    Columns will be named PCA_Dim1, PCA_Dim2, etc.
    '''

    subject_extract_pattern = re.compile(r'([^0-9]*).*')
    
    # Pattern for string starting with '$2a$...' or '$2b$...': 
    # i.e. one form of emplid hash:
    EMPLID_START_PATTERN = re.compile(r'\$2[a-z]\$.*')

    #--------------------------
    # Constructor 
    #----------------

    def __init__(self, 
                 vectors_file,
                 pca_outfile = None,
                 num_components = 2,
                 loggingLevel=logging.INFO,
                 logFile=None
                 ):
        '''
        Constructor
        '''

        self.setupLogging(loggingLevel, logFile)
        
        # A course-name to course-info mapper:
        crse_info_collector = CourseInfoCollector()

        vectors = self.load_vectors(vectors_file)
        
        # Number of components will be passed into a scikit learn method,
        # which expects an int; so make sure:
        num_components = int(num_components)
        self.num_components = num_components
        
        # Turn vectors into the rows of a dataframe:
        
        course_df = self.vecs_to_dataframe(vectors)
                
        # If there are majors or emplids in the 
        # sentences, remove them for the PCA:
                            
        course_df = self.extract_numerics(course_df, majors)                            
        
        x = self.standardize_data(course_df)
        
        self.logInfo("Computing PCA...")
        principalDf = self.compute_pca(x, num_components)
        self.logInfo("Done computing PCA.")
        
        # Add the course names as row names back in:
        principalDf.index = course_df.index
        
        # Add a column with the course names:
        principalDf.loc[:,'CourseName'] = principalDf.index
        
        # Add column with course subjects: CS, MS&E, PHYSICS, etc.
        subjects = self.subjects_from_course_names(principalDf.index)
        principalDf.loc[:,'Subject'] = subjects 
        
        # Add additional column with each course's School (acad_group):
        acad_groups = [crse_info_collector.get_acad_grp(course_name) for course_name in principalDf.index]
        principalDf.loc[:,'AcadGrp'] = acad_groups
        
        # Add short descriptions:
        # (NOTE: list comprehension not useable here, b/c get_course_descr()
        #        can throw KeyError.)
        
        crse_short_and_long_descr = []
        for course_name in principalDf.index:
            try:
                crse_short_and_long_descr.append(crse_info_collector.get_course_descr(course_name))
            except KeyError:
                crse_short_and_long_descr.append(('',''))
                continue

        # Attach the short and long descr column to the side:
        descriptions_df = pd.DataFrame(crse_short_and_long_descr, columns=['CrseDescrShort','CrseDescrLong'])
        descriptions_df.index = principalDf.index
        principalDf = pd.concat([principalDf, descriptions_df], axis=1)
                        
        self.output_as_csv(principalDf, pca_outfile)

    #--------------------------
    # load_vectors 
    #----------------

    def load_vectors(self, vectors_path):
        # Just in case they passed a model:
        if vectors_path.endswith('.model'):
            model = Word2Vec.load(vectors_path)
            vectors = model.wv 
        else:
            vectors = KeyedVectors.load(vectors_path)
        return vectors
            
    #--------------------------
    # vecs_to_dataframe 
    #----------------
            
    def vecs_to_dataframe(self, vectors):
        
        # Turn vectors into the rows of a dataframe. Index are the 
        # courses (i.e. the sentences).        
        # index2word is a list of courses/majors, i.e. the 'words'
        # of the training. 
        
        vectors_as_rows = []
        self.logInfo("Creating matrix from word vectors...")
        for vec_key in vectors.index2word:
            # Get this course's vector:
            vectors_as_rows.append(vectors[vec_key])
        self.logInfo("Done creating matrix from word vectors.")            
       
        self.logInfo("Creating dataframe from vectors...")
        course_df = pd.DataFrame.from_records(vectors_as_rows,
                                              vectors.index2word
                                              )
        self.logInfo("Done creating dataframe from vectors.")
        return course_df

    #--------------------------
    # extract_numerics
    #----------------

    def extract_numerics(self, course_df, majors):
        
        # If there are majors or emplids in the 
        # sentences, remove them for the PCA:
                
        self.logInfo("Removing vectors for majors and emplids, leaving only those for courses...")

        # List 'majors' has a list of all majors:
        df = course_df[~course_df.index.isin(majors)]
        
        # Drop vectors of emplids: the self.is_emplid_array(df.index)
        # returns a simple list of bools. We turn that list into a
        # numpy array. For numpy arrays the unary negator '~' flips
        # each element in the list:
        
        course_df = df[~np.array(self.is_emplid_array(df.index))]
        
        # There can also be a vector for '\N'; remove it:
        try:
            course_df = course_df.drop(labels=['\\N'])
        except KeyError:
            # No \N label present, even better:
            pass
        
        self.logInfo("Done removing vectors for majors and emplids, leaving only those for courses.")                            
        return course_df  
    
    #--------------------------
    # standardize_data 
    #----------------
      
    def standardize_data(self, course_df):
        '''
        Given a dataframe like this:
        DataFrame:                    0         1      ...          148       149
        
		   MATH51        0.717620 -1.844187    ...    -0.377891  0.620382
		   CS106A       -0.689994  0.262886    ...     0.575509  0.290112
        
        return a matrix with just the numeric portion, standardized
        to mean == 0 and std == 1
        
        @param course_df:
        @type course_df:
        '''
        X_scaled = preprocessing.scale(course_df.values)
        return X_scaled
        
    #--------------------------
    # is_emplid_array 
    #----------------
    
    def is_emplid_array(self, items):
        '''
        Takes an array of items. Returns an array of True/False,
        with True indicating that the respective element is a 
        Carta emplid string.

        The two emplid forms are recognizable like this:
           Form 1: is 60 chars long, and starts with regex: $2[a-z]$15
           Form 2: is 88 chars long, and ends with ==
        
        @param items: items to be checked
        @type items: [any]
        '''
        res = []
        for item in items:
            if not type(item) == str:
                res.append(False)
            elif len(item) == 60 and DimReducer.EMPLID_START_PATTERN is not None:
                res.append(True)
            elif len(item) == 88 and item.endswith('=='):
                res.append(True)
            else:
                res.append(False)
        
        return res
        
    #--------------------------
    # output_as_csv 
    #----------------
            
    def output_as_csv(self, df, output_file="/tmp/pca_output.csv"):
        if output_file is None:
            output_file = sys.stdout
        # Create col names for each PCA dimension:
        header = ['PCA_Dim'+str(n) for n in range(self.num_components)]
        header.append('CrseNames')
        header.append('CrseDescrShort')
        header.append('CrseDescrLong')
        df.to_csv(output_file, index=False)
        
    #--------------------------
    # subjects_from_course_names 
    #----------------
        
    def subjects_from_course_names(self, course_names):
        
        # Use regex to collect all chars that are not numbers
        # from each course name in turn. Creates an array:
        subjects = [DimReducer.subject_extract_pattern.search(course_name).group(1) for course_name in course_names]
        return subjects
    
    #--------------------------
    # compute_pca 
    #----------------
    
    def compute_pca(self, x, num_components=2):
        pca = PCA(n_components=num_components)
        principalComponents = pca.fit_transform(x)
        col_names = ['PCA_'+str(col_num) for col_num in range(num_components)]
        principalDf = pd.DataFrame(data = principalComponents, columns=col_names)
        return principalDf  
    
    # ------------------------- Utilities ----------------
    
    #--------------------------
    # setupLogging 
    #----------------
    
    def setupLogging(self, loggingLevel=logging.INFO, logFile=None):
        '''
        Set up the standard Python logger. 
        TODO: have the logger add the script name as Sef's original
        @param loggingLevel:
        @type loggingLevel:
        @param logFile:
        @type logFile:
        '''
        # Set up logging:
        #self.logger = logging.getLogger('pullTackLogs')
        DimReducer.logger = logging.getLogger(os.path.basename(__file__))

        # Create file handler if requested:
        if logFile is not None:
            handler = logging.FileHandler(logFile)
            print('Logging of control flow will go to %s' % logFile)            
        else:
            # Create console handler:
            handler = logging.StreamHandler()
        handler.setLevel(loggingLevel)

        # Create formatter
        formatter = logging.Formatter("%(name)s: %(asctime)s;%(levelname)s: %(message)s")       
        handler.setFormatter(formatter)
        
        # Add the handler to the logger
        DimReducer.logger.addHandler(handler)
        DimReducer.logger.setLevel(loggingLevel)
         
    #--------------------------
    # Logging class methods 
    #----------------
         
    @classmethod
    def logDebug(cls, msg):
        DimReducer.logger.debug(msg)

    @classmethod
    def logWarn(cls, msg):
        DimReducer.logger.warn(msg)

    @classmethod
    def logInfo(cls, msg):
        DimReducer.logger.info(msg)

    @classmethod
    def logErr(cls, msg):
        DimReducer.logger.error(msg)
          
    # ------------------------------ Main ------------------------
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), 
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description="PCA from vector embeddings."
                                     )
    parser.add_argument('-l', '--logfile',
                        help='fully qualified log file name to which info and error messages \n' +\
                             'are directed. Default: stdout.',
                        dest='errLogFile',
                        default=None);
    parser.add_argument('-o', '--outfile',
                        help='where to write the output; default: stdout',
                        default=None
                        ),
    parser.add_argument('-d', '--dimensions',
                        help='number of PCA dimensions to reduce to; default: 2',
                        default=2
                        )
    parser.add_argument('vectors',
                        help='file with vector embeddings.'
                        )

    args = parser.parse_args();
    
    #reducer = DimReducer('/Users/paepcke/EclipseWorkspacesNew/pathways/src/data/Word2vec/winning_model.model')
    reducer = DimReducer(args.vectors,
                         args.outfile,
                         num_components=args.dimensions,
                         logFile=args.errLogFile
                         )
    
            