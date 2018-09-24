'''
Created on Aug 28, 2018

@author: paepcke
'''
import os
import sqlite3
import numpy as np

import matplotlib.pyplot as plt
from _collections import OrderedDict

class DifficultyPlotter(object):
    '''
    classdocs
    '''
    
    def __init__(self, parent, course_list, block=True):
        '''
        Constructor
        '''
        
        self.db_file = os.path.join(os.path.dirname(__file__), '../data/enrollment_tally.sqlite')
        try:
            self.sqlite_db_conn = sqlite3.connect(self.db_file)
        except Exception as e:
            raise ValueError("Could not connect ot Sqlite3 db at '%s' (%s)" % (self.db_file, repr(e)))
        
        # Initialize the course stats class:
        CourseStats.__init_class__()
        
        # For each course, get a CourseStats instance.
        # Return is a dict crs_name : difficultyObj
        
        # Get dict evalunitids to CourseStats objects.
        # Those objs hold absolute, and percentage responses
        # for each level of difficulty:
        
        stats_dict = self.compute_weekly_effort(course_list, self.sqlite_db_conn)
        stats_summary_dict = self.compute_avg_effort_all_offerings(stats_dict)

        self.plot_summary_stats(stats_summary_dict)
        self.fig.show()
        
    #--------------------------------
    # plot_summary_stats 
    #------------------
    
    def plot_summary_stats(self, stats_dict):
        
        #num_courses  = len(list(stats_dict.keys()))
        course_names = [summary_obj['course_name'] for summary_obj in stats_dict.values()]

        # A sequence of y-values (i.e. response percentages) for
        # each course for each difficulty level. Those will the 
        # stacks in earch course bar:        
        difficulty_perc1 = [summary_obj[CourseStats.DIFF_LEVEL1] for summary_obj in stats_dict.values()]
        difficulty_perc2 = [summary_obj[CourseStats.DIFF_LEVEL2] for summary_obj in stats_dict.values()]
        difficulty_perc3 = [summary_obj[CourseStats.DIFF_LEVEL3] for summary_obj in stats_dict.values()]
        difficulty_perc4 = [summary_obj[CourseStats.DIFF_LEVEL4] for summary_obj in stats_dict.values()]
        difficulty_perc5 = [summary_obj[CourseStats.DIFF_LEVEL5] for summary_obj in stats_dict.values()]
        difficulty_perc6 = [summary_obj[CourseStats.DIFF_LEVEL6] for summary_obj in stats_dict.values()]
        difficulty_perc7 = [summary_obj[CourseStats.DIFF_LEVEL7] for summary_obj in stats_dict.values()]
        difficulty_perc8 = [summary_obj[CourseStats.DIFF_LEVEL8] for summary_obj in stats_dict.values()]

        X = course_names
        bar_width  = 0.35
        # Width by experimentation: 0.8 inches is about
        # the width needed for one course name. Multiply
        # by number bars, and add some air to the right 
        # and the left for the vertical axis labels.
        fig_width  = 0.8 * len(course_names) + 5*bar_width
        fig_height = 6.5 # inches
        
        self.fig, ax_diff_sum = plt.subplots(figsize=(fig_width, fig_height)) #@UnusedVariable
        ax_diff_sum.set_ylabel('Percent of reported difficulty')
        
        ax_diff_sum.bar(X,difficulty_perc1, align='center', width=bar_width, color='#9BA6BC')
        ax_diff_sum.bar(X,difficulty_perc2, bottom=difficulty_perc1, align='center', width=bar_width, color='#9BA6BC')
        ax_diff_sum.bar(X,difficulty_perc3, bottom=difficulty_perc2, align='center', width=bar_width, color='#6D80A5')
        ax_diff_sum.bar(X,difficulty_perc4, bottom=difficulty_perc3, align='center', width=bar_width, color='#6D80A5')
        ax_diff_sum.bar(X,difficulty_perc5, bottom=difficulty_perc4, align='center', width=bar_width, color='#4C6189')
        ax_diff_sum.bar(X,difficulty_perc6, bottom=difficulty_perc5, align='center', width=bar_width, color='#4C6189')
        ax_diff_sum.bar(X,difficulty_perc7, bottom=difficulty_perc6, align='center', width=bar_width, color='#262261')
        ax_diff_sum.bar(X,difficulty_perc8, bottom=difficulty_perc7, align='center', width=bar_width, color='#262261')
        
        
    
    #--------------------------------
    # compute_weekly_effort 
    #------------------
    
    def compute_weekly_effort(self, course_list, db):
        
        try:
            cur = db.cursor()
            query = '''SELECT crse_code,
    					          all_eval_xref.termcore,
    					          all_eval_xref.evalunitid,
    					          hour_response
    					  FROM all_eval_hours JOIN all_eval_xref
    					    ON all_eval_hours.evalunitid = all_eval_xref.evalunitid
    					 WHERE crse_code IN (%s)
    					    ORDER BY crse_code,
                                     all_eval_xref.evalunitid,
                                     hour_response
    					''' % ("'" + "','".join(course_list) + "'")
            cur.execute(query)
        except Exception as e:
            raise IOError("Could not retrieve hrs/week responses from db (%s)" % repr(e))
        
        
        stats_dict  = {}
        curr_evalunitid = None
        
        # Process first row to initialize data structs:
        try:
            crse_code, termcore, evalunitid, hour_response = cur.fetchone()
            curr_evalunitid = evalunitid
        except StopIteration:
            # Table empty. Complain:
            raise ValueError("Table of weekly hours is empty.")
        
        crse_dict = self.init_course_dict(evalunitid, termcore, crse_code, hour_response)
                
        for crse_code, termcore, evalunitid, hour_response in cur:
            if evalunitid != curr_evalunitid:
                # Brand new course starting. Sew up previous crse,
                # if it has more than 10 students, else ignore for
                # privacy:
                if crse_dict['num_students'] > 10:
                    stats_dict[evalunitid] = CourseStats(crse_dict)
                    crse_dict = self.init_course_dict(evalunitid, termcore, crse_code, hour_response)
                curr_evalunitid = evalunitid
                continue
            crse_dict['num_students'] += 1
            crse_dict[CourseStats.diff_level(hour_response)] += 1

        return stats_dict              
        
    #--------------------------------
    # compute_avg_effort_all_offerings 
    #------------------
    
    def compute_avg_effort_all_offerings(self, stats_dict):
        
        # Create a *set* of course names (therefore the curlies, instead
        # of the usual list comprehension square brackets):
        
        course_names = {stats_obj['crse_code'] for stats_obj in stats_dict.values()}
        
        # Map from course name to a CourseSummaryStats. This instance
        # holds the stats aggregated over all offerings of the course:
        
        summary_dict = {}

        # For each course, gather the stats of all its offerings,
        # getting the mean for each difficulty percentage:
        for course_name in course_names:
            # Find the stats for each offering of this course:
            course_stats_objs = [stats_obj for stats_obj in stats_dict.values() if stats_obj['crse_code'] == course_name]
            summary_dict[course_name] = CourseSummaryStats(course_stats_objs)
        return summary_dict

    #--------------------------------
    # init_course_dict 
    #------------------

    def init_course_dict(self, evalunitid, termcore, crse_code, hour_response):
        crse_dict = {'evalunitid'   : evalunitid,
                     'termcore'     : termcore,
                     'crse_code'    : crse_code,
                     'num_students' : 1,
                     CourseStats.DIFF_LEVEL1  : 0,
                     CourseStats.DIFF_LEVEL2  : 0,
                     CourseStats.DIFF_LEVEL3  : 0,
                     CourseStats.DIFF_LEVEL4  : 0,
                     CourseStats.DIFF_LEVEL5  : 0,
                     CourseStats.DIFF_LEVEL6  : 0,
                     CourseStats.DIFF_LEVEL7  : 0,
                     CourseStats.DIFF_LEVEL8  : 0    
                     }
        crse_dict[CourseStats.diff_level(hour_response)] = 1
        return crse_dict
    
