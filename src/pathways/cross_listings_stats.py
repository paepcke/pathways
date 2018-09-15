'''
Created on Sep 12, 2018

@author: paepcke
'''
import os
import numpy as np

from course2vec.word2vec_model_creation import Word2VecModelCreator, Action
    
def print_siblings_stats(cross_ref_files_file_dir):
    '''
    Import the cross registered files .csv file, and print how
    many times courses are cross listed, etc.
    
    @param cross_ref_files_file_dir: location of cross_registered_courses.csv
    @type cross_ref_files_file_dir: str
    '''
    cross_registered_course_filename = os.path.join(cross_ref_files_file_dir, 'cross_registered_courses.csv')
    wordvec_creator = Word2VecModelCreator(action=Action.CROSS_LIST_DICT,
                                           actionFileName=cross_registered_course_filename,
                                           hasHeader=False)
    cross_lists_dict = wordvec_creator.cross_listings
    print('Num of cross list sets: %s' % len(cross_lists_dict.keys()))
    
    # Get average number of cross list group size 
    # i.e. of number of sibling courses:
    cross_list_lengths = []
    for cross_list_set in cross_lists_dict.values():
        # Add 1, b/c key is another sibling
        cross_list_lengths.append(len(cross_list_set) + 1)
    print('Avg number of cross reg siblings: %s' % np.mean(cross_list_lengths))
    print('SD of number of cross reg siblings: %s' % np.std(cross_list_lengths))
    
def verify_model_cross_list_criteria_accuracy(cross_ref_files_file_dir):
    cross_registered_course_filename = os.path.join(cross_ref_files_file_dir, 'cross_registered_courses.csv')
    wordvec_creator = Word2VecModelCreator(action=Action.CROSS_LIST_DICT,
                                           actionFileName=cross_registered_course_filename,
                                           hasHeader=False)
    wordvec_creator.load_word_vectors(os.path.join(cross_ref_files_file_dir,
                                                   'all_since2000_vec200_win10_.vectors'
                                                   ))
    (percent_success, success_probs) = wordvec_creator.verify_model(topn=4, cross_lists_dict=wordvec_creator.cross_listings)
    print("TopN: %s" % )print result; try for higher top-n
******    
    
    
if __name__ == '__main__':
    curr_dir = os.path.dirname(__file__)
    data_dir = os.path.join(curr_dir, '../data/Word2vec/')
    #print_siblings_stats(data_dir)
    verify_model_cross_list_criteria_accuracy(data_dir)
    
