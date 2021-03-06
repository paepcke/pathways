#!/usr/bin/env python
'''
@author: paepcke

NOTE: had to:
   cp /Users/paepcke/anaconda2/envs/pathwaysPy3_7/lib/python3.7/site-packages/MulticoreTSNE/libtsne_multicore.so   \
            src/pathways/multicoretsne/MulticoreTSNE/
after  
   pip3 install MulticoreTSNE
   
in MulticoreTSNE's parent dir  

NOTE: for Eclipse to find PyQt5.sip I had to:
   pushd ~/anaconda3/envs/pathways/lib/python3.7/site-packages/PyQt5-5.13.1-py3.7-macosx-10.7-x86_64.egg/PyQt5/ 
   ln -s ../../PyQt5/sip.so .
'''

import argparse
from collections import OrderedDict
import csv
from enum import Enum
import functools
import itertools
from logging import error as logErr
from logging import info as logInfo
from logging import warning as logWarn
import logging
import math
import os
import pickle
from queue import Empty  # The regular queue's empty exception
import re
import sys
from threading import Timer
import time

from matplotlib import artist
import matplotlib
from matplotlib.path import Path

from fast_dot_retrieval.fast_dot_retrieval import DotManager
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from multicoretsne import  MulticoreTSNE as TSNE
import numpy as np
from color_constants import colors
from common_classes import Message
from course_sim_analytics import CourseSimAnalytics
from course_vector_creation import CourseVectorsCreator
from difficulty_plotter import DifficultyPlotter
from enrollment_plotter import EnrollmentPlotter


# Backend spec must be before pyplot import!
matplotlib.use('Qt5Agg')

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

class RestartRequest(Exception):
    def __init__(self, restart_instruction):
        super().__init__(restart_instruction)

class ShowOrSave(Enum):
    SHOW = 1
    SAVE = 2

class DotSizeFactor(object):
    '''
	Factors by which to increase a rendered
	dot for each pseudo artist at the same xy.
	For clarity the factor needs to be modified
	depending on how many total dots are on the
	plot. The more total number of dots, the more
	modest the per-underlying-dot enlargement 
	factor must be.
    '''
    
    LOW_LIMIT        = 500
    MEDIUM_LIMIT     = 5000
    LARGE_LIMIT      = 10000
    
    LOW_FACTOR       = 1.14
    MEDIUM_FACTOR    = 1.2
    LARGE_FACTOR     = 1.1
    HUGE_FACTOR      = 1.001

    MAX_DOT_SIZE     = 300 # Max size of any one dot
    EDGE_WIDTH       = 0.5  # Width of black edge around 
                            # dots whose size was capped.
    
    num_dots         = 0    # Remember num dots we are called with.
    
    @classmethod
    def dot_growth_factor(cls, num_dots_in_fig):

        # Retain for reference
        cls.num_dots = num_dots_in_fig
        
        if num_dots_in_fig <= cls.LOW_LIMIT:
            return cls.LOW_FACTOR
        elif num_dots_in_fig <= cls.MEDIUM_LIMIT:
            return cls.MEDIUM_FACTOR
        elif num_dots_in_fig <= cls.LARGE_LIMIT:
            return cls.LARGE_FACTOR
        else:
            return cls.HUGE_FACTOR
        