#------------------------    
    
    def attempt(self, course_list):
        N =  len(course_list)
        
        # Percent of students reporting levels 1-6:
        diff_level1 = (3,5,5)
        diff_level2 = (1,1,2)
        diff_level3 = (40,20,40)
        diff_level4 = (6,15,3)
        diff_level5 = (25,35,45)
        diff_level6 = (25,15,5)
        
        ind = np.arange(len(course_list))
        width = .35

        plot_diff1 = plt.bar(ind, diff_level1, width, color='#d62728') 
        plot_diff2 = plt.bar(ind, diff_level2, width, 
                             bottom=diff_level1
                             )

        plt.ylabel('Percentage of Reports')
        plt.title('Percentage of Students Reporting Course Difficulties 1-6')
        plt.xticks(ind, ('G1', 'G2', 'G3', 'G4', 'G5'))
        plt.yticks(np.arange(0, 100, 10))
        plt.legend((plot_diff1[0], plot_diff2[0]), ('CourseStats 1', 'CourseStats 2'))
        
        plt.show()        
        
    def test(self):


        N = 5
        menMeans = (20, 35, 30, 35, 27)
        womenMeans = (25, 32, 34, 20, 25)
        menStd = (2, 3, 4, 1, 2)
        womenStd = (3, 5, 2, 3, 3)
        ind = np.arange(N)    # the x locations for the courses
        width = 0.35       # the width of the bars: can also be len(x) sequence
        
        p1 = plt.bar(ind, menMeans, width, color='#d62728', yerr=menStd)
        p2 = plt.bar(ind, womenMeans, width,
                     bottom=menMeans, yerr=womenStd)
        
        plt.ylabel('Scores')
        plt.title('Scores by group and gender')
        plt.xticks(ind, ('G1', 'G2', 'G3', 'G4', 'G5'))
        plt.yticks(np.arange(0, 81, 10))
        plt.legend((p1[0], p2[0]), ('Men', 'Women'))
        
        plt.show()        
        
        
    def get_sums(self, course_list):
        conn = sqlite3.connect(self.db_file)
        cur  = conn.cursor()
        query = '''SELECT strm, SUM(enrollment) 
                      FROM enrollment_tally 
                     WHERE coursename IN (%s)
                     GROUP BY strm;
                     ''' % ','.join("'{0}'".format(x) for x in course_list)
        cur.execute(query)
        strm_sum_list = cur.fetchall()
        return strm_sum_list
    
    def plot_enrollment_history(self, data, course_list):
        
        quarters    = [int(strm_enrollment[0]) for strm_enrollment in data]
        enrollments = [strm_enrollment[1] for strm_enrollment in data]
        y_pos = np.arange(len(quarters))

        self.fig, ax = plt.subplots() #@UnusedVariable
        ax.bar(y_pos, enrollments, align='center', alpha=0.5)
        self.set_xticks(quarters, ax)
        partial_course_str = self.get_partial_course_list(course_list, 3)
        ax.set_ylabel('Enrollment')
        title = 'Quarterly Enrollment %s Since 2000' % partial_course_str
        ax.set_title(title)
        self.fig.canvas.set_window_title(title)
        
    def set_xticks(self, quarters, ax):
        '''
        Given a list of strm, create X-axis labels for just the
        Fall quarter of each year. Have them show an an angle.
        
        @param quarters: quarter codes (strms)
        @type quarters: [int]
        '''
        ax.set_xlim(1,len(quarters))
        indices_of_fall_quarters = []
        xtick_labels = []
        # First of the years in the strms: 
        # For 1182 that's 118:
        curr_year = int(quarters[0] / 10)
        
        for quarter_num, strm in enumerate(quarters):
            #if strm % 10 == 2:
            year = int(strm / 10) 
            if year != curr_year:
                # It's the first quarter in a new year. Populate the xticks:
                (strm_year, quarter_name) =  self.year_from_strm(strm)
                xtick_labels.append('%s %s' % (quarter_name, strm_year))
                indices_of_fall_quarters.append(quarter_num)
                curr_year = year
        ax.set_xticks(indices_of_fall_quarters)
        ax.set_xticklabels(xtick_labels, rotation='45')
        
    def year_from_strm(self, strm):
        return self.strm_computer.strm2AcadPeriod(strm)

    def get_partial_course_list(self, course_list, max_num_courses):
        '''
        Given course name list, return a string listing the first few
        names, adding ellipses if needed. Example: return 'Math104,CS105,CS107...'
        
        @param course_list: list of course names
        @type course_list: [str]
        @param max_num_courses: maximum number of courses to list
        @type max_num_courses: int
        '''
        partial_course_list = course_list[:min(max_num_courses,len(course_list))]
        partial_courses_str = ','.join(partial_course_list)
        # Add ellipses if needed:
        if len(course_list) > len(partial_course_list):
            partial_courses_str += '...'
        return partial_courses_str


    #------------------------------------- Interval Class ----------------
    
