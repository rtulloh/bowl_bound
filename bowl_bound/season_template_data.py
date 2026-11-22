"""Normalized historical fixture facts. See docs/season-schedules.md."""

BIG_EIGHT_TEAMS = """\
colorado,Big Eight
iowa-state,Big Eight
kansas,Big Eight
kansas-state,Big Eight
missouri,Big Eight
nebraska,Big Eight
oklahoma,Big Eight
oklahoma-state,Big Eight
"""

BIG_EIGHT_FIXTURES = """\
4,colorado,oklahoma-state,1,1972-09-30,
5,missouri,oklahoma-state,1,1972-10-07,
5,colorado,kansas-state,1,1972-10-07,
6,missouri,nebraska,1,1972-10-14,
6,iowa-state,colorado,1,1972-10-14,
6,kansas,kansas-state,1,1972-10-14,
7,kansas-state,iowa-state,1,1972-10-21,
7,nebraska,kansas,1,1972-10-21,
7,oklahoma,colorado,1,1972-10-21,
8,iowa-state,kansas,1,1972-10-28,
8,colorado,missouri,1,1972-10-28,
8,kansas-state,oklahoma,1,1972-10-28,
8,oklahoma-state,nebraska,1,1972-10-28,
9,missouri,kansas-state,1,1972-11-04,
9,oklahoma,iowa-state,1,1972-11-04,
9,kansas,oklahoma-state,1,1972-11-04,
9,nebraska,colorado,1,1972-11-04,
10,oklahoma-state,kansas-state,1,1972-11-11,
10,nebraska,iowa-state,1,1972-11-11,
10,kansas,colorado,1,1972-11-11,
10,missouri,oklahoma,1,1972-11-11,
11,kansas-state,nebraska,1,1972-11-18,
11,iowa-state,missouri,1,1972-11-18,
11,oklahoma,kansas,1,1972-11-18,
12,oklahoma,nebraska,1,1972-11-23,
12,kansas,missouri,1,1972-11-25,
12,iowa-state,oklahoma-state,1,1972-11-25,
13,oklahoma-state,oklahoma,1,1972-12-02,
"""

TEAMS_2002 = """\
alabama,SEC
arizona,Pac-10
arizona-state,Pac-10
arkansas,SEC
auburn,SEC
baylor,Big 12
boston-college,Big East
california,Pac-10
colorado,Big 12
duke,ACC
florida,SEC
georgia,SEC
georgia-tech,ACC
illinois,Big Ten
indiana,Big Ten
iowa,Big Ten
iowa-state,Big 12
kansas,Big 12
kansas-state,Big 12
kentucky,SEC
lsu,SEC
miami,Big East
michigan,Big Ten
michigan-state,Big Ten
minnesota,Big Ten
mississippi-state,SEC
missouri,Big 12
nc-state,ACC
nebraska,Big 12
northwestern,Big Ten
notre-dame,
ohio-state,Big Ten
oklahoma,Big 12
oklahoma-state,Big 12
ole-miss,SEC
oregon,Pac-10
oregon-state,Pac-10
penn-state,Big Ten
pittsburgh,Big East
purdue,Big Ten
rutgers,Big East
stanford,Pac-10
temple,Big East
tennessee,SEC
texas,Big 12
texas-a-m,Big 12
texas-tech,Big 12
ucla,Pac-10
usc,Pac-10
vanderbilt,SEC
virginia-tech,Big East
washington,Pac-10
washington-state,Pac-10
west-virginia,Big East
wisconsin,Big Ten
"""