class TSNECourseVisualizer(object):
    '''
    classdocs
    '''
    
    # Set to 'newplot' when __main__ should exit, rather than
    # creating another instance for a new plot
    status = 'running'

    # Number of pixels around a mouse event
    # location to consider as part of the area
    # that is intended to be indicated by a 
    # user's mouse cursor placement:
    
    PICK_RADIUS = 1
    
    # Where to put saved displays:
    DEFAULT_CACHE_FILE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../cache'))
    
    # Perplexity used when creating a TSNE model:
    DEFAULT_PERPLEXITY = 60
    
    # If not specified otherwise, run in draft mode for speed:
    DEFAULT_DRAFT_MODE = True
    
    # Time between checking instructions queue from parent process:
    QUEUE_CHECK_INTERVAL = 0.2 # seconds
    
    # Number of courses to list when user clicks
    # on a clump of stacked marks:
    MAX_NUM_COURSES_TO_LIST = 15
    
    # Width and color of polygon selection lines:
    POLY_SELECT_WIDTH = 3
    POLY_SELECT_COLOR = 'gray'
    
    # Matplotlib size of one dot:
    DOT_SIZE = 20
    
    # File with a bulk of explict mappings from course name to acadGrp:
    course2school_map_file  = os.path.join(os.path.dirname(__file__), '../data/courseNameAcademicOrg.csv')
    course_descr_file       = os.path.join(os.path.dirname(__file__), '../data/crsNmDescriptions.csv')
    course_vectors_file     = os.path.join(os.path.dirname(__file__), '../data/best_modelvec250_win15.vector')
    
    # Dict mapping course names to short and long descriptions:
    course_descr_dict = {}
    
    # Dict for the explicit course --> academicGroup map in course2school_map_file:
    course_school_dict = {}

    # NOTE: this list is replicated in ../utils/constants.py
    # An alternative to make changes in both places could/should
    # be to import from there. But am loathe to change this code
    # right now:
    
    acad_grp_name_root = {
        'AA'     : 'ENGR',
        'ACCT'  : 'GSB',
        'AFRICA' : 'H&S',
        'AME'   : 'H&S',        
        'AMSTUD' : 'H&S',
        'ANES' : 'MED',
        'ANTHRO' : 'H&S',
        'ANTHSCI' : 'H&S',
        'APP' : 'H&S',        
        'ARCH'   : 'H&S',
        'ART' : 'H&S',
        'ARAB' : 'H&S',
        'ASN' : 'H&S',        
        'ATHLETIC' : 'ATH',  # officially: Health and Human Performance
        'BIOC' : 'MED',
        'BIODS' : 'MED',
        'BIOE' : 'ENGR',
        'BIOH' : 'H&S',
        'BIOM' : 'MED',
        'BIOPH' : 'H&S',
        'BIO' : 'H&S',
        'BIOS' : 'MED',
        'BUSINESS' : 'GSB',
        'CAT' : 'H&S',
        'CBIO' : 'MED',
        'CE-MS' : 'ENGR',
        'CEE' : 'ENGR',
        'CHEM' : 'H&S',
        'CHEMENG' : 'ENGR',
        'CHIL' : 'H&S',
        'CHIN' : 'H&S',        
        'CHICAN' : 'H&S',
        'CHPR' : 'MED',
        'CLASS' : 'H&S',
        'CME' : 'ENGR',
        'COMM' : 'H&S',
        'COMPLIT' : 'H&S',
        'COMPMED' : 'MED',        
        'CS' : 'ENGR',
        'CSRE' : 'H&S',
        'CTL' : 'H&S',
        'CTS' : 'MED',        
        'DAN' : 'H&S',
        'DBIO' : 'H&S',        
        'DDRL' : 'H&S',
        'DERM' : 'MED',
        'DESINST' : 'ENGR',        
        'DLCL' : 'H&S',  
        'DRAMA' : 'H&S',
        'EALC' : 'H&S',        
        'EARTH' : 'EARTH',
        'EAST' : 'H&S',
        'ECON' : 'H&S',        
        'EDUC' : 'EDUC',
        'EESOR' : 'ENGR',
        'EEES'  : 'EARTH',
        'EESS'  : 'EARTH',
        'EES'   : 'ENGR',
        'EE'    : 'ENGR',
        'EFS'   : 'H&S',
        'EMED'    : 'MED',        
        'ENERGY' : 'EARTH',
        'ENGL-BA' : 'H&S',
        'ENGLISH' : 'H&S',
        'ENGR' : 'ENGR',
        'ENGR-MS' : 'ENGR',
        'ETHI' : 'H&S',
        'ENV' : 'EARTH',
        'ESF' : 'VPUE',        
        'ESS' : 'EARTH',
        'FAMMED' : 'MED',
        'FEM' : 'H&S',
        'FILM' : 'H&S',        
        'FINAN' : 'GSB',
        'FREN' : 'H&S',
        'GS' : 'EARTH',
        'GENE' : 'MED',
        'GEOP' : 'EARTH',        
        'GER' : 'H&S',
        'GES' : 'H&S',
        'GLOBAL' : 'H&S',
        'GSBGEN' : 'EDUC',
        'GYOB' : 'MED',
        'HISTORY' : 'H&S',
        'HRM' : 'GSB',
        'HRP' : 'MED',        
        'HPS' : 'H&S',
        'HRP' : 'H&S',        
        'HUM' : 'H&S',
        'IBER' : 'H&S',
        'ICA' : 'H&S',
        'IE' : 'ENGR',
        'IE-MS' : 'ENGR',
        'IIS' : 'H&S',        
        'IHUM' : 'H&S',        
        'ILAC' : 'H&S',
        'IMMUNOL' : 'MED',
        'INDE' : 'MED',
        'INTN' : 'H&S',        
        'IPS' : 'H&S',        
        'ITAL' : 'H&S',
        'JAP' : 'H&S',
        'JEWISH' : 'H&S',
        'KIN' : 'MED',
        'KOR' : 'H&S',
        'LATI' : 'H&S',
        'LAW' : 'LAW',
        'LEAD' : 'VPUE',
        'LIFE' : 'MED',
        'LIN' : 'H&S',
        'MKTG' : 'GSB',
        'MATH' : 'H&S',
        'MATSCI' : 'ENGR',        
        'MCP' : 'MED',
        'MCS' : 'H&S',        
        'MED' : 'H&S',
        'MGTECON' : 'GSB',
        'MI' : 'MED',
        'MLA' : 'OTHERS',
        'MPHA': 'MED',
        'MS&E' : 'ENGR',
        'MTL' : 'H&S',
        'MUSIC' : 'H&S',        
        'NATIVE' : 'H&S',
        'NEPR' : 'MED',
        'NBIO' : 'MED',
        'NSUR' : 'MED',
        'NENS' : 'H&S',
        'OPHT' : 'MED',                
        'ORTH' : 'MED',
        'OB'   : 'GSB',        
        'OBG'   : 'MED',
        'OIT' : 'GSB',
        'ORAL' : 'VPUE',        
        'OSP' : 'VPUE',
        'OTO' : 'MED',
        'OUTDOOR' : 'MED',   # Also in H&S
        'PAS' : 'MED',
        'PATH' : 'MED',
        'PEDS' : 'MED',
        'PE'   : 'ATH',  # officially: Health and Human Performance
        'PHIL' : 'H&S',
        'PHOTON' : 'H&S',
        'PHYSICS' : 'H&S',
        'POLE'  : 'GSB',
        'POLISC' : 'H&S',
        'POLSC-BA' : 'H&S',
        'PORT' : 'H&S',        
        'PSY' : 'H&S',
        'PUB' : 'H&S',        
        'PWR' : 'VPUE',
        'RAD' : 'MED',
        'RADO' : 'MED',
        'REES' : 'H&S',        
        'RELIG' : 'H&S',
        'RESPROG' : 'VPUE',
        'ROTC' : 'VPUE',
        'SBIO' : 'MED',
        'SCCM' : "H&S",
        'SIMILE' : "VPUE",        
        'SINY' : 'VPUE',
        'SIS'  : 'VPUE',
        'SIW' : 'H&S',        
        'SLAVIC' : 'H&S',
        'SLE' : 'VPUE',
        'SOC' : 'H&S',
        'SOMGEN' : 'MED',        
        'SPAN' : 'H&S',        
        'SPECLAN' : 'H&S',
        'SPEC' : 'OTHERS',
        'STATS' : 'H&S',
        'STEMREM' : 'MED',        
        'STRA' : 'GSB',
        'STS' : 'H&S',
        'SUST' : 'EARTH',
        'SYMBSYS' :  'H&S',      
        'SYMSYS' :  'H&S',      
        'SURG' : 'MED',
        'TAPS' : 'H&S',
        'THINK' : 'VPUE',
        'TIBET' : 'H&S',
        'URBANST' : 'H&S',
        'UAR' : 'VPUE',
        'UROL'  : 'MED',
        'VPTL' : 'OTHERS',
        'WELLNESS' : 'H&S',
        }    
 
    # Assign each major academic group to a color
    # For color choices see https://matplotlib.org/users/colors.html
    # 'tab:xxx' stands for Tableau. These are Tableau recommended
    # categorical colors. Use one color to lump together acad groups
    # we are less interested in to help unclutter the scatterplot:
    
    LUMP_COLOR = colors['poisongreen'].hex_format()
    course_color_dict   = OrderedDict(
        [
            ('ENGR' ,  colors['blue'].hex_format()),
            ('GSB'  ,  colors['banana'].hex_format()),
            ('H&S'  ,  colors['darkseagreen'].hex_format()),
            ('MED'  ,  colors['red1'].hex_format()),
            ('UG'   ,  colors['purple'].hex_format()),
            ('EARTH',  colors['brick'].hex_format()),     # Brown
            ('EDUC' ,  colors['bisque1'].hex_format()),   # Light brownish
            ('VPUE' ,  colors['cyan2'].hex_format()),
            ('LAW'  ,  colors['darkgray'].hex_format()),
            ('ATH'  ,  colors['black'].hex_format()),
            ('OTHERS' ,  LUMP_COLOR), # VPSA/VPTL/CSP
            ('VPSA',  LUMP_COLOR), # OTHERS
            ('VPTL',  LUMP_COLOR), # OTHERS
            ('CSP' ,  LUMP_COLOR)  # OTHERS
        ]
    ) 
    
    def __init__(self, 
                 course_vectors_model,
                 standalone=True,
                 in_queue=None, 
                 out_queue=None,
                 perplexity=None,
                 fittedModelFileName=None,
                 draft_mode=None,
                 active_acad_grps=None,
                 show_save=ShowOrSave.SHOW,
                 save_filename=None,
                 called_from_main=True
                 ):
        '''
        
        @param course_vectors_model:
        @type course_vectors_model:
        @param standalone: if true, create and maintain a text box for course
                listings.
        @type standalone: boolean
        @param in_queue: process queue through which we will receive instructions.
        @type in_queue: multiprocessing.Queue
        @param out_queue: process queue through which we will send msgs to the main process
        @type out_queue: multiprocessing.Queue
        @param perplexity: perplexity number to use when creating the TSNE model.
            Reasonable values are between 20 and 100, though this is not enforced.
        @type perplexity: int
        @param fittedModelFileName: file name with stored fitted model. Much faster. If
            None, will compute the model. In non-draft mode takes about 20 minutes. From
            precomputed file, no time at all. These files are created from the save()
            method.
        @param draft_mode: whether or not only to approximate the clusters using a subset
            of vectors, and only for a subset of academic groups.
        @type draft_mode: boolean
        @param active_acad_grps: academic groups that should be included in computations:
            ENGR, VPUE, etc.
        @type active_acad_grps: [str]
        @param show_save: whether to show the final figure on the screen,
            or create it in memory, and save to to save_filename.
        @type show_save: ShowOrSave
        @param save_filename: only relevant if show_save == ShowOrSave.SAVE
        @type save_filename: str
        @param called_from_main: Should be set to True (the default), if this
            instances is to be used in __main__. If so, the program will exit
            once the requested figures has been created, and shown or saved.
            If False, returns to caller.
        @type called_from_main: bool
        '''
    
        self.debug = True
        
        self.course_vectors_model = course_vectors_model
        self.in_queue   = in_queue
        self.out_queue  = out_queue
        self.standalone = standalone
        if draft_mode is None:
            TSNECourseVisualizer.draft_mode = TSNECourseVisualizer.DEFAULT_DRAFT_MODE
        else:
            TSNECourseVisualizer.draft_mode = draft_mode
        
        # Init the academic groups that should be included in calculations:
        self.school_set = frozenset(TSNECourseVisualizer.course_color_dict.keys())
        if active_acad_grps is None:
            # Include them all:
            TSNECourseVisualizer.active_acad_grps = list(self.school_set)
        else:
            TSNECourseVisualizer.active_acad_grps = active_acad_grps
        
        if perplexity is None:
            perplexity = TSNECourseVisualizer.DEFAULT_PERPLEXITY
        TSNECourseVisualizer.perplexity = perplexity 
                
        # Read the mapping from course name to academic organization 
        # roughly (a.k.a. school):
        
        with open(TSNECourseVisualizer.course2school_map_file, 'r') as fd:
            reader = csv.reader(fd)
            for (course_name, school_name) in reader:
                TSNECourseVisualizer.course_school_dict[course_name] = school_name
                
        # If available, read the course descriptions:
        
        try:
            with open(TSNECourseVisualizer.course_descr_file, 'r', encoding = "ISO-8859-1") as fd:
                reader = csv.reader(fd)
                try:
                    for (course_name, descr, description) in reader:
                        bold_descr = '<b>' + descr + '</b>'
                        TSNECourseVisualizer.course_descr_dict[course_name] = {'descr' : bold_descr, 'description' : description}
                except ValueError as e:
                    logErr(repr(e))
                    sys.exit()
        except IOError:
            logWarn("No course description file found. Descriptions won't be available.")
        
                
        # Regex to separate SUBJECT from CATALOG_NBR in a course name:
        self.crse_subject_re = re.compile(r'([^0-9]*).*$')
        
        self.course_name_list = self.create_course_name_list(self.course_vectors_model)     
        # Course names that have actually been plotted (as
        # opposed to *all* course names:
        self.all_used_course_names = []
                   
        # Map each course to the Tableau categorical color of its school (academicGroup):
        self.color_map = self.get_acad_grp_to_color_map(self.course_name_list)
        
        # Get an analytics object from course_sim_analytics.py. Used for top10:
        self.analyst = CourseSimAnalytics(TSNECourseVisualizer.course_vectors_file)
              
        self.timer = None
        self.init_new_plot(fittedModelFileName=fittedModelFileName,
                           show_save=show_save,
                           save_filename=save_filename)
        if called_from_main:
            if self.debug:
                print("Exiting __init__ back to __main__")
            sys.exit(0)      
        
    def init_new_plot(self, fittedModelFileName=None, 
                      show_save=ShowOrSave.SHOW, 
                      save_filename=None):
        
        # No text in the course_name list yet:
        self.course_names_text_artist = None
        
        # No course points plotted yet. Has a dictionary interface:
        self.course_points = CoursePoints()
        # Place to remember the x/y coords of a given course:
        self.course_xy = {}
        # No course highlight dots yet:
        self.course_highlights = {}
        # No course points lassoed yet:
        self.lassoed_course_points = []
        # No remembered dots yet:
        self.dot_manager = None
        
        # No selection polygon vertices yet:
        self.selection_polygon = None
        
        runtime = self.plot_tsne_clusters(fittedModelFileName=fittedModelFileName)
        logInfo('Time to build model: %s secs' % runtime)
        
        # Timer that has us check the in-queue for commands:
        # Create a new timer object. Set the interval to 100 milliseconds
        # (1000 is default) and tell the timer what function should be called.
        # Only relevant if not standalone:
        
        if not self.standalone and self.timer is None:
            self.timer = Timer(interval=TSNECourseVisualizer.QUEUE_CHECK_INTERVAL, function=self.check_in_queue)
            self.timer.start()

        # Save the finished scatterblot for fast redraw
        # via blit when drawing polygons on top:
        self.background = self.figure.canvas.copy_from_bbox(self.figure.bbox)

        self.send_to_main(Message('ready'))        
        self.send_status_to_main()
        
        if show_save == ShowOrSave.SHOW:
            plt.show(block=True)
            if self.debug:
                print("Plot show has unblocked.")
        elif show_save == ShowOrSave.SAVE:
            self.save_image(save_filename)

    # -------------------------------------------  Communication With Control Process if Used -----------

    #--------------------------
    # send_to_main 
    #----------------

    def send_to_main(self, msg):
        '''
        Sends msg to the out queue, i.e. up to the process
        that spawned us (if we are not running standalone).
        
        @param msg: message object to send
        @type msg: Message
        '''
        if self.out_queue is None:
            return
        self.out_queue.put(msg)


    #--------------------------
    # send_status_to_main 
    #----------------

    def send_status_to_main(self):
        '''
        Send to main (and from there to the control surface) 
        all the current state of the visualization that is relevant
        to the control surface: which academic group are set be
        be included, quality (draft mode or not). The control surface
        will be updated accordingly. Method does nothing if standalone.
        '''
    
        status_summary = {
            'active_acad_grps' : TSNECourseVisualizer.active_acad_grps,
            'draft_mode'       : TSNECourseVisualizer.draft_mode
            }
        self.send_to_main(Message('update_status', status_summary))

    #--------------------------
    # check_in_queue
    #----------------

    def check_in_queue(self):
        
        restart_timer = True
        
        if self.in_queue is None:
            return
        # Note: can't use the empty() method here, b/c it's 
        # unreliable for multiprocess operation:
        try:
            control_msg = self.in_queue.get(block=False)
            restart_timer = self.handle_msg_from_main(control_msg)
        except Empty:
            pass 
        
        # Check whether an earlier command told us 
        # to create a new chart. If so, the method 
        # handle_msg_from_main() method will have left
        # a flag for us after closing the current plot:
        
        if restart_timer:
            # Schedule the next queue check:
            self.timer = Timer(interval=TSNECourseVisualizer.QUEUE_CHECK_INTERVAL, function=self.check_in_queue)
            self.timer.start()
    
    #--------------------------
    # handle_msg_from_main 
    #----------------
        
    def handle_msg_from_main(self, msg):
        
        if self.debug:        
            print('From main to tsne: %s, %s' % (msg.msg_code, str(msg.state)))
        
        # In most cases we want the restart the in-queue check
        # timer again after this incoming msg is processed. But
        # if when we are shutting down this process for a recompute,
        # we don't want to start the timer:
        
        restart_timer = True
        
        msg_code = msg.msg_code
        if msg_code == 'stop':
            TSNECourseVisualizer.status='stop'
            restart_timer = False
            # Clean up:
            self.close()
            # Ask to be killed:
            self.send_to_main(Message('stop', None))
        elif msg_code == 'set_draft_mode':
            TSNECourseVisualizer.draft_mode = msg.state
        elif msg_code == 'set_acad_grps':
            TSNECourseVisualizer.active_acad_grps = msg.state
            self.update_figure_title()
        elif msg_code == 'save_viz':
            self.save()
        elif msg_code == 'restore_viz':
            # Read the pickled state file, initializing the TSNECourseVisualizer
            # class variables, close the app window, and restart:
            restart_timer = False
            try:
                self.restore(msg.state, restart=True)
            except FileNotFoundError:
                logErr('Restore request failed: %s does not exist.' % msg.state)
                restart_timer = True
        elif msg_code == 'kill_yourself':
            sys.exit(0)
        elif msg_code == 'recompute':
            # Exit this instance and start a new one with
            # the current class var values of TSNECourseVisualizer:
            restart_timer = False
            # Construct a dict with the current configuration, and request a restart:
            init_parms = self.create_viz_init_dict()
            # Destroy the current Tsne plot, and make a new one:
            self.restart(init_parms)
        elif msg_code == 'where_is':
            # Highlight the dot that represents the course.
            try:
                course_name = msg.state 
                self.add_course_highlight(course_name)
            except Exception as e:
                logErr("Error in where_is; course_name: %s (%s)" % (course_name, repr(e)))
        elif msg_code == 'top10':
            # Expect a course name in Msg.state, and send the top-10 
            # closest other courses back to control via main:
            course_name = msg.state
            if len(course_name) > 0:
                # Get list of two-tuples: [(crsName, probability), (crseName, prob...)...]:
                try:
                    siblings = self.analyst.similar_by_word(course_name, topn=10)
                except KeyError:
                    self.control_board_error('Course %s is not in the model; maybe used draft mode when building it?' % course_name)
                else:
                    if type(siblings) == list and len(siblings) > 0:
                        # Turn [('crs1', 0.9456324), (crs2, 00145453), ...)] into the display
                        # string  "('crs1', 0.9456324)<br>(crs2, 00145453), ...)". We go in 
                        # two steps:
                        text_array = ['' + str(crse_prob_tuple) for crse_prob_tuple in siblings]
                        text = '<br>'.join(text_array)
                        self.update_course_list_display(text)

        elif msg_code == 'enrollment_history':
            course_name = msg.state
            self.show_enrollment_history(course_name)
            
        return restart_timer
    
    #--------------------------
    # clear_board 
    #----------------
    
    def clear_board(self):
        if self.standalone:
            if self.course_names_text_artist is not None:
                self.course_names_text_artist.remove()
                self.course_names_text_artist = None
                self.ax_course_list.get_figure().canvas.draw_idle()
        else:
            self.out_queue.put(Message('clear_crse_board'))
    
    # ------------------------------------------------- Create Plot From Scratch ---------
        
    #--------------------------
    # plot_tsne_clusters 
    #----------------

    def plot_tsne_clusters(self, fittedModelFileName=None):
        '''
        Creates and TSNE self.course_vector_model and plots it.
    
        @return: model construction time in seconds.
        @rtype: int
        
        '''
        # Start in secs after start of epoch
        start_time = time.time()
        labels_course_names = []
        tokens_vectors      = []
        
        for course_name in self.course_vectors_model.wv.vocab:
            tokens_vectors.append(self.course_vectors_model.wv.__getitem__(course_name))
            labels_course_names.append(course_name)
        
        logInfo('Mapping %s word vector dimensions to 2D...' % self.course_vectors_model.vector_size)
        tsne_model = TSNE.MulticoreTSNE(perplexity=TSNECourseVisualizer.perplexity, 
                                        n_components=2, 
                                        init='random', 
                                        n_iter=2500, 
                                        random_state=23,
                                        n_jobs=4, # n_jobs is part of the MulticoreTSNE
                                        cheat_metric=True) # use Euclidean distance; supposedly faster with similar results.
        logInfo('Done mapping %s word vector dimensions to 2D.' % self.course_vectors_model.vector_size)
        logInfo('Fitting course vectors to t_sne model...')

        # If a pre-computed model is to be loaded, do that:
        if fittedModelFileName is not None:
            try:
                self.fitted_vectors = self.restore(fittedModelFileName, restart=False)
            except Exception as e:
                raise(ValueError("Problem loading pre-computed model from file '%s' (%s)" % \
                                  (fittedModelFileName, repr(e))))
        else:
            # Compute a new fit:
            np_tokens_vectors = np.array(tokens_vectors)
            # In test mode we only fit 500 courses to save time: 
            if TSNECourseVisualizer.draft_mode:
                self.fitted_vectors = tsne_model.fit_transform(np_tokens_vectors[0:500,])
            else:
                self.fitted_vectors = tsne_model.fit_transform(np_tokens_vectors)

        logInfo('Done fitting course vectors to t_sne model.')
    
        x = []
        y = []
        for value in self.fitted_vectors:
            x.append(value[0])
            y.append(value[1])

        # If running without a separate control surface, 
        # Create and maintain the selected-course board to the 
        # right of the plot. In non-standalone the separate
        # control surface serves this purpose:
        
        if self.standalone:        
            self.figure, axes_array = plt.subplots(nrows=1, ncols=2, 
                                          gridspec_kw={'width_ratios':[3,1]},
                                          figsize=(15,10)
                                          )
            self.ax_tsne = axes_array[0]
            self.ax_course_list = axes_array[1]
        else:
            # If only need to create a figure if we did not restore() above:
            if fittedModelFileName is None:
                self.figure, self.ax_tsne = plt.subplots(nrows=1, ncols=1,
                                                         figsize=(15,10)
                                                         ) 
        self.prepare_course_list_panel()
        # Only need to create the scatter points if we did not restore() above:
        if fittedModelFileName is None:
            self.add_course_scatter_points(x, y, labels_course_names)
        
            # Get the set of academic groups represented by these used courses.
            # That's different from the TSNECourseVisualizer.active_acad_grps list. That one
            # is the acad groups we are to limit ourselves to irrespective of
            # courses:
            self.used_acad_grps = frozenset([self.group_name_from_course_name(course_name) for course_name in self.all_used_course_names\
                                             if not isinstance(course_name, matplotlib.text.Text)])
        
            # Update the window title to reflect the number of courses
            # and academic groups being displayed:
            self.update_figure_title()
        
            logInfo("Adding legend...")
            self.add_legend(self.ax_tsne)
            logInfo("Done adding legend.")
    
        # Prepare annotation popups:
        annot = self.ax_tsne.annotate("",
                                      xy=(0,0),
                                      xytext=(20,20),
                                      textcoords="offset points",
                                      color='white',
                                      bbox=dict(boxstyle="round", fc="#FFFFFF"),
                                      arrowprops=dict(arrowstyle="->")
                            )
        annot.set_visible(False)
        # Use currying to create a function that called when
        # mouse moves. But in addition to the event, several 
        # other quantities are passed:
        curried_hover = functools.partial(self.hover, annot)

        # Increase dot sizes by how many pseudo artists are
        # below:
        
        self.adjust_dot_sizes()
                
        # Connect the listeners:
        
        # Hovering:
        self.figure.canvas.mpl_connect("motion_notify_event", curried_hover)
        
        # Clicking on a dot:
        self.figure.canvas.mpl_connect("pick_event", self.onpick)

        # Single or double clicking anywhere (clicking on point will be ignored,
        # so no conflict with self.onpick():
        self.figure.canvas.mpl_connect("button_release_event", self.onclick)
                                      
        # Keyboard presses:
        # self.figure.canvas.mpl_connect("key_press_event", self.onenter_key)
        
        logInfo('Done populating  t_sne plot.')

        runtime = int(time.time() - start_time)
        return runtime

    #--------------------------
    # add_course_scatter_points 
    #----------------
    
    def add_course_scatter_points(self, x, y, labels_course_names):
        # List of point coordinates:
        self.xys = []
        dot_artist = None
        # Fast retrieval of artists by coords:
        
        # Create a manager for the scatter dots we are 
        # about to create:
        self.dot_manager = DotManager((min(x), min(y)), 
                                      (max(x), max(y)),
                                      TSNECourseVisualizer.PICK_RADIUS)
        
        logInfo("Adding course scatter points...")
        for i in range(len(x)):
            try:
                course_name = labels_course_names[i]
                # If the course doesn't have an entry in the
                # color_map, it's a weird, one-off or unusual
                # course we filtered out earlier:
                if self.color_map.get(course_name, None) is None:
                    continue
            except IndexError:
                logWarn("Ran out of course names at i=%s" % i)
                continue
            acad_group = self.group_name_from_course_name(course_name)
            if acad_group is None:
                # One course has name '\\N', which obviously has
                # no acad group associated with it. Skip over that
                # data point:
                continue
            
            # If we are currently excluding the found acad group,
            # skip it:
            if acad_group not in TSNECourseVisualizer.active_acad_grps:
                continue

            course_name = labels_course_names[i]
            # Check whether a dot already exists in this
            # spot. If so, make this new artist a pseudo artist:
            
            if self.dot_manager.get_dots(x[i],y[i]) is not None:
                dot_artist = PseudoDotArtist(course_name, (x[i],y[i]))
            else:
                # Stopped making H&S smaller (originally b/c there are so many of 
                # them that overwhelm the images), b/c now we no longer overplot.
                # Left the code commented for reference:
    
                dot_artist = self.ax_tsne.scatter(x[i],y[i],
                                          c=self.color_map[course_name],
                                          picker=TSNECourseVisualizer.PICK_RADIUS, # Was 5
                                          label=labels_course_names[i],
                                          marker='o',
                                          s = TSNECourseVisualizer.DOT_SIZE
                                          #s = 10 if acad_group == 'H&S' else 20 # s is markersize
                                          )
            # Add this point's coords to our list. The offsets are 
            # a list of this scatterplot's points. But there is only 
            # a single one, since we add one by one:
            
            coords = dot_artist.get_offsets()[0]
            self.course_points[coords] = dot_artist
            
            # The course_points class existed first, and deals with
            # containment. Just for getting either real or pseudo 
            # artists quickly by coordinates. The two should be 
            # combined, but are optimized for somewhat different goals:
            
            self.dot_manager.add_dot(coords[0], coords[1], dot_artist)
            
            self.course_xy[course_name] = [x[i], y[i]]
            # Keep track of course names we actually used above (could be draft mode):
            self.all_used_course_names.append(course_name)
            
        logInfo("Done adding course scatter points.")
        return dot_artist

    #--------------------------------
    # adjust_dot_sizes
    #------------------
        
    def adjust_dot_sizes(self):
        
        _rendered, _pseudo, largest_family_size, num_dots = self.dot_manager.num_artists()
        # Get the per-pseudo-artist dot size increase factor
        # for the total number of dots in this figure:
        #*************
        #***size_growth_factor = DotSizeFactor.dot_growth_factor(num_dots)
        size_growth_factor = math.log(largest_family_size)
        dot_size_stepsize = (DotSizeFactor.MAX_DOT_SIZE - TSNECourseVisualizer.DOT_SIZE) / largest_family_size
        #*************
        
        # For each rendered dot, get number of pseudo artists below it:
        for rendered_artist in self.dot_manager.all_rendered_artists:
            num_pseudos_underneath = len(self.dot_manager.pseudo_artists_with_rendered(rendered_artist))
            #**************************
            # Current matplotlib dot size is available as a single-value list, like [40]
            curr_size = rendered_artist.get_sizes()[0]
            total_size_increase_factor = size_growth_factor ** num_pseudos_underneath
            new_size = curr_size * total_size_increase_factor
            
            new_size = TSNECourseVisualizer.DOT_SIZE + (num_pseudos_underneath * dot_size_stepsize)
            #**************

            
            #**************
            # Put a cap on the size:
            #************
