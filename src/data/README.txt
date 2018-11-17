

In Word2vec:

Files for building the course2vec model since 2000.

- File emplid_crs_major_strm_gt10_2000plus.csv

   2,537,276 records of students enrolling in courses since 2000.
   Includes all students (not just UG), but courses with fewer than
   10 students are excluded. Major reflects the final major. Taken
   Aug 27, 2018.

      "emplid","coursename","major","acad_career","strm"
      
      "$2b$15...MHUxqq","MED300A","MED-MD","MED","1016"
      "AbEuRW...pxOUM1,"MED300A","MED-MD","MED","1014"


- File all_since_2000_plus_majors_veclen150_win10.model
   Word2Vec model from emplid_crs_major_strm_gt10_2000plus.csv

  So:
   2,537,276 records of students enrolling in courses since 2000.
   Includes all students (not just UG), but courses with fewer than
   10 students are excluded. Major reflects the final major.

   Trained major as first word in sentence, followed by all
   courses of one student.

   Vector size: 150. Window size 10: 10 before and 10 after center.

- File all_since_2000_plus_majors_veclen150_win10.vectors:
     Key vectors only from the corresponding model. Use for speed.


- File cross_registered_courses: all courses that are cross
  registered. Taken Aug 27, 2018. Ordered by evalunitid.
  
  Format:

      "CEE 251","COU:1144:COMBO:202776:05265994"
      "CEE 151","COU:1144:COMBO:202776:05265994"
      "EARTHSCI 251","COU:1144:COMBO:202776:05265994"
      "MS&E 240","CRS:1098:COMBO:0290:05163541"
      "MS&E 140","CRS:1098:COMBO:0290:05163541"
      "STATS 160","CRS:1098:COMBO:0321:05440153"

  As long as evalunitid is the same in subsequent rows, the respective
  courses are cross listed.

  Used in course_sim_analytics.py: cross_listings_verification() to
  check whether a model properly predicts the crosslists as the
  nearest courses.

- File sentences_file.txt:
  the file that is fed to the neural net during vector training:

      major,crse1,crse2,...

  where each line is the major and courses-taken of one student.

  To re-create that file, use the crs_major_strm_gt10_2000plus.csv,
  and program word2vec_model_creation.py:

  python word2vec_model_creation.py --action create_sentences_file \
                                    --file .../data/Word2vec/emplid_crs_major_strm_gt10_2000plus.csv
                                    --savefile .../data/Word2vec/sentences_file.txt

---------- Data for word2vec with course enrollments true to time of  enrollment sequence ----------

Data are in /Users/paepcke/EclipseWorkspacesNew/pathways/src/data/SequenceTrueModel/data:

- Properties:
   o Includes students who were at some time undergrads, even if they
     then moved on to grad school at Stanford
   o Classes considered all have enrollment >= 10
   o To determine a student's major, we use only the major(s) at the
     latest calendar date where a change in major was made. If
     multiple changes were made on the same day (~700 students), an
     arbitrary (not truly random) choice is made.
   o Only course with strm >= 1002, Fall 2000 are included

- Stats:
   o Number of students in sentences: 55,460
   o Number of quarters: 78
   o Number with two majors (ever): 12,784
   o Number of distinct double majors: 4,548
      (select count(distinct major)  major from EnrollmentHistory where major REGEXP '[^_]*_.*';)
   o Number of courses (*not* offerings, but counting CS106A once): crse_id): 19,369
   o Number of offerings (distinct strm/course_code count): 107,839
      (select count(distinct strm,course_code) from EnrollmentHistory;)

   

- EnrollmentHistory: File created on staging.  has each enrollment
                      of each UG since 1002, incl.  The intent is
                      to hold all info desirable in Tableau down
                      the workflow. Most cols are obvious. Some
                      explanations:
  
                        course_code : concatenation of subject and
                        cat nbr: CS106A crse_id : the number for
                        all offerings of a course, i.e.  one number
                        for all of CS106A ever.  offered_by_grp: a
                        course's department: SOCIOLOGY, or
                        COMPUTSCI acad_grp : roughly: the school:
                        H&S, ENGR, etc. But also VPTL, VPUE.

                      Turns out that maybe enrollmentNums.csv is
                      better for Tableau.  Uses full emplids. See
                      enrollmentHistoryShortIds.csv for better
                      option.

- LinearSentences: File created on staging.  emplid, strm,
                      course_code, i.e. a row per enrollment.
                      Ordered by:

                         emplid, strm, then course

                      and limited to enrollments >= 10 The intent
                      is that after export, the CSV can be
                      processed in Python to create the final study
                      set for each student by sequentially reading
                      in.

                      This also enough information to find the
                      course details in EnrollmentHistory. Uses
                      full length emplids

- EnrollmentNums: File created on staging.  Just has the number of
                      enrollments in each offering. The info in
                      this table is the same as the
                      course_enrollment number in
                      EnrollmentHistory. But we also add the
                      offering department here.


- crs_sequenced_sentences.txt: <--- Use for modeling
   Sentences ready for input to gensim.models.word2vec.LineSentence() method.
   This file is generated by create_sentences.py. That file can be called such
   that only courses are included in a sentence, are such that an emplid is
   at the start of each sentence.

- enrollmentHistoryShortIds.csv: <--- Use in tableau
   Copy of enrollmentHistory.csv, but with emplids replaced by shorter ids.
   This file is created by program shorten_enrollment_history_emplids.py

- emplid_map.jsonL
   JSON-encoded, python-loadable dict mapping long emplids to short ones.
   Special key 'HighestStudentId' holds the next short-studentId number
   to use by shorten_enrollment_history_emplids.py are made.

