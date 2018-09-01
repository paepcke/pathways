'''
Created on Aug 29, 2018

@author: paepcke
'''

import os

from gensim.models.keyedvectors import Word2VecKeyedVectors

class CourseSimAnalytics(Word2VecKeyedVectors):
    '''
	Given word vectors, perform analytics. You can do:
		  >>> word_vectors = api.load("glove-wiki-gigaword-100")  # load pre-trained word-vectors from gensim-data
		  >>> result = word_vectors.most_similar(positive=['woman', 'king'], negative=['man'])
		     queen: 0.7699
		  >>>
		  >>> result = word_vectors.most_similar_cosmul(positive=['woman', 'king'], negative=['man'])
		     queen: 0.8965
		  >>>
		  >>> print(word_vectors.doesnt_match("breakfast cereal dinner lunch".split()))
		     cereal
		  >>>
		  >>> similarity = word_vectors.similarity('woman', 'man')
		  >>> similarity > 0.8
		      True
		  >>>
		  >>> result = word_vectors.similar_by_word("cat")
		      dog: 0.8798
		  >>>
		  >>> sentence_obama = 'Obama speaks to the media in Illinois'.lower().split()
		  >>> sentence_president = 'The president greets the press in Chicago'.lower().split()
		  >>>
		  >>> similarity = word_vectors.wmdistance(sentence_obama, sentence_president)
		      3.4893
		  >>>
		  >>> distance = word_vectors.distance("media", "media")
		      0.0
		  >>>
		  >>> sim = word_vectors.n_similarity(['sushi', 'shop'], ['japanese', 'restaurant'])
		      0.7067
		  >>>
		  >>> vector = word_vectors['computer']  # numpy vector of a word
		  >>> vector.shape
		      (100,)
		  >>>
		  >>> vector = word_vectors.wv.word_vec('office', use_norm=True)
		  >>> vector.shape
		      (100,)
    
    '''
    
    #--------------------------
    # __init__
    #----------------
    
    def __init__(self, keyed_vectors_filename):
        '''
        Constructor. The expected word vectors are the model.kv 
        word-vectors-only of gensim's course2vec. They are called
        KeyedVectors, and can be exported from the full course2vec
        model. The KeyedVectors class has many similarity computation
        methods.
        
        @param word_vectors: all vectors 
        @type word_vectors: [gensim]models.keyedvectors
        '''
        self.vectors_obj = super().load(keyed_vectors_filename)

        # Account for some changes in gensim that would lead to 
        # unknown var errors:

        self.vectors     = self.vectors_obj.vectors
        self.vocab       = self.vectors_obj.vocab
        self.index2word  = self.vectors_obj.index2word
        
        # The filename for cross listings:
        curr_dir = os.path.dirname(__file__)
        self.cross_lists_filename = os.path.join(curr_dir, '../data/Word2vec/cross_registered_courses.csv')
        
    
    #--------------------------
    # related
    #----------------
        
    def related(self, from_word, to_word, as_word):
        # from - to = x - as
        # x = from - to + as
        return self.most_similar(positive=[from_word, as_word], negative=[to_word])
    
         
