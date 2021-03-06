'''
Created on Aug 28, 2018

@author: paepcke
'''
from _collections import OrderedDict
import os
import re
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

class DifficultyPlotter(object):
    '''
    classdocs
    '''
    
    COURSE_NAME_SPLIT_DEP_NUM_PATTERN   = re.compile(r'([^0-9]*)(.*)')
    COURSE_NAME_HAS_3DIGITS_PATTERN = re.compile(r'[0-9]{3}')

    
    def __init__(self, course_list, block=True):
        '''
        Constructor
        '''
        
        self.db_file = os.path.join(os.path.dirname(__file__), '../data/enrollment_tally.sqlite')
        try:
            self.sqlite_db_conn = sqlite3.connect(self.db_file)
        except Exception as e:
            raise ValueError("Could not connect ot Sqlite3 db at '%s' (%s)" % (self.db_file, repr(e)))
        
        # Make sure that course names are canonicalized
        # i.e. have a space between, for instance, 'CS' and '140'.
        # Else evals dbs can't find the courses:
        if course_list is not None:
            course_list = [self.canonicalize_course_name(crse_nm) for crse_nm in course_list]
        
        
        # Initialize the course stats class:
        CourseStats.__init_class__()
        
        # For each course, get a CourseStats instance.
        # Return is a dict crs_name : difficultyObj
        
        # Get dict evalunitids to CourseStats objects.
        # Those objs hold absolute, and percentage responses
        # for each level of difficulty:
        
        #***************
        stats_dict = self.compute_weekly_effort(course_list, self.sqlite_db_conn)
        #****stats_dict = self.compute_weekly_effort(None, self.sqlite_db_conn)
        #***************
        
        # Distinguish between offerings and courses:
        num_offerings = len(stats_dict)
        course_name_set = {crse_stats_obj['crse_code'] for crse_stats_obj in stats_dict.values()}
        
        normalized_vote_counts = self.compute_response_distribution(stats_dict)
        
        # Create a figure prepared for showing all stats plots 
        # we want to show:
        num_plots = 2 if course_list is not None else 1
        if num_plots is None:
            # One plot: 1 row, 1 col, index 1:
            _fig, ax_difficulty_histogram = plt.subplots(1, 1)
        else:
            # Two plots: the histogram of difficulty distribution,
            # and the detailed difficulties:
            # Plots will be arranged in one row and two cols 
            _fig, [ax_difficulty_histogram, ax_difficulty_detail] = plt.subplots(1, 2)
        
        self.plot_difficulty_histogram(ax_difficulty_histogram,
                                       normalized_vote_counts,
                                       len(course_name_set),
                                       num_offerings
                                       )

        # Plot detail only if few enough courses
        # are included to plot
        if course_list is not None:
            avg_over_offerings_dict = self.compute_avg_effort_all_offerings(stats_dict)
            self.plot_difficulty_details(ax_difficulty_detail, avg_over_offerings_dict)
            
        plt.tight_layout()
        # Make a bit of room above the subplots
        # so that the main figure title doesn't overlap:
        plt.subplots_adjust(top=0.9)
        plt.show(block=True)
        
    #--------------------------------
    # plot_difficulty_details 
    #------------------
    
    def plot_difficulty_details(self, ax_diff_sum, stats_summary_dict):
        '''
        Plot the stacked bar chart of student percentages who
        responded with low, med, med_hi, high, or v_high. One
        bar for each course. Each bar has five slices, one each
        for low, med,...v_high
        
        @param ax_diff_sum: axes to plot into
        @type ax_diff_sum: matplotlib.Axes
        @param stats_summary_dict: Map course_name to CourseStats objects
        @type stats_summary_dict: {str : CourseStats}
        '''
        # Turn the dict into a Pandas dataframe, b/c those have
        # built-in stacked bar charts:
        
        difficulty_perc_df = pd.DataFrame()
        for course_stats_obj in stats_summary_dict.values():
            low,med,med_hi,high,v_high1,v_high2,v_high3,v_high4 = course_stats_obj.summary_dict.values()
            v_high = sum([v_high1,v_high2,v_high3,v_high4])
            next_row = pd.Series([low,med,med_hi,high,v_high],
                                 index=['low','med','med_hi','high','v_high'],
                                 name=course_stats_obj['course_name']
            )
            difficulty_perc_df = difficulty_perc_df.append(next_row)
        
        ax_diff_sum.set_xlabel('Percent of student-reported difficulty')
        
        # Have Pandas do the plotting into the already prepared subplot:
        difficulty_perc_df.plot.barh(stacked=True, ax=ax_diff_sum)
        
        plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
        
    #--------------------------------
    # plot_difficulty_histogram 
    #------------------
        
    def plot_difficulty_histogram(self, 
                                  ax_difficulty_histogram, 
                                  normalized_vote_counts, 
                                  num_courses,
                                  num_offerings):
        '''
        Given list of eight (or some other length) normalized
        difficulty counts, plot a histogram. Each count corresponds
        to a particular difficulty level: 1 though n. 
        
        Each count is assumed to be the sum of all students who reported the
        respective difficulty level as appropriate. Counts are
        expected to be normalized to be between zero and one.
        
        The creator of normalized_vote_counts would have selected
        the courses to include in the student responses. Could be all
        courses, or some small list of them.
        
        Number of courses is used only in the Y-axis label. If None,
        all courses are included.
        
        @param ax_difficulty_histogram: the Axes instance to plot on
        @type ax_difficulty_histogram: Axes
        @param normalized_vote_counts: counts of difficulty levels
        @type normalized_vote_counts: [float]
        @param num_courses: number of courses included in histogram
        @type num_courses: int
        '''
    
        #xlabel_text  = ['level%s' % str(n+1) for n in range(len(normalized_vote_counts))]
        xlabel_text = ['Low', 'Med', 'Med/Hi', 'High', 'V-High1','V-High2','V-High3','V-High4']
        bar_width  = 0.35
        
        ax_difficulty_histogram.set_ylabel('Reported Difficulty Levels for Course Cluster')
        ax_difficulty_histogram.get_figure().suptitle("Difficulty Distribution %s Courses, %s Offerings" %\
                                                       (num_courses, num_offerings)
                                                       )
        
        ax_difficulty_histogram.bar(xlabel_text, 
                                    normalized_vote_counts, 
                                    align='center', 
                                    width=bar_width, 
                                    color='#9BA6BC')
        plt.setp(ax_difficulty_histogram.xaxis.get_majorticklabels(), rotation=45)
        
    #--------------------------------
    # make_diffs_low_v_high_dataframe
    #------------------

    def make_diffs_low_v_high_dataframe(self, stats_dict):
        '''
        Returns a Pandas dataframe:
    
                      crs1, crs2, crs3, ...
           'low'    
           'med'
           'med_hi'
           'high'
           'v_high
    
        The cells are percentages of student answers.
        The levels 5-8 are summed to form v_high.
    
        @param stats_dict: map from evalunitid to course stats object
        @type stats_dict: {str : CourseStats}
        @returns: promised dataframe
        @rtype Pandas.DataFrame()
        '''
    
        course_names = [summary_obj['crse_code'] for summary_obj in stats_dict.values()]
    
        # Get 1-d difficulty percentages: perc for difficulty level 1 of all courses in one row,
        #                                 perc for difficulty level 2 of all courses in next row,
        #     etc:
        
        low_difficulties    = [course_stat_obj[CourseStats.DIFF_LEVEL1] for course_stat_obj in stats_dict.values()]
        med_difficulties    = [course_stat_obj[CourseStats.DIFF_LEVEL2] for course_stat_obj in stats_dict.values()]
        med_hi_difficulties = [course_stat_obj[CourseStats.DIFF_LEVEL3] for course_stat_obj in stats_dict.values()]
        high_difficulties   = [course_stat_obj[CourseStats.DIFF_LEVEL4] for course_stat_obj in stats_dict.values()]
    
        # Combine difficulty readings of levels 5-8: get the rows as
        # above, then form a dataframe, whose sum() method will produce
        # a Pandas Series of the levels 5-8:
      
        v_high_difficulties_a = [course_stat_obj[CourseStats.DIFF_LEVEL5] for course_stat_obj in stats_dict.values()]
        v_high_difficulties_b = [course_stat_obj[CourseStats.DIFF_LEVEL6] for course_stat_obj in stats_dict.values()]
        v_high_difficulties_c = [course_stat_obj[CourseStats.DIFF_LEVEL7] for course_stat_obj in stats_dict.values()]
        v_high_difficulties_d = [course_stat_obj[CourseStats.DIFF_LEVEL8] for course_stat_obj in stats_dict.values()]
    
        df_for_collapsing = pd.DataFrame({'diff_level_vhigh_a' : pd.Series(v_high_difficulties_a, index=course_names),
                                          'diff_level_vhigh_b' : pd.Series(v_high_difficulties_b, index=course_names),
                                          'diff_level_vhigh_c' : pd.Series(v_high_difficulties_c, index=course_names),
                                          'diff_level_vhigh_d' : pd.Series(v_high_difficulties_d, index=course_names)
                                          })
        # df_for_collapsing looks like this:
        #           diff_level_vhigh_a   diff_level_vhigh_b   ... diff_level_vhighd
        #   crs1
        #   crs2
        #    ...
        #
        # We need to sum row-wise. I.e. sum the percentages in diff_a through diff_d
        # for each course to have only one percentage for each course. The 'axis=1' below
        # ensures the row-wise addition (rather than col-wise, or all):
        
        diff_compressed_dict = {'low'     : pd.Series(low_difficulties, index=course_names),
                                'med'     : pd.Series(med_difficulties, index=course_names),
                                'med_hi'  : pd.Series(med_hi_difficulties, index=course_names),
                                'high'    : pd.Series(high_difficulties, index=course_names),
                                'v_high'  : df_for_collapsing.sum(axis=1)
                                }
        difficulties_compressed_df = pd.DataFrame(diff_compressed_dict, index=course_names)
        
        difficulties_full_range_df = pd.concat([difficulties_compressed_df, df_for_collapsing], sort=False)
        
        return (difficulties_compressed_df, difficulties_full_range_df)
        
    #--------------------------------
    # compute_weekly_effort 
    #------------------
    
    def compute_weekly_effort(self, course_list, db):
        '''
        For each course in courselist, compute the percentage of
        students who reported difficulty 1-8. Each offering of
        a course is treated as a different course in this context.
        Method  compute_average_effort_all_offerings() combines
        offerings later.
        
        If course_list is NULL, all 5k plus courses are processed.
        This will take around four or five minutes.
        
        @param course_list: list of course names for which to compute percentages
        @type course_list: {[str] | None}
        @param db: Sqlite3 connection object
        @type db: connection
        '''
        
        try:
            cur = db.cursor()
            
            # If we were given a specific list of courses,
            # only include those in the query, else pull info
            # on all courses:
            
            if course_list is not None:
                # The funky format string below creates a sequence
                # of single-quoted strings: ('CS 108', 'MATH 40', ...):
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
            else:
                query = '''SELECT crse_code,
        					      all_eval_xref.termcore,
        					      all_eval_xref.evalunitid,
        					      hour_response
        					  FROM all_eval_hours JOIN all_eval_xref
        					    ON all_eval_hours.evalunitid = all_eval_xref.evalunitid
        					    ORDER BY crse_code,
                                         all_eval_xref.evalunitid,
                                         hour_response
        					'''
                
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
        except TypeError:
            # No entry found for any course:
            raise ValueError("Course not found from %s" % course_list)
        
        crse_dict = self.init_course_dict(evalunitid, termcore, crse_code, hour_response)
        
        try: 
            for crse_code, termcore, evalunitid, hour_response in cur:
                
                if evalunitid != curr_evalunitid:
                    # Brand new course starting. Sew up previous crse,
                    # if it has more than 10 students, else ignore for
                    # privacy:
                    if crse_dict['num_students'] > 10:
                        stats_dict[curr_evalunitid] = CourseStats(crse_dict)
                        crse_dict = self.init_course_dict(evalunitid, termcore, crse_code, hour_response)
                    curr_evalunitid = evalunitid
                    continue
                crse_dict['num_students'] += 1
                crse_dict[CourseStats.diff_level(hour_response)] += 1
        finally:
            # Add the last one we were working on when 
            # we ran out of db results:
            stats_dict[evalunitid] = CourseStats(crse_dict)
        return stats_dict              
        
    #--------------------------------
    # compute_avg_effort_all_offerings 
    #------------------
    
    def compute_avg_effort_all_offerings(self, stats_dict):
        '''
        Given a dict {evalunitid : CourseStats objects},
        return a new dict with summary statistics:
          o Avg number of 'votes' for each difficulty level across all offerings.
          o List of termcores when course was offered.
        The returned obj behaves more or less like a dict, and 
        provides metho percent_by_difficulty() 
        
        @param stats_dict: map evalunitid to CourseStats objs, one for each offering
            of every class
        @type stats_dict: {str : CourseStats}
        '''
        
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
    # compute_response_distribution 
    #------------------

    def compute_response_distribution(self, stats_dict):
        '''
        Given a dict evalunitid --> CourseStats object
        with all offerings being separate entries, compute
        the overall distribution of 'votes' for the difficulty
        slots 1-8. We just separately add the numbers for each
        difficulty. At the end we normalize to 0-1. We return
        vectors X and Y, where X is [1,2,...8], and Y are the 
        (normalized) numbers of students who reported the respective
        difficulty. 
        
        @param stats_dict: dict from evalunitid to CourseStats obj
        @type stats_dict: {str : CourseStat}
        @return: list of eight elements. The nth element (0<=n<=7)
            is the number of votes for difficult n+1.
        @rtype: float
            
        '''
        sums = [0] * 8
        for course_stats_obj in stats_dict.values():
            # CourseStats objs have info, such as the term
            # when the offering occurred, etc. The obj
            # also acts as a dict for the difficulty levels
            sums[0] += course_stats_obj[CourseStats.DIFF_LEVEL1]
            sums[1] += course_stats_obj[CourseStats.DIFF_LEVEL2]
            sums[2] += course_stats_obj[CourseStats.DIFF_LEVEL3]
            sums[3] += course_stats_obj[CourseStats.DIFF_LEVEL4]
            sums[4] += course_stats_obj[CourseStats.DIFF_LEVEL5]
            sums[5] += course_stats_obj[CourseStats.DIFF_LEVEL6]
            sums[6] += course_stats_obj[CourseStats.DIFF_LEVEL7]
            sums[7] += course_stats_obj[CourseStats.DIFF_LEVEL8]
        np_sums = np.array(sums)
        normed_sums = list(np_sums / max(np_sums))
        return normed_sums

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
    
    #--------------------------------
    # canonicalize_course_name 
    #------------------
    
    def canonicalize_course_name(self, crs_nm):
        '''
        Given a course name like 'CS140' return 
        the name with a space between the number and 
        the department: 'CS 140'.
        
        @param crs_nm:
        @type crs_nm:
        '''
        # Split name into department and catalog number parts:
        match_obj = DifficultyPlotter.COURSE_NAME_SPLIT_DEP_NUM_PATTERN.search(crs_nm)
        if match_obj is None:
            # Just leave the name alone: 
            return crs_nm
        else:
            # Groups will be like: ('CS', '140').
            # Save that tuple
            dep, catalog_nbr = match_obj.groups()

        # There also need to be three digits for
        # the catalog nbr:
        match_obj = DifficultyPlotter.COURSE_NAME_HAS_3DIGITS_PATTERN.search(catalog_nbr)
        if match_obj is None:
            # Catalog nbr does not have 3 digits:
            catalog_nbr = '0' + catalog_nbr
            # Does catalog number now have 3 digits? 
            # (Not the length, digits, b/c it could
            # be CS1N
            match_obj = DifficultyPlotter.COURSE_NAME_HAS_3DIGITS_PATTERN.search(catalog_nbr)
            if match_obj is None:
                # Nope, need another leading zero:
                catalog_nbr = '0' + catalog_nbr
        
        crse_nm = ' '.join([dep.strip(), catalog_nbr.strip()])
        return crse_nm
        
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
    #DifficultyPlotter(['CS 106A', 'CS 106B', 'CS 106X'])        
    #DifficultyPlotter(['CS 106A', 'CS 106B', 'CS 106X', 'CS 140'])        
    #DifficultyPlotter(['CS 140'])
    #DifficultyPlotter(['CS 106X'])
    #DifficultyPlotter(['CS 106A'])
    #DifficultyPlotter(['CS 106B'])
    #DifficultyPlotter(['CS 140', 'CS 231N'])
    DifficultyPlotter(['CS 045N'])
    
    # Test single course not found (missing space between Math and 104):
    #DifficultyPlotter(['MATH104'])
    
    # Test one of several courses not found (missing space between Math and 104):
    # Simply uses the one it finds:
    #DifficultyPlotter(['CS 106A', 'MATH104'])
    
    # Same, but bad course is first:
    # Simply uses the one it finds:
    #DifficultyPlotter(['MATH104', 'CS 106A'])
    