class Interval(object):
    '''
    Very primitive interval class. Not like the interval
    class on PyPi. Just open/closed intervals, and an 'in'
    operator.
    '''    
    
    def __init__(self):
        self.interval_range = None

    def open(self, incl_low, incl_high):
        self.low  = incl_low
        self.high = incl_high + 1
        self.interval_range = '[%s,%s]' % (incl_low, incl_high)
        
    def closed_open(self, excl_low, incl_high):
        self.low  = excl_low + 1
        self.high = incl_high + 1
        self.interval_range = '(%s,%s]' % (excl_low, incl_high)
        
    def closed_closed(self, excl_low, excl_high):
        self.low  = excl_low + 1
        self.high = excl_high
        self.interval_range = '(%s,%s)' % (excl_low, excl_high)
        
    def open_closed(self, incl_low, excl_high):
        self.low  = incl_low
        self.high = excl_high
        self.interval_range = '[%s,%s)' % (incl_low, excl_high)
        
    def includes(self, num):
        return (num >= self.low and num < self.high)
    
    def interval(self):
        return self.interval_range

    # ------------------------------- CourseStats Class ---------------------
    
class CourseStats(object):
    
    DIFF_LEVEL1 = Interval()
    DIFF_LEVEL2 = Interval()
    DIFF_LEVEL3 = Interval()
    DIFF_LEVEL4 = Interval()
    DIFF_LEVEL5 = Interval()
    DIFF_LEVEL6 = Interval()
    DIFF_LEVEL7 = Interval()
    DIFF_LEVEL8 = Interval()
    
    col_names = [
				 'crse_code',         
				 'termcore',
				 'evalunitid',
				 'avg_hrs',
				 'std_hrs',
				 'adjusted_avg_hrs',
				 'all_offerings_lt_5_hrs',
				 'all_offerings_rng_5_10_hrs',
				 'all_offerings_rng_10_15_hrs',
				 'all_offerings_rng_15_20_hrs',
				 'all_offerings_rng_20_25_hrs',
				 'all_offerings_rng_25_30_hrs',
				 'all_offerings_rng_30_35_hrs',
                 'all_offerings_gt_35_hrs'
                 ]        
    
    #--------------------------------
    # Constructor 
    #------------------
    
    def __init__(self, stats):
        '''

		@param stats: dict of weekly hrs to spend.
        @type stats: dict.
        '''
        
        # If user forgot to call the class init method,
        # do it now:
        
        if CourseStats.DIFF_LEVEL1.interval() is None:
            CourseStats.__init_class__()
        
        # Add the percentages of each difficulty level to
        # the dict:
        
        stats['diff_level1_perc'] = 100 * stats[CourseStats.DIFF_LEVEL1] / stats['num_students']
        stats['diff_level2_perc'] = 100 * stats[CourseStats.DIFF_LEVEL2] / stats['num_students']        
        stats['diff_level3_perc'] = 100 * stats[CourseStats.DIFF_LEVEL3] / stats['num_students']
        stats['diff_level4_perc'] = 100 * stats[CourseStats.DIFF_LEVEL4] / stats['num_students']
        stats['diff_level5_perc'] = 100 * stats[CourseStats.DIFF_LEVEL5] / stats['num_students']
        stats['diff_level6_perc'] = 100 * stats[CourseStats.DIFF_LEVEL6] / stats['num_students']
        stats['diff_level7_perc'] = 100 * stats[CourseStats.DIFF_LEVEL7] / stats['num_students']
        stats['diff_level8_perc'] = 100 * stats[CourseStats.DIFF_LEVEL8] / stats['num_students']      
        
        self.check_consistency(stats)
        
        self.stats = stats
    
    #--------------------------------
    # __init_class__ 
    #------------------
    
    @staticmethod
    def __init_class__():
        '''
        We can't create the Interval instances in the
        class def as, for instance, Interval().open_closed(0,5).
        Don't know why. So we do it here. This method must
        be called once. If an instance of this class (CourseStats)
        is created, this method is called automatically. But if
        one wants to use the DIFF_LEVEL<n> class variables without
        first creating a CourseStats instance, then call this once.
        
        '''
        CourseStats.DIFF_LEVEL1.open_closed(0,5)  
        CourseStats.DIFF_LEVEL2.open_closed(5,10) 
        CourseStats.DIFF_LEVEL3.open_closed(10,15)
        CourseStats.DIFF_LEVEL4.open_closed(15,20)
        CourseStats.DIFF_LEVEL5.open_closed(20,25)
        CourseStats.DIFF_LEVEL6.open_closed(25,30)
        CourseStats.DIFF_LEVEL7.open_closed(30,35)
        CourseStats.DIFF_LEVEL8.open_closed(35,60)
        
    #--------------------------------
    # __getitem__ 
    #------------------

    def __getitem__(self, key):
        return self.stats[key]
            
    #--------------------------------
    # iter 
    #------------------
    
    def iter(self):
        
        return iter(self.stats)

    #--------------------------------
    # percent_by_difficulty 
    #------------------

    def percent_by_difficulty(self, difficulty_level):
        '''
        Given either an integer difficulty level between 1 and 8,
        or one of the instances CourseStats.DIFF_LEVEL<n>, return
        this course's percentage of responses that lie in that difficulty
        range.
        
        @param difficulty_level: indicator of which difficulty level is wanted
        @type difficulty_level: {int | Interval}
        '''
        
        if difficulty_level == 1 or difficulty_level == CourseStats.DIFF_LEVEL1:
            return self.stats['diff_level1_perc']
        elif difficulty_level == 2 or difficulty_level == CourseStats.DIFF_LEVEL2:
            return self.stats['diff_level2_perc']
        elif difficulty_level == 3 or difficulty_level == CourseStats.DIFF_LEVEL3:
            return self.stats['diff_level3_perc']
        elif difficulty_level == 4 or difficulty_level == CourseStats.DIFF_LEVEL4:
            return self.stats['diff_level4_perc']
        elif difficulty_level == 5 or difficulty_level == CourseStats.DIFF_LEVEL5:
            return self.stats['diff_level5_perc']
        elif difficulty_level == 6 or difficulty_level == CourseStats.DIFF_LEVEL6:
            return self.stats['diff_level6_perc']
        elif difficulty_level == 7 or difficulty_level == CourseStats.DIFF_LEVEL7:
            return self.stats['diff_level7_perc']
        elif difficulty_level == 8 or difficulty_level == CourseStats.DIFF_LEVEL8:
            return self.stats['diff_level8_perc']

    #--------------------------------
    # diff_level 
    #------------------
    
    @classmethod
    def diff_level(cls, num):
        '''
        Given a (usually hours/wk) number, return the Interval object
        that represents the corresponding difficulty.
        
        @param num: number to check
        @type num: {int | float}
        '''
        if cls.DIFF_LEVEL1.includes(num):
            return CourseStats.DIFF_LEVEL1 
        if cls.DIFF_LEVEL2.includes(num):
            return CourseStats.DIFF_LEVEL2
        if cls.DIFF_LEVEL3.includes(num):
            return CourseStats.DIFF_LEVEL3
        if cls.DIFF_LEVEL4.includes(num):
            return CourseStats.DIFF_LEVEL4
        if cls.DIFF_LEVEL5.includes(num):
            return CourseStats.DIFF_LEVEL5
        if cls.DIFF_LEVEL6.includes(num):
            return CourseStats.DIFF_LEVEL6
        if cls.DIFF_LEVEL7.includes(num):
            return CourseStats.DIFF_LEVEL7
        else:
            return CourseStats.DIFF_LEVEL8
                  
    #--------------------------------
    # check_consistency 
    #------------------
        
    def check_consistency(self, stats_dict):
        '''
        Checks that response counts add to num_students,
        that percentages add to 100, and that at least
        one percentage is computed correctly.
        
        @param stats_dict: statistics for one evalunitid
        @type stats_dict: dict
        '''
        
        student_sum = sum([stats_dict[CourseStats.DIFF_LEVEL1],
                           stats_dict[CourseStats.DIFF_LEVEL2],
                           stats_dict[CourseStats.DIFF_LEVEL3],
                           stats_dict[CourseStats.DIFF_LEVEL4],
                           stats_dict[CourseStats.DIFF_LEVEL5],
                           stats_dict[CourseStats.DIFF_LEVEL6],
                           stats_dict[CourseStats.DIFF_LEVEL7],
                           stats_dict[CourseStats.DIFF_LEVEL8]
            ])
        if student_sum != stats_dict['num_students']:
            raise ValueError("Student responses don't sum to num students.")
        for (diff_level, diff_level_perc) in [
											  (stats_dict[CourseStats.DIFF_LEVEL1],stats_dict['diff_level1_perc']),
											  (stats_dict[CourseStats.DIFF_LEVEL2],stats_dict['diff_level2_perc']),
											  (stats_dict[CourseStats.DIFF_LEVEL3],stats_dict['diff_level3_perc']),
											  (stats_dict[CourseStats.DIFF_LEVEL4],stats_dict['diff_level4_perc']),
											  (stats_dict[CourseStats.DIFF_LEVEL5],stats_dict['diff_level5_perc']),
											  (stats_dict[CourseStats.DIFF_LEVEL6],stats_dict['diff_level6_perc']),
											  (stats_dict[CourseStats.DIFF_LEVEL7],stats_dict['diff_level7_perc']),
											  (stats_dict[CourseStats.DIFF_LEVEL8],stats_dict['diff_level8_perc'])            
						                    ]:
            if diff_level_perc != (100 * diff_level / stats_dict['num_students']):
                raise ValueError("Student response percentages don't sum to num students.")
     
    # --------------------------------------- CourseSummaryStats -------
    
