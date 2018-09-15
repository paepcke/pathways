'''
Created on Sep 13, 2018

@author: paepcke
'''
import os

from pathways.course_tsne_visualization import TSNECourseVisualizer, ShowOrSave
from pathways.course_vector_creation import CourseVectorsCreator


class VisualClusterQualityExplorer(object):
    '''
    classdocs
    '''
    DRAFT_MODE = False
    
    def __init__(self, model_filename_list):
        '''
        Constructor
        '''
        vector_creator = CourseVectorsCreator()
        data_dir = os.path.join(os.path.dirname(__file__), '../data/Word2vec')
        
        for model_filename in model_filename_list:
            filename_root = model_filename.split('.')[0]
            cluster_img_filename = os.path.join(data_dir, 'TsneTestImages/' + filename_root)
            cluster_img_filename += '_draft.png' if VisualClusterQualityExplorer.DRAFT_MODE else '_fullqual.png'
            vector_creator.load_word2vec_model(os.path.join(data_dir, model_filename))
            self.visualizer = TSNECourseVisualizer(vector_creator,
                                                   draft_mode=VisualClusterQualityExplorer.DRAFT_MODE,
                                                   show_save=ShowOrSave.SAVE,
                                                   save_filename=cluster_img_filename,
                                                   called_from_main=False)
    
if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '../data/Word2vec')
    model_files = [filename for filename in os.listdir(data_dir) if filename.endswith('.model')]
    explorer = VisualClusterQualityExplorer(model_files)