'''
Created on Sep 19, 2018

@author: paepcke
'''

from matplotlib.collections import PathCollection
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

    def __init__(self, lower_left, upper_right, picker_radius, grid_edge_len=10):
        '''
        Constructor
        '''
        
        self.picker_radius = picker_radius
        
        x_min = lower_left[0]
        x_max = upper_right[0]
        y_min = lower_left[1]
        y_max = upper_right[1]
        
        # We'll keep track of lowest/highest
        # values of x and y as we add points.
        # That's to enable initial checks when
        # coordinate is given in get_dots() to 
        # see whether there could possibly be a
        # dot:
        
        self.x_min_observed = self.x_max_observed = None
        self.y_min_observed = self.y_max_observed = None
        
        
        # Create the grid of cell-size range/numGrids
        # for x and y:
        x_range = x_max - x_min
        y_range = y_max - y_min
        x_steps = ceil(x_range/float(grid_edge_len)) 
        y_steps = ceil(y_range/float(grid_edge_len)) 
        
        # Lists of data-space coordinates that are the 
        # cell boundaries for x and y respectively
        self.x_partitions = [x for x in range(floor(x_min), ceil(x_max)+x_steps+1, x_steps)]
        self.y_partitions = [y for y in range(floor(y_min), ceil(y_max)+y_steps+1, y_steps)]
        
        num_rows = len(self.y_partitions)
        num_cols =  len(self.x_partitions)

        # Keep track of rendered and pseudo artist obs:        
        self.all_rendered_artists = []
        self.all_pseudo_artists = []
        
        # For each rendered obj, keep track of associated
        # pseudo artists:
        
        self.stacked_dots_dict = {}
        
        # Create the 2D array with an empty dict in each cell.
        # Any of the pythonic ways surprise you by having cells
        # unexpectedly share data structures within them. So don't
        # use this construct:
        #    self.dot_dict_matrix = [[{}] * (num_cols+1) for _i in range(num_rows+1)]
        # Instead do it the pedestrian way:
        
        self.dot_dict_matrix = []
        for _rows in range(num_rows+1):
            columns = []
            for _cols in range(num_cols+1):
                columns.append({})
            self.dot_dict_matrix.append(columns)


    #--------------------------------
    # get_dots 
    #------------------
        
    def get_dots(self, x, y):
        '''
        Return a list of dot artists that already exist 
        at x,y. Return None if no artists have been added
        in that area yet. The match is fuzzy in that any
        dot added in the area defined by x+- picker_radius
        and y+- picker_radius qualify as 'being at x/y'.
        
        A rendered artist is guaranteed to be first in
        the list.
        
        @param x: abscissa in data space
        @type x: float
        @param y: ordinal in data space
        @type y: float
        @return: list of dot artist objects or None
        @rtype: [{PathCollection | PseudoArtist}]
        '''
        
        # Find x/y-positions in dot matrix
        # Is the requested coord outside all the points
        # that have been added so far?
        
        # If no points were added so far, there surely
        # is nothing at the given coords, or anywhere else:
        if self.x_min_observed is None:
            return None
        
        if x < self.x_min_observed or x > self.x_max_observed or\
           y < self.y_min_observed or y > self.y_max_observed:
            return None
        
        x_in_dot_matrix, y_in_dot_matrix = self.find_dot_matrix_indices(x, y)
        try:
            dot_dict = self.dot_dict_matrix[x_in_dot_matrix][y_in_dot_matrix]
        except IndexError as e:
            print('Error: %s' % repr(e))
            
        fuzzy_match = self.match_fuzzily(dot_dict, x, y)
        if fuzzy_match is None:
            return None
        else:
            return dot_dict[fuzzy_match]
    
    #--------------------------------
    # match_fuzzily 
    #------------------
    
    def match_fuzzily(self, dot_dict, x, y):
        '''
        In the given dict of the form {(x_pos,y_pos) : [dot_objects]}, find
        the (x_pos,y_pos) that are within picker_radius of x,y.
        Return that tuple, or None. 
        
        @param dot_dict: dict of position tuples to list of dot objects
        @type dot_dict: {(float,float) : [{PathCollection | PseudoArtist}]
        @param x: x position for which to perform fuzzy search
        @type x: float
        @param y: y position for which to perform fuzzy search
        @type y: float
        '''
        
        for dot_x,dot_y in dot_dict.keys():
            low_x_bound  = dot_x - self.picker_radius
            high_x_bound = dot_x + self.picker_radius
            low_y_bound  = dot_y - self.picker_radius
            high_y_bound = dot_y + self.picker_radius
            if (low_x_bound <= x) and (high_x_bound >= x) and\
               (low_y_bound <= y) and (high_y_bound >= y):
                return (dot_x, dot_y)
        return None
        
    
    #--------------------------------
    # add_dot 
    #------------------
      
    def add_dot(self, x, y, dot_artist_obj):
        '''
        Add one dot to the dot matrix. Updates the
        lowest/highest x and y coordinates of all added
        dots. 
        
        Dot artists are guaranteed to stay in the order
        in which they were added.
        
        Updates lists of rendered and pseudo artists.
        Updates dict mapping rendered artists to their
        associated pseudo artists. I.e. the unrendered 
        artists that would be underneath.
        
        @param x: abscissa in data space
        @type x: float
        @param y: ordinal in data space
        @type y: float
        @param dot_artist_obj: the artist to add
        @type dot_artist_obj: {PathCollection | PseudoArtist}
        '''
        
        # Find x/y-positions in the dot matrix grid:
        
        x_in_dot_matrix, y_in_dot_matrix = self.find_dot_matrix_indices(x, y)

        # Get dict that holds the dots in that grid: 
        dot_dict = self.dot_dict_matrix[x_in_dot_matrix][y_in_dot_matrix]
        
        fuzzy_match = self.match_fuzzily(dot_dict, x, y)
        if fuzzy_match is None:
            # No dot at the given x,y
            dot_dict[(x,y)] = [dot_artist_obj]
        else:
            dot_dict[fuzzy_match].append(dot_artist_obj)
            
        # Update the lowest/highest seen dot coordinate
        # for x/y:
        self.x_min_observed = x if self.x_min_observed is None else min(self.x_min_observed, x)
        self.x_max_observed = x if self.x_max_observed is None else max(self.x_max_observed, x)
            
        self.y_min_observed = y if self.y_min_observed is None else min(self.y_min_observed, y)
        self.y_max_observed = y if self.y_max_observed is None else max(self.y_max_observed, y)
        
        # Update lists of rendered/pseudo artists:
        
        if isinstance(dot_artist_obj, PathCollection):
            self.all_rendered_artists.append(dot_artist_obj)
            # First (and only) rendered artist at this precise
            # place. Init the self.stacked_dots_dict entry
            # for that rendered artists:
            self.stacked_dots_dict[dot_artist_obj] = []
        else:
            self.all_pseudo_artists.append(dot_artist_obj)
            # Get the already existing rendered artist
            # at this spot. It's the first in the list
            # of dots at xy:
            rendered_artist_at_xy = dot_dict[fuzzy_match][0]
            self.stacked_dots_dict[rendered_artist_at_xy].append(dot_artist_obj)

    #--------------------------------
    # pseudo_artists_with_rendered 
    #------------------

    def pseudo_artists_with_rendered (self, rendered_artist):
        '''
        Given a rendered artist object, return a list
        of pseudo artists that lie underneath at the
        same xy.
        
        If given an object that does not exist in this
        manager, throw an error
        
        @param rendered_artist: a rendered artist obj 
        @type rendered_artist: PathCollection
        @return: possibly empty list of pseudo artists
        @rtype: [PseudoArtist]
        @raise ValueError: error when rendered_object was never added to 
            this manager.
        '''
        try:
            return self.stacked_dots_dict[rendered_artist]
        except KeyError:
            raise ValueError('Unknown rendered artist: %s' % rendered_artist)
        
             
    #--------------------------------
    # num_artists 
    #------------------
    
    def num_artists(self):
        '''
        Return:
           1 number of rendered dots (i.e. the PathCollection objs)
           2 number of pseudo dots (i.e. the PseudoArtist obs hiding underneath)
           3 largest number of dots in one spot, incl. rendered and pseudo
           4 total number of dots
        
        Number 3 is the 'largest family'.
        
        @return: triplet: number of rendered, number of pseudo artists, 
            and their sum
        @rtype: (int,int,int)
        '''
        num_rendered   = len(self.all_rendered_artists)
        num_pseudo     = len(self.all_pseudo_artists)
        total_artists  = num_rendered + num_pseudo
        # The '1 + ...' is to count the rendered dot:
        largest_family = 1 + max([len(pseudos) for pseudos in self.stacked_dots_dict.values()])
        return (num_rendered, num_pseudo, largest_family, total_artists)
    
    #--------------------------------
    # stats 
    #------------------
    
    def stats(self):
        '''
        Returns a 2-tuple: number of dots actually rendered
        by matplotlib, and the number of pseudo artists.
        
        @return: number of rendered and non-rendered artists so far
        @rtype: (int, int)
        '''
        
        # Flatten the matrix 2d array into 1d:
        # (Not very readable, but oh so pythonic):
        dicts_array = [grid_col for rows in self.dot_dict_matrix for grid_col in rows]
        
        num_rendered_artists = 0 
        num_pseudo_artists = 0
        for grid_dict in dicts_array:
            for artists_in_one_spot in grid_dict.values():
                for artist in artists_in_one_spot:
                    if isinstance(artist, PathCollection):
                        num_rendered_artists += 1
                    else:
                        num_pseudo_artists += 1
        return (num_rendered_artists, num_pseudo_artists)
        
        
    #--------------------------------
    # find_dot_matrix_indices 
    #------------------

    def find_dot_matrix_indices(self, data_x, data_y):
        
        x_in_dot_matrix = self.x_partitions.index((next(x_coord for x_coord in self.x_partitions if x_coord >= data_x)))
        y_in_dot_matrix = self.y_partitions.index((next(y_coord for y_coord in self.y_partitions if y_coord >= data_y)))
        return (x_in_dot_matrix, y_in_dot_matrix)
