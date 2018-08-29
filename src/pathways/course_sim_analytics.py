'''
Created on Aug 29, 2018

@author: paepcke
'''

import os

from gensim.models.keyedvectors import Word2VecKeyedVectors


class CourseSimAnalytics(Word2VecKeyedVectors):
    '''
    classdocs
    '''
    
    def __init__(self, keyed_vectors_filename):
        '''
        Constructor. The expected word vectors are the model.kv 
        word-vectors-only of gensim's word2vec. They are called
        KeyedVectors, and can be exported from the full word2vec
        model. The KeyedVectors class has many similarity computation
        methods.
        
        @param word_vectors: all vectors 
        @type word_vectors: [gensim]models.keyedvectors
        '''


        self.vectors_obj = super().load(keyed_vectors_filename)
        self.vectors     = self.vectors_obj.vectors
        self.vocab       = self.vectors_obj.vocab
        self.index2word  = self.vectors_obj.index2word
        
        
if __name__ == '__main__':
    keyed_vec_filename = os.path.join(os.path.dirname(__file__), '../data/course2vecModelWin10.vectors')
    simAn = CourseSimAnalytics(keyed_vec_filename)
    # res = simAn.most_similar_cosmul(positive=['CS106A'])
    res = simAn.most_similar_cosmul(positive=['CS140'])
    print(str(res))
    
    
    