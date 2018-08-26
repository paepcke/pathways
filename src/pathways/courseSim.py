'''
Created on Aug 19, 2018

@author: paepcke
'''
from multiprocessing import Process, Queue
import os
from queue import Empty  # The regular queue's empty exception
from time import sleep

from pathways.control_surface_process import ControlSurface
from pathways.course_tsne_visualization import TSNECourseVisualizer
from pathways.course_vector_creation import CourseVectorsCreator
from test.support import multiprocessing
from pathways.common_classes import Message

class TsneCourseExplorer(object):
    '''
    Main thread
    '''
    QUEUE_LISTEN_TIME = 0.2 # seconds
    
    def __init__(self):
        '''
        '''
        
        self.debug = True
        
        data_dir = os.path.join(os.path.dirname(__file__), '../data/')
        ui_dir   = os.path.join(os.path.dirname(__file__), '../qtui/')
        ui_file  = os.path.join(ui_dir, 'courseTsne.ui')
         
        self.control_surface_from_queue   = Queue()
        self.control_surface_to_queue   = Queue()
        control_surface_process = Process(target=ControlSurface, 
                                          args=(ui_file, 
                                                self.control_surface_from_queue,
                                                self.control_surface_to_queue
                                                )
                                          )
        control_surface_process.name = 'tsne_control_surface'
        control_surface_process.start()

        self.tsne_viz_to_queue = Queue()
        self.tsne_viz_from_queue = Queue()
        # Since we'll run the TSNE viz with a separate control interface,
        # we tell the visualizer not to maintain its own course display board: 
        tsne_standalone = False 
        
        vector_creator = CourseVectorsCreator() 
        vector_creator.load_word2vec_model(os.path.join(data_dir, 'course2vecModelWin10.model'))
 
        tsne_process = Process(target=TSNECourseVisualizer, 
                               args=(vector_creator,
                                     tsne_standalone,
                                     self.tsne_viz_to_queue,
                                     self.tsne_viz_from_queue
                                     )
                               )
        tsne_process.start()

        # Await ready-signal from viz:
        msg = self.tsne_viz_from_queue.get(block=True)
        if msg.msg_code != 'ready':
            raise ValueError("Was expecting 'ready' message from viz process.")
        
        # Raise the control surface, b/c it gets buried by the viz:
        self.send_to_control(msg_code='raise')
        
        self.keep_going = True
        try:
            while self.keep_going:
                try:
                    control_msg = self.control_surface_from_queue.get(block=False)
                    self.handle_msg_from_control(control_msg)
                except Empty:
                    pass
    
                try:
                    tsne_msg = self.tsne_viz_from_queue.get(block=False)
                    self.handle_msg_from_tse(tsne_msg)                
                except Empty:
                    pass
                # Delay before checking queues again:
                sleep(0.01)
        except Exception as e:
            print("Left main control loop: %s." % repr(e))
        
        # Wait for control surface to stop
        # in response to the Stop button, or window closure:
        control_surface_process.join()
        
        # Wait for the Tsne viz thread to stop:
        tsne_process.join()

    def handle_msg_from_control(self, msg):
        print("In main: Msg from control: %s, %s" % (msg.msg_code, msg.state))
        msg_code = msg.msg_code
        if msg_code == 'stop':
            self.keep_going = False
            self.tsne_viz_to_queue.put('stop')
        else:
            if self.debug:
                print('Sending from main to tsne: %s, %s' % (msg.msg_code, msg.state))
            
            self.tsne_viz_to_queue.put(msg)
    
    def handle_msg_from_tse(self, msg):
        # If it's a 'ready' message, that's from a recomputation
        # request. Ignore it:
        if msg.msg_code == 'ready':
            return
        # Just forward to the control surface:
        self.send_to_control(msg)
        if self.debug:
            print("In main: Msg from Tsne viz: %s; %s" % (msg.msg_code, msg.state))
    
    def send_to_control(self, msg=None, msg_code=None, state=None):
        if msg is not None:
            self.control_surface_to_queue.put(msg)
        else:
            self.control_surface_to_queue.put(Message(msg_code, state))
    
if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    TsneCourseExplorer()
#     #tsne_similarity_explorer = TsneCourseSimExplorer()
    #sys.exit(tsne_similarity_explorer.app.exec_())
