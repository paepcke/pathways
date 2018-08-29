#!/usr/bin/env python

'''
Created on Feb 26, 2017

@author: paepcke
'''
import datetime
from datetime import date
import dateutil.parser
import math
import sys
import os
from dateutil.relativedelta import relativedelta

class StrmComputer(object):
    '''
    Given any of (1) a date, (2) a strm, or (3) the word 'today',
    convert between date and strm. Class can be used from the 
    command line or via import into another module. 

    Month and day of idealized-quarter boundaries: 

    FALL_START    = '09-20'
    FALL_END      = '12-19'
    WINTER_START  = '12-20'
    WINTER_END    = '03-19'
    SPRING_START  = '03-20'
    SPRING_END    = '06-19'
    SUMMER_START  = '06-20'
    SUMMER_END    = '09-19'
    '''

    quarters = {2 : 'Autumn',
                4 : 'Winter',
                6 : 'Spring',
                8 : 'Summer'}

    # Create quarter start dates templates for year
    # 0001. For any given date we'll replace
    # that year later. We have to use year 
    # 1, rather than the more convenient year 0,
    # because we would get an out-of-bounds error:

    QUARTER_BOUNDS = {'fall'   : date(1,9,20),
                      'winter' : date(1,12,20),
                      'spring' : date(1,3,20),
                      'summer' : date(1,6,20)
                      }

    #-----------------------------
    # constructor 
    #-----------------------    

    def __init__(self):
        # Make more convenient quarter bounds struct:
        self.bounds = StrmComputer.QUARTER_BOUNDS

    #-----------------------------------
    # strm2AcadPeriod
    #-----------------
    
    def strm2AcadPeriod(self, strm):
        '''
        Given a STRM return a tuple (academicYear, quarter)
        Example return: (2015, Spring)
        
        @param strm: STRM to decode
        @type strm: int
        @return: tuple (yyyy, {'Autumn', 'Winter', 'Spring', 'Summer'})
        @rtype: (int, str)
        '''
        quarter_code = int(strm) % 10
        quarter = StrmComputer.quarters[quarter_code]
        
        # Chop off the quarter code (last digit:
        strm = math.floor(strm / 10)
        if strm >= 100:
            acad_year = (strm % 100) + 2000
        else:
            acad_year = (strm % 100) + 1900
        return (acad_year, quarter)
    
    #-----------------------------------
    # today2Strm
    #-----------------
    
    def today2Strm(self):
        '''
        Returns STRM corresponding to today's date.
        
        @return: STRM that would be assigned today
        @rtype: int
        '''
        
        # Get object: datetime.date(2017, 2, 26):
        return self.strm_from_date(date.today())

    #-----------------------------------
    # strm_from_date
    #-----------------

    def strm_from_date(self, datetimeOrDateObj):
        '''
        Given a datetime.date object, return
        the STRM as an integer
        
        @param datetimeOrDateObj: datetimeObj(yyyy,mm,dd)
        @type datetimeOrDateObj: {date | datetime}
        @return: STRM
        @rtype: int
        '''
        
        try:
            date_obj = datetime.datetime.date(datetimeOrDateObj)
        except TypeError:
            date_obj = datetimeOrDateObj

        cal_year  = date_obj.year

        # Build a tentative date obj from this calendar
        # year's fall quarter start. The -1 is b/c
        # the QUARTER_BOUNDS template is year 1:

        fall_start = self.bounds['fall'] +\
                        relativedelta(years=cal_year-1)

        # If calendar month/day is before fall quarter 
        # start, then academic year same as cal
        # year:

        if fall_start <= date_obj <= date(cal_year,12,31): 
            acad_year = cal_year + 1
        else:
            acad_year = cal_year

        # Create date objects for the remaining
        # quarter starts relative to the given
        # calendar year:
    
        # Winter quarter starts in same yr as fall:
        winter_start = self.bounds['winter'] + relativedelta(years=fall_start.year-1)
        spring_start = self.bounds['spring'] + relativedelta(years=acad_year-1)
        summer_start = self.bounds['summer'] + relativedelta(years=acad_year-1)

        if acad_year >= 2000:
            strm = '1'
        else:
            strm = '0'
          
        # Append the last two digits of
        # the year:
        strm += "%02d" % (acad_year % 100)
        
        # Determine the quarter: we only care about
        # months and days now. So get the given
        # date transposed to 1901 for direct compare
        # with the templates:
        date_1901 = date_obj + relativedelta(years=-date_obj.year+1)

        if self.bounds['fall'] <= date_1901 < self.bounds['winter']:
            strm += '2'    # Autumn
        elif (self.bounds['winter'] <= date_1901 <= date(1,12,31)) or date_1901 < self.bounds['spring']:
            strm += '4'    # Winter
        elif self.bounds['spring'] <= date_1901 < self.bounds['summer']:
            strm += '6'    # Spring
        elif self.bounds['summer'] <= date_1901 < self.bounds['fall']:
            strm += '8'    # Summer
        else:
            print("Bad date: %s (fall: %s, winter: %s spring: %s, summer: %s.)" %\
                      (date_obj, fall_start, winter_start, spring_start, summer_start))
            sys.exit(1)
        
        return int(strm)
      
if __name__ == '__main__':
 
    if len(sys.argv) < 2 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
        print("Usage: %s {STRM | 'today' | <date>}" % os.path.basename(sys.argv[0]))
        print("   NOTE: a year 2017 is academic year 2016/17")
        sys.exit(1)
    
    # Wants STRM for current quarter?
    if sys.argv[1] == 'today':
        print(StrmComputer().today2Strm())
        sys.exit(0)

    # If given a single arg, it's either a STRM,
    # or a date without spaces, such as 2017-3-17:
    if len(sys.argv) == 2:
        try:
            strm = int(sys.argv[1])
            # It's a STRM
            res_tuple = StrmComputer().strm2AcadPeriod(strm)
            print('%g, %s' % (res_tuple[0], res_tuple[1]))
            sys.exit(0)
        except ValueError:
            pass
        
        try:
            maybe_date_str = ' '.join(sys.argv[1:])
            date_obj = dateutil.parser.parse(maybe_date_str)
        except ValueError:
            print("Bad date format: %s" % maybe_date_str)
            sys.exit(1)
        strm = StrmComputer().strm_from_date(date_obj)
        print(strm)
        sys.exit(0)  

#   print(StrmComputer().today2Strm())
#   print(StrmComputer().strm2AcadPeriod(1142))  # (2014,'Autumn')
#   print(StrmComputer().strm2AcadPeriod(1146))  # (2014,'Spring')
#   print(StrmComputer().strm2AcadPeriod(146))     # (1914,'Spring')

  
