'''
Created on Sep 19, 2018

@author: paepcke
'''
import unittest
import os

if os.getenv('ECLIPSE') == '1':
    from fast_dot_retrieval import DotManager
else:
    # Works in shell, but complains in Eclipse
    from .fast_dot_retrieval import DotManager

TEST_ALL = True
#TEST_ALL = False

class TestFastDotRetrieval(unittest.TestCase):

    #--------------------------------
    # test_within_bounds 
    #------------------
    
    @unittest.skipIf(not TEST_ALL, 'Temporarily skipped')
    def test_within_bounds(self):
        
        man = DotManager((0,0),(10,20))
         
        man.add_dot(1, 8, 'foo_obj')
        man.add_dot(1, 8, 'bar_obj')
        res = man.get_dots(1, 8)
        self.assertEqual(res, ['foo_obj', 'bar_obj'])
    
    #--------------------------------
    # test_low_bounds 
    #------------------

    @unittest.skipIf(not TEST_ALL, 'Temporarily skipped')
    def test_low_bounds(self):
        man = DotManager((0,0),(10,20))
        
        man.add_dot(0,0, 'low_border')
        res = man.get_dots(0, 0)
        self.assertEqual(res, ['low_border'])


    #--------------------------------
    # test_high_bounds 
    #------------------

    @unittest.skipIf(not TEST_ALL, 'Temporarily skipped')
    def test_high_bounds(self):
        
        man = DotManager((0,0),(10,20))
        man.add_dot(10,20, 'high_border')
        res = man.get_dots(10, 20) 
        self.assertEqual(res, ['high_border'])

    #--------------------------------
    # test_non_origin_manager 
    #------------------

    @unittest.skipIf(not TEST_ALL, 'Temporarily skipped')
    def test_non_origin_manager(self):

        man = DotManager((10,0),(50,20))      
        man.add_dot(50,20, 'high_border')
        res = man.get_dots(50, 20) 
        self.assertEqual(res, ['high_border'])
        

    #-------------------------- Main ------------------
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testLowBounds']
    unittest.main()