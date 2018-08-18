'''
@author: paepcke
'''

from collections import OrderedDict
import csv
import functools
import itertools
from logging import error as logErr
from logging import info as logInfo
from logging import warn as logWarn
import logging
import os
import re
import sys
import warnings

from MulticoreTSNE import  MulticoreTSNE as TSNE
from matplotlib.collections import PathCollection as tsne_dot_class
from matplotlib.path import Path
from matplotlib.widgets import LassoSelector

from color_constants import colors
from course_vector_creation import CourseVectorsCreator
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


def fxn():
    warnings.warn("deprecated", DeprecationWarning)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    fxn()                

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

class TSNECourseVisualizer(object):
    '''
    classdocs
    '''
    
    # Number of courses to list when user clicks
    # on a clump of stacked marks:
    MAX_NUM_COURSES_TO_LIST = 15
    
    # File with a bulk of explict mappings from course name to acadGrp:
    course2school_map_file  = os.path.join(os.path.dirname(__file__), 'courseNameAcademicOrg.csv')
    course_descr_file       = os.path.join(os.path.dirname(__file__), 'crsNmDescriptions.csv')
    
    # Dict mapping course names to short and long descriptions:
    course_descr_dict = {}
    
    # Dict for the explicit course --> academicGroup map in course2school_map_file:
    course_school_dict = {}

    acad_grp_name_root = {
        'AA'     : 'ENGR',
        'ACCT'  : 'GSB',
        'AFRICA' : 'H&S',
        'AME'   : 'H&S',        
        'AMSTUD' : 'H&S',
        'ANES' : 'MED',
        'ANTHRO' : 'H&S',
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
        'CAT' : 'H&S',
        'CBIO' : 'MED',
        'CEE' : 'ENGR',
        'CHEM' : 'H&S',
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
        'ENGLISH' : 'H&S',
        'ENGR' : 'ENGR',
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
        'HISTORY' : 'H&S',
        'HRM' : 'GSB',
        'HRP' : 'MED',        
        'HPS' : 'H&S',
        'HRP' : 'H&S',        
        'HUM' : 'H&S',
        'IBER' : 'H&S',
        'ICA' : 'H&S',
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
        'MLA' : 'CSP',
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
        'PE'   : 'H&S',
        'PHIL' : 'H&S',
        'PHOTON' : 'H&S',
        'PHYSICS' : 'H&S',
        'POLE'  : 'GSB',
        'POLISC' : 'H&S',
        'PORT' : 'H&S',        
        'PSY' : 'H&S',
        'PUB' : 'H&S',        
        'PWR' : 'H&S',
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
        'SPEC' : 'VPSA',
        'STATS' : 'H&S',
        'STEMREM' : 'MED',        
        'STRA' : 'GSB',
        'STS' : 'H&S',
        'SUST' : 'EARTH',
        'SYMSYS' :  'H&S',      
        'SURG' : 'MED',
        'TAPS' : 'H&S',
        'THINK' : 'VPUE',
        'TIBET' : 'H&S',
        'URBANST' : 'H&S',
        'UAR' : 'VPUE',
        'UROL'  : 'MED',
        'VPTL' : 'VPTL',
        'WELLNESS' : 'H&S',
        }    
 
    # Assign each major academic group to a color
    # For color choices see https://matplotlib.org/users/colors.html
    # 'tab:xxx' stands for Tableau. These are Tableau recommended
    # categorical colors. Use one color to lump together acad groups
    # we are less interested in to help unclutter the scatterplot:
    
    LUMP_COLOR = colors['darkgray'].hex_format()
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
            ('ATH'  ,  LUMP_COLOR),
            ('LAW'  ,  LUMP_COLOR),
            ('VPSA' ,  LUMP_COLOR),
            ('VPTL' ,  LUMP_COLOR),
            ('CSP'  ,  LUMP_COLOR)
        ]
    ) 
    
    def __init__(self, course_vectors_model):
        '''
        Constructor
        '''
        # Read the mapping from course name to academic organization 
        # roughly (a.k.a. school):
        
        with open(TSNECourseVisualizer.course2school_map_file, 'r') as fd:
            reader = csv.reader(fd)
            for (course_name, school_name) in reader:
                TSNECourseVisualizer.course_school_dict[course_name] = school_name
                
        # If available, read the course descriptions:
        
        try:
            with open(TSNECourseVisualizer.course_descr_file, 'r') as fd:
                reader = csv.reader(fd)
                try:
                    for (course_name, descr, description) in reader:
                        TSNECourseVisualizer.course_descr_dict[course_name] = {'descr' : descr, 'description' : description}
                except ValueError as e:
                    logErr(`e`)
                    sys.exit()
        except IOError:
            logWarn("No course description file found. Descriptions won't be available.")
        
                
        # Regex to separate SUBJECT from CATALOG_NBR in a course name:
        self.crse_subject_re = re.compile(r'([^0-9]*).*$')
        
        course_name_list = self.create_course_name_list(course_vectors_model)                
        # Map each course to the Tableau categorical color of its school (academicGroup):
        color_map = self.get_acad_grp_to_color_map(course_name_list)
        
        # No text in the course_name list yet:
        self.course_names_text_artist = None
        
        # No course points plotted yet. Has a dictionary interface:
        self.course_points = CoursePoints()
        # No course points lassoed yet:
        self.lassoed_course_points = []
        
        self.plot_tsne_clusters(course_vectors_model, color_map, course_name_list)
        
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
        # return list(filter(lambda name: name != '\N', course_names))
        
    def plot_tsne_clusters(self, course_vector_model, color_map, course_name_seq):
        '''
        Creates and TSNE course_vector_model and plots it
        '''
        
        #**************
        # logInfo("Testing course names...")
        # for course_name in course_name_seq:
        #     group_name = self.group_name_from_course_name(course_name)
        #
        # logInfo("Done testing course names.")
        #**************        
        
        labels_course_names = []
        tokens_vectors      = []
        
        for course_name in course_vector_model.wv.vocab:
            tokens_vectors.append(course_vector_model[course_name])
            labels_course_names.append(course_name)
        
        logInfo('Mapping %s word vector dimensions to 2D...' % course_vector_model.vector_size)
        tsne_model = TSNE(perplexity=60, 
                          n_components=2, 
                          init='random', 
                          n_iter=2500, 
                          random_state=23,
                          n_jobs=4) # n_jobs is part of the MulticoreTSNE
        logInfo('Done mapping %s word vector dimensions to 2D.' % course_vector_model.vector_size)
        logInfo('Fitting course vectors to t_sne model...')
        #*******
        np_tokens_vectors = np.array(tokens_vectors)
        #*****new_values = tsne_model.fit_transform(np_tokens_vectors)
        new_values = tsne_model.fit_transform(np_tokens_vectors[0:500,])
        #****
        logInfo('Done fitting course vectors to t_sne model.')
    
        x = []
        y = []
        for value in new_values:
            x.append(value[0])
            y.append(value[1])
            
        # Two plots side by side the left one three times as wide
        # as the one on the right:
        fig,axes_arr = plt.subplots(nrows=1, ncols=2, 
                                    gridspec_kw={'width_ratios':[3,1]},
                                    figsize=(15,10)
                                    )
        self.ax_tsne = axes_arr[0]
        self.ax_course_list = axes_arr[1]
        self.prepare_course_list_panel()
        # List of point coordinates:
        self.xys = []

        for i in range(len(x)):
            try:
                course_name = labels_course_names[i]
            except IndexError:
                logWarn("Ran out of course names at i=%s" % i)
                continue
            acad_group = self.group_name_from_course_name(course_name)
            if acad_group is None:
                # One course has name '\N', which obviously has
                # no acad group associated with it. Skip over that
                # data point:
                continue
            
            #******************
            # Leave out H&S:
            #if acad_group == 'H&S':
            #    continue
            # Thin out the chart for test speed:
            if not (acad_group == 'MED' or acad_group == 'ENGR'):
                continue
            #***************
            scatter_plot = self.ax_tsne.scatter(x[i],y[i],
                                      c=color_map[course_name],
                                      picker=5,
                                      label=labels_course_names[i])
            # Add this point's coords to our list. The offsets are 
            # a list of this scatterplot's points. But there is only 
            # a single one, since we add one by one:
            
            self.course_points[scatter_plot.get_offsets()[0]] = scatter_plot

        self.add_legend(scatter_plot)

        # Prepare annotation popups:
        annot = self.ax_tsne.annotate("",
                            xy=(0,0),
                            xytext=(20,20),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->")
                            )
        annot.set_visible(False)
        # Use currying to create a function that called when
        # mouse moves. But in addition to the event, several 
        # other quantities are passed:
        curried_hover = functools.partial(self.hover, annot)
        
        self.lasso = LassoSelector(self.ax_tsne, onselect=self.onselect)
        
        # Connect the listeners:
        
        # Hovering:
        fig.canvas.mpl_connect("motion_notify_event", curried_hover)
        
        # Clicking on a dot:
        fig.canvas.mpl_connect("pick_event", self.onpick)

        # Double clicking anywhere:
        fig.canvas.mpl_connect("button_press_event", self.onclick)
                                      
        # Lassoing points:
        fig.canvas.mpl_connect("key_press_event", self.onenter_key)
        
        logInfo('Done populating  t_sne plot.')

        plt.show()
        
    def add_legend(self, scatter_plot):
        
        ax = scatter_plot.axes
        LUMP_COLOR = TSNECourseVisualizer.LUMP_COLOR
        
        # Shrink current axis's height by 10% on the bottom
        # to make room for a horizontal legend:
        #***********
        #box = ax.get_position()
        #ax.set_position([box.x0, box.y0 + box.height * 0.1,
        #         box.width, box.height * 0.9])
        #***********        
        
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
            

    def update_annot(self, mark_ind, annot):
        plot_element = self.ax_tsne.get_children()[mark_ind]
        pos = plot_element.get_offsets()
        # Position is like array([[9.90404368, 2.215768  ]]). So
        # grab first pair:
        annot.xy = pos[0]
        course_name   = plot_element.get_label()
        acad_grp_name = self.group_name_from_course_name(course_name)
        if acad_grp_name is None:
            # Ignore the one course named '\N':
            return
        label_text    = course_name + '/' + acad_grp_name
        annot.set_text(label_text)
        dot_color = plot_element.get_facecolor()[0]
        annot.get_bbox_patch().set_facecolor(dot_color)
        annot.get_bbox_patch().set_alpha(0.4)

    def hover(self, annot, event):
        vis = annot.get_visible()
        fig = self.ax_tsne.get_figure()
        
        if event.inaxes == self.ax_tsne:
            try:
                # plot_element.contains(event) returns a two-tuple: (False, {'ind': array([], dtype=int32)})
                # Look for the first dot where contains is True:
                mark_ind = next(i for i,plot_element in enumerate(self.ax_tsne.get_children()) 
                                if plot_element.contains(event)[0] and isinstance(plot_element, tsne_dot_class) 
                                )
            except StopIteration:
                mark_ind = None
            if mark_ind is not None:
                self.update_annot(mark_ind, annot)
                annot.set_visible(True)
                fig.canvas.draw_idle()
            else:
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()


    def update_course_list_display(self, new_text, refresh_course_name_display=False):
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

    def append_to_course_list_display(self, course_name, refresh_course_name_display=False):
        '''
        Get already-displayed course descriptions. See whether we already have more
        than our upper limit. If not, find courses descriptions, make a new line for
        the display (course name plus descr, plus description). 
        
        If refresh_course_name_display is True, erase current list on the display,
        and replace it with the new content:
        
        @param course_name:
        @type course_name:
        @param refresh_course_name_display:
        @type refresh_course_name_display:
        '''

        try:
            if self.course_names_text_artist is not None:
                
                # Already showing text; internally add new course to that
                # list if that doesn't exceed max courses to show, and 
                # erase current text if we will replace the text:
                
                curr_text = self.course_names_text_artist.get_text()
                # Already have max lines plus a line saying "... more buried under."?
                num_lines = curr_text.count('\n')
                if num_lines >= TSNECourseVisualizer.MAX_NUM_COURSES_TO_LIST + 1:
                    new_text = None
                    return
                elif num_lines == TSNECourseVisualizer.MAX_NUM_COURSES_TO_LIST:
                    new_text = curr_text + '\n... more buried under.'
                    return 
                # Have room for more courses in the displayed list:
                curr_text += '\n'
            else:
                curr_text = ''
                
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
                if description != '\N':
                    new_text += '; ' + description
        finally:
            if new_text is not None:
                self.update_course_list_display(new_text, refresh_course_name_display)


    def onpick(self, event):
        
        course_name = event.artist.get_label()
        
        # Get existing list in course name list and
        # add the new course to it:
          
        self.append_to_course_list_display(course_name, refresh_course_name_display=True)

    def onclick(self, event):
        '''
        If double click, erase text area:
        
        @param event:
        @type event:
        '''
        if event.dblclick and self.course_names_text_artist is not None:
            self.course_names_text_artist.remove()
            self.course_names_text_artist = None
            self.lassoed_course_points    = []
            self.ax_course_list.get_figure().canvas.draw_idle()
            
    def onenter_key(self, event):
        if not event.key == "enter":
            return
        print('Pressed Enter')
        #******self.disconnect()

    def onselect(self, verts):
        lasso_path = Path(verts)
        self.lassoed_course_points.extend(self.course_points.contains_course_points(lasso_path))
        # Output list of names to GUI:
        course_names = [course_point.get_label() for course_point in self.lassoed_course_points]
        # Remove duplicates:
        for course_name in course_names:
            self.append_to_course_list_display(course_name,refresh_course_name_display=False)
        self.ax_course_list.get_figure().canvas.draw_idle()
        #print('Selected courses: %s.' % course_names)

    def disconnect(self):
        self.lasso.disconnect_events()
        self.ax_tsne.get_figure().canvas.draw_idle()

    def get_acad_grp_to_color_map(self, course_name_list):

        color_map = {}
        for course_name in course_name_list:
            if course_name == '\N':
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
                raise ValueError("Don't have color assignment for course/acadGrp %s/%s." % (course_name, school))
        return color_map


    def group_name_from_course_name(self, course_name):
        
        if course_name == '\N':
            return None
                
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
                raise ValueError('Could not find subject for %s' % course_name)
        
    def prepare_course_list_panel(self):
        #*****self.ax_course_list.facolor('red')
        self.ax_course_list.set_title('List of Clicked Courses', fontsize=15)
        #*****self.ax_course_list.suptitle('Double-click to erase', fontsize=10, style='italic')
        self.ax_course_list.axis('off')

class CoursePoints(dict):
    '''
    A dict mapping nparray coordinate points to scatterplot
    objects, i.e. to what's returned from an ax.scatter() call.
    Special methods: contains_course_point(<nparray of one coordinate pair>)
                     contains_course_points(array of <nparray of one coordinate pair>)
    '''
    
    def __init__(self):
        super(CoursePoints, self).__init__()
        
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
        
        coord_pairs = self.keys()
        contained_pair_booleans = path.contains_points(coord_pairs)
        # Our keys are tuples of coordinate pairs. The itertools' compress()
        # method returns an iterator with just the non-masked array/list members:
        scatter_artists = [self[coord_pair] for coord_pair in itertools.compress(coord_pairs, contained_pair_booleans)] 
        return scatter_artists

    
#***************   
if __name__ == '__main__':
    vector_creator = CourseVectorsCreator()
    vector_creator.load_word2vec_model(os.path.join(os.getenv('HOME'), 'Project/Pathways/Data/Course2VecData/course2vecModelWin10.model'))
    visualizer = TSNECourseVisualizer(vector_creator)
    
        