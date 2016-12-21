from bs4 import BeautifulSoup
import requests
from operator import itemgetter
from flask import Flask, render_template, request, redirect, url_for
from urlparse import parse_qs, urlparse

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the URL that the user entered in the form.
        url = request.form['url']
        invalidURL = False
        try:
            teams, turnoverCol = setup(url)
        except:
            invalidURL = True
            return render_template('index.html', invalidURL=invalidURL)
        query = parse_qs(urlparse(url).query, keep_blank_values=True)
        leagueId = str(query['leagueId'][0])
        return redirect(url_for('rankings', leagueId=leagueId))
    else:
        return render_template('index.html')


@app.route('/rankings/<leagueId>')
def rankings(leagueId):
    url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId=2017'.format(str(leagueId))
    teams, turnoverCol = setup(url)
    matchups, rankings = computeStats(teams, turnoverCol)
    return render_template('results.html', rankings=rankings, leagueId=leagueId)


@app.route('/matchups/<leagueId>')
def matchups(leagueId):
    url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId=2017'.format(str(leagueId))
    teams, turnoverCol = setup(url)
    matchups, rankings = computeStats(teams, turnoverCol)
    return render_template('matchups.html', matchups=matchups)


# Scrapes the "Season Stats" table from the ESPN Fantasy Standings page.
def setup(url):
    source_code = requests.get(url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text, 'html.parser')

    seasonStats = soup.find('table', {'id': 'statsTable'})
    teams = []
    turnoverCol = 0
    catlist = seasonStats.findAll('tr')[2].findAll('a')
    for category in catlist:
        if str(category.string) == 'TO':
            turnoverCol = catlist.index(category)
            break

    rows = seasonStats.findAll('tr')[3:]
    # Creates a 2-D matrix which resembles the Season Stats table.
    for row in range(len(rows)):
        team_row = []
        # The first 3 columns are always present.
        for column in rows[row].findAll('td')[:(3 + len(catlist))]:
            team_row.append(column.getText())

        # Add each team to a teams matrix.
        teams.append(team_row)
    return teams, turnoverCol


# Computes the power rankings and matchup predictions, and stores the
# values in a tuple.
def computeStats(teams, turnoverCol):
    # Initialize the dictionary which will hold information about each team
    # along with their "power rankings score".
    teamDict = {}
    for team in teams:
        teamDict[team[1]] = 0

    matchupsList = []
    for team1 in teams:
        for team2 in teams:
            score = calculateScore(team1[3:], team2[3:], turnoverCol)
            if team1 != team2:
                # The value for the dictionary is the power rankings score. A win increases the score and a loss
                # decreases the "PR" score.
                if score[0] > score[1]:
                    teamDict[team1[1]] += 1
                elif score[0] < score[1]:
                    teamDict[team1[1]] -= 1
                # map(str, score) is for formatting the score tuple into a
                # string.
                matchupsList.append(
                    team1[1] + ' vs. ' + team2[1] + ' || SCORE (W-L-T): ' + '-'.join(map(str, score)))
        matchupsList.append('*' * 100)

    # Check if two keys in the dictionary have the same value (used to process
    # ties in PR score).
    result = {}
    for val in teamDict:
        if teamDict[val] in result:
            result[teamDict[val]].append(val)
        else:
            result[teamDict[val]] = [val]

    # Sort the dictionary by greatest PR score.
    sortedDict = sorted(result.items(), key=itemgetter(0), reverse=True)

    # Contains the Power Rankings.
    rankingsList = []
    counter = 1
    # Keys are the PR score, values are the team names.
    for k, v in sortedDict:
        rankingsList.append(str(counter) + '. ' + ', '.join(v))
        counter += 1

    return matchupsList, rankingsList


# Calculates the score for individual matchups.
def calculateScore(teamA, teamB, turnoverCol):
    wins = 0
    losses = 0
    ties = 0

    for i, (a, b) in enumerate(zip(teamA, teamB)):
        # Ignore empty values.
        if a != '' and b != '':
            a = float(a)
            b = float(b)
            # When comparing turnovers, having a smaller value is a "win".
            if i == turnoverCol:
                if a < b:
                    wins += 1
                elif a == b:
                    ties += 1
                else:
                    losses += 1
            else:
                if a > b:
                    wins += 1
                elif a == b:
                    ties += 1
                else:
                    losses += 1

    return wins, losses, ties


# Run the Flask app.
if __name__ == '__main__':
    app.run()

# Comment out the if statement above and uncomment the line below to debug Python code.
# setup('http://games.espn.com/fba/standings?leagueId=224165&seasonId=2017')
