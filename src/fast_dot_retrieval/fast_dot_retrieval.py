'''
Created on Sep 19, 2018

@author: paepcke
'''

from math import floor, ceil

class DotManager(object):
    '''
    Store and retrieve scatter dot objects from an arbitrary 2D plane.
    Emphasis on speed. Partitions plane into an nxn grid, overlaid on
    the plane. Objects may be any Python item, not just matplotlib.PathCollection
    objects. The dimension 'n' is settable during instantiation.
    
    Each cell contains a dict mapping an x/y coordinate to the list of
    dot objects that are present at that x/y. Adding a dot
    at position x/y finds the cell that encloses x/y, and updates the
    dict that resides there.
    '''
    #--------------------------------
    # __init__
    #------------------

    def __init__(self, lower_left, upper_right, grid_edge_len=10):
        '''
        Constructor
        '''
        x_min = lower_left[0]
        x_max = upper_right[0]
        y_min = lower_left[1]
        y_max = upper_right[1]
        
        x_range = x_max - x_min
        y_range = y_max - y_min
        x_steps = ceil(x_range/float(grid_edge_len)) 
        y_steps = ceil(y_range/float(grid_edge_len)) 
        
        self.x_partitions = [x for x in range(floor(x_min), ceil(x_max)+x_steps+1, x_steps)]
        self.y_partitions = [y for y in range(floor(y_min), ceil(y_max)+y_steps+1, y_steps)]
        
        num_rows = len(self.y_partitions)
        num_cols =  len(self.x_partitions)
        self.dot_dict_matrix = [[{}] * (num_cols+1) for _i in range(num_rows+1)]

    #--------------------------------
    # get_dots 
    #------------------
        
    def get_dots(self, x, y):
        
        # Find x/y-positions in dot matrix:
        
        x_in_dot_matrix, y_in_dot_matrix = self.find_dot_matrix_indices(x, y)
        try:
            dot_dict = self.dot_dict_matrix[x_in_dot_matrix][y_in_dot_matrix]
        except IndexError as e:
            print('Error: %s' % repr(e))
            
        return dot_dict.get((x,y), None)
    
    #--------------------------------
    # add_dot 
    #------------------
      
    def add_dot(self, x, y, dot_obj):
        
        # Find x/y-positions in dot matrix:
        
        x_in_dot_matrix, y_in_dot_matrix = self.find_dot_matrix_indices(x, y)
        dot_dict = self.dot_dict_matrix[x_in_dot_matrix][y_in_dot_matrix]
        if dot_dict.get((x,y), None) is None:
            dot_dict[(x,y)] = [dot_obj]
        else:
            dot_dict[(x,y)].append(dot_obj)
            
    #--------------------------------
    # find_dot_matrix_indices 
    #------------------

    def find_dot_matrix_indices(self, data_x, data_y):
        
        x_in_dot_matrix = self.x_partitions.index((next(x_coord for x_coord in self.x_partitions if x_coord >= data_x)))
        y_in_dot_matrix = self.y_partitions.index((next(y_coord for y_coord in self.y_partitions if y_coord >= data_y)))
        return (x_in_dot_matrix, y_in_dot_matrix)