FIXTURES_2002 = """\
1,arizona-state,nebraska,0,2002-08-24,222360158
1,texas-tech,ohio-state,0,2002-08-24,222360194
2,baylor,california,0,2002-08-31,222430025
2,kansas,iowa-state,1,2002-08-31,222430066
2,mississippi-state,oregon,0,2002-08-31,222432483
2,missouri,illinois,0,2002-08-31,222430356
2,vanderbilt,georgia-tech,0,2002-08-31,222430059
2,washington,michigan,0,2002-08-31,222430130
2,lsu,virginia-tech,0,2002-09-01,222440259
2,auburn,usc,0,2002-09-03,222450030
3,oregon-state,temple,0,2002-09-05,222480218
3,alabama,oklahoma,0,2002-09-07,222500201
3,miami,florida,0,2002-09-07,222500057
3,purdue,notre-dame,0,2002-09-07,222500087
3,stanford,boston-college,0,2002-09-07,222500103
3,texas-a-m,pittsburgh,0,2002-09-07,222500221
3,west-virginia,wisconsin,0,2002-09-07,222500275
4,california,michigan-state,0,2002-09-14,222570127
4,duke,northwestern,0,2002-09-14,222570077
4,indiana,kentucky,0,2002-09-14,222570096
4,iowa-state,iowa,0,2002-09-14,222572294
4,miami,temple,1,2002-09-14,222570218
4,michigan,notre-dame,0,2002-09-14,222570087
4,ole-miss,texas-tech,0,2002-09-14,222572641
4,ucla,oklahoma-state,0,2002-09-14,222570197
4,usc,colorado,0,2002-09-14,222570038
4,vanderbilt,auburn,1,2002-09-14,222570002
4,washington-state,ohio-state,0,2002-09-14,222570194
4,nebraska,penn-state,0,2002-09-15,222570213
5,auburn,mississippi-state,1,2002-09-19,222620344
5,arizona,wisconsin,0,2002-09-21,222640275
5,boston-college,miami,1,2002-09-21,222642390
5,colorado,ucla,0,2002-09-21,222640026
5,florida,tennessee,1,2002-09-21,222642633
5,nc-state,texas-tech,0,2002-09-21,222642641
5,notre-dame,michigan-state,0,2002-09-21,222640127
5,rutgers,pittsburgh,1,2002-09-21,222640221
5,usc,kansas-state,0,2002-09-21,222642306
5,vanderbilt,ole-miss,1,2002-09-21,222640145
5,virginia-tech,texas-a-m,0,2002-09-21,222640245
6,alabama,arkansas,1,2002-09-28,222710008
6,indiana,ohio-state,1,2002-09-28,222710194
6,iowa,penn-state,1,2002-09-28,222710213
6,kentucky,florida,1,2002-09-28,222710057
6,michigan,illinois,1,2002-09-28,222710356
6,minnesota,purdue,1,2002-09-28,222712509
6,mississippi-state,lsu,1,2002-09-28,222710099
6,nebraska,iowa-state,1,2002-09-28,222710066
6,northwestern,michigan-state,1,2002-09-28,222710127
6,oregon-state,usc,1,2002-09-28,222710030
6,rutgers,tennessee,0,2002-09-28,222712633
6,stanford,arizona-state,1,2002-09-28,222710009
6,washington-state,california,1,2002-09-28,222710025
7,illinois,minnesota,1,2002-10-04,222760135
7,arkansas,tennessee,1,2002-10-05,222782633
7,california,washington,1,2002-10-05,222780264
7,florida,ole-miss,1,2002-10-05,222780145
7,georgia,alabama,1,2002-10-05,222780333
7,kansas,baylor,1,2002-10-05,222780239
7,kansas-state,colorado,1,2002-10-05,222780038
7,ohio-state,northwestern,1,2002-10-05,222780077
7,oklahoma,missouri,1,2002-10-05,222780142
7,oklahoma-state,texas,1,2002-10-05,222780251
7,penn-state,wisconsin,1,2002-10-05,222780275
7,purdue,iowa,1,2002-10-05,222782294
7,stanford,notre-dame,0,2002-10-05,222780087
7,texas-tech,texas-a-m,1,2002-10-05,222780245
7,ucla,oregon-state,1,2002-10-05,222780204
7,usc,washington-state,1,2002-10-05,222780265
7,oregon,arizona,1,2002-10-06,222780012
8,virginia-tech,boston-college,1,2002-10-10,222830103
8,northwestern,minnesota,1,2002-10-11,222830135
8,arizona,washington,1,2002-10-12,222850264
8,arkansas,auburn,1,2002-10-12,222850002
8,california,usc,1,2002-10-12,222850030
8,colorado,kansas,1,2002-10-12,222852305
8,lsu,florida,1,2002-10-12,222850057
8,michigan-state,iowa,1,2002-10-12,222852294
8,missouri,nebraska,1,2002-10-12,222850158
8,oklahoma-state,kansas-state,1,2002-10-12,222852306
8,oregon,ucla,1,2002-10-12,222850026
8,penn-state,michigan,1,2002-10-12,222850130
8,pittsburgh,notre-dame,0,2002-10-12,222850087
8,purdue,illinois,1,2002-10-12,222850356
8,tennessee,georgia,1,2002-10-12,222850061
8,texas,oklahoma,1,2002-10-12,222850201
8,texas-a-m,baylor,1,2002-10-12,222850239
8,texas-tech,iowa-state,1,2002-10-12,222850066
8,washington-state,stanford,1,2002-10-12,222850024
8,west-virginia,rutgers,1,2002-10-12,222850164
8,wisconsin,indiana,1,2002-10-12,222850084
8,oregon-state,arizona-state,1,2002-10-13,222850009
9,arizona,stanford,1,2002-10-19,222920024
9,arizona-state,oregon,1,2002-10-19,222922483
9,auburn,florida,1,2002-10-19,222920057
9,baylor,colorado,1,2002-10-19,222920038
9,duke,nc-state,1,2002-10-19,222920152
9,iowa,indiana,1,2002-10-19,222920084
9,iowa-state,oklahoma,1,2002-10-19,222920201
9,kentucky,arkansas,1,2002-10-19,222920008
9,michigan,purdue,1,2002-10-19,222922509
9,minnesota,michigan-state,1,2002-10-19,222920127
9,missouri,texas-tech,1,2002-10-19,222922641
9,nebraska,oklahoma-state,1,2002-10-19,222920197
9,northwestern,penn-state,1,2002-10-19,222920213
9,ohio-state,wisconsin,1,2002-10-19,222920275
9,ole-miss,alabama,1,2002-10-19,222920333
9,rutgers,virginia-tech,1,2002-10-19,222920259
9,texas,kansas-state,1,2002-10-19,222922306
9,texas-a-m,kansas,1,2002-10-19,222922305
9,ucla,california,1,2002-10-19,222920025
9,vanderbilt,georgia,1,2002-10-19,222920061
9,washington,usc,1,2002-10-19,222920030
10,alabama,tennessee,1,2002-10-26,222992633
10,boston-college,pittsburgh,1,2002-10-26,222990221
10,california,oregon-state,1,2002-10-26,222990204
10,georgia,kentucky,1,2002-10-26,222990096
10,indiana,illinois,1,2002-10-26,222990356
10,iowa,michigan,1,2002-10-26,222990130
10,iowa-state,texas,1,2002-10-26,222990251
10,kansas,missouri,1,2002-10-26,222990142
10,kansas-state,baylor,1,2002-10-26,222990239
10,lsu,auburn,1,2002-10-26,222990002
10,miami,west-virginia,1,2002-10-26,222990277
10,nebraska,texas-a-m,1,2002-10-26,222990245
10,ole-miss,arkansas,1,2002-10-26,222990008
10,penn-state,ohio-state,1,2002-10-26,222990194
10,purdue,northwestern,1,2002-10-26,222990077
10,stanford,ucla,1,2002-10-26,222990026
10,temple,virginia-tech,1,2002-10-26,222990259
10,texas-tech,colorado,1,2002-10-26,222990038
10,usc,oregon,1,2002-10-26,222992483
10,wisconsin,michigan-state,1,2002-10-26,222990127
10,washington,arizona-state,1,2002-10-27,222990009
10,washington-state,arizona,1,2002-10-27,222990012
11,alabama,vanderbilt,1,2002-11-02,223060238
11,arizona,oregon-state,1,2002-11-02,223060204
11,arizona-state,washington-state,1,2002-11-02,223060265
11,auburn,ole-miss,1,2002-11-02,223060145
11,baylor,texas-tech,1,2002-11-02,223062641
11,boston-college,notre-dame,0,2002-11-02,223060087
11,colorado,oklahoma,1,2002-11-02,223060201
11,georgia-tech,nc-state,1,2002-11-02,223060152
11,illinois,penn-state,1,2002-11-02,223060213
11,indiana,northwestern,1,2002-11-02,223060077
11,kansas-state,kansas,1,2002-11-02,223062305
11,kentucky,mississippi-state,1,2002-11-02,223060344
11,miami,rutgers,1,2002-11-02,223060164
11,michigan-state,michigan,1,2002-11-02,223060130
11,minnesota,ohio-state,1,2002-11-02,223060194
11,missouri,iowa-state,1,2002-11-02,223060066
11,stanford,oregon,1,2002-11-02,223062483
11,texas-a-m,oklahoma-state,1,2002-11-02,223060197
11,west-virginia,temple,1,2002-11-02,223060218
11,wisconsin,iowa,1,2002-11-02,223062294
11,florida,georgia,1,2002-11-03,223060061
11,pittsburgh,virginia-tech,1,2002-11-03,223060259
11,texas,nebraska,1,2002-11-03,223060158
11,ucla,washington,1,2002-11-03,223060264
12,baylor,texas,1,2002-11-09,223130251
12,boston-college,west-virginia,1,2002-11-09,223130277
12,california,arizona-state,1,2002-11-09,223130009
12,colorado,missouri,1,2002-11-09,223130142
12,florida,vanderbilt,1,2002-11-09,223130238
12,illinois,wisconsin,1,2002-11-09,223130275
12,kansas,nebraska,1,2002-11-09,223130158
12,lsu,kentucky,1,2002-11-09,223130096
12,miami,tennessee,0,2002-11-09,223132633
12,michigan-state,indiana,1,2002-11-09,223130084
12,mississippi-state,alabama,1,2002-11-09,223130333
12,northwestern,iowa,1,2002-11-09,223132294
12,ohio-state,purdue,1,2002-11-09,223132509
12,oklahoma,texas-a-m,1,2002-11-09,223130245
12,oklahoma-state,texas-tech,1,2002-11-09,223132641
12,oregon,washington-state,1,2002-11-09,223130265
12,oregon-state,washington,1,2002-11-09,223130264
12,temple,pittsburgh,1,2002-11-09,223130221
12,iowa-state,kansas-state,1,2002-11-10,223132306
12,michigan,minnesota,1,2002-11-10,223130135
12,ole-miss,georgia,1,2002-11-10,223130061
12,ucla,arizona,1,2002-11-10,223130012
12,usc,stanford,1,2002-11-10,223130024
13,arizona,california,1,2002-11-16,223200025
13,duke,georgia-tech,1,2002-11-16,223200059
13,georgia,auburn,1,2002-11-16,223200002
13,iowa,minnesota,1,2002-11-16,223200135
13,missouri,texas-a-m,1,2002-11-16,223200245
13,nebraska,kansas-state,1,2002-11-16,223202306
13,ohio-state,illinois,1,2002-11-16,223200356
13,oklahoma,baylor,1,2002-11-16,223200239
13,oklahoma-state,kansas,1,2002-11-16,223202305
13,oregon-state,stanford,1,2002-11-16,223200024
13,penn-state,indiana,1,2002-11-16,223200084
13,purdue,michigan-state,1,2002-11-16,223200127
13,temple,rutgers,1,2002-11-16,223200164
13,tennessee,mississippi-state,1,2002-11-16,223200344
13,texas,texas-tech,1,2002-11-16,223202641
13,vanderbilt,kentucky,1,2002-11-16,223200096
13,washington,oregon,1,2002-11-16,223202483
13,wisconsin,michigan,1,2002-11-16,223200130
13,alabama,lsu,1,2002-11-17,223200099
13,arizona-state,usc,1,2002-11-17,223200030
13,iowa-state,colorado,1,2002-11-17,223200038
14,west-virginia,virginia-tech,1,2002-11-21,223240259
14,pittsburgh,miami,1,2002-11-22,223252390
14,arkansas,mississippi-state,1,2002-11-23,223270344
14,auburn,alabama,1,2002-11-23,223270333
14,baylor,oklahoma-state,1,2002-11-23,223270197
14,boston-college,temple,1,2002-11-23,223270218
14,illinois,northwestern,1,2002-11-23,223270077
14,indiana,purdue,1,2002-11-23,223272509
14,kansas-state,missouri,1,2002-11-23,223270142
14,michigan,ohio-state,1,2002-11-23,223270194
14,michigan-state,penn-state,1,2002-11-23,223270213
14,minnesota,wisconsin,1,2002-11-23,223270275
14,oregon,oregon-state,1,2002-11-23,223270204
14,rutgers,notre-dame,0,2002-11-23,223270087
14,stanford,california,1,2002-11-23,223270025
14,tennessee,vanderbilt,1,2002-11-23,223270238
14,usc,ucla,1,2002-11-23,223270026
14,washington,washington-state,1,2002-11-23,223270265
14,ole-miss,lsu,1,2002-11-24,223270099
14,texas-tech,oklahoma,1,2002-11-24,223270201
15,arizona-state,arizona,1,2002-11-29,223330012
15,colorado,nebraska,1,2002-11-29,223330158
15,lsu,arkansas,1,2002-11-29,223330008
15,mississippi-state,ole-miss,1,2002-11-29,223320145
15,texas-a-m,texas,1,2002-11-29,223330251
15,georgia-tech,georgia,0,2002-11-30,223340061
15,kentucky,tennessee,1,2002-11-30,223342633
15,oklahoma,oklahoma-state,1,2002-11-30,223340197
15,rutgers,boston-college,1,2002-11-30,223340103
15,west-virginia,pittsburgh,1,2002-11-30,223340221
15,notre-dame,usc,0,2002-12-01,223340030
16,virginia-tech,miami,1,2002-12-07,223412390
16,washington-state,ucla,1,2002-12-07,223410026
"""

