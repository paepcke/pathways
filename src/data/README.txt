

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
