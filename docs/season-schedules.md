# Historical season schedules

A historical template is a fixed calendar of playable matchups. The season manager
uses the conference each team belonged to in that year. Campaign standings start
empty and reflect the games played in the campaign.

| Template | Teams | Fixtures | Scope |
| --- | ---: | ---: | --- |
| 1972 Big Eight | 8 | 28 | Complete original conference calendar |
| 2002 NCAA | 55 | 236 | Regular-season fixtures between the 55 published chart teams |
| 2007 NCAA | 116 | 640 | Regular-season fixtures between the 116 published chart teams |

Templates appear when all their required team editions are installed. The 1972
template covers conference games. The 2002 and 2007 templates omit games against
the other teams, conference championship games, and bowls. Season results,
standings, and strength of schedule cover the competition defined by the selected
template. Home and away designations are those shown by the source. They are
fixture roles even for historical games held at a neutral site.

## Sources and normalization

The League's historical Big Eight membership is listed in the University of
Colorado's [conference history](https://static.cubuffs.com/custompages/Football/2020_Info_Guide/161-166_conference_history.pdf).
The 1972 fixtures were transcribed from the corresponding team schedules and
record books. Weeks run Monday through Sunday beginning September 4, 1972.
The Iowa State and Oklahoma State schedule pages disagree on their matchup
date. The Oklahoma State schedule, the Iowa State fact book and contemporary
UPI coverage support November 25. [Colorado football record book](https://static.cubuffs.com/custompages/football/2025_Record_Book/2025_Record_Book.pdf),
[Iowa State schedule](https://cyclones.com/sports/football/schedule/1972),
[Iowa State football fact book](https://s3.us-east-2.amazonaws.com/sidearm.nextgen.sites/isuni.sidearmsports.com/documents/2015/5/5/Media_Guide.pdf),
[Kansas opponent histories](https://kuathletics.com/sports/football/opponent-history/university-of-missouri/2900),
[Kansas State schedule](https://www.kstatesports.com/sports/football/schedule/1972),
[Missouri schedule](https://mutigers.com/sports/football/schedule/season/1972),
[Nebraska schedule](https://huskers.com/sports/football/schedule/season/1972),
[Oklahoma football guide](https://s3.us-east-2.amazonaws.com/sidearm.nextgen.sites/soonersports.com/documents/2013/7/25/2012_ou_football_guide.pdf),
[Oklahoma State schedule](https://okstate.com/sports/football/schedule/text/1972),
[November 26, 1972 Times-News](https://tfpl.sfo2.digitaloceanspaces.com/Newspapers/Times-News_TF295/PDF/1972_11_26.pdf).

The 2002 and 2007 fixture facts come from CollegeFootballData via SportsDataverse
cfbfastR-data commit `05424e595b2f24f7a9474c061bf7fc73a7494d72`. Each row
retains the source game ID and UTC date, which can be one day later than the
stadium's local date. Conference names are year-specific and independents have
no conference. A game can count in conference standings when the source flag
is set and both teams belong to the same conference. This corrects conflicts
such as 2002 Washington at Michigan and 2007 Oregon at Michigan. Only factual
fixture fields and conference names are retained. Historical scores,
play-by-play, attendance, predictions, logos, and source narrative are omitted.
[2002 source CSV](https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/05424e595b2f24f7a9474c061bf7fc73a7494d72/schedules/csv/cfb_schedules_2002.csv),
[2007 source CSV](https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/05424e595b2f24f7a9474c061bf7fc73a7494d72/schedules/csv/cfb_schedules_2007.csv).

| Source file | SHA-256 |
| --- | --- |
| `cfb_schedules_2002.csv` | `cad41175d46b4262be952b32fedda1e5d084270d0775ea7ac01ee8f57f9b34b6` |
| `cfb_schedules_2007.csv` | `6b4a87e86c60a91fd57f0a3ddba056ef05c3e2f2f5d4d259b2b198889c47b022` |
