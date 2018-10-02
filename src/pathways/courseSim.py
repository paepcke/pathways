'''
Created on Aug 19, 2018

@author: paepcke
'''
import argparse
from multiprocessing import Process, Queue
import multiprocessing
import os
from queue import Empty  # The regular queue's empty exception
import sys
from time import sleep

from pathways.common_classes import Message
from pathways.control_surface_process import ControlSurface
from pathways.course_tsne_visualization import TSNECourseVisualizer
from pathways.course_vector_creation import CourseVectorsCreator


class TsneCourseExplorer(object):
    '''
    Main thread
    '''
    QUEUE_LISTEN_TIME = 0.2 # seconds
    
    def __init__(self,
                 draft_mode=True,
                 vector_file=None):
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

        self.vector_creator = CourseVectorsCreator() 
        if vector_file is None:
            self.vector_creator.load_word2vec_model(os.path.join(data_dir, 'best_modelvec250_win15.model'))
        else:
            self.vector_creator.load_word2vec_model(vector_file)
 
        # Start in draft mode for speedy viz appearance:
        # (standalone <== False is added in the start_tsne_process()
        # method):
        self.start_tsne_process({'draft_mode' : draft_mode})
        
        # Await ready-signal from viz:
        msg = self.tsne_viz_from_queue.get(block=True)
        if msg.msg_code != 'ready':
            raise ValueError("Was expecting 'ready' message from viz process.")
        
        # Raise the control surface, b/c it gets buried by the viz
        # (Doesn't work):
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
        self.tsne_process.join()

    def start_tsne_process(self, kwargs={}):
        self.tsne_viz_to_queue = Queue()
        self.tsne_viz_from_queue = Queue()
        # Since we'll run the TSNE viz with a separate control interface,
        # we tell the visualizer not to maintain its own course display board:
        kwargs['in_queue']   = self.tsne_viz_to_queue
        kwargs['out_queue']  = self.tsne_viz_from_queue
        kwargs['standalone'] = False
        self.tsne_process = Process(target=TSNECourseVisualizer,
                                    args=(self.vector_creator,),
                                    kwargs=kwargs
                                    )
        #***********
        #self.tsne_process.daemon = True
        #***********
        self.tsne_process.start()
        

    def handle_msg_from_control(self, msg):
        print("In main: Msg from control: %s, %s" % (msg.msg_code, msg.state))
        msg_code = msg.msg_code
        if msg_code == 'stop':
            self.tsne_viz_to_queue.put(Message('stop', None))
        else:
            if self.debug:
                print('Sending from main to tsne: %s, %s' % (msg.msg_code, msg.state))
            
            self.tsne_viz_to_queue.put(msg)
    
    def handle_msg_from_tse(self, msg):
        
        if self.debug:
            print("In main: Msg from Tsne viz: %s; %s" % (msg.msg_code, msg.state))
        
        # If it's a 'ready' message, that's from a recomputation
        # request. Ignore it:
        if msg.msg_code == 'ready':
            return
        
        # Does the viz want to restart?
        elif msg.msg_code == 'restart':
            self.tsne_viz_to_queue.put(Message('kill_yourself', None))
            self.tsne_process.terminate()
            self.tsne_process.join()
            # state will be a dict of initialization parms 
            # for the new process:
            self.start_tsne_process(msg.state)
            
        elif msg.msg_code == 'stop':
            self.tsne_process.terminate()
            self.tsne_process.join()
            self.keep_going = False
        else:    
            # Just forward to the control surface:
            self.send_to_control(msg)

    
    def send_to_control(self, msg=None, msg_code=None, state=None):
        if msg is not None:
            self.control_surface_to_queue.put(msg)
        else:
            self.control_surface_to_queue.put(Message(msg_code, state))
    
if __name__ == '__main__':
    curr_dir = os.path.dirname(__file__)
    
    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--file',
                        help='fully qualified path to model file. Default is best model that includes all academic careers.',
                        default=None);
    parser.add_argument('-m', '--draftMode',
                        choices=['true', 'false'],
                        help='whether or not to show model in draft mode, or full quality. Default is full.',
                        default='true');
    
    args = parser.parse_args();
                        
    multiprocessing.set_start_method('spawn')
    TsneCourseExplorer(vector_file=args.file,
                       draft_mode=True if args.draftMode == 'true' else False)
#     #tsne_similarity_explorer = TsneCourseSimExplorer()
    #sys.exit(tsne_similarity_explorer.app.exec_())