class CourseSummaryStats(object):
    '''
    Holds the summary statistics of all offerings of
    a single class. Included: average percentages of responses
    across all offerings of one course. So there will be
    a single instance for each course name. 
    
    Also included: a list of termcore numbers when the
    course was offered.
    
    '''
    
    #--------------------------------
    # Constructor CourseSummaryStats
    #------------------
    
    
    def __init__(self, course_stats_obj_list):

        self.course_name = course_stats_obj_list[0]['crse_code']
        
        num_offerings = len(course_stats_obj_list)

        # Compute average percentage in each difficulty level
        # of each offering:
        
        diff_level1_sum = 0
        diff_level2_sum = 0
        diff_level3_sum = 0
        diff_level4_sum = 0
        diff_level5_sum = 0
        diff_level6_sum = 0
        diff_level7_sum = 0
        diff_level8_sum = 0
        # Sum the percentage difficulties for each
        # difficulty for all offerings of the current course:
        for course_stat_obj in course_stats_obj_list:
            diff_level1_sum += course_stat_obj.percent_by_difficulty(1)
            diff_level2_sum += course_stat_obj.percent_by_difficulty(2)
            diff_level3_sum += course_stat_obj.percent_by_difficulty(3)
            diff_level4_sum += course_stat_obj.percent_by_difficulty(4)
            diff_level5_sum += course_stat_obj.percent_by_difficulty(5)
            diff_level6_sum += course_stat_obj.percent_by_difficulty(6)
            diff_level7_sum += course_stat_obj.percent_by_difficulty(7)
            diff_level8_sum += course_stat_obj.percent_by_difficulty(8)
        self.summary_dict = OrderedDict({CourseStats.DIFF_LEVEL1 : diff_level1_sum / num_offerings,
                                         CourseStats.DIFF_LEVEL2 : diff_level2_sum / num_offerings,
                                         CourseStats.DIFF_LEVEL3 : diff_level3_sum / num_offerings,
                                         CourseStats.DIFF_LEVEL4 : diff_level4_sum / num_offerings,
                                         CourseStats.DIFF_LEVEL5 : diff_level5_sum / num_offerings,
                                         CourseStats.DIFF_LEVEL6 : diff_level6_sum / num_offerings,
                                         CourseStats.DIFF_LEVEL7 : diff_level7_sum / num_offerings,
                                         CourseStats.DIFF_LEVEL8 : diff_level8_sum / num_offerings
                                         })
        self.num_offerings = num_offerings
        # List of termcores when course was offered
        self.termcores     = [stats_obj['termcore'] for stats_obj in course_stats_obj_list]
        
    #--------------------------------
    # values 
    #------------------
    
    def values(self):
        '''
        Return an iterator over summary percentage of each
        difficulty level. Order is guaranteed to be from 
        level 1 to level 8.
        '''
        return self.summary_dict.values()
    
    #--------------------------------
    # __getitem__
    #------------------
    
    def __getitem__(self, key):
        '''
        If key is a DIFF_LEVEL<n> instance, return that 
        difficult level's summary response percentage.
        Else key must be one of 
          o num_offerings
          o termcores
          o course_name
        The non-difficulty keys would likely be better
        done with properties. But this is very clear:
        '''
        if isinstance(key, Interval):
            return self.summary_dict[key]
        elif key == 'num_offerings':
            return self.num_offerings
        elif key == 'termcores':
            return self.termcores
        elif key == 'course_name':
            return self.course_name
        else:
            raise KeyError("Key '%s' not in dict." % key)
    
        
    #--------------------------------
    # percent_by_difficulty 
    #------------------

    def percent_by_difficulty(self, difficulty_level):
        '''
        Given either an integer difficulty level between 1 and 8,
        or one of the instances CourseStats.DIFF_LEVEL<n>, return
        this course's average percentage across all offerings of 
        responses that lie in that difficulty range.
        
        @param difficulty_level: indicator of which difficulty level is wanted
        @type difficulty_level: {int | Interval}
        '''
        
        if difficulty_level == 1 or difficulty_level == CourseStats.DIFF_LEVEL1:
            return self.summary_dict['diff_level1_perc']
        elif difficulty_level == 2 or difficulty_level == CourseStats.DIFF_LEVEL2:
            return self.summary_dict['diff_level2_perc']
        elif difficulty_level == 3 or difficulty_level == CourseStats.DIFF_LEVEL3:
            return self.summary_dict['diff_level3_perc']
        elif difficulty_level == 4 or difficulty_level == CourseStats.DIFF_LEVEL4:
            return self.summary_dict['diff_level4_perc']
        elif difficulty_level == 5 or difficulty_level == CourseStats.DIFF_LEVEL5:
            return self.summary_dict['diff_level5_perc']
        elif difficulty_level == 6 or difficulty_level == CourseStats.DIFF_LEVEL6:
            return self.summary_dict['diff_level6_perc']
        elif difficulty_level == 7 or difficulty_level == CourseStats.DIFF_LEVEL7:
            return self.summary_dict['diff_level7_perc']
        elif difficulty_level == 8 or difficulty_level == CourseStats.DIFF_LEVEL8:
            return self.summary_dict['diff_level8_perc']
    
        
        
if __name__ == '__main__':
    DifficultyPlotter(None,['CS 106A', 'CS 106B', 'CS 106X'])        
    #DifficultyPlotter(['CS106A'])
    #DifficultyPlotter(['MATH104'])
