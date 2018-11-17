'''
Created on Nov 8, 2018

@author: paepcke
'''
import csv
from logging import error as logErr
from logging import warning as logWarn
import os
import re
import sys

from .constants import acad_grp_name_root


#from logging import info as logInfo
class CourseInfoCollector(object):
    '''
    Gathers information for every course: its admin name, 
    as well as short and long descriptions. Maybe more in 
    future.
    
    Depends on files ourseNameAcademicOrg.csv and crsNmDescriptions.csv
    '''

    # File with a bulk of explict mappings from course name to acadGrp:
    course2school_map_file  = os.path.join(os.path.dirname(__file__), '../data/courseNameAcademicOrg.csv')
    course_descr_file       = os.path.join(os.path.dirname(__file__), '../data/crsNmDescriptions.csv')
    
    #--------------------------
    # Constructor 
    #----------------
    
    def __init__(self):
        '''
        Prepare the data structures for all courses:
        '''
        
        self.acad_grp_name_root = acad_grp_name_root
        self.course_school_dict = {}
        self.course_descr_dict  = {}
        
        # Regex to separate SUBJECT from CATALOG_NBR in a course name:
        self.crse_subject_re = re.compile(r'([^0-9]*).*$')

    
        with open(CourseInfoCollector.course2school_map_file, 'r') as fd:
            reader = csv.reader(fd)
            for (course_name, school_name) in reader:
                self.course_school_dict[course_name] = school_name
                
        # Read the course descriptions:
        self.init_course_desc()
                
    #--------------------------
    # get_acad_grp
    #----------------

    def get_acad_grp(self, course_name):
        '''
        Find the academic groups of courses. We first try the course_school_dict. 
        If the course is not found there, try a heuristic.
        
        @param course_name_list: list of course names involved in the plot
        @type course_name_list: [string]
        @return: academic group, or KeyError if not found
        @rtype: str
        @raise exception: KeyError
        '''

        # One course name shows as '\N'; ignore it:
        if course_name == '\\N':
            return None
        
        # Another one is 'GR-SV' and some other: don't know what those are:
        hopeful = True
        for hopeless_course_name_root in ['GR-SV', 'UGNM-SV', 'CASA', 
                                          'GR-NDO', 'UGNM-GNM','INSST-IHN'
                                          ]:
            # Yes, we unnecessarily go through all, but I'm tired:
            if course_name.startswith(hopeless_course_name_root):
                return None
                
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
            return None
        try:
            # First try the explicit course-->acadGrp map:
            school = self.course_school_dict[course_name]
        except KeyError:
            try:
                # Didn't find a mapping. Use heuristic:
                school = self.group_name_from_course_name(course_name)
            except KeyError:
                raise ValueError("Don't know to which academic group (~=school) '%s' belongs." % course_name)
        return school

    #--------------------------
    # get_course_descr 
    #----------------

    def get_course_descr(self, course_name):
        '''
        Given a course catalog number, return a two-tuple:
        short description, and long description if available.
        For short descriptions we clean up any leading and 
        trailing <b> and </b> tags, respectively.
        
        The long description can be '\\N'. We replace this with 
        the empty string: ''
        
        @param course_name: catalog name, such as CS106A
        @type course_name: str
        @returns: short and long descriptions; long descr may be None.
        @rtype: (str, {str | None})
        @raise KeyError
        '''
        
        short_long_dict = self.course_descr_dict[course_name]
        descr = short_long_dict['descr']
        # We assume that if we have a trailing </b>, then
        # we also have a leading <b>:
        if descr.endswith('</b>'):
            descr = descr[len('<b>'):len(descr) - len('</b>')]
        long_descr = short_long_dict['description']
        if long_descr == '\\N':
            long_descr = ''
        
        return (descr, long_descr)


    # -------------------- Lookup and Init Functions -------------------

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
            return self.course_school_dict[course_name]
        except KeyError:
            pass
        
        # Heuristics:
        if course_name.startswith('AA'):
            return self.acad_grp_name_root['AA']
        if course_name.startswith('AFRICA'):
            return self.acad_grp_name_root['AFRICA']
        if course_name.startswith('AME'):
            return self.acad_grp_name_root['AME']
        if course_name.startswith('AMSTUD'):
            return self.acad_grp_name_root['AMSTUD']
        elif course_name.startswith('ANTHRO'):
            return self.acad_grp_name_root['ANTHRO']
        elif course_name.startswith('APP'):
            return self.acad_grp_name_root['APP']        
        elif course_name.startswith('ARAB'):
            return self.acad_grp_name_root['ARAB']        
        elif course_name.startswith('ARCH'):
            return self.acad_grp_name_root['ARCH']
        elif course_name.startswith('ART'):
            return self.acad_grp_name_root['ART']
        elif course_name.startswith('ASN'):
            return self.acad_grp_name_root['ASN']
        elif course_name.startswith('ATHLETIC'):
            return self.acad_grp_name_root['ATHLETIC']
        elif course_name.startswith('BIOC'):
            return self.acad_grp_name_root['BIOC']
        elif course_name.startswith('BIODS'):
            return self.acad_grp_name_root['BIODS']
        elif course_name.startswith('BIOE'):
            return self.acad_grp_name_root['BIOE']
        elif course_name.startswith('BIOH'):
            return self.acad_grp_name_root['BIOH']
        elif course_name.startswith('BIOM'):
            return self.acad_grp_name_root['BIOM']
        elif course_name.startswith('BIOPH'):
            return self.acad_grp_name_root['BIOPH']
        elif course_name.startswith('BIO'):
            return self.acad_grp_name_root['BIO']
        elif course_name.startswith('BIOS'):
            return self.acad_grp_name_root['BIOS']
        elif course_name.startswith('CAT'):
            return self.acad_grp_name_root['CAT']
        elif course_name.startswith('CEE'):
            return self.acad_grp_name_root['CEE']
        elif course_name.startswith('CHIL'):
            return self.acad_grp_name_root['CHIL']
        elif course_name.startswith('CHEM'):
            return self.acad_grp_name_root['CHEM']
        elif course_name.startswith('CHIN'):
            return self.acad_grp_name_root['CHIN']
        elif course_name.startswith('CHICAN'):
            return self.acad_grp_name_root['CHICAN']
        elif course_name.startswith('CLASS'):
            return self.acad_grp_name_root['CLASS']
        elif course_name.startswith('CME'):
            return self.acad_grp_name_root['CME']
        elif course_name.startswith('COMPLIT'):
            return self.acad_grp_name_root['COMPLIT']
        elif course_name.startswith('CSRE'):       # Must be before CS
            return self.acad_grp_name_root['CSRE']
        elif course_name.startswith('CS'):          
            return self.acad_grp_name_root['CS']
        elif course_name.startswith('CTL'):
            return self.acad_grp_name_root['CTL']
        elif course_name.startswith('DAN'):
            return self.acad_grp_name_root['DAN']
        elif course_name.startswith('DBIO'):
            return self.acad_grp_name_root['DBIO']
        elif course_name.startswith('DRAMA'):
            return self.acad_grp_name_root['DRAMA']
        elif course_name.startswith('EARTH'):
            return self.acad_grp_name_root['EARTH']
        elif course_name.startswith('EAST'):
            return self.acad_grp_name_root['EAST']
        elif course_name.startswith('ECON'):
            return self.acad_grp_name_root['ECON']
        elif course_name.startswith('EDUC'):
            return self.acad_grp_name_root['EDUC']
        elif course_name.startswith('EESOR'):      # Order of all EE* is important
            return self.acad_grp_name_root['EESOR']
        elif course_name.startswith('EEES'):
            return self.acad_grp_name_root['EEES']
        elif course_name.startswith('EESS'):
            return self.acad_grp_name_root['EESS']
        elif course_name.startswith('EES'):
            return self.acad_grp_name_root['EES']
        elif course_name.startswith('EFS'):
            return self.acad_grp_name_root['EFS']
        elif course_name.startswith('EMED'):
            return self.acad_grp_name_root['EMED']
        elif course_name.startswith('ESS'):
            return self.acad_grp_name_root['ESS']
        elif course_name.startswith('EE'):
            return self.acad_grp_name_root['EE']
        elif course_name.startswith('ENERGY'):
            return self.acad_grp_name_root['ENERGY']
        elif course_name.startswith('ENGLISH'):
            return self.acad_grp_name_root['ENGLISH']
        elif course_name.startswith('ENV'):
            return self.acad_grp_name_root['ENV']
        elif course_name.startswith('ETHI'):
            return self.acad_grp_name_root['ETHI']
        elif course_name.startswith('FAMMED'):
            return self.acad_grp_name_root['FAMMED']
        elif course_name.startswith('FEM'):
            return self.acad_grp_name_root['FEM']
        elif course_name.startswith('FILM'):
            return self.acad_grp_name_root['FILM']
        elif course_name.startswith('FINAN'):
            return self.acad_grp_name_root['FINAN']
        elif course_name.startswith('FREN'):
            return self.acad_grp_name_root['FREN']
        elif course_name.startswith('GEOP'):
            return self.acad_grp_name_root['GEOP']
        elif course_name.startswith('GER'):
            return self.acad_grp_name_root['GER']
        elif course_name.startswith('GES'):
            return self.acad_grp_name_root['GES']
        elif course_name.startswith('GS'):
            return self.acad_grp_name_root['GS']
        elif course_name.startswith('GSBGEN'):
            return self.acad_grp_name_root['GSBGEN']
        elif course_name.startswith('HISTORY'):
            return self.acad_grp_name_root['HISTORY']
        elif course_name.startswith('HPS'):
            return self.acad_grp_name_root['HPS']
        elif course_name.startswith('HRM'):
            return self.acad_grp_name_root['HRM']
        elif course_name.startswith('HUM'):
            return self.acad_grp_name_root['HUM']
        elif course_name.startswith('IBER'):
            return self.acad_grp_name_root['IBER']
        elif course_name.startswith('ILAC'):
            return self.acad_grp_name_root['ILAC']
        elif course_name.startswith('INTN'):
            return self.acad_grp_name_root['INTN']
        elif course_name.startswith('IPS'):
            return self.acad_grp_name_root['IPS']
        elif course_name.startswith('ITAL'):
            return self.acad_grp_name_root['ITAL']
        elif course_name.startswith('JAP'):
            return self.acad_grp_name_root['JAP']
        elif course_name.startswith('KOR'):
            return self.acad_grp_name_root['KOR']
        elif course_name.startswith('JEWISH'):
            return self.acad_grp_name_root['JEWISH']
        elif course_name.startswith('LATI'):
            return self.acad_grp_name_root['LATI']
        elif course_name.startswith('LAW'):
            return self.acad_grp_name_root['LAW']
        elif course_name.startswith('LIN'):
            return self.acad_grp_name_root['LIN']
        elif course_name.startswith('MATH'):
            return self.acad_grp_name_root['MATH']
        elif course_name.startswith('MED'):
            return self.acad_grp_name_root['MED']
        elif course_name.startswith('MGTECON'):
            return self.acad_grp_name_root['MGTECON']
        elif course_name.startswith('MI'):
            return self.acad_grp_name_root['MI']
        elif course_name.startswith('MS&E'):
            return self.acad_grp_name_root['MS&E']
        elif course_name.startswith('ME'):
            return self.acad_grp_name_root['MS&E']
        elif course_name.startswith('MUSIC'):
            return self.acad_grp_name_root['MUSIC']
        elif course_name.startswith('NATIVE'):
            return self.acad_grp_name_root['NATIVE']
        elif course_name.startswith('OBG'):                             # Must be before 'OB'
            return self.acad_grp_name_root['OBG']
        elif course_name.startswith('OB'):
            return self.acad_grp_name_root['OB']
        elif course_name.startswith('OIT'):
            return self.acad_grp_name_root['OIT']
        elif course_name.startswith('ORAL'):
            return self.acad_grp_name_root['ORAL']
        elif course_name.startswith('OSP'):
            return self.acad_grp_name_root['OSP']
        elif course_name.startswith('ORTH'):
            return self.acad_grp_name_root['ORTH']
        elif course_name.startswith('OTO'):
            return self.acad_grp_name_root['OTO']
        elif course_name.startswith('OUTDOOR'):
            return self.acad_grp_name_root['OUTDOOR']
        elif course_name.startswith('PEDS'):
            return self.acad_grp_name_root['PEDS']
        elif course_name.startswith('PHIL'):
            return self.acad_grp_name_root['PHIL']
        elif course_name.startswith('PHOTON'):
            return self.acad_grp_name_root['PHOTON']
        elif course_name.startswith('PHYSICS'):
            return self.acad_grp_name_root['PHYSICS']
        elif course_name.startswith('POLE'):
            return self.acad_grp_name_root['POLE']        
        elif course_name.startswith('POLISC'):
            return self.acad_grp_name_root['POLISC']
        elif course_name.startswith('PORT'):
            return self.acad_grp_name_root['PORT']
        elif course_name.startswith('PSY'):
            return self.acad_grp_name_root['PSY']
        elif course_name.startswith('PUB'):
            return self.acad_grp_name_root['PUB']
        elif course_name.startswith('PWR'):
            return self.acad_grp_name_root['PWR']
        elif course_name.startswith('RELIG'):
            return self.acad_grp_name_root['RELIG']
        elif course_name.startswith('ROTC'):
            return self.acad_grp_name_root['ROTC']
        elif course_name.startswith('SINY'):
            return self.acad_grp_name_root['SINY']
        elif course_name.startswith('SCCM'):
            return self.acad_grp_name_root['SCCM']
        elif course_name.startswith('SLAV'):
            return self.acad_grp_name_root['SLAVIC']
        elif course_name.startswith('SOC'):
            return self.acad_grp_name_root['SOC']
        elif course_name.startswith('SPAN'):
            return self.acad_grp_name_root['SPAN']
        elif course_name.startswith('SPECLAN'):
            return self.acad_grp_name_root['SPECLAN']
        elif course_name.startswith('STATS'):
            return self.acad_grp_name_root['STATS']
        elif course_name.startswith('STRA'):
            return self.acad_grp_name_root['STRA']
        elif course_name.startswith('STS'):
            return self.acad_grp_name_root['STS']
        elif course_name.startswith('SURG'):
            return self.acad_grp_name_root['SURG']
        elif course_name.startswith('SYMSYS'):
            return self.acad_grp_name_root['SYMSYS']
        elif course_name.startswith('TAPS'):
            return self.acad_grp_name_root['TAPS']
        elif course_name.startswith('TIBET'):
            return self.acad_grp_name_root['TIBET']
        
        else:
            subject_part = self.crse_subject_re.match(course_name).group(1)
            if len(subject_part) > 0:
                # Assume that course name (i.e. SUBJECT) is known in acad_grp_name_root: 
                try:
                    return self.acad_grp_name_root[subject_part]
                except KeyError:
                    return None
            else:
                raise ValueError("Could not find subject for '%s'" % course_name)

    #--------------------------
    # init_course_desc 
    #----------------
      
    def init_course_desc(self):
        '''
        Reads course descriptions from course_descr_file, and 
        initializes course_descr_dict.
        '''
        
        # If available, read the course descriptions:
        try:
            with open(CourseInfoCollector.course_descr_file, 'r', encoding = "ISO-8859-1") as fd:
                reader = csv.reader(fd)
                try:
                    for (course_name, descr, description) in reader:
                        bold_descr = '<b>' + descr + '</b>'
                        self.course_descr_dict[course_name] = {'descr' : bold_descr, 'description' : description}
                except ValueError as e:
                    logErr(repr(e))
                    sys.exit()
        except IOError:
            logWarn("No course description file found. Descriptions won't be available.")
        