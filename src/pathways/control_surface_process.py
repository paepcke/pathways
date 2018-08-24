'''
Created on Aug 21, 2018

@author: paepcke
'''

import functools
import os
import sys

from PySide2.QtCore import QFile, QTimer
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QWidget, QVBoxLayout, QCheckBox

from queue import Empty

from pathways.common_classes import Message


class ControlSurface(object):
    '''
    The control surface PySide2 UI is entirely created, and 
    its events serviced here.
    '''

    # Number of courses to list when user clicks
    # on a clump of stacked marks:
    MAX_NUM_COURSES_TO_LIST = 15

    # Time between checking instructions queue from parent process:
    QUEUE_CHECK_INTERVAL = 200 # milliseconds

    def __init__(self, ui_file, out_queue=None, in_queue=None):
        super().__init__()
    
        self.ui_file = ui_file
        self.out_queue = out_queue    
        self.in_queue = in_queue            
        
        self.chkBox_names_acad_groups = ['EngrChk', 'GsbChk', 'HandSChk', 'MedChk', 
                            'UgChk', 'EarthChk', 'EducChk', 'VpueChk',
                            'LawChk', 'OthersChk'
                            ]

        self.app = QApplication()
        self.control_surface_widget = ContainerWidget(self.ui_file)
        
        # Convenience pointer to the course display board:
        self.crse_board = self.control_surface_widget.widget.infoDisplay       

        self.connect_signals()         
        self.control_surface_widget.show()

        # Timer that has us check the in-queue for commands:
        # Create a new timer object as a child of the main widget. That way
        # we will be able to to PySidey things from the timer service
        # routine:

        self.timer = QTimer(self.control_surface_widget)
        self.timer.timeout.connect(self.check_in_queue)
        self.timer.start(ControlSurface.QUEUE_CHECK_INTERVAL)
        
        sys.exit(self.app.exec_())
        
    def connect_signals(self):
        recompButton = self.control_surface_widget.widget.recomputeButton
        recompButton.clicked.connect(self.slot_recompute_btn)
        
        quitBtn = self.control_surface_widget.widget.quitBtn
        quitBtn.clicked.connect(self.slot_quit_btn)
        
        clrBtn = self.control_surface_widget.widget.clrBoardButton
        clrBtn.clicked.connect(self.clear_msg_board)
        
        # Remember the checkbox objects for easy reference:
        self.chk_box_obj_dict = {}
        
        for chkBox_name in self.chkBox_names_acad_groups:
            chkBox_obj = self.control_surface_widget.widget.findChild(QCheckBox, chkBox_name)
            self.connect_chk_box(chkBox_obj, self.slot_acad_grp_chk)
        
        # The draft mode checkbox:
        draft_chk_box_obj = self.control_surface_widget.widget.findChild(QCheckBox, 'draftModeChk')
        self.connect_chk_box(draft_chk_box_obj, self.slot_draft_mode)
        
        
    def connect_chk_box(self, chkBoxObj, slot_func):
        '''
        Link signals from chkBoxObj to method slot_func. But
        modify the called function to expect the chkBox's name.
        Slots for checkboxes should therefore expect two args:
        a checkbox name, and the new state.
        
        @param chkBoxObj:
        @type chkBoxObj:
        @param slot_func:
        @type slot_func:
        '''
        chkBox_name = chkBoxObj.objectName()
        # Init the dict as in {'ENGR' : <checked/unchecked state>}:
        self.chk_box_obj_dict[chkBox_name] = chkBoxObj
        
        # Add the name of the check box to the args of the 
        # callback function:
        chkBoxObj.stateChanged.connect(functools.partial(slot_func, chkBox_name))
                    
    def slot_recompute_btn(self):
        if self.out_queue is not None:
            self.out_queue.put(Message('recompute'))
        
        print('In control process: Button pushed')
        
    def slot_quit_btn(self):
        print('In control process: quit button')
        if self.out_queue is not None:
            self.out_queue.put(Message('stop'))
            self.out_queue.close()
        self.app.exit()
    
    def slot_draft_mode(self, chkBox_name, new_state):
        if self.chk_box_obj_dict['draftModeChk'].isChecked(): 
            self.write_to_main('set_draft_mode', True)
        else:
            self.write_to_main('set_draft_mode', False)
        
    def slot_acad_grp_chk(self, chkBox_name, new_state):
        print('ChkBox %s: %s' % (chkBox_name, new_state))
        # Update status of check boxes:
        self.chk_box_obj_dict[chkBox_name] = new_state
        
    def check_in_queue(self):
        if self.in_queue is None:
            return
        # Note: can't use the empty() method here, b/c it's 
        # unreliable for multiprocess operation:
        try:
            control_msg = self.in_queue.get(block=False)
            print("Control msg %s; state: %s" % (control_msg.msg_code, control_msg.state))
            self.handle_msg_from_main(control_msg)
        except Empty:
            pass 
        
    def write_to_main(self, msg_code, state):
        self.out_queue.put(Message(msg_code, state))
        
    def handle_msg_from_main(self, msg):
        if msg.msg_code == 'update_crse_board':
            self.write_to_msg_board(msg.state)
        elif msg.msg_code == 'clear_crse_board':
            self.clear_msg_board()
        elif msg.msg_code == 'raise':
            # Being asked to raise our window to the top
            # (above the viz window):
            #*****self.app.activeWindow().activateWindow()
            pass
            
    def clear_msg_board(self):
        self.crse_board.clear()
        
        
    def write_to_msg_board(self, text):
        curr_txt = self.crse_board.toPlainText()
        # Already have max lines plus a line saying "... more buried under."?
        num_lines = curr_txt.count('\n')
        if num_lines >= ControlSurface.MAX_NUM_COURSES_TO_LIST + 1:
            # Board is full, with elipses already added:
            return
        elif num_lines == ControlSurface.MAX_NUM_COURSES_TO_LIST:
            curr_txt = curr_txt + '\n... more buried under.'
        else:
            # Have room for more courses in the displayed list:
            if len(curr_txt) == 0:
                curr_txt = text
            else:
                curr_txt += '\n' + text
        
        self.crse_board.setText(curr_txt)
        
class ContainerWidget(QWidget):

    def __init__(self, ui_file):
        super().__init__()
        self.loader = QUiLoader()
        q_file = QFile(ui_file)
        q_file.open(QFile.ReadOnly)
        self.widget = self.loader.load(q_file)
        q_file.close()

        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)

    
if __name__ == '__main__':
    ui_dir   = os.path.join(os.path.dirname(__file__), '../qtui/')
    ui_file  = os.path.join(ui_dir, 'courseTsne.ui')
    control_surface = ControlSurface(ui_file)
    sys.exit(control_surface.app.exec_())
