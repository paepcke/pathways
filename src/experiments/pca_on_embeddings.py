'''
Created on Oct 30, 2018

@author: paepcke
'''

import argparse
import logging
import os
import re
import sqlite3
import sys

from gensim.models.deprecated.word2vec import Word2Vec
from gensim.models.keyedvectors import KeyedVectors
from sklearn import preprocessing
from sklearn.decomposition import PCA

import numpy as np
import pandas as pd
from utils.constants import majors
from utils.course_info_collector import CourseInfoCollector


# Path to sqlite db that holds info on which courses were available
# in each quarter:
#
# 	  CREATE TABLE CourseAvailability (
# 	      strm_year int,
# 	      course_key int
# 	      );
# 	  CREATE TABLE AllCourses (
# 	      id int,
# 	      course_code varchar(50)
# 	      );

COURSE_INFO_PATH = '/Users/paepcke/EclipseWorkspacesNew/pathways/src/data/courseAvailability.sqlite'

# List of all majors:
class DimReducerSimple(object):
    '''
    Given a vector file as exported from a gensim model, 
    compute the top p PCA components from the n-dimensional 
    vectors. Usually p == 2 to allow planar plotting. But the
    number of dimensions can be set during instance creation.
    CSV output can be to stdout, or a file.
    
    Columns will be named PCA_Dim1, PCA_Dim2, etc., and output
    of the result vectors is either stdout, or a given file.
    
    The subclass DimReducerByYear(DimReducerSimple) applies PCA 
    separately only to courses that were available during the
    various years. It thus creates one set of vectors for
    each year since 2000.
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
                 num_components = 2,
                 loggingLevel=logging.INFO,
                 logFile=None,
                 ):
        '''
        Constructor. Prepares data. This step needs to be done
        by instances of this superclass, as well as instances
        olf the DimReducerByYear subclass.
        
        Initializes self.vectors, self.course_df, and self.num_components
                
        @param vectors_file: vectors created by gensim.word2vec()
        @type vectors_file: str
        @param num_components: target number of dimensions
        @type num_components: int
        @param loggingLevel: see Python logging module
        @type loggingLevel:
        @param logFile: log destination. Default, stdout 
        @type logFile: str
        '''
        

        self.setupLogging(loggingLevel, logFile)
        
        # Prepare record of explained variance for each strm:
        self.explained_variance_ratios = {}
        
        self.vectors = self.load_vectors(vectors_file)
        
        # Number of components will be passed into a scikit learn method,
        # which expects an int; so make sure:
        self.num_components = int(num_components)
        
        # Turn vectors into the rows of a dataframe:
        
        self.course_df = self.vecs_to_dataframe(self.vectors)
                
        # If there are majors or emplids in the 
        # sentences, remove them for the PCA:
                            
        self.course_df = self.extract_numerics(self.course_df, majors)
        
    #--------------------------
    # run 
    #----------------
    
    def run(self, pca_outfile):
        
        principalDf = self.generate_low_dim_vecs(self.course_df, self.num_components)
        self.output_as_csv(principalDf, pca_outfile)
        self.explained_variance_ratios = {'allYears: %s' % self.pca.explained_variance_ratio_}

        
    #--------------------------
    # generate_low_dim_vecs 
    #----------------

    def generate_low_dim_vecs(self, course_df, num_components):
        '''
        Given a dataframe with each course's high dimensional vector:
        
        DataFrame:            0         1      ...          148       149
			MATH51        0.717620 -1.844187    ...    -0.377891  0.620382
			CS106A       -0.689994  0.262886    ...     0.575509  0.290112
			CHEM33       -2.393712 -2.051752    ...     0.337395  1.404484
		
		i.e. the index is the courses, but the body of the DF are the raw
		course embedding vectors from word2vec.
		
		Return a new dataframe with course names as the index AND a
		column with the course names, plus columns for the course's academic
		group, subject, and both short, and long course descriptions.
		
		The method standardizes the data before running PCA. Final DF:
		
		    Index       CourseName     Subject    AcadGroup    CrseDescrShort      CrseDescrLong
		  <crseName>       ...                           ...                      ...
        
        @param course_df: dataframe of raw, unstandardized course vectors,
            with course names as the row names (index)
        @type course_df: pandas.DataFrame
        @param num_components: number of dimensions to which the vectors are
            to be reduced.
        @type num_components: int
        @return dataframe with course info and low-dim vectors.
        @rtype pandas.DataFrame
        '''

        self.logInfo("Standardizing data...")
        x_matrix = self.standardize_data(course_df)
        self.logInfo("Done standardizing data...")
        
        # A course-name to course-info mapper:
        crse_info_collector = CourseInfoCollector()
        
        self.logInfo("Computing PCA...")
        principalDf = self.compute_pca(x_matrix, num_components)
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
                        
        return principalDf
        
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
            elif len(item) == 60 and DimReducerSimple.EMPLID_START_PATTERN is not None:
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
        subjects = [DimReducerSimple.subject_extract_pattern.search(course_name).group(1) for course_name in course_names]
        return subjects
    
    #--------------------------
    # compute_pca 
    #----------------
    
    def compute_pca(self, x, num_components=2):
        '''
        Given a numpy matrix of row vectors, or a dataframe,
        return the result of a PCA. The number of components
        in the mapping is controlled by num_components. 
        
        If a dataframe is returned, with column names 
        PCA_1, PCA_2, ... If a df was passed in, the resulting
        df will have the same row labels (i.e. index as the
        passed-in arg). 
        
        The instance var self.pca will contain the PCA instance.
        So callers can examine, for example: self.pca.explained_variance_ratios
        
        @param x: vectors to be reduced
        @type x: {nparray | pandas.DataFrame}
        @param num_components: target number of components
        @type num_components: int
        '''
        if type(x) == pd.DataFrame:
            # Save the df index (i.e. row labels):
            row_lables = x.index
            # Extract just the numbers for the PCA:
            x = x.values
        else:
            row_lables = None 
        
        self.pca = PCA(n_components=num_components)
        principalComponents = self.pca.fit_transform(x)
        col_names = ['PCA_'+str(col_num) for col_num in range(num_components)]
        principalDf = pd.DataFrame(data = principalComponents, columns=col_names)
        if row_lables is not None:
            principalDf.index = row_lables
            
        return principalDf  
    
    
    # ------------------------- Database Access ----------------    

    #--------------------------
    # init_sqlite3_db 
    #----------------

    def init_sqlite3_db(self, sqlite_file):
        '''
        Creates an Sqlite3 connection to the given .sqlite file.
        Sets the connection's row_factory to sqlite3.Row, so that
        results will be tuples that also function as dicts, with
        keys are column names.
        
        @param sqlite_file: database file
        @type sqlite_file: str
        '''
        
        conn = sqlite3.connect(sqlite_file)
        conn.row_factory = sqlite3.Row

        self.db_cursor = conn.cursor()
        

    #--------------------------
    # courses_in_strm_year 
    #----------------

    def courses_in_strm_year(self, strm_year):
        '''
        Takes the first three digits of a strm,
        i.e. the year part, and returns a list of
        all courses that were available during that
        year.
        
        @param strm_year: three-digit strm year
        @type strm_year: {int | str}
        '''
        
        res = self.db_cursor.execute('''SELECT course_code
                                		  FROM CourseAvailability LEFT JOIN AllCourses
                                		    ON course_key = id   
                                		 WHERE strm_year = %s;''' % strm_year
                              )
        rows = res.fetchall()
        courses = [row['course_code'] for row in rows]
                              
        return courses
    
    # ------------------------- Utilities ----------------
    
    #--------------------------
    # variance_ratios 
    #----------------
    
    def variance_ratios(self, features):
        '''
        Given the features of a space, return each
        feature's variance, it's variance ratio, and
        total variance
        
        Input should be a dataframe of the form:
        
                 Feature1   Feature2   Feature3...
        sample1   number     number     ...
        sample2   number     number     ...
           ...
           
        Example:
                     EmbeddingDim1   EmbeddingDim2  EmbeddingDim3 ...
         course1
         course2
           ...
           
        Variances are computed for each column. Total variance:
        Sum of all feature variances, variance ratios: featureVariance/totalVariance
        
        @param features: samples x features dataframe
        @type features: pandas.DataFrame
        @return: variance object with each total variance, each feature's
            variance, and variance ratio.
        @rtype: Variance 
        '''
    
    
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
        DimReducerSimple.logger = logging.getLogger(os.path.basename(__file__))

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
        DimReducerSimple.logger.addHandler(handler)
        DimReducerSimple.logger.setLevel(loggingLevel)
         
    #--------------------------
    # Logging class methods 
    #----------------
         
    @classmethod
    def logDebug(cls, msg):
        DimReducerSimple.logger.debug(msg)

    @classmethod
    def logWarn(cls, msg):
        DimReducerSimple.logger.warn(msg)

    @classmethod
    def logInfo(cls, msg):
        DimReducerSimple.logger.info(msg)

    @classmethod
    def logErr(cls, msg):
        DimReducerSimple.logger.error(msg)
        
        
    # ------------------------------ Class DimReducerByYear ------------------------        
          
class DimReducerByYear(DimReducerSimple):
    '''
    In contrast to instances of DimReducerSimple, DimReducerByYear
    computes a separate PCA for each academic year from 2000 on.
    
    Output is as one file per year to a given directory, optionally 
    starting with a given prefix. The files will be called 
    <prefix>pca_vecs.txt 
    '''
    
    #--------------------------
    # Constructor DimReducerByYear 
    #----------------
    
    def __init__(self, 
                 vectors_file,
                 num_components = 2,
                 loggingLevel=logging.INFO,
                 logFile=None
                 ):
        '''
        Constructor. Prepares data, then runs the PCA.
                
        @param vectors_file: vectors created by gensim.word2vec()
        @type vectors_file: str
        @param pca_outfile: destination of the lower-dim vectors. Default: stdout
        @type pca_outfile: str
        @param num_components: target number of dimensions
        @type num_components: int
        @param loggingLevel: see Python logging module
        @type loggingLevel:
        @param logFile: log destination. Default, stdout 
        @type logFile: str
        '''
        
        # Have superclass initialize logging,
        # read the vectors, and create dataframe 
        # course_df.
        super().__init__(vectors_file,
                         num_components = 2,
                         loggingLevel=logging.INFO,
                         logFile=None
                         )
        
        
    #--------------------------
    # run 
    #----------------
        
    def run(self, pca_outdir, sqlite_file):
        
        self.init_sqlite3_db(sqlite_file)
        # Get sequence of strm_year-years: 100, 101, 102, ...
        # Method strm_sequence() returns quarters: 1002, 1004,...
        # Divide each of these by 10, using the array element-by-element
        # division of numpy arrays:
          
        for strm_year in (np.array(self.strm_sequence()) / 10).astype(int):
            
            self.logInfo("Computing pca for %s." % strm_year)
            courses_during_strm = self.courses_in_strm_year(strm_year)
            
            # Do PCA only on courses offered during strm_year:
            course_vectors_strm_df = self.course_df[self.course_df.index.isin(courses_during_strm)]
            
            course_vectors_strm_df_standardized = self.standardize_data(course_vectors_strm_df)
            reduced_dim_df = self.compute_pca(course_vectors_strm_df_standardized, self.num_components)
            
            # Create a file name for this strm_year's PCA:
            outfile = os.path.join(pca_outdir, 'pca_vectors_%s' % strm_year)
            self.output_as_csv(reduced_dim_df, outfile)
            self.explained_variance_ratios[strm_year] = self.pca.explained_variance_ratio_
             
            self.logInfo("Done pca for %s. Explained variance ratio: %s" % (strm_year, self.pca.explained_variance_ratio_))
            
        
    #--------------------------
    # strm_sequence 
    #----------------
        
    def strm_sequence(self):
        '''
        Return an iterable with all strm values
        in order from 2000 to 2018.
        '''
        years = range(100,120)
        # Create [[1002,1004,1006,1008], [1012,1014,1016,1018], ...]]:
        strms = [[10 * year_strm + 2, 10 * year_strm + 4, 10 * year_strm + 6, 10 * year_strm + 8] for year_strm in years]
        # Flatten into a single list; you can do that with a
        # nested list comprehension, but I don't like those:
        res = []
        for four_quarters_arr in strms:
            res.extend(four_quarters_arr)
        return res
        
    # ---------------------------- Class Variance ---------------------
    
class Variance(object):
    
    def __init__(self, feature_vectors):
        self._total_variance = None
        self._feature_variances = {}
        self._feature_vectors = feature_vectors
        self.compute_variances()
    
    def total_variance(self):
        return self._total_variance
    
    def feature_variance(self, feature_name):
        return self._feature_variances[feature_name]
        
    def feature_variance_ratio(self, feature_name):
        return self._feature_variances[feature_name]/self._total_variance
        
    def compute_variances(self):
        variances = self._feature_vectors.var(axis=0)
        for (feature_name) in self._feature_vectors.columns:
            self._feature_variances[feature_name] = variances[feature_name]
            
        self._total_variance = variances.sum()
        
            
         
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
    parser.add_argument('-o', '--outlocation',
                        help='where to write the output; default: stdout',
                        default=None
                        ),
    parser.add_argument('-d', '--dimensions',
                        help='number of PCA dimensions to reduce to; default: 2',
                        default=2
                        )
    parser.add_argument('-y', '--years',
                        help='if this switch is present, create separate PCAs for each year; outlocation must then be a directory',
                        action='store_true'
                        )
    parser.add_argument('vectors',
                        help='file with vector embeddings.'
                        )

    args = parser.parse_args();
    
    #reducer = DimReducerSimple('/Users/paepcke/EclipseWorkspacesNew/pathways/src/data/Word2vec/winning_model.model')
    if args.years:
        if not os.path.isdir(args.outlocation):
            print("Outlocation must be a directory; nothing done.")
            sys.exit()
        reducer = DimReducerByYear(args.vectors,
                                   num_components=args.dimensions,
                                   logFile=args.errLogFile
                                   )
        # Do one PCA per strm, writing to directory outlocation:
        reducer.run(args.outlocation, COURSE_INFO_PATH)

    else:
        reducer = DimReducerSimple(args.vectors,
                                   num_components=args.dimensions,
                                   logFile=args.errLogFile
                                   )
        reducer.run(args.outlocation)

    reducer.logInfo("Explained variance ratio(s): %s" % reducer.explained_variance_ratios)

            