TEAMS_2007 = """\
air-force,Mountain West
akron,Mid-American
alabama,SEC
arizona,Pac-10
arizona-state,Pac-10
arkansas,SEC
arkansas-state,Sun Belt
army,
auburn,SEC
ball-state,Mid-American
baylor,Big 12
boise-state,Western Athletic
boston-college,ACC
bowling-green,Mid-American
byu,Mountain West
california,Pac-10
central-michigan,Mid-American
cincinnati,Big East
clemson,ACC
colorado,Big 12
colorado-state,Mountain West
duke,ACC
east-carolina,Conference USA
eastern-michigan,Mid-American
florida,SEC
florida-atlantic,Sun Belt
florida-international,Sun Belt
florida-state,ACC
fresno-state,Western Athletic
georgia,SEC
georgia-tech,ACC
hawai-i,Western Athletic
houston,Conference USA
idaho,Western Athletic
illinois,Big Ten
indiana,Big Ten
iowa,Big Ten
iowa-state,Big 12
kansas,Big 12
kansas-state,Big 12
kent-state,Mid-American
kentucky,SEC
louisiana,Sun Belt
louisiana-tech,Western Athletic
louisville,Big East
lsu,SEC
marshall,Conference USA
maryland,ACC
memphis,Conference USA
miami,ACC
miami-oh,Mid-American
michigan,Big Ten
michigan-state,Big Ten
middle-tennessee,Sun Belt
minnesota,Big Ten
mississippi-state,SEC
missouri,Big 12
navy,
nc-state,ACC
nebraska,Big 12
nevada,Western Athletic
new-mexico,Mountain West
new-mexico-state,Western Athletic
north-carolina,ACC
north-texas,Sun Belt
northern-illinois,Mid-American
northwestern,Big Ten
notre-dame,
ohio,Mid-American
ohio-state,Big Ten
oklahoma,Big 12
oklahoma-state,Big 12
ole-miss,SEC
oregon,Pac-10
oregon-state,Pac-10
penn-state,Big Ten
pittsburgh,Big East
purdue,Big Ten
rice,Conference USA
rutgers,Big East
san-diego-state,Mountain West
san-jose-state,Western Athletic
smu,Conference USA
south-carolina,SEC
south-florida,Big East
southern-miss,Conference USA
stanford,Pac-10
syracuse,Big East
tcu,Mountain West
temple,Mid-American
tennessee,SEC
texas,Big 12
texas-a-m,Big 12
texas-tech,Big 12
toledo,Mid-American
troy,Sun Belt
tulane,Conference USA
tulsa,Conference USA
ucf,Conference USA
ucla,Pac-10
uconn,Big East
ul-monroe,Sun Belt
unlv,Mountain West
usc,Pac-10
utah,Mountain West
utah-state,Western Athletic
vanderbilt,SEC
virginia,ACC
virginia-tech,ACC
wake-forest,ACC
washington,Pac-10
washington-state,Pac-10
west-virginia,Big East
western-michigan,Mid-American
wisconsin,Big Ten
wyoming,Mountain West
"""