#             if new_size > DotSizeFactor.MAX_DOT_SIZE:
#                 new_size = DotSizeFactor.MAX_DOT_SIZE
#                 rendered_artist.set_linewidth([DotSizeFactor.EDGE_WIDTH])
#                 rendered_artist.set_edgecolor('black')
            #************
            
            rendered_artist.set_sizes([new_size])

    #--------------------------
    # add_legend 
    #----------------
        
    def add_legend(self, scatter_plot):
        '''
        Add the legend of academic groups below the chart:
        
        @param scatter_plot: existing scatter plot figure
        @type scatter_plot: figure ?
        '''
        
        ax = scatter_plot.axes
        LUMP_COLOR = TSNECourseVisualizer.LUMP_COLOR
        

        # Create proxy artists: the color patches for the legend:
        color_patches = []
        combine_remaining_groups = False
        combined_acad_goup_text  = '' 
        for (acad_group, rgb_color) in TSNECourseVisualizer.course_color_dict.items():
            if combine_remaining_groups:
                combined_acad_goup_text += ',' + acad_group
                continue
            # Have we reached the first acad group that we are
            # lumping together?
            if rgb_color == LUMP_COLOR:
                combined_acad_goup_text = acad_group
                combine_remaining_groups = True
                continue
                
            color_patches.append(mpatches.Patch(color=rgb_color, label=acad_group))
        # Add the final legend entry of combined acad groups:
        color_patches.append(mpatches.Patch(color=LUMP_COLOR, label=combined_acad_goup_text))

        return ax.legend(loc='upper center', 
                         bbox_to_anchor=(0.5, -0.05),
                         fancybox=True, 
                         shadow=True, 
                         ncol=9,
                         handles=color_patches)
            
    #--------------------------
    # update_annot 
    #----------------

    def update_annot(self, dot_artist, annot, num_in_cluster):
        '''
        Update the tooltip surface with the course name
        
        @param dot_artist: list of point coordinates
        @type dot_artist: [[float,float]]
        @param annot: tooltip surface
        @type annot: ?
        @param num_in_cluster: number of dots in the cluster 
        @type num_in_cluster: int
        '''
        pos = dot_artist.get_offsets()
        # Position is like array([(9.90404368, 2.215768)]). So
        # grab first pair:
        annot.xy = pos[0]
        course_name   = dot_artist.get_label()
        acad_grp_name = self.group_name_from_course_name(course_name)
        if acad_grp_name is None:
            # Ignore the one course named '\\N':
            return
        label_text    = course_name + '/' + acad_grp_name + '(%s)' % num_in_cluster
        annot.set_text(label_text)
        #dot_color = dot_artist.get_facecolor()[0]
        #annot.get_bbox_patch().set_facecolor(dot_color)
        annot.get_bbox_patch().set_facecolor('#00000000') # Black
        
        annot.get_bbox_patch().set_alpha(0.7)

    #--------------------------
    # prepare_course_list_panel 
    #----------------
        
    def prepare_course_list_panel(self):
        '''
        If running standalone, prepare the course list text pane:
        '''
        if not self.standalone:
            return
        self.ax_course_list.set_title('List of Clicked Courses', fontsize=15)
        self.ax_course_list.axis('off')

    #--------------------------
    # control_board_error 
    #----------------

    def control_board_error(self, err_msg):
        '''
        Ask control board to show an error message in a 
        popup dialog. TODO: do something similar for standalone
        
        @param err_msg: msg to display
        @type err_msg: str
        '''
        if self.standalone:
            logErr(err_msg)
            return
        self.send_to_main(Message('error', err_msg))
        
    #--------------------------
    # update_course_list_display 
    #----------------

    def update_course_list_display(self, new_text):
        '''
        Update the course list text box. When running standalone, 
        the text is delivered to the matplotlib subplot, else
        text will go to board in control surface. 
        
        @param new_text: text to display
        @type new_text: string
        '''
        if self.standalone:
            if self.course_names_text_artist is not None:
                self.course_names_text_artist.remove()
                self.course_names_text_artist = None
            
            # Remove any duplicates:
            new_text = "\n".join(list(OrderedDict.fromkeys(new_text.split("\n"))))
            self.course_names_text_artist = self.ax_course_list.text(-0.2, 0.95, 
                new_text, 
                transform=self.ax_course_list.transAxes, 
                fontsize=10, 
                va='top', 
                wrap=True)
            self.ax_course_list.get_figure().canvas.draw_idle()
            return
        else:
            # Send text to control board via main:
            self.send_to_main(Message('update_crse_board', new_text))
            

    #--------------------------
    # append_to_course_list_display 
    #----------------

    def append_to_course_list_display(self, course_name_or_names, priorText=''):
        '''
        Get already-displayed course descriptions. See whether we already have more
        than our upper limit. If not, find courses descriptions, make a new line for
        the display (course name plus descr, plus description). 
        
        If standalone, updates the local display. If control surface is
        separate, then just return the new line of course/descr.
        
        @param course_name_or_names: course name(s) to append
        @type course_name_or_names: {string | (string)
        @param priorText: any text to which course info is to be appended
        @type priorText: str
        @return: priorText with course name with course description attached.
        @rtype: str
        '''
        new_text = ''
        curr_text = priorText
        # Get text from standalone board, or empty str if not
        # standalone:
        curr_text += self.get_text_standalone_board()
        if isinstance(course_name_or_names, str):
            course_name_or_names = [course_name_or_names]

        try:
            for course_name in course_name_or_names:            
                new_text = curr_text + course_name
                # If we have course descriptions loaded, add short and long descriptions:
                if len(TSNECourseVisualizer.course_descr_dict) > 0:
                    try:
                        descr_description_dict = TSNECourseVisualizer.course_descr_dict[course_name] 
                        descr = descr_description_dict['descr']
                        description = descr_description_dict['description']
                    except KeyError:
                        # descr/description unavalable for this course:
                        descr = 'unavailable'
                        description = ''
                    new_text += ' ' + descr
                    if description != '\\N':
                        new_text += '; ' + description
                curr_text = new_text + '<br>'
        finally:
            if len(new_text) > 0 and self.standalone:
                # Update local display:
                self.update_course_list_display(new_text)
            return new_text

    #--------------------------
    # get_text_standalone_board 
    #----------------
                
    def get_text_standalone_board(self):
        
        if not self.standalone or self.course_names_text_artist is None:
            return ''
                
        # Already showing text; internally add new course to that
        # list if that doesn't exceed max courses to show, and 
        # erase current text if we will replace the text:
        
        curr_text = self.course_names_text_artist.get_text()
        # Already have max lines plus a line saying "... more buried under."?
        num_lines = curr_text.count('\n')
        if num_lines >= TSNECourseVisualizer.MAX_NUM_COURSES_TO_LIST + 1:
            return
        elif num_lines == TSNECourseVisualizer.MAX_NUM_COURSES_TO_LIST:
            return 
        # Have room for more courses in the displayed list:
        curr_text += '\n'
        return curr_text
     
    #--------------------------------
    # sort_crs_desc_html 
    #------------------
     
    def sort_crs_desc_html(self, html_txt):
        '''
        Given an html list of course names with descriptions,
        return a new html string in which the entries are
        sorted by course name: Example input:
        
           '<b>MATH54</b> Linear algebra<br>...<br>'
        
        @param html_txt:
        @type html_txt:
        '''
        # Get each line as a string item in an array:
        html_txt_arr = html_txt.split('<br>')
        
        # Sort the array. The search keys are the course
        # names, which are before a space in each line:
        html_txt_arr_sorted = sorted(html_txt_arr,
                                     key=lambda course_desc: course_desc[:course_desc.find(' ')]
                           )
        # Reconstruct string, putting <br>s back in:
        html_txt = '<br>'.join(html_txt_arr_sorted)
        return html_txt
        
    #--------------------------
    # restart 
    #----------------
     
    def restart(self, init_parm_dict=None):
        TSNECourseVisualizer.status = 'newplot'
        # Clean up:
        self.close()
        self.send_to_main(Message('restart', init_parm_dict))
     
    #--------------------------
    # close 
    #----------------
     
    def close(self):
        '''
        Close the application window, causing the plt.show() in the
        __init__() method to unblock and return. The loop in 
        function start_viz() will thereby unblock. It's up to the
        caller to set TSNECourseVisualizer.status to the correct
        follow-on action ('stop', 'newplot') before calling this
        method.
        
        '''
        pass

    # ---------------------------------------- UI Dynamics --------------
    
    #--------------------------
    # hover 
    #----------------

    def hover(self, annot, event):
        vis = annot.get_visible()
        fig = self.ax_tsne.get_figure()
        
        if event.inaxes == self.ax_tsne:
            dot_artists = self.dot_manager.get_dots(event.xdata, event.ydata)
            first_artist = None if dot_artists is None else dot_artists[0]
            if first_artist is not None:
                self.update_annot(first_artist, annot, len(dot_artists))
                annot.set_visible(True)
                fig.canvas.draw_idle()
            else:
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

    #--------------------------
    # onpick 
    #----------------

    def onpick(self, event):
        '''
        Clicked on a course point. Append that course and all other
        course in the clicked-on cluster to the course board
        display. This method is called multiple times when marks are
        overlapping. Collect the events that belong to one click, and
        only update board in the end:
        
        @param event: click event
        @type event: 
        '''
        
        # Get names of all courses in click-on cluster:
        artists_in_cluster = self.dot_manager.get_dots(event.mouseevent.xdata, event.mouseevent.ydata)
        if artists_in_cluster is None:
            self.control_board_error('Please click near the center of dots.')
            return
        course_names = [artist.get_label() for artist in artists_in_cluster] 
        
        # Get existing list in course name list and
        # add the new course to it:
          
        crse_name_plus_descr = self.append_to_course_list_display(course_names)
        if not self.standalone:
            self.send_to_main(Message('update_crse_board', self.sort_crs_desc_html(crse_name_plus_descr)))

    #--------------------------
    # onclick
    #----------------

    def onclick(self, event):
        '''
        If double click, erase text area. If standalone, the
        text box in this application is erased. Else a message
        is sent to the control process.
        
        @param event:
        @type event:
        '''
        lassoing = self.currently_lassoing()
        single_click = not event.dblclick and event.button == 1
        
        # Single-clicks when we are not poly-lassoing
        # are only relevant if on a course highlight. In
        # that case we remove the highlight:
        if single_click and not lassoing:
            highlights = CourseHighlight.get_instance()
            highlight = highlights.contains(event) 
            if highlight:
                highlights.remove_course_highlight(highlight)
            return
          
        double_click = event.dblclick
        right_click  = event.button == 3
        
        x = event.xdata
        y = event.ydata
        
        if right_click and not lassoing:
            
            # Right-button click: start a polygon select:
            self.selection_polygon = Polygon(self.ax_tsne, x, y, background_copy=self.background)
            return
        
        if right_click and lassoing:
            
            # Close the lasso polygon, and show lassoed classes:
            self.selection_polygon.close()
            # Collect the polygon's vertices...
            verts = self.selection_polygon.vertices()
            # ... and display all the enclosed courses:
            self.poly_lasso_was_closed(verts)
            return
        
        if double_click and not lassoing:
            
            # User wants to erase the course board:
            
            # Are we standalone, and therefore have a course board?
            # If so, then is there anything on that course board?
            if self.standalone and self.course_names_text_artist is not None:
                self.clear_board()        
            else:
                # We have a control board peer window. Tell it to clear the board:
                self.clear_board()
            self.lassoed_course_points    = []
            return
            
        if single_click and lassoing:
            
            # If the polygon is already closed, we take the
            # single click as a request to erase the polygon:
            
            if self.selection_polygon.is_closed():
                self.exit_lassoing_state()
                return
            
            # Add new point to poly-lasso:
            self.selection_polygon.add_point(x, y, draw=True)
            return

    #--------------------------
    # on_enroll_history_close
    #----------------

    def on_enroll_history_close(self, event):
        '''
        Called when a popped-up barchart history of previously
        lassoed courses is closed. In response we stop the lassoing
        
        @param event:
        @type event:
        '''
        self.exit_lassoing_state()
        
    #--------------------------
    # exit_lassoing_state 
    #----------------
    
    def exit_lassoing_state(self):
        # Erase on screen:
        # If user hasn't earlier erased the lasso polygon
        # by clicking on empty space, erase it now:
        if self.selection_polygon is not None:
            self.selection_polygon.erase()
            # Allow GC:
            self.selection_polygon = None        
                    
    #--------------------------
    # poly_lasso_was_closed
    #----------------

    def poly_lasso_was_closed(self, verts):
        '''
        Handle lassoing by finding the lassoed courses, and 
        either displaying them on the local course board, or
        sending an update message to the control process (depending
        on whether running standalone):
        
        @param verts: coordinates of points touched by the lasso
        @type verts: [[float,float]]
        '''
        
        # This method is called both at the end of a lasso, and
        # when the mouse is released form a simple click on a point.
        # The diff is the when just a click, there are only two
        # vertices. Use that to destinguish between lasso and click:
        
        if len(verts) <= 2:
            return
         
        # Have a clear board for each lasso: 
        self.clear_board()
            
        lasso_path = Path(verts)
        self.lassoed_course_points = self.course_points.contains_course_points(lasso_path)

        # Course names are labels of the point objects:
        course_names = [course_point.get_label() for course_point in self.lassoed_course_points]
        
        new_text = ''    
        for course_name in course_names:
            new_text += '<br>' + self.append_to_course_list_display(course_name)

        # Add course names to the course display:

        if self.standalone:            
            self.ax_course_list.get_figure().canvas.draw_idle()
            #print('Selected courses: %s.' % course_names)
        else:
            # Notify the main thread, and from there the control surface
            # to update the control surface's course list panel:
            if len(new_text) > 0:
                # Sort the courses by alpha:
                new_text = self.sort_crs_desc_html(new_text)
                
                self.out_queue.put(Message('update_crse_board', new_text))
                # Raise the enrollment history char:
                EnrollmentPlotter(self, course_names, block=False)
                # Raise the difficulty overview charts:
                try:
                    DifficultyPlotter(course_names, block=False)
                except ValueError:
                    # Don't have evals of effort requirements for any
                    # of the courses (e.g. Law):
                    self.control_board_error('No intensity info on any of the circled courses') 
                
        self.ax_tsne.get_figure().canvas.draw_idle()
            
            
    #--------------------------
    # currently_lassoing 
    #----------------

    def currently_lassoing(self):
        return self.selection_polygon is not None

    #--------------------------
    # show_enrollment_history 
    #----------------
        
    def show_enrollment_history(self, course_name):
        EnrollmentPlotter(self, [course_name], block=False)
        self.ax_tsne.get_figure().canvas.draw_idle()
        
    #--------------------------
    # disconnect 
    #----------------

    def disconnect(self):
        '''
        Not used.
        '''
        self.lasso.disconnect_events()
        self.ax_tsne.get_figure().canvas.draw_idle()

    #--------------------------
    # update_figure_title  
    #----------------

    def update_figure_title(self):
        fig = self.ax_tsne.get_figure() 
        fig.suptitle('t_sne Clusters of %s courses in %s; %s quality (perplexity: %s)' %\
                     (len(self.all_used_course_names),
                      ','.join(TSNECourseVisualizer.active_acad_grps),
                      'draft' if TSNECourseVisualizer.draft_mode else 'full',
                      TSNECourseVisualizer.perplexity
                      )
                     )
        fig.canvas.draw_idle()
     
    # ------------------------------------------------ Preparation Done Once --------------

    #--------------------------
    # create_course_name_list 
    #----------------
    
    def create_course_name_list(self, course_vectors_model):
        '''
        Create a list of tokens, i.e. course names as they are ordered
        in the model's vocabulary list.
        
        @param course_vectors_model: trained skip gram model for the input 'sentences':
        @type course_vectors_model: CourseVectorsCreator instance
        '''
        
        course_names = course_vectors_model.wv.vocab.keys()
        return course_names
        # Remove '\N' entries:
        # return list(filter(lambda name: name != '\\N', course_names))
 

    #--------------------------
    # get_acad_grp_to_color_map
    #----------------

    def get_acad_grp_to_color_map(self, course_name_list):
        '''
        Create a color map from course names. Every course's academic group
        gets its own color. To get the academic group from each course name,
        first try the course_school_dict. If the course is not found there, try
        a heuristic.
        
        @param course_name_list: list of all course names involved in the plot
        @type course_name_list: [string]
        '''

        color_map = {}
        for course_name in course_name_list:
            # One course name shows as '\N'; ignore it:
            if course_name == '\\N':
                continue
            # Another one is 'GR-SV' and some other: don't know what those are:
            hopeful = True
            for hopeless_course_name_root in ['GR-SV', 'UGNM-SV', 'CASA', 
                                              'GR-NDO', 'UGNM-GNM','INSST-IHN'
                                              ]:
                # Yes, we unnecessarily go through all, but I'm tired:
                if course_name.startswith(hopeless_course_name_root):
                    hopeful = False
                    
            if  course_name.endswith('-AUD') or\
                course_name.endswith('-BA') or\
                course_name.endswith('-BAH') or\
                course_name.endswith('-BAS') or\
                course_name.endswith('-BS') or\
                course_name.endswith('-BSH') or\
                course_name.endswith('-MA') or\
                course_name.endswith('-MS') or\
                course_name.endswith('-PHD') or\
                course_name.endswith('-PD') or\
                course_name.endswith('-NHSA') or\
                course_name.endswith('-HSV') or\
                course_name.endswith('-IHN') or\
                course_name.endswith('-NM') or\
                course_name.endswith('-VR') or\
                course_name.startswith('PETENG') or\
                course_name.startswith('WCT'):
                hopeful = False
            if not hopeful:
                continue
            try:
                # First try the explicit course-->acadGrp map:
                school = TSNECourseVisualizer.course_school_dict[course_name]
            except KeyError:
                try:
                    # Didn't find a mapping. Use heuristic:
                    school = self.group_name_from_course_name(course_name)
                except KeyError:
                    raise ValueError("Don't know to which academic group (~=school) '%s' belongs." % course_name)
            try:
                # Got the academic group; get a color assignment:
                color_map[course_name] = TSNECourseVisualizer.course_color_dict[school]
            except KeyError:
                # These failures are one-off, or otherwise strange courses:
                logWarn("Don't have color assignment for course/acadGrp %s/%s." % (course_name, school))
                continue
        return color_map

    # --------------------------------------- Lookup Methods -------------

    #--------------------------
    # group_name_from_course_name 
    #----------------

    def group_name_from_course_name(self, course_name):
        '''
        Given a course name, try to guess its academic group.
        
        @param course_name: name of course
        @type course_name: string
        '''
        
        if course_name == '\\N':
            return None
        
        # Try the explicitly mapped course--group dict:
        try:
            return TSNECourseVisualizer.course_school_dict[course_name]
        except KeyError:
            pass
        
        # Heuristics:
        if course_name.startswith('AA'):
            return TSNECourseVisualizer.acad_grp_name_root['AA']
        if course_name.startswith('AFRICA'):
            return TSNECourseVisualizer.acad_grp_name_root['AFRICA']
        if course_name.startswith('AME'):
            return TSNECourseVisualizer.acad_grp_name_root['AME']
        if course_name.startswith('AMSTUD'):
            return TSNECourseVisualizer.acad_grp_name_root['AMSTUD']
        elif course_name.startswith('ANTHRO'):
            return TSNECourseVisualizer.acad_grp_name_root['ANTHRO']
        elif course_name.startswith('APP'):
            return TSNECourseVisualizer.acad_grp_name_root['APP']        
        elif course_name.startswith('ARAB'):
            return TSNECourseVisualizer.acad_grp_name_root['ARAB']        
        elif course_name.startswith('ARCH'):
            return TSNECourseVisualizer.acad_grp_name_root['ARCH']
        elif course_name.startswith('ART'):
            return TSNECourseVisualizer.acad_grp_name_root['ART']
        elif course_name.startswith('ASN'):
            return TSNECourseVisualizer.acad_grp_name_root['ASN']
        elif course_name.startswith('ATHLETIC'):
            return TSNECourseVisualizer.acad_grp_name_root['ATHLETIC']
        elif course_name.startswith('BIOC'):
            return TSNECourseVisualizer.acad_grp_name_root['BIOC']
        elif course_name.startswith('BIODS'):
            return TSNECourseVisualizer.acad_grp_name_root['BIODS']
        elif course_name.startswith('BIOE'):
            return TSNECourseVisualizer.acad_grp_name_root['BIOE']
        elif course_name.startswith('BIOH'):
            return TSNECourseVisualizer.acad_grp_name_root['BIOH']
        elif course_name.startswith('BIOM'):
            return TSNECourseVisualizer.acad_grp_name_root['BIOM']
        elif course_name.startswith('BIOPH'):
            return TSNECourseVisualizer.acad_grp_name_root['BIOPH']
        elif course_name.startswith('BIO'):
            return TSNECourseVisualizer.acad_grp_name_root['BIO']
        elif course_name.startswith('BIOS'):
            return TSNECourseVisualizer.acad_grp_name_root['BIOS']
        elif course_name.startswith('CAT'):
            return TSNECourseVisualizer.acad_grp_name_root['CAT']
        elif course_name.startswith('CEE'):
            return TSNECourseVisualizer.acad_grp_name_root['CEE']
        elif course_name.startswith('CHIL'):
            return TSNECourseVisualizer.acad_grp_name_root['CHIL']
        elif course_name.startswith('CHEM'):
            return TSNECourseVisualizer.acad_grp_name_root['CHEM']
        elif course_name.startswith('CHIN'):
            return TSNECourseVisualizer.acad_grp_name_root['CHIN']
        elif course_name.startswith('CHICAN'):
            return TSNECourseVisualizer.acad_grp_name_root['CHICAN']
        elif course_name.startswith('CLASS'):
            return TSNECourseVisualizer.acad_grp_name_root['CLASS']
        elif course_name.startswith('CME'):
            return TSNECourseVisualizer.acad_grp_name_root['CME']
        elif course_name.startswith('COMPLIT'):
            return TSNECourseVisualizer.acad_grp_name_root['COMPLIT']
        elif course_name.startswith('CSRE'):       # Must be before CS
            return TSNECourseVisualizer.acad_grp_name_root['CSRE']
        elif course_name.startswith('CS'):          
            return TSNECourseVisualizer.acad_grp_name_root['CS']
        elif course_name.startswith('CTL'):
            return TSNECourseVisualizer.acad_grp_name_root['CTL']
        elif course_name.startswith('DAN'):
            return TSNECourseVisualizer.acad_grp_name_root['DAN']
        elif course_name.startswith('DBIO'):
            return TSNECourseVisualizer.acad_grp_name_root['DBIO']
        elif course_name.startswith('DRAMA'):
            return TSNECourseVisualizer.acad_grp_name_root['DRAMA']
        elif course_name.startswith('EARTH'):
            return TSNECourseVisualizer.acad_grp_name_root['EARTH']
        elif course_name.startswith('EAST'):
            return TSNECourseVisualizer.acad_grp_name_root['EAST']
        elif course_name.startswith('ECON'):
            return TSNECourseVisualizer.acad_grp_name_root['ECON']
        elif course_name.startswith('EDUC'):
            return TSNECourseVisualizer.acad_grp_name_root['EDUC']
        elif course_name.startswith('EESOR'):      # Order of all EE* is important
            return TSNECourseVisualizer.acad_grp_name_root['EESOR']
        elif course_name.startswith('EEES'):
            return TSNECourseVisualizer.acad_grp_name_root['EEES']
        elif course_name.startswith('EESS'):
            return TSNECourseVisualizer.acad_grp_name_root['EESS']
        elif course_name.startswith('EES'):
            return TSNECourseVisualizer.acad_grp_name_root['EES']
        elif course_name.startswith('EFS'):
            return TSNECourseVisualizer.acad_grp_name_root['EFS']
        elif course_name.startswith('EMED'):
            return TSNECourseVisualizer.acad_grp_name_root['EMED']
        elif course_name.startswith('ESS'):
            return TSNECourseVisualizer.acad_grp_name_root['ESS']
        elif course_name.startswith('EE'):
            return TSNECourseVisualizer.acad_grp_name_root['EE']
        elif course_name.startswith('ENERGY'):
            return TSNECourseVisualizer.acad_grp_name_root['ENERGY']
        elif course_name.startswith('ENGLISH'):
            return TSNECourseVisualizer.acad_grp_name_root['ENGLISH']
        elif course_name.startswith('ENV'):
            return TSNECourseVisualizer.acad_grp_name_root['ENV']
        elif course_name.startswith('ETHI'):
            return TSNECourseVisualizer.acad_grp_name_root['ETHI']
        elif course_name.startswith('FAMMED'):
            return TSNECourseVisualizer.acad_grp_name_root['FAMMED']
        elif course_name.startswith('FEM'):
            return TSNECourseVisualizer.acad_grp_name_root['FEM']
        elif course_name.startswith('FILM'):
            return TSNECourseVisualizer.acad_grp_name_root['FILM']
        elif course_name.startswith('FINAN'):
            return TSNECourseVisualizer.acad_grp_name_root['FINAN']
        elif course_name.startswith('FREN'):
            return TSNECourseVisualizer.acad_grp_name_root['FREN']
        elif course_name.startswith('GEOP'):
            return TSNECourseVisualizer.acad_grp_name_root['GEOP']
        elif course_name.startswith('GER'):
            return TSNECourseVisualizer.acad_grp_name_root['GER']
        elif course_name.startswith('GES'):
            return TSNECourseVisualizer.acad_grp_name_root['GES']
        elif course_name.startswith('GS'):
            return TSNECourseVisualizer.acad_grp_name_root['GS']
        elif course_name.startswith('GSBGEN'):
            return TSNECourseVisualizer.acad_grp_name_root['GSBGEN']
        elif course_name.startswith('HISTORY'):
            return TSNECourseVisualizer.acad_grp_name_root['HISTORY']
        elif course_name.startswith('HPS'):
            return TSNECourseVisualizer.acad_grp_name_root['HPS']
        elif course_name.startswith('HRM'):
            return TSNECourseVisualizer.acad_grp_name_root['HRM']
        elif course_name.startswith('HUM'):
            return TSNECourseVisualizer.acad_grp_name_root['HUM']
        elif course_name.startswith('IBER'):
            return TSNECourseVisualizer.acad_grp_name_root['IBER']
        elif course_name.startswith('ILAC'):
            return TSNECourseVisualizer.acad_grp_name_root['ILAC']
        elif course_name.startswith('INTN'):
            return TSNECourseVisualizer.acad_grp_name_root['INTN']
        elif course_name.startswith('IPS'):
            return TSNECourseVisualizer.acad_grp_name_root['IPS']
        elif course_name.startswith('ITAL'):
            return TSNECourseVisualizer.acad_grp_name_root['ITAL']
        elif course_name.startswith('JAP'):
            return TSNECourseVisualizer.acad_grp_name_root['JAP']
        elif course_name.startswith('KOR'):
            return TSNECourseVisualizer.acad_grp_name_root['KOR']
        elif course_name.startswith('JEWISH'):
            return TSNECourseVisualizer.acad_grp_name_root['JEWISH']
        elif course_name.startswith('LATI'):
            return TSNECourseVisualizer.acad_grp_name_root['LATI']
        elif course_name.startswith('LAW'):
            return TSNECourseVisualizer.acad_grp_name_root['LAW']
        elif course_name.startswith('LIN'):
            return TSNECourseVisualizer.acad_grp_name_root['LIN']
        elif course_name.startswith('MATH'):
            return TSNECourseVisualizer.acad_grp_name_root['MATH']
        elif course_name.startswith('MED'):
            return TSNECourseVisualizer.acad_grp_name_root['MED']
        elif course_name.startswith('MGTECON'):
            return TSNECourseVisualizer.acad_grp_name_root['MGTECON']
        elif course_name.startswith('MI'):
            return TSNECourseVisualizer.acad_grp_name_root['MI']
        elif course_name.startswith('MS&E'):
            return TSNECourseVisualizer.acad_grp_name_root['MS&E']
        elif course_name.startswith('ME'):
            return TSNECourseVisualizer.acad_grp_name_root['MS&E']
        elif course_name.startswith('MUSIC'):
            return TSNECourseVisualizer.acad_grp_name_root['MUSIC']
        elif course_name.startswith('NATIVE'):
            return TSNECourseVisualizer.acad_grp_name_root['NATIVE']
        elif course_name.startswith('OBG'):                             # Must be before 'OB'
            return TSNECourseVisualizer.acad_grp_name_root['OBG']
        elif course_name.startswith('OB'):
            return TSNECourseVisualizer.acad_grp_name_root['OB']
        elif course_name.startswith('OIT'):
            return TSNECourseVisualizer.acad_grp_name_root['OIT']
        elif course_name.startswith('ORAL'):
            return TSNECourseVisualizer.acad_grp_name_root['ORAL']
        elif course_name.startswith('OSP'):
            return TSNECourseVisualizer.acad_grp_name_root['OSP']
        elif course_name.startswith('ORTH'):
            return TSNECourseVisualizer.acad_grp_name_root['ORTH']
        elif course_name.startswith('OTO'):
            return TSNECourseVisualizer.acad_grp_name_root['OTO']
        elif course_name.startswith('OUTDOOR'):
            return TSNECourseVisualizer.acad_grp_name_root['OUTDOOR']
        elif course_name.startswith('PEDS'):
            return TSNECourseVisualizer.acad_grp_name_root['PEDS']
        elif course_name.startswith('PHIL'):
            return TSNECourseVisualizer.acad_grp_name_root['PHIL']
        elif course_name.startswith('PHOTON'):
            return TSNECourseVisualizer.acad_grp_name_root['PHOTON']
        elif course_name.startswith('PHYSICS'):
            return TSNECourseVisualizer.acad_grp_name_root['PHYSICS']
        elif course_name.startswith('POLE'):
            return TSNECourseVisualizer.acad_grp_name_root['POLE']        
        elif course_name.startswith('POLISC'):
            return TSNECourseVisualizer.acad_grp_name_root['POLISC']
        elif course_name.startswith('PORT'):
            return TSNECourseVisualizer.acad_grp_name_root['PORT']
        elif course_name.startswith('PSY'):
            return TSNECourseVisualizer.acad_grp_name_root['PSY']
        elif course_name.startswith('PUB'):
            return TSNECourseVisualizer.acad_grp_name_root['PUB']
        elif course_name.startswith('PWR'):
            return TSNECourseVisualizer.acad_grp_name_root['PWR']
        elif course_name.startswith('RELIG'):
            return TSNECourseVisualizer.acad_grp_name_root['RELIG']
        elif course_name.startswith('ROTC'):
            return TSNECourseVisualizer.acad_grp_name_root['ROTC']
        elif course_name.startswith('SINY'):
            return TSNECourseVisualizer.acad_grp_name_root['SINY']
        elif course_name.startswith('SCCM'):
            return TSNECourseVisualizer.acad_grp_name_root['SCCM']
        elif course_name.startswith('SLAV'):
            return TSNECourseVisualizer.acad_grp_name_root['SLAVIC']
        elif course_name.startswith('SOC'):
            return TSNECourseVisualizer.acad_grp_name_root['SOC']
        elif course_name.startswith('SPAN'):
            return TSNECourseVisualizer.acad_grp_name_root['SPAN']
        elif course_name.startswith('SPECLAN'):
            return TSNECourseVisualizer.acad_grp_name_root['SPECLAN']
        elif course_name.startswith('STATS'):
            return TSNECourseVisualizer.acad_grp_name_root['STATS']
        elif course_name.startswith('STRA'):
            return TSNECourseVisualizer.acad_grp_name_root['STRA']
        elif course_name.startswith('STS'):
            return TSNECourseVisualizer.acad_grp_name_root['STS']
        elif course_name.startswith('SURG'):
            return TSNECourseVisualizer.acad_grp_name_root['SURG']
        elif course_name.startswith('SYMSYS'):
            return TSNECourseVisualizer.acad_grp_name_root['SYMSYS']
        elif course_name.startswith('TAPS'):
            return TSNECourseVisualizer.acad_grp_name_root['TAPS']
        elif course_name.startswith('TIBET'):
            return TSNECourseVisualizer.acad_grp_name_root['TIBET']
        
        else:
            subject_part = self.crse_subject_re.match(course_name).group(1)
            if len(subject_part) > 0:
                # Assume that course name (i.e. SUBJECT) is known in acad_grp_name_root: 
                try:
                    return TSNECourseVisualizer.acad_grp_name_root[subject_part]
                except KeyError:
                    return None
            else:
                raise ValueError("Could not find subject for '%s'" % course_name)
        
        
    # ------------------------------------------------------- Save/Restore ----------------------
    
    #--------------------------
    # get_tsne_file_name  
    #----------------
    
    def get_tsne_file_name(self):
        filename = os.path.join(TSNECourseVisualizer.DEFAULT_CACHE_FILE_DIR, 'tsneModel_%sCourses_%s_Perplexity_%s' %\
            (len(self.all_used_course_names),
             '_'.join(self.used_acad_grps),
             TSNECourseVisualizer.perplexity
             ))
        if TSNECourseVisualizer.draft_mode:
            filename += '_draftQual'
        else:
            filename += '_fullQual'
        filename += '.pickle'
        return filename
        

    #--------------------------
    # save 
    #----------------
    
    def save(self, filename=None):
        '''
        Save the data structures that allow future 
        resurrection of the entire model. This is 
        different from the save_image() method, which
        just saves an image of the plot as a png.
        
        @param filename:
        @type filename:
        '''
        if filename is None:
            filename = self.get_tsne_file_name()
            
        # If filename is not absolute, put it into the
        # default viz cache directory:
        if not os.path.isabs(filename):
            filename = os.path.join(TSNECourseVisualizer.DEFAULT_CACHE_FILE_DIR, filename)
                                    
            
        important_structs = [self.all_used_course_names,
                             self.used_acad_grps,       # Groups found from courses we actually used
                             TSNECourseVisualizer.active_acad_grps,     # Groups we are to use in any new computation.
                             TSNECourseVisualizer.perplexity,
                             TSNECourseVisualizer.draft_mode,
                             self.figure,
                             self.course_points,
                             self.dot_manager,
                             self.fitted_vectors]
        pickle.dump(important_structs, open(filename, 'wb'))
        return filename
    
    #--------------------------
    # restore 
    #----------------
        
    def restore(self, filename, restart=False):
        '''
        Recover an entire model, and plot the
        corresponding figure. 
        
        @param filename:
        @type filename:
        @param restart: if True, restart the plot with the restored
            data structures in place. If false, return the vectors.
        @type restart: boolean
        '''
        viz_file = open(filename, 'rb')
        (self.all_used_course_names,
         self.used_acad_grps,   # Groups found from courses we actually used
         TSNECourseVisualizer.active_acad_grps, # Groups we are to use in any new computation.
         TSNECourseVisualizer.perplexity,
         TSNECourseVisualizer.draft_mode,
         self.figure,
         self.course_points,  # {(x,y) : dot_obj}
         self.dot_manager,
         self.fitted_vectors) = pickle.load(viz_file)
         
        # We don't save self.course_xy; it is the reverse lookup
        # of self.course_points, except that the key needs to be
        # not a dot_obj, but a coursename:
        
        for dot_coords, dot_obj in self.course_points.items():
            self.course_xy[dot_obj.get_label()] = dot_coords
         
        # Get the scatter plot; it's the only subplot,
        # therefore the ',0':
        self.ax_tsne = self.figure.get_axes()[0]
        if restart:
            self.restart(self.create_viz_init_dict(filename))
        else:
            return self.fitted_vectors 
        
    #--------------------------
    # save_image 
    #----------------

    def save_image(self, filename):
        '''
        Save the plot itself as a png.
        
        @param filename: full path to file
        @type filename: str
        '''
        self.ax_tsne.get_figure().savefig(filename)
        
        
    #--------------------------
    # create_viz_init_dict
    #----------------
        
    def create_viz_init_dict(self, fittedModelFileName=None):
        '''
        Return a dict that contains the state needed
        for a restart.
        '''
        init_parms = {'draft_mode' : TSNECourseVisualizer.draft_mode,
                      'active_acad_grps' : TSNECourseVisualizer.active_acad_grps,
                      'perplexity' : TSNECourseVisualizer.perplexity,
                      'fittedModelFileName' : fittedModelFileName
                      }
        return init_parms
        
    
    #--------------------------
    # add_course_highlight 
    #----------------
    
    def add_course_highlight(self, course_name):
        try:
            x,y = self.course_xy[course_name]
        except KeyError:
            self.control_board_error('Course %s not in model (maybe used draft mode?).' % course_name)
            return
        
        CourseHighlight.get_instance().add_course_highlight(self.ax_tsne, x,y,course_name)
        
        self.figure.canvas.draw_idle()

    #--------------------------
    # quit 
    #----------------
