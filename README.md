# H1 Interactive College Course Cluster Display

This standalone application shows two panels: a *control surface* with
buttons, and a *cluster canvas* where courses are shown as colored
dots. The colors indicate schools; a legend is at the bottom of the
cluster canvas.

The check boxes at the top of the control surface are *school
selectors*. They allow choice of which school(s) to include when
recomputing a clustering. The more schools are selected, the slower
the recomputation.

The draft checkbox allows limiting the total number of courses that
are included in the cluster panel. Checking this box results in an
incomplete view, but all operations are faster.

Dot size indicates that several courses are combined into the one
dot.

# H2 Things to do

- Hover over a dot and see one of the courses represented by that dot.
- Left-click on a dot and see the comprised courses in the *course board*,
  which is the tall, white area on the right of the control surface.
- Right-click on a white area of the cluster canvas, then left click
  to lasso several dots. When the lasso is to be closed, right-click
  again. The result is display of all lassoed courses in the control
  surface's course list panel.

  In addition, the reported difficulties and enrollment history of the
  lassoed courses is shown in two separate popup windows. Those
  windows are on top of each other; so move the top one out of the way
  with the mouse.

- Entering a course number, such as "cs 106a" in the search box below
  the draft mode selector, and clicking the *Where Is* button shows
  where in the cluster canvas the course is represented.

- With a course number in the search box, click *Top 10 Like Above
  Course* to find bundles of related courses. Even courses not in the
  model are included in these lists.

- The *Save Visualization* saves the current cluster canvas and
  associated metadata in a file in <proj-root>/src/cache. An
  appropriate name is contructed, which includes the parameters of the
  display, such as which schools where included, and whether draft or
  high quality mode.

- The *Load Visualization* displays shows the files in the src/cache
  directory, and loads the user-selected file.

- The *Recompute* button refits a Tsne model, honoring the currently
  selected choices: draft/full mode, selected schools. In full quality
  mode the process takes several minutes, up to 20 minutes when all
  schools are included.

# H2 Running the Code

The main code consists of three files: `courseSim.py` is the main
entry point. Starting it without command line arguments starts
everything. Python 3 is required.

# H2 Installation

Clone this repo. Then:
```
python setup.py install
python setup.py test
```

# H2 Code Components (for developers)

File `courseSim.py` is the entry point into the system.
File `control_surface_process.py` generates, and responds to the
buttons and text boxes in the control surface. The UI is constructed
using QtDesigner. The generated .ui file is in the `qtui/courseTsne.ui`
file. This file drives the Python code for the control surface. The
interaction is managed using PyQt5.

File `course_tsne_visualization.py` creates the cluster panel, and
recomputes. All three files are in their own threads, and communicate
via command queues.

The courseSim.py is a mediator between the cluster panel application
and the control surface. Message from the control panel to the cluster
canvas travel through courseSim.py.

Creating an entirely new vector space model, as opposed to just
recomputing a Tsne projection, involves creating input sentences into
the word2vec program. Sentence format is:

       *major, course1, course2, course3,...*

where course_n comprise one student's courses in partial order between
Freshman and Senior years, inclusive. The README.txt in the data
subdirectory contains the necessary queries and other procedures.