if __name__ == '__main__':
    # keyed_vec_filename = os.path.join(os.path.dirname(__file__), '../data/course2vecModelWin10.vectors')
    keyed_vec_filename = os.path.join(os.path.dirname(__file__), '../data/Word2vec/all_since_2000_plus_majors_veclen150_win10.vectors')
    simAn = CourseSimAnalytics(keyed_vec_filename)
    # res = simAn.most_similar_cosmul(positive=['CS106A'])          # ENGR70 and very varied others
    # res = simAn.most_similar_cosmul(positive=['CS140'])           
                                                                    # ('CS143', 0.9375626444816589), Compilers 
                                                                    # ('CS149', 0.9368202090263367), Parallel Computing
                                                                    # ('EE282', 0.8906934857368469),... Computer Systems Architecture
    # res = simAn.doesnt_match(['CS140','CS143','CS145','CS399'])   # CS399
    # res = simAn.doesnt_match(['CS140','CS143','CS145','CS240'])   # CS145
    # res = simAn.doesnt_match(['CS157','PHIL156A', 'PHIL267A', 'PHIL357', 'PHIL150', 'PHIL 170'])  
                                                                    # CS: Intro to logic, 
                                                                    # PHIL: Research Seminar Logic&Cognition
                                                                    # PHIL: Philosopy of Biology
                                                                    # PHIL: Mathematical Logic     <----- wrong PHIL150
                                                                    # PHIL: Ethical Theory
    # res = simAn.doesnt_match(['CS157','PHIL156A', 'PHIL267A', 'PHIL357', 'PHIL150', 'PHIL 170', 'PHIL74A'])  
                                                                    # CS: Intro to logic, 
                                                                    # PHIL: Research Seminar Logic&Cognition
                                                                    # PHIL: Philosopy of Biology
                                                                    # PHIL: Mathematical Logic     <----- wrong PHIL150
                                                                    # PHIL: Ethical Theory
                                                                    # PHIL: Ethics in Human Life
    # res = simAn.doesnt_match(['CLASSICS26N','CLASSICS101L', 'CLASSICS58','CLASSICS81'])   
                                                                    # Roman Empire: Its Grandeur and Fall
                                                                    # Advanced Latin               <------ Correct
                                                                    # Egypt in the Age of Heresy
                                                                    # Ancient Empires
    # res = simAn.doesnt_match(['CLASSICS26N','CLASSICS101L', 'CLASSICS58','CLASSICS81', 'CLASSICS262'])   
                                                                    # Roman Empire: Its Grandeur and Fall
                                                                    # Advanced Latin               <------ Correct
                                                                    # Egypt in the Age of Heresy
                                                                    # Ancient Empires
                                                                    # Sex and the Early Church
                                                                    # Aristophanes: Comedy, and Democracy
    # res = simAn.doesnt_match(['CLASSICS26N','CLASSICS101L', 'CLASSICS58','CLASSICS81', 'CLASSICS262', 'CLASSICS318'])   
                                                                    # Roman Empire: Its Grandeur and Fall <------ Wrong?
                                                                    # Advanced Latin               
                                                                    # Egypt in the Age of Heresy
                                                                    # Ancient Empires
                                                                    # Sex and the Early Church
                                                                    # Aristophanes: Comedy, and Democracy                                               
                                                                                                                   
    # res = simAn.similar_by_word('CS140')                            # Same or close to most_similar_cosmul
    
    # Cosine similarity between Means of vectors in each set:
    # Two systems students compared: 0.91831756
    #res = simAn.n_similarity(['CS140', 'CS144', 'CS240', 'CS245', 'EE282', 'EE282', 'CS244', 'CS255', 'CS249A', 'CS276', 'CS251', 'CS316'], # sys1
    #                         ['CS144', 'EE282', 'CS245', 'CS348B', 'CS243', 'CS341', 'CS343', 'CS316', 'CS249A', 'CS246'])                  # sys2
    # Systems1 with Info Management: 0.8029297
    #res = simAn.n_similarity(['CS224N','CS276','CS229', 'CS346', 'CS243', 'CS144', 'CS229T', 'CS240', 'CS228T', 'CS224U'],                  # Info
    #                         ['CS140', 'CS144', 'CS240', 'CS245', 'EE282', 'EE282', 'CS244', 'CS255', 'CS249A', 'CS276', 'CS251', 'CS316']) # Sys1
    # System 2 with Info Management: 0.8670983
    #res = simAn.n_similarity(['CS224N','CS276','CS229', 'CS346', 'CS243', 'CS144', 'CS229T', 'CS240', 'CS228T', 'CS224U'],                   # Info
    #                         ['CS144', 'EE282', 'CS245', 'CS348B', 'CS243', 'CS341', 'CS343', 'CS316', 'CS249A', 'CS246'])                   # sys2
    #                         
     
    #res = simAn.related('CS140', 'CS101', 'MUSIC20A')         # Works badly MUSIC160 instead of MUSIC1
    
    #print(str(res))
    
    
    