#**********************    
#     def quit(self):
#         '''
#         Shut down cleanly
#         '''
#         self.close()
#         TSNECourseVisualizer.status = 'stop'
#         raise RestartRequest('stop')        
#         #*****sys.exit('stop')
#**********************
    # ------------------------------------------------------- Polygon Class ----------------------
    
class Polygon(object):
    '''
    Keep adding points, draw, and erase. Control line width
    and color per instance.
    '''    
    
    def __init__(self, 
                 axes,
                 x_start, 
                 y_start,
                 line_width=TSNECourseVisualizer.POLY_SELECT_WIDTH, 
                 line_color=TSNECourseVisualizer.POLY_SELECT_COLOR,
                 background_copy=None):

        self.line_width = line_width
        self.line_color = line_color
        self.ax         = axes
        self.X = [x_start]
        self.Y = [y_start]
        
        self.fig     = axes.get_figure()
        self.canvas  = self.fig.canvas
        
        if background_copy is None:
            # Remember who the plot looks without this polygon on 
            # top of it. We'll use it for redraw speed:
            self.background = self.canvas.copy_from_bbox(self.fig.bbox)
        else:
            self.background = background_copy
        
        # Remember line segments so we can erase them:
        self.line_artists = []
        
    #--------------------------
    # add_point 
    #----------------
    
    def add_point(self, x, y, draw=True):
        self.X.append(x)
        self.Y.append(y)
        if draw:
            self.canvas.restore_region(self.background)
            line_artist = self.ax.plot(self.X[-2:], self.Y[-2:],
                                       linewidth=self.line_width,
                                       color=self.line_color,
                                       dash_capstyle='round'
                                       )
            
            # The line artist is returned as a singleton
            # array, so extend instead of append:
            self.line_artists.extend(line_artist)            
            
            # Fast redraw:
            for artist in self.line_artists: 
                self.ax.draw_artist(artist)
            self.canvas.blit(self.fig.bbox)

    #--------------------------
    # is_closed 
    #----------------
    
    def is_closed(self):
        '''
        Return True if the polygon is a loop. Just a simple test
        whether the first and last point are identical.
        '''
        
        return len(self.X) > 1 and\
                   self.X[0] == self.X[-1] and\
                   self.Y[0] == self.Y[-1]
        
    #--------------------------
    # close 
    #----------------
    
    def close(self, draw=True):
        '''
        Add a point that turns the polygon into a closed
        loop. No fancy analysis around self crossings.
        Just duplicate the starting point as the end point
        '''
        
        self.add_point(self.X[0], self.Y[0], draw)
        
    
    #--------------------------
    # vertices 
    #----------------
    
    def vertices(self):
        '''
        Return a single array of two-tuples. Each
        tuple contains the x/y of one vertex. The order
        of the vertices is in order of how the points were
        added.
        
        '''
        # In Python 3 zip() returns a zip generator!
        # So to get a list, need to be explicit about
        # it:
        return list(zip(self.X, self.Y))
        
    #--------------------------
    # erase 
    #----------------
        
    def erase(self):
        for line_artist in self.line_artists:
            line_artist.remove()
        self.fig.canvas.draw_idle()
    
    # ------------------------------------------------------- CourseHighlight Class ----------------------


