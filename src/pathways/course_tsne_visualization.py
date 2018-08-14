'''
@author: paepcke
'''

import csv
from logging import info as logInfo
from logging import warn as logWarn
import logging
import re
import os

from MulticoreTSNE import  MulticoreTSNE as TSNE

from color_constants import colors

from course_vector_creation import CourseVectorsCreator
import matplotlib.pyplot as plt


logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

class TSNECourseVisualizer(object):
    '''
    classdocs
    '''
    # File with a bulk of explict mappings from course name to acadGrp:
    course2school_map_file  = os.path.join(os.path.dirname(__file__), 'courseNameAcademicOrg.csv')
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
        'ENERGY' : 'ENGR',
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
    # categorical colors:
    
    course_color_dict   = {
        'ENGR' :  colors['blue'].hex_format(), 
        'GSB'  :  colors['banana'].hex_format(), 
        'H&S'  :  colors['darkseagreen'].hex_format(),
        'MED'  :  colors['red1'].hex_format(),
        'UG'   :  colors['purple'].hex_format(),
        'EARTH':  colors['brick'].hex_format(),         # Brown
        'EDUC' :  colors['bisque1'].hex_format(),       # light brownish
        'VPUE' :  colors['cyan2'].hex_format(),
        'ATH'  :  colors['darkgray'].hex_format(),
        'LAW'  :  colors['darkgray'].hex_format(), 
        'VPSA' :  colors['darkgray'].hex_format(),
        'VPTL' :  colors['darkgray'].hex_format(), 
        'CSP'  :  colors['darkgray'].hex_format(), 
        }
#     course_color_dict  = {'ENGR' : 'tab:blue',
#                           'GSB'  : 'tab:pink',
#                           'H&S'  : 'tab:green',
#                           'MED'  : 'tab:red',
#                           'UG'   : 'tab:purple',
#                           'EARTH': 'tab:brown',
#                           'EDUC' : 'tab:cyan',
#                           'VPUE' : 'tab:orange',
#                           'ATH'  : 'tab:olive',
#                           'LAW'  : 'tab:gray',
#                           'VPSA' : 'tab:gray',
#                           'VPTL' : 'tab:gray',
#                           'CSP'  : 'tab:gray',  # Continuous education; MLA courses
#                           }

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
                
        # Regex to separate SUBJECT from CATALOG_NBR in a course name:
        self.crse_subject_re = re.compile(r'([^0-9]*).*$')
        
        course_name_list = self.create_course_name_list(course_vectors_model)                
        # Map each course to the Tableau categorical color of its school (academicGroup):
        color_map = self.get_acad_grp_to_color_map(course_name_list)
        
        self.plot_tsne_clusters(course_vectors_model, color_map, course_name_list)
        
    def create_course_name_list(self, course_vectors_model):
        '''
        Create a list of tokens, i.e. course names as they are ordered
        in the model's vocabulary list.
        
        @param course_vectors_model: trained skip gram model for the input 'sentences':
        @type course_vectors_model: CourseVectorsCreator instance
        '''
        
        course_names = course_vectors_model.wv.vocab.keys()
        # Remove '\N' entries:
        return list(filter(lambda name: name != '\N', course_names))
        
    def plot_tsne_clusters(self, course_vector_model, color_map, course_name_seq):
        '''
        Creates and TSNE course_vector_model and plots it
        '''
        
        #**************
#         logInfo("Testing course names...")
#         for course_name in course_name_seq:
#             group_name = self.group_name_from_course_name(course_name)
# 
#         logInfo("Done testing course names.")
        #**************        
        
        word_vectors = course_vector_model.wv.vectors
        
        logInfo('Mapping %s word vector dimensions to 2D...' % course_vector_model.vector_size)
        tsne_model = TSNE(perplexity=60, 
                          n_components=2, 
                          init='random', 
                          n_iter=2500, 
                          random_state=23,
                          n_jobs=4) # n_jobs is part of the MulticoreTSNE
        logInfo('Done mapping %s word vector dimensions to 2D.' % course_vector_model.vector_size)
        logInfo('Fitting course vectors to t_sne model...')
        new_values = tsne_model.fit_transform(word_vectors)
        logInfo('Done fitting course vectors to t_sne model.')
    
        x = []
        y = []
        for value in new_values:
            x.append(value[0])
            y.append(value[1])
            
        plt.figure(figsize=(16, 16))
        logInfo('Populating  t_sne plot...') 
        for i in range(len(x)):
            try:
                course_name = course_name_seq[i]
            except IndexError:
                logWarn("Ran out of course names at i=%s" % i)
                continue
            #***************
            acad_group = self.group_name_from_course_name(course_name)
            # Leave out H&S:
            if acad_group == 'H&S':
                continue
            #***************
            plt.scatter(x[i],y[i], c=color_map[course_name])
            #plt.annotate(labels[i],
            #             xy=(x[i], y[i]),
            #             xytext=(5, 2),
            #             textcoords='offset points',
            #             ha='right',
            #             va='bottom')
        logInfo('Done populating  t_sne plot.') 
        plt.show()
        return tsne_model

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
                return TSNECourseVisualizer.acad_grp_name_root[subject_part]
            else:
                raise ValueError('Could not find subject for %s' % course_name)
        
    
if __name__ == '__main__':
    vector_creator = CourseVectorsCreator()
    vector_creator.load_word2vec_model(os.path.join(os.getenv('HOME'), 'Project/Pathways/Data/Course2VecData/course2vecModelWin10.model'))
    visualizer = TSNECourseVisualizer(vector_creator)
    
        