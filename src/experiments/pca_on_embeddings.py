'''
Created on Oct 30, 2018

@author: paepcke
'''

import argparse
from enum import Enum
import logging
import os
import re
import sqlite3
import sys

from gensim.models.deprecated.word2vec import Word2Vec
from gensim.models.keyedvectors import KeyedVectors
from sklearn import preprocessing
from sklearn.decomposition import KernelPCA
from sklearn.decomposition import PCA
from sklearn.manifold.t_sne import TSNE
from sklearn.cluster import KMeans

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
COURSE_AVAILABILITY_PATH = '/Users/paepcke/EclipseWorkspacesNew/pathways/src/data/courseAvailability.sqlite3'
COURSE_INFO_PATH         = '/Users/paepcke/EclipseWorkspacesNew/pathways/src/data/fullEnrollmentHistory.sqlite3'

class CourseVectorFilter(Enum):
    STEM_ONLY = 'stem_only'
    NO_STEM   = 'no_stem'
    SUBJECTS  = 'subjects'
    
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
                 pca_type=None,
                 tsne=False,
                 course_filters=[],
                 subjects=[],
                 years=[],
                 loggingLevel=logging.INFO,
                 logFile=None,
                 ):
        '''
        Constructor. Prepares data. This step needs to be done
        by instances of this superclass, as well as instances
        olf the DimReducerByYear subclass.
        
        If filter is non-None it is expected to be a member
        of the enum CourseVectorFilter. It therefore controls whether
        only stem, non-stem or otherwise characterized courses
        are to be included.
        
        Initializes self.course_df, and self.num_components
                
        @param vectors_file: vectors created by gensim.word2vec()
        @type vectors_file: str
        @param num_components: target number of dimensions
        @type num_components: int
        @param pca_type: if not None, KernelPCA is performed instead
            of PCA. The argument must then be one of 
            'linear','poly', 'rbf', 'sigmoid', or 'cosine'
        @type pca_type: {None | str}
        @param tsne: if True, t_sne is performed instead of pca.
            pca_type is ignored if tsne is True
        @type tsne: bool
        @param course_filters: one enum member of CourseVectorFilter, or list of them
        @type course_filter: {CourseVectorFilter  | [CourseVectorFilter]}
        @param subjects: individual (course) subject, or list of subject to
            use for filtering: only courses of given subjects will
            be used in transformations/analyses. Only used if course_filters
            is CourseVectorFilter.SUBJECTS. 
        @type subjects: {str | [str]}
        @param years: year(s) to which courses should be limited. Used in 
            conjunction with filter CourseVectorFilter.YEAR
        @type years: { int | [int] }
        @param loggingLevel: see Python logging module
        @type loggingLevel:
        @param logFile: log destination. Default, stdout 
        @type logFile: str
        '''

        self.setupLogging(loggingLevel, logFile)
        
        self.pca_type = pca_type
        self.tsne     = tsne
        
        if type(course_filters) == CourseVectorFilter:
            self.filters = [course_filters]
        else:
            self.filters = course_filters
            
        if type(subjects) == str:
            self.subjects = [subjects]
        else:
            self.subjects = subjects
        
        if type(years) == int:
            self.years = [years]
        else:
            self.years= years
        
        # Dict whose values will hold Sqlite connectors,
        # if needed:
        self.sqlite_conns = {}
        
        # Prepare record of explained variance for each strm:
        self.explained_variance_ratios = {}
        
        # Get dataframe with index (i.e. row labels) being the course names,
        # and columns being feature values:
        self.course_df = self.load_vectors(vectors_file)
        
        # Number of components will be passed into a scikit learn method,
        # which expects an int; so make sure:
        self.num_components = int(num_components)
        
        # If there are majors or emplids in the 
        # sentences, remove them for the PCA:
                            
        self.course_df = self.extract_numerics(self.course_df, majors)
              
        
    #--------------------------
    # run 
    #----------------
    
    def run(self, pca_outfile):
        '''
        Assigns the PCA-reduced df to self.principalDf.
        This df will include a column with the course names,
        and miscellaneous columns for each course.
        Writes principalDf to file.
        
        @param pca_outfile: destination of the reduced-dimension vectors
        @type pca_outfile: str
        '''
        
        self.init_sqlite3_dbs(COURSE_INFO_PATH, 'course_info_db')
        
        # Filter out unwanted courses:
        for course_filter in self.filters:
            if course_filter == CourseVectorFilter.NO_STEM or \
               course_filter == CourseVectorFilter.STEM_ONLY:
                self.course_df = self.vector_filter_limit_by_stem(self.course_df, years=self.years, only=course_filter)
            elif course_filter == CourseVectorFilter.SUBJECTS:
                self.vector_filter_limit_by_subject(self.course_df, self.subjects, years=self.years)
        
        self.principalDf = self.generate_low_dim_vecs(self.course_df, self.num_components)
        self.output_as_csv(self.principalDf, pca_outfile)
        self.explained_variance_ratios = self.goodness_of_fit(self.transformer)

    #--------------------------
    # goodness_of_fit 
    #----------------
    
    def goodness_of_fit(self, transformer):
        
        if isinstance(transformer, PCA):
            return {'allYears' : '%s' % transformer.explained_variance_ratio_}
        else:
            return {}
     
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
		
		    Index      PCA_0    PCA_1   ... CourseName     Subject    AcadGroup    CrseDescrShort      CrseDescrLong
		  <crseName>       ...                           ...                      ...
		  
		Stores the PCA_x names in self.pca_column_names.
        
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
        
        if self.tsne:
            self.logInfo("Computing t_sne...")
            principalDf = self.compute_tsne(x_matrix, num_components)
            self.logInfo("Done computing t_sne.")
        elif self.pca_type is None:
            self.logInfo("Computing PCA...")
            principalDf = self.compute_pca(x_matrix, num_components)
            self.logInfo("Done computing PCA.")
        else:
            self.logInfo("Computing KernelPCA...")
            principalDf = self.compute_kpca(x_matrix, num_components)
            self.logInfo("Done computing KernelPCA.")

        # Add the course names as row names back in:
        principalDf.index = course_df.index
        
        # Right now, principalDf only has vector columns.
        # Before we add more, save the PCA_x col names:
        self.pca_column_names = principalDf.columns 
        
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
            # Turn vectors into the rows of a dataframe:
            vectors_df = self.vecs_to_dataframe(vectors)
             
        else:
            try:
                vectors = KeyedVectors.load(vectors_path)
                # Turn vectors into the rows of a dataframe:
                vectors_df = self.vecs_to_dataframe(vectors)
            except Exception:
                # Content of the vectors_path file might not be
                # pickled pandas.KeyedVectors, but a regular
                # .csv file:
                vectors_df = self.load_csv_to_df(vectors_path, vector_col_name_root='PCA_')
                # Must return just the numeric vectors, no other 
                # columns.
                vectors_df = vectors_df[[col_name for col_name in vectors_df.columns.get_values()
                                         if col_name.startswith('PCA_')]] 
        return vectors_df
         
    #--------------------------
    # load_csv_to_df 
    #----------------
    
    def load_csv_to_df(self, 
                       infile, 
                       vector_col_names=None, 
                       vector_col_name_root=None, 
                       index_col_name=None):
        '''
        Very specialized method: file is expected to contain
        a column header, and rows of vectors, possibly including
        other data. Like this:
        
               'PCA_1','PCA_2','PCA_3','CourseName','Ranking',...
                0.4,     0.1,    0.7,     'CS106A',     3,  
                0.6,     0.9,    0.1,     'MATH52',     2,
                        ...
                        
        The vector_col_names must list the columns that comprise the
        vectors. If it is None, then vector_col_name_root must have the
        prefix of columns that contain vectors. In the above example,
        that is 'PCA_'. If vector_col_names is provided, the vector_col_name_root
        is ignored. 
        
        The index_col_name must be the name of the column whose
        values will be used as the index (i.e. row labels) of the result
        dataframe. If None, the col name is assumed to be the first
        non-vector column.             
        
        @param infile: location of file to import
        @type infile: str
        @param vector_col_names: list of names for columns that comprise the vectors.
        @type vector_col_names: {None | [str]}
        @param vector_col_name_root: Prefix of column names that contain
            vector values. Ignored if vector_col_names is provided.
        @type vector_col_name_root: {None | str}
        @param index_col_name: name of column whose values are to be the dataframe index
        @type index_col_name: str
        @return: a dataframe with the index being values in the index_col_name column,
            and data being the vectors. All other information is discarded.
        '''
        # Unfortunately, pd.read_csv() wants to know
        # the *numeric* index of the column that has the
        # index values (i.e. the row labels). For generality
        # we ask callers for the column name instead. Read
        # the first line, and find the index of the given 
        # index_col_name:
        csv_header_info_dict = self.parse_vectors_header(infile, 
                                                         vector_col_names=vector_col_names, 
                                                         vector_col_name_root=vector_col_name_root, 
                                                         index_col_name=index_col_name)
        vector_col_names = csv_header_info_dict['vector_cols']
        col_name_of_index_names = csv_header_info_dict['col_name']
        
        course_df = pd.read_csv(infile, 
                    			header=0,    # Column names in line 0
                    			index_col=csv_header_info_dict['index_values_col_num'],
                    			usecols=vector_col_names.append(pd.Index([col_name_of_index_names]))
                                )
        return course_df

    #--------------------------
    # vector_filter_limit_by_stem 
    #----------------

    def vector_filter_limit_by_stem(self, vector_df, years=[], only=CourseVectorFilter.STEM_ONLY):
        '''
        Given a dataframe with index of course names, return
        another df with only courses that are either stem or
        non-stem, depending on argument 'only'. That arg should
        be one of 'stem' and 'non-stem'. 
        
        If strm_year is not none, only courses from that year are included. 
         
        @param vector_df: df of vectors with index being course names
        @type vector_df: pandas.Dataframe
        @param years: year(s) to which returned courses should be limited.
            If empty list, all years are returned.
        @type years: int
        @param only: Either CourseVectorFilter.STEM_ONLY, or CourseVectorFilter.NO_STEM
        @type only: CourseVectorFilter
        @return: dataframe limited to either stem, or non-stem courses.
        @rtype: pandas.Dataframe
        '''
        
        # Get the courses that are or are not stem, depending
        # on the value of 'only':
        only_value = 1 if only == CourseVectorFilter.STEM_ONLY else 0
        query = '''SELECT distinct course_code
                     FROM FullEnrollmentHistory
                    WHERE is_stem_course = %s''' % only_value
        
        if len(years) > 0:
            # Make string with years out of list of years
            years_str = ','.join([str(yr) for yr in years])
            query += ''' and year in (%s)''' % years_str

        self.logInfo("Finding courses that are %s STEM..." % ('not' if only == CourseVectorFilter.NO_STEM else ''))
        res = self.sqlite_conns['course_info_db'].execute(query)
        self.logInfo("Done finding courses that are %s STEM." % ('not' if only == CourseVectorFilter.NO_STEM else ''))
        
        # Get an array of dicts. Each dict holds the
        # data from one row. Since we only asked for
        # the course_code, each dict will only have
        #   rows[x]['course_code'] == 'CHEM130' or such:
        
        self.logInfo('Retrieving result of STEM/NO-STEM query...')
        rows = res.fetchall()
        self.logInfo('Done retrieving result of STEM/NO-STEM query.')
        
        # Get list of courses:
        courses = [row_dict['course_code'] for row_dict in rows]

        # Subset the course vectors. Start by getting at 
        # mask [True, False, False,...] for which rows to keep
        # or discard:
        
        self.logInfo('Filtering courses, potentially keeping %s...' % len(courses))
        row_selection_mask = vector_df.index.isin(courses)     
        res_df = vector_df.loc[row_selection_mask,:]
        self.logInfo('Done filtering courses, potentially keeping %s...' % len(courses))
        
        self.logInfo('Final number of courses retained: %s' % len(res_df))
        return res_df
        
    #--------------------------
    # vector_filter_limit_by_subject 
    #----------------
        
    def vector_filter_limit_by_subject(self, vector_df, subjects, years=[]):
        '''
        Given a dataframe with index of course names, return
        another df with only courses that are have one of the 
        given subjects. 
        
        If strm_year is not none, only courses from that year are included. 
         
        @param vector_df: df of vectors with index being course names
        @type vector_df: pandas.Dataframe
        @param subjects: Single subject, or list of subjects, such as CS,
            AA, EE, etc. I.e. non-numeric part of course catalog.
        @type subjects: {str | [str]}
        @param years: year(s) to which returned courses should be limited.
            If None, all years are returned.
        @type years: {int | [int]}
        @return: dataframe limited to either stem, or non-stem courses.
        @rtype: pandas.Dataframe
        '''
        
        # Turn individual subjects into list:
        if type(subjects) == str:
            subjects = [str]
            
        # Create a string from the subjects list.
        # Must look like this: "'CS','AA'":
        subjects_str = "'" + "','".join(subjects) + "'"
        
        query = '''SELECT distinct course_code
                     FROM FullEnrollmentHistory
                    WHERE subject in (%s)''' % subjects_str
        
        if len(years) > 0:
            # Create string from years as per 'subjects' above:
            years_str = ','.join([str(yr) for yr in years])
            query += ''' and year in (%s)''' % years_str

        self.logInfo("Finding courses with subject(s) %s..." % subjects_str)
        res = self.sqlite_conns['course_info_db'].execute(query)
        self.logInfo("Done finding courses with subject(s) %s." % subjects_str)
        
        # Get an array of dicts. Each dict holds the
        # data from one row. Since we only asked for
        # the course_code, each dict will only have
        #   rows[x]['course_code'] == 'CHEM130' or such:
        
        self.logInfo('Retrieving result of subject(s) query...')
        rows = res.fetchall()
        self.logInfo('Done retrieving result of subject(s) query.')
        
        # Get list of courses:
        courses = [row_dict['course_code'] for row_dict in rows]

        # Subset the course vectors. Start by getting at 
        # mask [True, False, False,...] for which rows to keep
        # or discard:
        
        self.logInfo('Filtering courses, potentially keeping %s...' % len(courses))
        row_selection_mask = vector_df.index.isin(courses)     
        res_df = vector_df.loc[row_selection_mask,:]
        self.logInfo('Done filtering courses, potentially keeping %s...' % len(courses))
        
        self.logInfo('Final number of courses retained: %s' % len(res_df))
        return res_df
        
    #--------------------------
    # parse_vectors_header 
    #----------------
    
    def parse_vectors_header(self, 
                             csv_file,
                             vector_col_names=None,
                             vector_col_name_root=None,
                             index_col_name=None):
        res_dict = {}
        with open(csv_file, 'r') as fd:
            line = fd.readline().strip()
            try:
                all_col_names = line.split(',')
                
                # Figure out names of vector columns:
                if vector_col_names is not None:
                    res_dict['vector_cols'] = vector_col_names
                elif vector_col_name_root is not None:
                    res_dict['vector_cols'] = [col_name for col_name in all_col_names if col_name.startswith(vector_col_name_root)]
                else:
                    res_dict['vector_cols'] = None

                # Name of column that holds the row labels-to-be:
                if index_col_name is None:
                    # Without the name given, assume it's the 
                    # first column after the vectors:
                    if res_dict['vector_cols'] is None:
                        raise(ValueError("Cannot determine name of column with row labels."))
                    else:
                        # Use name of first column after all the vector columns:
                        res_dict['col_name'] = all_col_names[len(res_dict['vector_cols'])]
                else:
                    res_dict['col_name'] = index_col_name
                
                res_dict['index_values_col_num'] = all_col_names.index(res_dict['col_name'])
                
            except ValueError:
                print("Could not find column '%s' with values for df index." % index_col_name)
                sys.exit()
        return res_dict
        
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
        
        The instance var self.transformer will contain the PCA instance.
        So callers can examine, for example: self.transformer.explained_variance_ratios
        
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
        
        self.transformer = PCA(n_components=num_components)
        principalComponents = self.transformer.fit_transform(x)
        col_names = ['PCA_'+str(col_num) for col_num in range(num_components)]
        principalDf = pd.DataFrame(data = principalComponents, columns=col_names)
        if row_lables is not None:
            principalDf.index = row_lables
            
        return principalDf  
    
    #--------------------------
    # compute_kpca 
    #----------------
    
    def compute_kpca(self, x, num_components=2):
        '''
        Given a numpy matrix of row vectors, or a dataframe,
        return the result of a Kernel PCA. The number of components
        in the mapping is controlled by num_components. 
        
        If a dataframe is returned, with column names 
        PCA_1, PCA_2, ... If a df was passed in, the resulting
        df will have the same row labels (i.e. index as the
        passed-in arg). 
        
        The instance var self.transformer will contain the KernelPCA instance.
        So callers can examine, for example: self.transformer.explained_variance_ratios
        
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
        
        self.transformer   = KernelPCA(num_components, kernel='linear')
        x_transformed = self.transformer.fit_transform(x) 
        
        col_names = ['PCA_'+str(col_num) for col_num in range(num_components)]
        principalDf = pd.DataFrame(data = x_transformed, columns=col_names)
        if row_lables is not None:
            principalDf.index = row_lables
            
        return principalDf  
    
    #--------------------------
    # compute_tsne
    #----------------
    
    def compute_tsne(self, x, num_components=2):
        '''
        Given a numpy matrix of row vectors, or a dataframe,
        return the result of a tsne computation. The number of components
        in the mapping is controlled by num_components. 
        
        If a dataframe is returned, with column names 
        PCA_1, PCA_2, ... If a df was passed in, the resulting
        df will have the same row labels (i.e. index as the
        passed-in arg). 
        
        The instance var self.transformer will contain the TSNE instance.
        So callers can examine, for example: self.transformer.explained_variance_ratios
        
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
        
        self.transformer   = TSNE(num_components)
        x_transformed = self.transformer.fit_transform(x) 
        
        col_names = ['PCA_'+str(col_num) for col_num in range(num_components)]
        principalDf = pd.DataFrame(data = x_transformed, columns=col_names)
        if row_lables is not None:
            principalDf.index = row_lables
            
        return principalDf  
    
    #--------------------------
    # compute_kmeans 
    #----------------
    
    def compute_kmeans(self, x, num_clusters=8):
         
        kmeans = KMeans(n_clusters=num_clusters, random_state=0)
        x_cluster_space = kmeans.fit_transform(x)
        print(x_cluster_space)
        
    
    # ------------------------- Database Access ----------------    

    #--------------------------
    # init_sqlite3_dbs 
    #----------------

    def init_sqlite3_dbs(self, sqlite_file_list, db_names):
        '''
        Creates one Sqlite3 connection for each of the given .sqlite files.
        Sets the connections' row_factory to sqlite3.Row, so that
        results will be tuples that also function as dicts, with
        keys are column names.
        
        Arg db_names will be used as keys in the result dict. That
        dict's values will be cursors for respective dbs.
                
        @param sqlite_file: database file
        @type sqlite_file: str
        '''
        
        if type(sqlite_file_list) != list:
            sqlite_file_list = [sqlite_file_list]
        if type(db_names) != list:
            db_names = [db_names]
        
        # Get [(1,filename1),(2,filename2),(3,filename3)...]:
        db_names_and_files = [(db_names[indx], filename) for indx,filename in enumerate(sqlite_file_list)]
        for (conn_key_name, sqlite_filename) in db_names_and_files:
            self.sqlite_conns[conn_key_name] = sqlite3.connect(sqlite_filename)
            self.sqlite_conns[conn_key_name].row_factory = sqlite3.Row

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
        
        res = self.course_availability_db.execute('''SELECT course_code
                                		               FROM CourseAvailability LEFT JOIN AllCourses
                                		                 ON course_key = id   
                                		              WHERE strm_year = %s;''' % strm_year
                              )
        rows = res.fetchall()
        courses = [row['course_code'] for row in rows]
                              
        return courses
    
    #--------------------------
    # course_information 
    #----------------
    
    def course_information(self, course_code, strm):
        '''
        Given a course name, such as 'CS106A', return a
        dict with all course information provided in table
        FullEnrollmentHistory:
        
		   Emplid     
		   major
		   strm
		   quarter
		   year
		   course_code
		   crse_id int(11),
		   subject
		   offered_by_grp
		   acad_grp
		   course_enrollment
		   short_descr
		   long_descr
		   subschool
		   first_major
		   second_major
		   is_stem_course
		   is_stem_major
        
        @param course_code: name of course
        @type course_code: str
        @param strm: quarter of the course offering
        @type strm: int
        @return: dict with the course info; col names are the keys.
        @rtype: {str : str}
        '''
        
        res = self.course_info_db.execute('''SELECT *
                                		       FROM FullEnrollmentHistory
                                		      WHERE course_code = %s and
                                		            strm = %s''' % (course_code, strm)
                                    )
        res_dict = res.fetchone()
        return res_dict
    
    
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
        
    def run(self, pca_outdir, course_availability_file, course_info_file, db_names):
        
        self.init_sqlite3_dbs([course_availability_file, course_info_file], 
                              db_names
                              )
        
        # Filter out unwanted courses:
        if filter == CourseVectorFilter.STEM_ONLY:
            self.course_df = self.vector_filter_limit_by_stem(self.course_df, only=filter)
        
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
            self.explained_variance_ratios[strm_year] = self.transformer.explained_variance_ratio_
             
            self.logInfo("Done pca for %s. Explained variance ratio: %s" % (strm_year, self.transformer.explained_variance_ratio_))
            
        
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
    parser.add_argument('-k', '--kpca',
                        help="if this switch is present, use kernel PCA with the argument being kernel to use.",
                        choices=['linear','poly', 'rbf', 'sigmoid', 'cosine'],
                        default=None
                        )
    parser.add_argument('-t', '--tsne',
                        help="if this switch is present, compute t_sne; kpca is ignored in this case.",
                        action='store_true',
                        default=False
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
        reducer.run(args.outlocation, 
                    COURSE_AVAILABILITY_PATH,
                    COURSE_INFO_PATH,
                    ['course_availability_db', 'course_info_db']
                    )

    elif args.tsne:
        # If tsne, and vectors are higher dim than 50, need first to 
        # reduce to ~50 via PCA dimensions, as recommended by sklearn:
        vectors = KeyedVectors.load(args.vectors)
        
        if vectors.vector_size > 50:
            reducer = DimReducerSimple(args.vectors,
                                       num_components=50,
                                       logFile=args.errLogFile,
                                       )
            reducer.run('/tmp/_intermediate_vectors50.csv')
            
            # Read the reduced-dim file back int a dataframe,
            # Dropping all columns other than the vectors:
            reducer.load_csv_to_df('/tmp/_intermediate_vectors50.csv',
                                   reducer.pca_column_names,   # Names of just the vector columns
                                   'CourseName'                # Name of column that holds course names
                                   )
                
            # Now do the tsne:
            reducer = DimReducerSimple('/tmp/_intermediate_vectors50.csv',
                                       num_components=2,
                                       tsne=True,
                                       logFile=args.errLogFile
                                       )
            tsne_vectors = reducer.run(args.outlocation)    
        
        
    else:
        reducer = DimReducerSimple(args.vectors,
                                   #num_components=args.dimensions,
                                   num_components=2,
                                   pca_type=args.kpca,
                                   tsne=args.tsne,
                                   #course_filters=CourseVectorFilter.STEM_ONLY, 
                                   #course_filters=CourseVectorFilter.NO_STEM,
                                   course_filters=CourseVectorFilter.SUBJECTS,
                                   years=2015,
                                   subjects='CS',
                                   logFile=args.errLogFile
                                   )
        reducer.run(args.outlocation)

    reducer.logInfo("Explained variance ratio(s): %s" % reducer.explained_variance_ratios)

            