'''
Created on Aug 13, 2018

@author: paepcke
'''
from pathways.course_tsne_visualization import vector_creator
from pathways.course_vector_creation import CourseVectorsCreator


class Vec2DendrogramMaker(object):
    '''
    classdocs
    '''


    def __init__(self, course2vec_model_file):
        '''
        Constructor
        '''
        vector_creator = CourseVectorsCreator()
        course2vec_model = vector_creator.load_word2vec_model(course2vec_model_file)
        
        
if __name__ == '__main__':
    Vec2DendrogramMaker('/users/Paepcke/Project/Pathways/Data/Course2VecData/course2vecModelWin10.model')
            