'''
Created on Nov 15, 2018

@author: paepcke
'''

from sklearn import preprocessing
from sklearn.decomposition.pca import PCA

import pandas as pd
from pathways.courseSim import CourseVectorsCreator
import matplotlib.pyplot as plt


class PcaDebugger(object):
    '''
    classdocs
    '''


    def __init__(self, model_file):
        '''
        Constructor
        '''
        course_vector_creator = CourseVectorsCreator()
        model = course_vector_creator.load_word2vec_model(model_file)
        vecs2d = self.compute_pca(model)
        self.scatterplot(vecs2d)
        print('Done')
        
    def compute_pca(self, model):
        X = model.wv.vectors
        #self.plot_matrix(X, 'Before')
        scaler = preprocessing.StandardScaler()
        X_scaled = scaler.fit_transform(X)
        #self.plot_matrix(X_scaled, 'After')
        
        pca = PCA(n_components=2)
        principalComponents = pca.fit_transform(X_scaled)
                    
        print(pca.explained_variance_ratio_)
        self.scatterplot(principalComponents)
        
        return principalComponents
     
     
    def plot_matrix(self, vectors, label):
        plt.bar(range(len(vectors)), vectors[:,0])
        plt.xlabel(label)
        plt.show()
        
    def scatterplot(self, x_y):
        plt.scatter(x_y[:,0], x_y[:,1])
        plt.show()
        
        
if __name__ == '__main__':
    debugger = PcaDebugger('/Users/paepcke/EclipseWorkspacesNew/pathways/src/data/Word2vec/all_since2000_vec128_win10.model')        
        