class CourseHighlight(object):
    
    SINGLETON_INSTANCE = None

    #--------------------------
    # __init__: singleton contructor 
    #----------------
    
    def __init__(self):
        super().__init__()

        CourseHighlight.SINGLETON_INSTANCE = self
        self.highlight_artists = {}
        
    #--------------------------
    # get_instance 
    #----------------
    
    @classmethod
    def get_instance(cls):
        if CourseHighlight.SINGLETON_INSTANCE is None:
            # Need to create the singleton instance; init method
            # will assign the instance to the SINGLETON_INSTANCE class var:
            return CourseHighlight()
        else:
            return CourseHighlight.SINGLETON_INSTANCE
        
    #--------------------------
    # add_course_highlight 
    #----------------
    
    def add_course_highlight(self, ax, x, y, course_name):
        '''
        Add a course scatter dot highlight: an annotation
        with an arrow to the dot, and the name of the course
        in a plaque.
        
        @param ax: the chart with the dots
        @type ax: subplot
        @param x: dot's x coord
        @type x: float
        @param y: dot's y coord
        @type y: float
        @param course_name: text for the annotation plaque
        @type course_name: string
        @return: annotation object
        @return: annotation
        '''
        
        self.x  = x
        self.y  = y
        self.ax = ax

        # Already have an annotation on this course?
        try:
            artist = self.highlight_artists[course_name]
            return artist
        except KeyError:
            pass

        # No, new course:
        self.highlight_artist = ax.annotate(course_name,
                                            xy=(x,y), xycoords='data',
                                            xytext=(-70,-80), textcoords='offset points',
                                            size=20,
                                            bbox=dict(boxstyle="round4,pad=.5", fc="0.8"),
                                            arrowprops=dict(arrowstyle="->",
                                                            connectionstyle="angle,angleA=0,angleB=-90,rad=10")
                                            )
        self.highlight_artists[course_name] = self.highlight_artist
        return self.highlight_artist
    
    #--------------------------
    #  remove_course_highlight
    #----------------
    
    def remove_course_highlight(self, course_name_or_highlight_artist):
        
        if isinstance(course_name_or_highlight_artist, matplotlib.text.Annotation):
            course_name = course_name_or_highlight_artist.get_text()
        else:
            course_name = course_name_or_highlight_artist
        try:
            self.highlight_artists[course_name].remove()
            del self.highlight_artists[course_name]
        except KeyError:
            pass
        
        self.ax.get_figure().canvas.draw_idle()
        
    #--------------------------
    # remove_all_course_highlights 
    #----------------
    
    def remove_all_course_highlights(self):
        course_names = self.highlight_artists.keys()
        for course_name in course_names:
            # Entries in the dict are removed by this call:
            self.remove_course_highlight(course_name)
        
    #--------------------------
    # course_names 
    #----------------
    
    def course_names(self):
        return self.highlight_artists.keys()
    
    #--------------------------
    # contains 
    #----------------
    
    def contains(self, mouse_event):
        '''
        Given a mouse event, return a highlight artist
        if that artist contains the mouse event location.
        Else return False
        
        @param mouse_event: event containing x/y coords
        @type mouse_event: mouseevent.
        '''
        for highlight_artist in self.highlight_artists.values():
            if highlight_artist.contains(mouse_event):
                return highlight_artist
        return False
        