FIXTURES_2007 = """\
1,miami-oh,ball-state,1,2007-08-30,272422050
1,tulsa,ul-monroe,0,2007-08-30,272422433
1,kent-state,iowa-state,0,2007-08-31,272420066
1,lsu,mississippi-state,1,2007-08-31,272420344
1,navy,temple,0,2007-08-31,272430218
1,unlv,utah-state,0,2007-08-31,272420328
1,utah,oregon-state,0,2007-08-31,272420204
1,arizona,byu,0,2007-09-01,272440252
1,arkansas-state,texas,0,2007-09-01,272440251
1,army,akron,0,2007-09-01,272442006
1,baylor,tcu,0,2007-09-01,272442628
1,central-michigan,kansas,0,2007-09-01,272442305
1,colorado-state,colorado,0,2007-09-01,272440038
1,east-carolina,virginia-tech,0,2007-09-01,272440259
1,eastern-michigan,pittsburgh,0,2007-09-01,272440221
1,florida-international,penn-state,0,2007-09-01,272440213
1,georgia-tech,notre-dame,0,2007-09-01,272440087
1,houston,oregon,0,2007-09-01,272442483
1,iowa,northern-illinois,0,2007-09-01,272442459
1,kansas-state,auburn,0,2007-09-01,272440002
1,louisiana,south-carolina,0,2007-09-01,272442579
1,marshall,miami,0,2007-09-01,272442390
1,middle-tennessee,florida-atlantic,1,2007-09-01,272442226
1,missouri,illinois,0,2007-09-01,272440356
1,nevada,nebraska,0,2007-09-01,272440158
1,north-texas,oklahoma,0,2007-09-01,272440201
1,oklahoma-state,georgia,0,2007-09-01,272440061
1,ole-miss,memphis,0,2007-09-01,272440235
1,purdue,toledo,0,2007-09-01,272442649
1,troy,arkansas,0,2007-09-01,272440008
1,ucf,nc-state,0,2007-09-01,272440152
1,ucla,stanford,1,2007-09-01,272440024
1,uconn,duke,0,2007-09-01,272440150
1,virginia,wyoming,0,2007-09-01,272442751
1,wake-forest,boston-college,1,2007-09-01,272440103
1,washington,syracuse,0,2007-09-01,272430183
1,washington-state,wisconsin,0,2007-09-01,272440275
1,western-michigan,west-virginia,0,2007-09-01,272440277
1,bowling-green,minnesota,0,2007-09-02,272440135
1,idaho,usc,0,2007-09-02,272440030
1,san-jose-state,arizona-state,0,2007-09-02,272440009
1,tennessee,california,0,2007-09-02,272440025
1,texas-tech,smu,0,2007-09-03,272462567
1,florida-state,clemson,1,2007-09-04,272460228
2,middle-tennessee,louisville,0,2007-09-06,272490097
2,oregon-state,cincinnati,0,2007-09-06,272492132
2,navy,rutgers,0,2007-09-07,272500164
2,air-force,utah,1,2007-09-08,272510254
2,akron,ohio-state,0,2007-09-08,272510194
2,alabama,vanderbilt,1,2007-09-08,272510238
2,ball-state,eastern-michigan,1,2007-09-08,272512199
2,boise-state,washington,0,2007-09-08,272510264
2,bowling-green,michigan-state,0,2007-09-08,272510127
2,byu,ucla,0,2007-09-08,272510026
2,california,colorado-state,0,2007-09-08,272510036
2,duke,virginia,1,2007-09-08,272510258
2,florida-atlantic,oklahoma-state,0,2007-09-08,272510197
2,fresno-state,texas-a-m,0,2007-09-08,272510245
2,hawai-i,louisiana-tech,1,2007-09-08,272512348
2,kent-state,kentucky,0,2007-09-08,272510096
2,maryland,florida-international,0,2007-09-08,272512229
2,miami,oklahoma,0,2007-09-08,272510201
2,miami-oh,minnesota,0,2007-09-08,272510135
2,mississippi-state,tulane,0,2007-09-08,272512655
2,missouri,ole-miss,0,2007-09-08,272510145
2,nc-state,boston-college,1,2007-09-08,272510103
2,nebraska,wake-forest,0,2007-09-08,272510154
2,nevada,northwestern,0,2007-09-08,272510077
2,north-carolina,east-carolina,0,2007-09-08,272510151
2,notre-dame,penn-state,0,2007-09-08,272510213
2,ohio,louisiana,0,2007-09-08,272510309
2,oregon,michigan,0,2007-09-08,272510130
2,rice,baylor,0,2007-09-08,272510239
2,san-diego-state,washington-state,0,2007-09-08,272510265
2,san-jose-state,kansas-state,0,2007-09-08,272512306
2,south-carolina,georgia,1,2007-09-08,272510061
2,southern-miss,tennessee,0,2007-09-08,272512633
2,tcu,texas,0,2007-09-08,272510251
2,toledo,central-michigan,1,2007-09-08,272512117
2,troy,florida,0,2007-09-08,272510057
2,ul-monroe,clemson,0,2007-09-08,272510228
2,utah-state,wyoming,0,2007-09-08,272512751
2,west-virginia,marshall,0,2007-09-08,272510276
2,colorado,arizona-state,0,2007-09-09,272510009
2,indiana,western-michigan,0,2007-09-09,272512711
2,new-mexico-state,new-mexico,0,2007-09-09,272510167
2,north-texas,smu,0,2007-09-09,272512567
2,south-florida,auburn,0,2007-09-09,272510002
2,syracuse,iowa,0,2007-09-09,272512294
2,virginia-tech,lsu,0,2007-09-09,272510099
2,wisconsin,unlv,0,2007-09-09,272512439
3,west-virginia,maryland,0,2007-09-13,272560120
3,tcu,air-force,1,2007-09-14,272562005
3,akron,indiana,0,2007-09-15,272580084
3,arkansas,alabama,1,2007-09-15,272580333
3,army,wake-forest,0,2007-09-15,272580154
3,ball-state,navy,0,2007-09-15,272582426
3,central-michigan,purdue,0,2007-09-15,272582509
3,cincinnati,miami-oh,0,2007-09-15,272580193
3,eastern-michigan,northern-illinois,1,2007-09-15,272582459
3,florida-international,miami,0,2007-09-15,272582390
3,fresno-state,oregon,0,2007-09-15,272582483
3,houston,tulane,1,2007-09-15,272582655
3,illinois,syracuse,0,2007-09-15,272580183
3,iowa,iowa-state,0,2007-09-15,272580066
3,louisiana-tech,california,0,2007-09-15,272580025
3,louisville,kentucky,0,2007-09-15,272580096
3,minnesota,florida-atlantic,0,2007-09-15,272582226
3,mississippi-state,auburn,1,2007-09-15,272580002
3,notre-dame,michigan,0,2007-09-15,272580130
3,ohio,virginia-tech,0,2007-09-15,272580259
3,ohio-state,washington,0,2007-09-15,272580264
3,oklahoma-state,troy,0,2007-09-15,272572653
3,ole-miss,vanderbilt,1,2007-09-15,272580238
3,pittsburgh,michigan-state,0,2007-09-15,272580127
3,smu,arkansas-state,0,2007-09-15,272582032
3,southern-miss,east-carolina,1,2007-09-15,272580151
3,temple,uconn,0,2007-09-15,272580041
3,tennessee,florida,1,2007-09-15,272580057
3,texas,ucf,0,2007-09-15,272582116
3,texas-tech,rice,0,2007-09-15,272580242
3,toledo,kansas,0,2007-09-15,272582305
3,ucla,utah,0,2007-09-15,272580254
3,ul-monroe,texas-a-m,0,2007-09-15,272580245
3,utah-state,oklahoma,0,2007-09-15,272580201
3,virginia,north-carolina,1,2007-09-15,272580153
3,western-michigan,missouri,0,2007-09-15,272580142
3,boston-college,georgia-tech,1,2007-09-16,272580059
3,byu,tulsa,0,2007-09-16,272580202
3,duke,northwestern,0,2007-09-16,272580077
3,florida-state,colorado,0,2007-09-16,272580038
3,hawai-i,unlv,0,2007-09-16,272582439
3,idaho,washington-state,0,2007-09-16,272580265
3,middle-tennessee,lsu,0,2007-09-16,272580099
3,new-mexico,arizona,0,2007-09-16,272580012
3,san-diego-state,arizona-state,0,2007-09-16,272580009
3,san-jose-state,stanford,0,2007-09-16,272580024
3,usc,nebraska,0,2007-09-16,272580158
3,wyoming,boise-state,0,2007-09-16,272580068
4,texas-a-m,miami,0,2007-09-20,272632390
4,air-force,byu,1,2007-09-22,272650252
4,arizona,california,1,2007-09-22,272650025
4,arkansas-state,tennessee,0,2007-09-22,272652633
4,army,boston-college,0,2007-09-22,272650103
4,ball-state,nebraska,0,2007-09-22,272650158
4,clemson,nc-state,1,2007-09-22,272650152
4,colorado-state,houston,0,2007-09-22,272650248
4,duke,navy,0,2007-09-22,272652426
4,east-carolina,west-virginia,0,2007-09-22,272650277
4,florida,ole-miss,1,2007-09-22,272650145
4,florida-atlantic,north-texas,1,2007-09-22,272650249
4,florida-international,kansas,0,2007-09-22,272652305
4,georgia,alabama,1,2007-09-22,272650333
4,georgia-tech,virginia,1,2007-09-22,272650258
4,illinois,indiana,1,2007-09-22,272650084
4,iowa-state,toledo,0,2007-09-22,272652649
4,kent-state,akron,1,2007-09-22,272652006
4,kentucky,arkansas,1,2007-09-22,272650008
4,marshall,cincinnati,0,2007-09-22,272652132
4,maryland,wake-forest,1,2007-09-22,272650154
4,memphis,ucf,1,2007-09-22,272652116
4,miami-oh,colorado,0,2007-09-22,272650038
4,michigan-state,notre-dame,0,2007-09-22,272650087
4,new-mexico-state,auburn,0,2007-09-22,272650002
4,north-carolina,south-florida,0,2007-09-22,272650058
4,northern-illinois,idaho,0,2007-09-22,272650070
4,northwestern,ohio-state,1,2007-09-22,272650194
4,oklahoma,tulsa,0,2007-09-22,272640202
4,penn-state,michigan,1,2007-09-22,272650130
4,rice,texas,0,2007-09-22,272650251
4,south-carolina,lsu,1,2007-09-22,272650099
4,syracuse,louisville,1,2007-09-22,272650097
4,temple,bowling-green,1,2007-09-22,272650189
4,texas-tech,oklahoma-state,1,2007-09-22,272650197
4,troy,louisiana,1,2007-09-22,272650309
4,uconn,pittsburgh,1,2007-09-22,272650221
4,wyoming,ohio,0,2007-09-22,272650195
4,iowa,wisconsin,1,2007-09-23,272650275
4,oregon,stanford,1,2007-09-23,272650024
4,oregon-state,arizona-state,1,2007-09-23,272650009
4,purdue,minnesota,1,2007-09-23,272650135
4,san-jose-state,utah-state,1,2007-09-23,272650328
4,smu,tcu,0,2007-09-23,272652628
4,utah,unlv,1,2007-09-23,272652439
4,washington,ucla,1,2007-09-23,272650026
4,washington-state,usc,1,2007-09-23,272650030
5,memphis,arkansas-state,0,2007-09-27,272702032
5,southern-miss,boise-state,0,2007-09-27,272700068
5,air-force,navy,0,2007-09-29,272722426
5,akron,uconn,0,2007-09-29,272720041
5,alabama,florida-state,0,2007-09-29,272720052
5,baylor,texas-a-m,1,2007-09-29,272720245
5,california,oregon,1,2007-09-29,272722483
5,clemson,georgia-tech,1,2007-09-29,272720059
5,colorado-state,tcu,1,2007-09-29,272722628
5,duke,miami,1,2007-09-29,272722390
5,east-carolina,houston,1,2007-09-29,272720248
5,eastern-michigan,vanderbilt,0,2007-09-29,272720238
5,florida-atlantic,kentucky,0,2007-09-29,272720096
5,florida-international,middle-tennessee,1,2007-09-29,272722393
5,hawai-i,idaho,1,2007-09-29,272720070
5,indiana,iowa,1,2007-09-29,272722294
5,iowa-state,nebraska,1,2007-09-29,272720158
5,kansas-state,texas,1,2007-09-29,272720251
5,kent-state,ohio,1,2007-09-29,272720195
5,louisiana,ucf,0,2007-09-29,272722116
5,louisville,nc-state,0,2007-09-29,272720152
5,lsu,tulane,0,2007-09-29,272722655
5,maryland,rutgers,0,2007-09-29,272720164
5,michigan,northwestern,1,2007-09-29,272720077
5,michigan-state,wisconsin,1,2007-09-29,272720275
5,mississippi-state,south-carolina,1,2007-09-29,272722579
5,north-carolina,virginia-tech,1,2007-09-29,272720259
5,north-texas,arkansas,0,2007-09-29,272720008
5,northern-illinois,central-michigan,1,2007-09-29,272722117
5,notre-dame,purdue,0,2007-09-29,272722509
5,oklahoma,colorado,1,2007-09-29,272720038
5,ole-miss,georgia,1,2007-09-29,272720061
5,penn-state,illinois,1,2007-09-29,272720356
5,pittsburgh,virginia,0,2007-09-29,272720258
5,syracuse,miami-oh,0,2007-09-29,272720193
5,temple,army,0,2007-09-29,272720349
5,ucla,oregon-state,1,2007-09-29,272720204
5,ul-monroe,troy,1,2007-09-29,272722653
5,unlv,nevada,0,2007-09-29,272722440
5,utah-state,utah,0,2007-09-29,272720254
5,west-virginia,south-florida,1,2007-09-29,272710058
5,western-michigan,toledo,1,2007-09-29,272722649
5,arizona-state,stanford,1,2007-09-30,272720024
5,auburn,florida,1,2007-09-30,272720057
5,byu,new-mexico,1,2007-09-30,272720167
5,cincinnati,san-diego-state,0,2007-09-30,272720021
5,louisiana-tech,fresno-state,1,2007-09-30,272720278
5,ohio-state,minnesota,1,2007-09-30,272720135
5,usc,washington,1,2007-09-30,272720264
5,washington-state,arizona,1,2007-09-30,272720012
6,marshall,memphis,1,2007-10-03,272750235
6,kentucky,south-carolina,1,2007-10-04,272772579
6,rice,southern-miss,1,2007-10-04,272762572
6,akron,western-michigan,1,2007-10-06,272792711
6,arizona,oregon-state,1,2007-10-06,272790204
6,arizona-state,washington-state,1,2007-10-06,272790265
6,arkansas-state,ul-monroe,1,2007-10-06,272792433
6,bowling-green,boston-college,0,2007-10-06,272790103
6,central-michigan,ball-state,1,2007-10-06,272792050
6,colorado,baylor,1,2007-10-06,272790239
6,eastern-michigan,michigan,0,2007-10-06,272790130
6,fresno-state,nevada,1,2007-10-06,272792440
6,georgia,tennessee,1,2007-10-06,272792633
6,georgia-tech,maryland,1,2007-10-06,272790120
6,houston,alabama,0,2007-10-06,272790333
6,idaho,san-jose-state,1,2007-10-06,272790023
6,iowa,penn-state,1,2007-10-06,272790213
6,iowa-state,texas-tech,1,2007-10-06,272792641
6,kansas,kansas-state,1,2007-10-06,272792306
6,louisiana-tech,ole-miss,0,2007-10-06,272790145
6,miami,north-carolina,1,2007-10-06,272790153
6,miami-oh,kent-state,1,2007-10-06,272792309
6,minnesota,indiana,1,2007-10-06,272790084
6,nc-state,florida-state,1,2007-10-06,272790052
6,north-texas,louisiana,1,2007-10-06,272790309
6,northern-illinois,temple,1,2007-10-06,272790218
6,northwestern,michigan-state,1,2007-10-06,272790127
6,oklahoma,texas,1,2007-10-06,272790251
6,oklahoma-state,texas-a-m,1,2007-10-06,272790245
6,san-diego-state,colorado-state,1,2007-10-06,272790036
6,south-florida,florida-atlantic,0,2007-10-06,272792226
6,stanford,usc,1,2007-10-06,272790030
6,tcu,wyoming,1,2007-10-06,272792751
6,troy,florida-international,1,2007-10-06,272792229
6,tulane,army,0,2007-10-06,272790349
6,ucf,east-carolina,1,2007-10-06,272790151
6,utah,louisville,0,2007-10-06,272780097
6,vanderbilt,auburn,1,2007-10-06,272790002
6,virginia,middle-tennessee,0,2007-10-06,272792393
6,virginia-tech,clemson,1,2007-10-06,272790228
6,wake-forest,duke,1,2007-10-06,272790150
6,west-virginia,syracuse,1,2007-10-06,272790183
6,wisconsin,illinois,1,2007-10-06,272790356
6,cincinnati,rutgers,1,2007-10-07,272790164
6,florida,lsu,1,2007-10-07,272790099
6,nebraska,missouri,1,2007-10-07,272790142
6,notre-dame,ucla,0,2007-10-07,272790026
6,ohio-state,purdue,1,2007-10-07,272792509
6,unlv,air-force,1,2007-10-07,272792005
6,utah-state,hawai-i,1,2007-10-07,272790062
6,new-mexico-state,boise-state,1,2007-10-08,272800068
7,florida-state,wake-forest,1,2007-10-11,272840154
7,navy,pittsburgh,0,2007-10-11,272830221
7,air-force,colorado-state,1,2007-10-13,272860036
7,alabama,ole-miss,1,2007-10-13,272860145
7,arizona,usc,1,2007-10-13,272860030
7,army,central-michigan,0,2007-10-13,272862117
7,auburn,arkansas,1,2007-10-13,272860008
7,baylor,kansas,1,2007-10-13,272862305
7,boston-college,notre-dame,0,2007-10-13,272860087
7,bowling-green,miami-oh,1,2007-10-13,272860193
7,eastern-michigan,ohio,1,2007-10-13,272860195
7,fresno-state,idaho,1,2007-10-13,272860070
7,georgia,vanderbilt,1,2007-10-13,272860238
7,georgia-tech,miami,1,2007-10-13,272862390
7,hawai-i,san-jose-state,1,2007-10-13,272850023
7,illinois,iowa,1,2007-10-13,272862294
7,indiana,michigan-state,1,2007-10-13,272860127
7,kent-state,ohio-state,0,2007-10-13,272860194
7,louisiana,arkansas-state,1,2007-10-13,272862032
7,louisville,cincinnati,1,2007-10-13,272862132
7,lsu,kentucky,1,2007-10-13,272860096
7,marshall,tulsa,1,2007-10-13,272860202
7,minnesota,northwestern,1,2007-10-13,272860077
7,missouri,oklahoma,1,2007-10-13,272860201
7,new-mexico,wyoming,1,2007-10-13,272862751
7,new-mexico-state,louisiana-tech,1,2007-10-13,272862348
7,oklahoma-state,nebraska,1,2007-10-13,272860158
7,oregon-state,california,1,2007-10-13,272860025
7,purdue,michigan,1,2007-10-13,272860130
7,rice,houston,1,2007-10-13,272860248
7,rutgers,syracuse,1,2007-10-13,272860183
7,san-diego-state,utah,1,2007-10-13,272860254
7,smu,southern-miss,1,2007-10-13,272862572
7,south-carolina,north-carolina,0,2007-10-13,272860153
7,tcu,stanford,0,2007-10-13,272860024
7,temple,akron,1,2007-10-13,272862006
7,tennessee,mississippi-state,1,2007-10-13,272860344
7,texas,iowa-state,1,2007-10-13,272860066
7,texas-a-m,texas-tech,1,2007-10-13,272862641
7,ucf,south-florida,0,2007-10-13,272860058
7,uconn,virginia,0,2007-10-13,272860258
7,ul-monroe,north-texas,1,2007-10-13,272860249
7,virginia-tech,duke,1,2007-10-13,272860150
7,washington-state,oregon,1,2007-10-13,272862483
7,western-michigan,northern-illinois,1,2007-10-13,272862459
7,wisconsin,penn-state,1,2007-10-13,272860213
7,byu,unlv,1,2007-10-14,272862439
7,colorado,kansas-state,1,2007-10-14,272862306
7,middle-tennessee,memphis,0,2007-10-14,272860235
7,washington,arizona-state,1,2007-10-14,272860009
7,nevada,boise-state,1,2007-10-15,272870068
8,south-florida,rutgers,1,2007-10-18,272910164
8,northwestern,eastern-michigan,0,2007-10-19,272922199
8,utah,tcu,1,2007-10-19,272912628
8,arkansas,ole-miss,1,2007-10-20,272930145
8,arkansas-state,middle-tennessee,1,2007-10-20,272932393
8,army,georgia-tech,0,2007-10-20,272930059
8,ball-state,western-michigan,1,2007-10-20,272932711
8,boise-state,louisiana-tech,1,2007-10-20,272932348
8,bowling-green,kent-state,1,2007-10-20,272932309
8,california,ucla,1,2007-10-20,272930026
8,central-michigan,clemson,0,2007-10-20,272930228
8,cincinnati,pittsburgh,1,2007-10-20,272930221
8,florida,kentucky,1,2007-10-20,272930096
8,florida-atlantic,louisiana,1,2007-10-20,272930309
8,florida-international,ul-monroe,1,2007-10-20,272932433
8,iowa,purdue,1,2007-10-20,272932509
8,kansas,colorado,1,2007-10-20,272930038
8,kansas-state,oklahoma-state,1,2007-10-20,272930197
8,louisville,uconn,1,2007-10-20,272920041
8,memphis,rice,1,2007-10-20,272930242
8,miami,florida-state,1,2007-10-20,272930052
8,miami-oh,temple,1,2007-10-20,272930218
8,michigan-state,ohio-state,1,2007-10-20,272930194
8,mississippi-state,west-virginia,0,2007-10-20,272930277
8,nc-state,east-carolina,0,2007-10-20,272930151
8,nevada,utah-state,1,2007-10-20,272930328
8,north-texas,troy,1,2007-10-20,272932653
8,northern-illinois,wisconsin,0,2007-10-20,272930275
8,ohio,toledo,1,2007-10-20,272932649
8,oklahoma,iowa-state,1,2007-10-20,272930066
8,oregon,washington,1,2007-10-20,272930264
8,penn-state,indiana,1,2007-10-20,272930084
8,san-jose-state,fresno-state,1,2007-10-20,272930278
8,stanford,arizona,1,2007-10-20,272930012
8,tennessee,alabama,1,2007-10-20,272930333
8,texas,baylor,1,2007-10-20,272930239
8,texas-a-m,nebraska,1,2007-10-20,272930158
8,texas-tech,missouri,1,2007-10-20,272930142
8,usc,notre-dame,0,2007-10-20,272930087
8,vanderbilt,south-carolina,1,2007-10-20,272932579
8,wake-forest,navy,0,2007-10-20,272932426
8,wyoming,air-force,1,2007-10-20,272932005
8,auburn,lsu,1,2007-10-21,272930099
8,colorado-state,unlv,1,2007-10-21,272932439
8,idaho,new-mexico-state,1,2007-10-21,272930166
8,michigan,illinois,1,2007-10-21,272930356
8,new-mexico,san-diego-state,1,2007-10-21,272930021
8,tulane,smu,1,2007-10-21,272932567
8,virginia,maryland,1,2007-10-21,272930120
8,southern-miss,marshall,1,2007-10-22,272940276
9,boston-college,virginia-tech,1,2007-10-25,272980259
9,air-force,new-mexico,1,2007-10-26,272980167
9,arizona,washington,1,2007-10-27,273000264
9,ball-state,illinois,0,2007-10-27,273000356
9,baylor,kansas-state,1,2007-10-27,273002306
9,boise-state,fresno-state,1,2007-10-27,272990278
9,central-michigan,kent-state,1,2007-10-27,273002309
9,clemson,maryland,1,2007-10-27,273000120
9,colorado,texas-tech,1,2007-10-27,273002641
9,florida-international,arkansas,0,2007-10-27,273000008
9,georgia,florida,1,2007-10-27,273000061
9,idaho,nevada,1,2007-10-27,273002440
9,indiana,wisconsin,1,2007-10-27,273000275
9,iowa-state,missouri,1,2007-10-27,273000142
9,kansas,texas-a-m,1,2007-10-27,273000245
9,louisiana-tech,utah-state,1,2007-10-27,273000328
9,memphis,tulane,1,2007-10-27,273002655
9,miami-oh,vanderbilt,0,2007-10-27,273000238
9,michigan-state,iowa,1,2007-10-27,273002294
9,middle-tennessee,north-texas,1,2007-10-27,273000249
9,minnesota,michigan,1,2007-10-27,273000130
9,mississippi-state,kentucky,1,2007-10-27,273000096
9,nebraska,texas,1,2007-10-27,273000251
9,north-carolina,wake-forest,1,2007-10-27,273000154
9,northern-illinois,toledo,1,2007-10-27,273002649
9,northwestern,purdue,1,2007-10-27,273002509
9,ohio,bowling-green,1,2007-10-27,273000189
9,ole-miss,auburn,1,2007-10-27,273000002
9,pittsburgh,louisville,1,2007-10-27,273000097
9,rice,marshall,1,2007-10-27,273000276
9,smu,tulsa,1,2007-10-27,273000202
9,south-carolina,tennessee,1,2007-10-27,273002633
9,south-florida,uconn,1,2007-10-27,273000041
9,stanford,oregon-state,1,2007-10-27,273000204
9,troy,arkansas-state,1,2007-10-27,273002032
9,ucla,washington-state,1,2007-10-27,273000265
9,ul-monroe,florida-atlantic,1,2007-10-27,273002226
9,unlv,wyoming,1,2007-10-27,273002751
9,usc,oregon,1,2007-10-27,273002483
9,utah,colorado-state,1,2007-10-27,273000036
9,virginia,nc-state,1,2007-10-27,273000152
9,west-virginia,rutgers,1,2007-10-27,273000164
9,western-michigan,eastern-michigan,1,2007-10-27,273002199
9,california,arizona-state,1,2007-10-28,273000009
9,duke,florida-state,1,2007-10-28,273000052
9,new-mexico-state,hawai-i,1,2007-10-28,273000062
9,ohio-state,penn-state,1,2007-10-28,273000213
9,ucf,southern-miss,1,2007-10-29,273012572
10,virginia-tech,georgia-tech,1,2007-11-01,273050059
10,akron,bowling-green,1,2007-11-02,273060189
10,temple,ohio,1,2007-11-02,273060195
10,arizona-state,oregon,1,2007-11-03,273072483
10,army,air-force,0,2007-11-03,273072005
10,ball-state,indiana,0,2007-11-03,273070084
10,cincinnati,south-florida,1,2007-11-03,273070058
10,clemson,duke,1,2007-11-03,273070150
10,colorado-state,byu,1,2007-11-03,273070252
10,east-carolina,memphis,1,2007-11-03,273070235
10,eastern-michigan,toledo,1,2007-11-03,273072649
10,florida-international,arkansas-state,1,2007-11-03,273072032
10,iowa,northwestern,1,2007-11-03,273070077
10,kansas-state,iowa-state,1,2007-11-03,273070066
10,louisiana,tennessee,0,2007-11-03,273072633
10,louisiana-tech,idaho,1,2007-11-03,273070070
10,lsu,alabama,1,2007-11-03,273070333
10,marshall,ucf,1,2007-11-03,273072116
10,maryland,north-carolina,1,2007-11-03,273070153
10,michigan,michigan-state,1,2007-11-03,273070127
10,middle-tennessee,ul-monroe,1,2007-11-03,273072433
10,missouri,colorado,1,2007-11-03,273070038
10,navy,notre-dame,0,2007-11-03,273070087
10,nc-state,miami,1,2007-11-03,273072390
10,nebraska,kansas,1,2007-11-03,273072305
10,nevada,new-mexico-state,1,2007-11-03,273060166
10,new-mexico,tcu,1,2007-11-03,273072628
10,purdue,penn-state,1,2007-11-03,273070213
10,rutgers,uconn,1,2007-11-03,273070041
10,san-jose-state,boise-state,1,2007-11-03,273070068
10,syracuse,pittsburgh,1,2007-11-03,273070221
10,texas,oklahoma-state,1,2007-11-03,273070197
10,texas-tech,baylor,1,2007-11-03,273070239
10,troy,georgia,0,2007-11-03,273070061
10,tulsa,tulane,1,2007-11-03,273072655
10,ucla,arizona,1,2007-11-03,273070012
10,utah-state,fresno-state,1,2007-11-03,273070278
10,vanderbilt,florida,1,2007-11-03,273070057
10,wake-forest,virginia,1,2007-11-03,273070258
10,washington,stanford,1,2007-11-03,273070024
10,wisconsin,ohio-state,1,2007-11-03,273070194
10,florida-state,boston-college,1,2007-11-04,273070103
10,illinois,minnesota,1,2007-11-04,273070135
10,oregon-state,usc,1,2007-11-04,273070030
10,south-carolina,arkansas,1,2007-11-04,273070008
10,texas-a-m,oklahoma,1,2007-11-04,273070201
10,washington-state,california,1,2007-11-04,273070025
10,wyoming,san-diego-state,1,2007-11-04,273070021
10,smu,houston,1,2007-11-05,273080248
11,central-michigan,western-michigan,1,2007-11-07,273102711
11,ohio,akron,1,2007-11-08,273112006
11,louisville,west-virginia,1,2007-11-09,273120277
11,tcu,byu,1,2007-11-09,273120252
11,air-force,notre-dame,0,2007-11-10,273140087
11,alabama,mississippi-state,1,2007-11-10,273140344
11,arizona-state,ucla,1,2007-11-10,273140026
11,arkansas,tennessee,1,2007-11-10,273142633
11,arkansas-state,florida-atlantic,1,2007-11-10,273142226
11,auburn,georgia,1,2007-11-10,273140061
11,baylor,oklahoma,1,2007-11-10,273140201
11,boise-state,utah-state,1,2007-11-10,273140328
11,bowling-green,eastern-michigan,1,2007-11-10,273132199
11,colorado,iowa-state,1,2007-11-10,273140066
11,colorado-state,new-mexico,1,2007-11-10,273140167
11,east-carolina,marshall,1,2007-11-10,273140276
11,florida-state,virginia-tech,1,2007-11-10,273140259
11,georgia-tech,duke,1,2007-11-10,273140150
11,houston,tulsa,1,2007-11-10,273140202
11,illinois,ohio-state,1,2007-11-10,273140194
11,indiana,northwestern,1,2007-11-10,273140077
11,kansas-state,nebraska,1,2007-11-10,273140158
11,kent-state,northern-illinois,1,2007-11-10,273142459
11,kentucky,vanderbilt,1,2007-11-10,273140238
11,louisiana,middle-tennessee,1,2007-11-10,273142393
11,memphis,southern-miss,1,2007-11-10,273142572
11,michigan,wisconsin,1,2007-11-10,273140275
11,michigan-state,purdue,1,2007-11-10,273142509
11,minnesota,iowa,1,2007-11-10,273142294
11,navy,north-texas,0,2007-11-10,273140249
11,new-mexico-state,san-jose-state,1,2007-11-10,273140023
11,north-carolina,nc-state,1,2007-11-10,273140152
11,penn-state,temple,0,2007-11-10,273140218
11,rice,smu,1,2007-11-10,273142567
11,rutgers,army,0,2007-11-10,273130349
11,south-florida,syracuse,1,2007-11-10,273140183
11,stanford,washington-state,1,2007-11-10,273140265
11,texas-a-m,missouri,1,2007-11-10,273140142
11,texas-tech,texas,1,2007-11-10,273140251
11,uconn,cincinnati,1,2007-11-10,273142132
11,wake-forest,clemson,1,2007-11-10,273140228
11,wyoming,utah,1,2007-11-10,273140254
11,boston-college,maryland,1,2007-11-11,273140120
11,florida,south-carolina,1,2007-11-11,273142579
11,fresno-state,hawai-i,1,2007-11-11,273140062
11,kansas,oklahoma-state,1,2007-11-11,273140197
11,louisiana-tech,lsu,0,2007-11-11,273140099
11,san-diego-state,unlv,1,2007-11-11,273142439
11,usc,california,1,2007-11-11,273140025
11,virginia,miami,1,2007-11-11,273142390
11,washington,oregon-state,1,2007-11-11,273140204
12,toledo,ball-state,1,2007-11-14,273172050
12,akron,miami-oh,1,2007-11-15,273180193
12,north-texas,arkansas-state,1,2007-11-16,273192032
12,oregon,arizona,1,2007-11-16,273190012
12,byu,wyoming,1,2007-11-17,273212751
12,california,washington,1,2007-11-17,273210264
12,duke,notre-dame,0,2007-11-17,273210087
12,eastern-michigan,central-michigan,1,2007-11-17,273202117
12,florida-atlantic,florida,0,2007-11-17,273210057
12,hawai-i,nevada,1,2007-11-17,273202440
12,idaho,boise-state,1,2007-11-17,273210068
12,iowa-state,kansas,1,2007-11-17,273212305
12,kent-state,temple,1,2007-11-17,273210218
12,kentucky,georgia,1,2007-11-17,273210061
12,lsu,ole-miss,1,2007-11-17,273210145
12,marshall,houston,1,2007-11-17,273210248
12,maryland,florida-state,1,2007-11-17,273210052
12,miami,virginia-tech,1,2007-11-17,273210259
12,mississippi-state,arkansas,1,2007-11-17,273210008
12,missouri,kansas-state,1,2007-11-17,273212306
12,nc-state,wake-forest,1,2007-11-17,273210154
12,new-mexico,utah,1,2007-11-17,273210254
12,north-carolina,georgia-tech,1,2007-11-17,273210059
12,northern-illinois,navy,0,2007-11-17,273212426
12,northwestern,illinois,1,2007-11-17,273210356
12,ohio-state,michigan,1,2007-11-17,273210130
12,oregon-state,washington-state,1,2007-11-17,273210265
12,penn-state,michigan-state,1,2007-11-17,273210127
12,pittsburgh,rutgers,1,2007-11-17,273210164
12,purdue,indiana,1,2007-11-17,273210084
12,san-diego-state,air-force,1,2007-11-17,273212005
12,syracuse,uconn,1,2007-11-17,273210041
12,tulane,rice,1,2007-11-17,273210242
12,tulsa,army,0,2007-11-17,273210349
12,ucf,smu,1,2007-11-17,273212567
12,ul-monroe,alabama,0,2007-11-17,273210333
12,utah-state,new-mexico-state,1,2007-11-17,273210166
12,vanderbilt,tennessee,1,2007-11-17,273212633
12,western-michigan,iowa,0,2007-11-17,273212294
12,wisconsin,minnesota,1,2007-11-17,273210135
12,boston-college,clemson,1,2007-11-18,273210228
12,louisiana,florida-international,1,2007-11-18,273212229
12,louisville,south-florida,1,2007-11-18,273210058
12,oklahoma,texas-tech,1,2007-11-18,273212641
12,oklahoma-state,baylor,1,2007-11-18,273210239
12,san-jose-state,louisiana-tech,1,2007-11-18,273212348
12,unlv,tcu,1,2007-11-18,273212628
12,west-virginia,cincinnati,1,2007-11-18,273212132
13,middle-tennessee,troy,1,2007-11-21,273242653
13,arkansas,lsu,1,2007-11-23,273270099
13,central-michigan,akron,1,2007-11-23,273272006
13,nebraska,colorado,1,2007-11-23,273270038
13,ole-miss,mississippi-state,1,2007-11-23,273270344
13,texas,texas-a-m,1,2007-11-23,273270245
13,toledo,bowling-green,1,2007-11-23,273270189
13,usc,arizona-state,1,2007-11-23,273260009
13,wyoming,colorado-state,1,2007-11-23,273270036
13,arkansas-state,southern-miss,0,2007-11-24,273282572
13,ball-state,northern-illinois,1,2007-11-24,273282459
13,boise-state,hawai-i,1,2007-11-24,273270062
13,duke,north-carolina,1,2007-11-24,273280153
13,florida-state,florida,0,2007-11-24,273280057
13,georgia,georgia-tech,0,2007-11-24,273280059
13,kansas-state,fresno-state,0,2007-11-24,273280278
13,maryland,nc-state,1,2007-11-24,273280152
13,miami,boston-college,1,2007-11-24,273280103
13,miami-oh,ohio,1,2007-11-24,273280195
13,nevada,san-jose-state,1,2007-11-24,273280023
13,notre-dame,stanford,0,2007-11-24,273280024
13,oklahoma-state,oklahoma,1,2007-11-24,273280201
13,oregon,ucla,1,2007-11-24,273280026
13,smu,memphis,1,2007-11-24,273280235
13,south-florida,pittsburgh,1,2007-11-24,273280221
13,temple,western-michigan,1,2007-11-24,273282711
13,tennessee,kentucky,1,2007-11-24,273280096
13,tulane,east-carolina,1,2007-11-24,273280151
13,tulsa,rice,1,2007-11-24,273280242
13,uconn,west-virginia,1,2007-11-24,273280277
13,unlv,new-mexico,1,2007-11-24,273280167
13,utah,byu,1,2007-11-24,273280252
13,utah-state,idaho,1,2007-11-24,273280070
13,virginia-tech,virginia,1,2007-11-24,273280258
13,wake-forest,vanderbilt,0,2007-11-24,273280238
13,alabama,auburn,1,2007-11-25,273280002
13,cincinnati,syracuse,1,2007-11-25,273280183
13,clemson,south-carolina,0,2007-11-25,273282579
13,florida-atlantic,florida-international,1,2007-11-25,273282229
13,missouri,kansas,1,2007-11-25,273282305
13,tcu,san-diego-state,1,2007-11-25,273280021
13,ul-monroe,louisiana,1,2007-11-25,273280309
13,washington-state,washington,1,2007-11-25,273280264
14,rutgers,louisville,1,2007-11-30,273330097
14,army,navy,0,2007-12-01,273352426
14,byu,san-diego-state,1,2007-12-01,273350021
14,florida-atlantic,troy,1,2007-12-01,273352653
14,fresno-state,new-mexico-state,1,2007-12-01,273340166
14,louisiana-tech,nevada,1,2007-12-01,273352440
14,oregon-state,oregon,1,2007-12-01,273352483
14,ucla,usc,1,2007-12-01,273350030
14,arizona,arizona-state,1,2007-12-02,273350009
14,california,stanford,1,2007-12-02,273350024
14,north-texas,florida-international,1,2007-12-02,273352229
14,pittsburgh,west-virginia,1,2007-12-02,273350277
14,washington,hawai-i,0,2007-12-02,273350062
"""
