'''
Created on Nov 13, 2018

@author: paepcke
'''
import argparse
import csv
import json
import os
import sys


class SentenceCreator(object):
    '''
    Given a CSV file of enrollment records, create the input
    for model creation with word2vec. The input is expected
    to have format:
    
        "emplid","strm","course_code"
        
    and is expected to be SORTED by emplid-->strm-->course_code.
    Each course taken by one student will thus be on one line.
    The file is expected to have a header line.
    
    Two output files are created, one with input sentences for
    word2vec, and the second with a dictionary that maps emplids
    to more readable short IDs that preserve uniqueness. The latter
    can be used to modify emplids in EnrollmentHistory to match.
    
    An optional switch can indicate that an already existing
    json-encoded emplid-shortStudentID should be used, with 
    extensions made if needed. In this case the existing dict
    is expected to have a key 'HighestStudentId' with the
    next short student ID to be used if a new emnplid is encountered.
     
    Output1:
    
    This output is another CSV having one of two forms, depending
    on arguments to the constructor. Both forms are suitable for
    use with gensim.models.word2vec.LineSentence(). I.e. each line
    will be a space-separated list of tokens. So the output file
    path can be passed into the LineSentence() method.
        
    Form1:    
        <crs1Student1> <crs2Student1> <crs3Student1> 
        <crs1Student2> <crs6Student2> <crs3Student2> <crs6Student2> <crs1Student2>
        
    Form2:
        <emplid1Shortened> <crs1Student1> <crs2Student1> <crs3Student1> 
        <emplid2Shortened> <crs1Student2> <crs6Student2> <crs3Student2> <crs6Student2> <crs1Student2>
            ...
            
    Each row contains the courses of one student in the order 
    taken. Courses are named as in CS106A, MATH51, etc. Note that
    rows will have unequal lengths.
    '''

    #--------------------------
    # Constructor 
    #----------------


    def __init__(self, 
                 linear_sentences_path, 
                 outfile_sentences_path, 
                 emplid_map_path,
                 include_emplid=False
                 ):
        '''
        Do the whole thing. If include_emplid is True, then each of the
        output sentences with have as first token the shortened emplid
        of the student whose study set is listed in that sentence.
        
        If the emplid_map_path already exists, then it is read and
        used. Any unfound emplids are added, and the json encoded 
        dict is written back out at the end as usual.
        The dict is expected to have at least one key: 'HighestStudentId', 
        which contains the next short Id number to use for constructing a 
        short Id.
        
        @param linear_sentences_path: path to file with one enrollment per student and course
        @type linear_sentences_path: str
        @param outfile_sentences_path: where to place the word2vec-ready sentences input 
        @type outfile_sentences_path: str
        @param emplid_map_path: path to an existing json-encoded map from emplid to short student Id or,
            if no such file exists yet, the path where the file is to go.
        @type emplid_map_path: str
        @param include_emplid: if true, each sentence will be prepended with short student path.
        @type include_emplid: boolean
        '''

        # If the json-encoded dict mapping emplid to short student ids
        # exists, use it:
         
        if os.path.exists(emplid_map_path):
            try:
                with open(emplid_map_path, 'r') as map_fd:
                    self.emplid_map = json.load(map_fd)
            except Exception as e:
                print('Could not load given emplid-->shortStudentId dict; nothing done: %s' % e)
                sys.exit()
            try:
                self.emplid_seq_num = self.emplid_map['HighestStudentId']
            except KeyError:
                print("Given emplid-->shortStudentId map does not include required key 'HighestStudentId; nothing done.")
                sys.exit()
        else:
            self.emplid_map = {}
            self.emplid_seq_num = 1

        with open(linear_sentences_path, 'r') as enrollments_fd:
            with open(outfile_sentences_path, 'w') as sentences_fd:
                csv_reader = csv.reader(enrollments_fd)
                # Discard header line:
                next(csv_reader)
                
                # Read the first line: emplid, strm, course_code:
                (emplid, _strm, course_code) = next(csv_reader)
                
                curr_emplid = emplid
                short_stud_id = self.encode_emplid(emplid)
                
                if include_emplid:
                    sentences_fd.write(short_stud_id + ' ' + course_code)
                else:
                    sentences_fd.write(course_code)
                
                for (emplid, _strm, course_code) in csv_reader:
                    
                    # Is this a new emplid?
                    if emplid != curr_emplid:
                        # End the current output line:
                        sentences_fd.write('\n')
                        curr_emplid = emplid
                    else:
                        # We know that we wrote at least one course,
                        # so add a space in prep of this new course
                        # being added:
                        sentences_fd.write(' ')
                        
                    short_stud_id = self.encode_emplid(emplid)
                    
                    if include_emplid:
                        sentences_fd.write(short_stud_id + ' ' + course_code)
                    else:
                        sentences_fd.write(course_code)

                self.output_emplid_map(emplid_map_path)
                    
        
    #--------------------------
    # encode_emplid 
    #----------------
                
    def encode_emplid(self, emplid):
        '''
        Given a raw emplid, construct a shorter, but unique
        within the input file alternative student ID. The
        method also updates the emplid_map to keep track of
        the emplid-->shortId mapping.
        
        @param emplid: hashed ID as used in Carta
        @type emplid: str
        @return: shortened id
        @rtype: str
        '''
        # Have we encoded this emplid into a short name
        # before?
        
        stud_id = self.emplid_map.get(emplid, None)
        
        if stud_id is None:
            # No, create a new short id:
            stud_id = 'stud' + str(self.emplid_seq_num)
            self.emplid_map[emplid] = stud_id
            self.emplid_seq_num += 1
        
        return stud_id;
                    
    #--------------------------
    # output_emplid_map 
    #----------------
    
    def output_emplid_map(self, outfile_emplid_map_path):
        '''
        Output the emplid-->shortStudentId dict as JSON
        to the given file. Adds key 'HighestStudentId' to
        the dict for future extensions with new emplids.
        
        @param outfile_emplid_map_path: path to destination file
        @type outfile_emplid_map_path: str
        '''
        
        # Add the currently highest student ID number as a 
        # special entry in the emplid-->shortEmplid map. That
        # the the dict can be expanded later:
        
        self.emplid_map['HighestStudentId'] = self.emplid_seq_num
        
        with open(outfile_emplid_map_path, 'w') as json_fd:
            json.dump(self.emplid_map, json_fd)
        
if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--include',
                        help='include the shortened student ID at the start of each sentence',
                        default=False
                        )
    parser.add_argument('infile',
                        help='fully qualified path where the linearly arranged, sorted enrollments are found\n'
                        )
    
    parser.add_argument('outfile',
                        help='fully qualified path where result sentences file will be placed \n'
                        )
    parser.add_argument('dictfile',
                        help='file path where emplid-->shortStudentId JSON encoded dict will be stored'
                        )

    args = parser.parse_args();
    
    SentenceCreator(args.infile,
                    args.outfile, 
                    args.dictfile, 
                    args.include)
    