#     #--------------------------
#     # draw_artists 
#     #----------------
#     
#     def draw_artists(self):
#         '''
#         Refresh just the annotations:
#         '''
#         plt.draw()
#         
    # ------------------------------------------------------- CoursePoints Class ----------------------

class CoursePoints(dict):
    '''
    A dict mapping nparray coordinate points to scatterplot
    objects, i.e. to what's returned from an ax.scatter() call.
    Special methods: contains_course_point(<nparray of one coordinate pair>)
                     contains_course_points(array of <nparray of one coordinate pair>)
    '''
    
    def __init__(self):
        super(CoursePoints, self).__init__()
        

    #--------------------------
    # __setitem__ 
    #----------------

    def __setitem__(self, coord_pair, course_point):
        '''
        Handle coordinate pairs that are arrays, tuples, or numpy arrays.
        
        @param coord_pair: Coordinates to find in the collection
        @type coord_pair: {array | tuple | numpy.narray
        @param course_point: a scatter plot point, i.e. a course point
        @type course_point: PathCollection
        '''
        if isinstance(coord_pair, np.ndarray):
            coord_pair = coord_pair.tolist()
        super(CoursePoints, self).__setitem__(tuple(coord_pair), course_point)
        
    #--------------------------
    # contains_course_point 
    #----------------
        
    def contains_course_point(self, path, coord_pair):
        '''
        Given one array of two coordinates, return the course point
        that lives there, or None, if no course point lives at that location.
        @param coord_pair: Array of two floats. Coordinate system must match elements that 
            were previously put in.
        @type coord_pair: [float,float]
        @return: scatter artist or None.
        @rtype: PathCollection or None
        '''
        coord_pair_tuple = tuple(coord_pair)
        if path.contains_point(coord_pair):
            return self[coord_pair_tuple]
        else:
            return None 
    
    #--------------------------
    # contains_course_points 
    #----------------
    
    def contains_course_points(self, path):
        '''
        Given a path around course points, i.e. scatter artists.
        return the scatter artists that lie within the path:

        @return: Possibly empty array of scatter artists
        @rtype: [PathCollection]
        '''
        # Get an array of booleans that indicate which of the 
        # pairs we have stored lie within the path. This will
        # be a mask in the form of a True/False array:
        
        coord_pairs = list(self.keys())
        contained_pair_booleans = path.contains_points(coord_pairs)
        # Our keys are tuples of coordinate pairs. The itertools' compress()
        # method returns an iterator with just the non-masked array/list members:
        scatter_artists = [self[coord_pair] for coord_pair in itertools.compress(coord_pairs, contained_pair_booleans)] 
        return scatter_artists

    # ------------------------------------------------------- PseudoDotArtist Class ----------------------
    
