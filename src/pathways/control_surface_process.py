'''
Created on Aug 21, 2018

@author: paepcke
'''

import functools
import os
from queue import Empty
import sys

from PySide2.QtCore import QFile, QTimer
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QWidget, QVBoxLayout, QCheckBox, QFileDialog

#from PySide2.QtWidgets import qApp 
#from PySide2.QtCore import Qt

from pathways.common_classes import Message
from PyQt5.Qt import QMessageBox

class ControlSurface(object):
    '''
    The control surface PySide2 UI is entirely created, and 
    its events serviced here.
    '''

    # Where to put saved displays:
    DEFAULT_CACHE_FILE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../cache'))

    # Number of courses to list when user clicks
    # on a clump of stacked marks:
    MAX_NUM_COURSES_TO_LIST = 1000

    # Time between checking instructions queue from parent process:
    QUEUE_CHECK_INTERVAL = 200 # milliseconds

    def __init__(self, ui_file, out_queue=None, in_queue=None):
        super().__init__()
    
        self.debug = True
    
        self.ui_file = ui_file
        self.out_queue = out_queue    
        self.in_queue = in_queue
        
        self.chkBox_names_acad_groups = ['EngrChk', 'GsbChk', 'HandSChk', 'MedChk', 
                            'UgChk', 'EarthChk', 'EducChk', 'VpueChk',
                            'LawChk', 'AthleticsChk', 'OthersChk'
                            ]
        self.chkBox_name_to_acac_grp = {
            'EngrChk': 'ENGR', 
            'GsbChk': 'GSB', 
            'HandSChk': 'H&S', 
            'MedChk': 'MED', 
            'UgChk': 'UG', 
            'EarthChk': 'EARTH', 
            'EducChk': 'EDUC', 
            'VpueChk': 'VPUE',
            'LawChk': 'LAW',
            'AthleticsChk': 'ATH',
            'OthersChk': 'OTHERS'
            }

        # Not currently synchronizing widgets with 
        # viz state:
        
        self.synchronizing = False

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
        
        whereIsButton = self.control_surface_widget.widget.whereIsButton
        whereIsButton.clicked.connect(self.slot_where_is_btn)
        
        top10Button = self.control_surface_widget.widget.top10Button
        top10Button.clicked.connect(self.slot_top10_btn)
        
        enrollHistoryButton = self.control_surface_widget.widget.enrollmentButton
        enrollHistoryButton.clicked.connect(self.slot_enrollment_history_btn)
        
        recompButton = self.control_surface_widget.widget.recomputeButton
        recompButton.clicked.connect(self.slot_recompute_btn)
        
        quitBtn = self.control_surface_widget.widget.quitBtn
        quitBtn.clicked.connect(self.slot_quit_btn)
        
        clrBtn = self.control_surface_widget.widget.clrBoardButton
        clrBtn.clicked.connect(self.clear_msg_board)
        
        saveBtn = self.control_surface_widget.widget.saveVizButton
        saveBtn.clicked.connect(self.slot_save_viz_btn)

        restoreBtn = self.control_surface_widget.widget.loadVizButton
        restoreBtn.clicked.connect(self.slot_restore_viz_btn)
        
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

    def slot_where_is_btn(self):
        course_name = self.canonical_course_name()
        self.write_to_main('where_is', course_name)
                    
    def slot_top10_btn(self):
        course_name = self.canonical_course_name()
        self.write_to_main('top10', course_name)

    def slot_enrollment_history_btn(self):
        course_name = self.canonical_course_name()
        self.write_to_main('enrollment_history', course_name)
    
    def slot_recompute_btn(self):
        if self.user_confirms('Recomputation can take up to 20 minutes', 'Do it?'):
            self.write_to_main('recompute', None)
        
    def slot_save_viz_btn(self):
        if self.user_confirms('If file for this configuration already exists:', 
                              'Overwrite?',
                              defaultButton='Cancel'):        
            self.write_to_main('save_viz', None)
        
    def slot_restore_viz_btn(self):
        # Get file name from user:
        filename, _ = QFileDialog.getOpenFileName(
                            caption='Select viz file...',
                            dir=ControlSurface.DEFAULT_CACHE_FILE_DIR,
                            filter='*.pickle'
                            )
        
        self.write_to_main('restore_viz', filename)
        
        
    def slot_quit_btn(self):
        if self.user_confirms('Quitting removes the plot for good', 
                              '(Alternative: cancel, Save Visualization; then quit.)',
                              defaultButton='Cancel'):
            self.write_to_main('stop', None)
            if self.out_queue is not None:
                self.out_queue.close()
            self.app.exit()
    
    def slot_draft_mode(self, chkBox_name, new_state):
        
        # If setting checkbox in response to a sync request
        # from viz, rather than because user clicked on checkbox,
        # Ignore:
        if self.synchronizing:
            return
        
        if self.chk_box_obj_dict['draftModeChk'].isChecked(): 
            self.write_to_main('set_draft_mode', True)
        else:
            self.write_to_main('set_draft_mode', False)
        
    def slot_acad_grp_chk(self, chkBox_name, new_state):
        '''
        Make a list of academic group names whose checkboxes
        are checked.
        
        @param chkBox_name: name of checkbox that was clicked
        @type chkBox_name: string
        @param new_state: New state: checked vs. unchecked
        @type new_state: Qt checkbox state
        '''

        # If setting checkbox in response to a sync request
        # from viz, rather than because user clicked on checkbox,
        # Ignore:
        if self.synchronizing:
            return
        
        # print('ChkBox %s: %s' % (chkBox_name, new_state))
        # Go through all the checkboxes and grab the ones that
        # refer academic groups, and are checked. Then get
        # their names:
        
        active_acad_grps = [self.chkBox_name_to_acac_grp[chkBox_name] 
                            for (chkBox_name, chkBox_obj) in self.chk_box_obj_dict.items()  
                            if chkBox_obj.isChecked() and chkBox_name in self.chkBox_names_acad_groups
                            ]
        
        self.write_to_main('set_acad_grps', active_acad_grps)

    def canonical_course_name(self):
        '''
        Take the content of the course name input field, and ensure
        that it is at least in form a course name that the vector model
        understands: block caps, and no spaces. 
        
        @return: content of course name control surface input field
            block capitalized, and spaces removed.
        @rtype: str
        '''
        course_name_input = self.control_surface_widget.widget.CourseInput
        course_name = course_name_input.text()
        if len(course_name) == 0:
            self.user_info('Enter a course name such as MATH51 in the course name box first.')
            return
        # Canonicalize course name:
        course_name = course_name.upper().replace(' ','')
        return course_name
        
    def check_in_queue(self):
        if self.in_queue is None:
            return
        # Note: can't use the empty() method here, b/c it's 
        # unreliable for multiprocess operation:
        try:
            control_msg = self.in_queue.get(block=False)
            if self.debug:
                print("In to cntrl from main: %s; state: %s" % (control_msg.msg_code, control_msg.state))
            self.handle_msg_from_main(control_msg)
        except Empty:
            pass 
        
    def write_to_main(self, msg_code, state):
        if self.debug:
            if self.out_queue is None:
                print('Would send from control to main: %s, %s' % (msg_code, state))
            else:
                print('Sending from control to main: %s, %s' % (msg_code, state))
        if self.out_queue is not None:
            self.out_queue.put(Message(msg_code, state))
        
    def handle_msg_from_main(self, msg):
        msg_code = msg.msg_code
        if msg_code == 'update_crse_board':
            self.write_to_msg_board(msg.state)
        elif msg_code == 'clear_crse_board':
            self.clear_msg_board()
        elif msg_code == 'update_status':
            self.sync_widgets_to_viz_status(msg.state)
        elif msg_code == 'error':
            self.error_msg(msg.state)
        elif msg_code == 'raise':
            # Being asked to raise our window to the top
            # (above the viz window):
            # main_window_widget = self.control_surface_widget.widget.findChild(QWidget, 'MainWindow')
            # main_window_widget.activateWindow()
            # main_window_widget.raise_()
            pass
            
    def clear_msg_board(self):
        self.crse_board.clear()
        self.refresh_crse_board()
        
    def sync_widgets_to_viz_status(self, state_summary):
        '''
        Given a control-surface-relevant summary of the visualization,
        update the surface to reflect that state. Used when a new
        viz is brought up, maybe from a saved file. Set the control
        surface to what's actually going on.
        
        @param state_summary: summary of visualzation state
        @type state_summary: dict
        '''
        
        # Prevent changes we make to the control surface in response to
        # the viz process' sync request from triggering messages back to
        # the viz. Normally, when user changes a checkbox state with the mouse,
        # the resulting signal will trigger a msg to the viz:
         
        try:
            self.synchronizing = True
            self.chk_box_obj_dict['draftModeChk'].setChecked(state_summary['draft_mode'])
            self.uncheck_all_acad_groups()
            
            # Get list of acad groups to set checkmarks for.
            # List is like ['ENGR', 'MED',...]
            acad_grps_to_set = state_summary['active_acad_grps']
            
            for chk_box_name in self.chkBox_name_to_acac_grp.keys():
                acad_grp_name = self.chkBox_name_to_acac_grp[chk_box_name]
                if acad_grp_name in acad_grps_to_set:
                    self.chk_box_obj_dict[chk_box_name].setChecked(True)
        finally:
            self.synchronizing = False
            
                                                         
    def uncheck_all_acad_groups(self):
        for chkBox_name in self.chkBox_names_acad_groups:
            self.chk_box_obj_dict[chkBox_name].setChecked(False)
        
        
    def write_to_msg_board(self, text, ):
        curr_txt = self.crse_board.toHtml()
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
                curr_txt += '<br>' + text
        
        self.crse_board.setHtml(curr_txt)
        self.refresh_crse_board()
        
    def refresh_crse_board(self):
        
        # Only way to clear the board AND update the display.
        # Widget redraw via update() doesn't work:
        self.crse_board.hide()
        self.crse_board.show()
        
        
    def error_msg(self, err_msg):
        self.user_info('<font color="red">' + err_msg + '</font>')
        
    def user_info(self, text):
        '''
        Raise dialog with explanation, and an OK button. Returns
        after user clicked OK button
        
        @param text: explanatory text
        @type text: str
        '''
        msg_box = QMessageBox()
        msg_box.setText(text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setDefaultButton(QMessageBox.Ok)
        msg_box.exec_()
        
    def user_confirms(self, statement, question=None, defaultButton='Ok'):
        '''
        Get user confirmation before an action. Options will
        be Cancel and OK, with OK being the default button.
        Msg box will be the statement in large, and the question
        in smaller. As in:
        
                 Recomputation may take up to 20 minutes
                      Go ahead?
        
        @param statement: text shown in large: the fact
        @type statement: str
        @param question: optional question/subtext/explanation
        @type question: str
        @param defaultButton: which button is to be the default
        @param defaultButton: {'Cancel' | 'Ok'}
        @return: user feedback: True for Yes, False for No
        @rtype: bool
        '''
        msg_box = QMessageBox()
        msg_box.setText(statement)
        if question is not None:
            msg_box.setInformativeText(question)
        msg_box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        if defaultButton == 'Ok':
            msg_box.setDefaultButton(QMessageBox.Ok)
        else:
            msg_box.setDefaultButton(QMessageBox.Cancel)
        return msg_box.exec_() == QMessageBox.Ok
        
        
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
