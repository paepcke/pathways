'''
Created on Aug 31, 2018

@author: paepcke
'''

import matplotlib.pyplot as plt
import matplotlib.animation

class Plotter(object):

    def __init__(self, xy_pairs=None):

        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('X Axis', size = 12)
        self.ax.set_ylabel('Y Axis', size = 12)
        self.ax.axis([0,1,0,1])
        
        # Just three points:
        self.x_vals, self.y_vals = [0.1,0.4,0.6], [0.4, 0.6,0.9]
        # Colors red, green, and blue:
        self.colors = [[1,0,0],[0,1,0],[0,0,1]]
                
        self.scatter = self.ax.scatter(self.x_vals,self.y_vals, c=self.colors, vmin=0,vmax=1)
        
        # Start out fully visible; without this init, get_alpha() will
        # return None the first time:
        self.scatter.set_alpha(1.0)
        
        # Currently on the way down to less visibility:
        self.dimming = True
        
        self.ani = matplotlib.animation.FuncAnimation(self.fig, 
                                                      self.update,
                                                      blit=True,
                                                      interval=50)  # msecs between calls to update()
    
        plt.show()    

    def update(self, frame_number):
        '''
        Called for each animation iteration.
        
        @param frame_number: iteration number of calls to this method, or next
            frame item, if FuncAnimation() was called with parameter 'frames='
            being an iterable.
        @type frame_number: any
        '''
        curr_alpha = self.scatter.get_alpha()
        if self.dimming:
            if curr_alpha >= 0.04:
                # Dim further
                #self.scatter.set_alpha(curr_alpha * 0.96)
                self.scatter.set_alpha(curr_alpha * 0.8)
            else: 
                # Reached near-transparency: start growing visibility again:
                self.dimming = False
        else:
            # Currently growing in visibility:
            next_alpha = curr_alpha * 1.2
            if next_alpha <= 1.0:
                self.scatter.set_alpha(next_alpha)
            else:
                # Reached max visibility, start dimming again:
                self.scatter.set_alpha(1.0)
                self.dimming = True
        
        if frame_number > 200:
            self.ani._stop()        
        return [self.scatter]
        
if __name__ == '__main__':
    Plotter()
            