class PseudoDotArtist(object):
    '''
    A featherlight stand-in for a matplotlib scatter plot
    dot. I.e. for a PathCollection instance. Whenever a dot
    would be covering an already existing dot, we create an
    instance of this class. This subterfuge helps speed up 
    redraw.
    '''
    
    def __init__(self, course_name, coords, picker_distance=None):
        self.course_name = course_name
        self.coords = coords
        if picker_distance is None:
            self.picker_distance = TSNECourseVisualizer.PICK_RADIUS
        else:
            self.picker_distance = picker_distance
            
        self.x = coords[0]
        self.y = coords[1]
        # Compute the bounding rectangle, given by
        # the picker variable:
        
    def get_label(self):
        return self.course_name
    
    def contained_in(self, mouse_event):
        x = mouse_event.xdata
        y = mouse_event.ydata
        is_contained = x >= self.x - self.picker_distance and \
                       x <= self.x + self.picker_distance and \
                       y >= self.y - self.picker_distance and \
                       y <= self.y + self.picker_distance
        return is_contained
        
    def get_offsets(self):
        '''
        Like real artists: return a list of coordinate 2-tuples.
        '''
        return [self.coords]



# ----------------------------------------------- Main -------------------
if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description="Show Tsne projection of Stanford courses"
                                     )

    parser.add_argument('-d', '--draft',
                        help='Operate in full mode, instead of draft (slower). Default: draft',
                        action='store_true',
                        default=True
                        );

    args = parser.parse_args();
    
    vector_creator = CourseVectorsCreator()
    data_dir = os.path.join(os.path.dirname(__file__), '../data/')
    vector_creator.load_word2vec_model(os.path.join(data_dir, 'best_modelvec250_win15.model'))
    visualizer = TSNECourseVisualizer(vector_creator,  #@UnusedVariable
                                      in_queue=None, 
                                      out_queue=None, 
                                      draft_mode=args.draft)
    print('Visualizer exited.')
    