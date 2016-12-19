from bs4 import BeautifulSoup
import requests
from operator import itemgetter
from flask import Flask, render_template, request

# Holds the tuple returned by computeStats() function.
dataTuple = ()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the URL that the user entered in the form.
        url = request.form['url']
        setup(url)
        # dataTuple[1] holds information about each team along with their "power rankings score".
        data = dataTuple[1]
        return render_template('results.html', data=data)
    else:
        return render_template('index.html')

@app.route('/matchups')
def matchups():
    # dataTuple[1] holds complete matchup predictions data.
    data = dataTuple[0]
    return render_template('matchups.html', data=data)

# Scrapes the "Season Stats" table from the ESPN Fantasy Standings page.
def setup(url):
    source_code = requests.get(url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text, 'html.parser')

    seasonStats = soup.find('table', {'id': 'statsTable'})
    teams = []

    rows = seasonStats.findAll('tr')[3:]
    # Creates a 2-D matrix which resembles the Season Stats table.
    for row in range(len(rows)):
        team_row = []
        for column in rows[row].findAll('td'):
            team_row.append(column.getText())

        # Get rid of useless columns.
        del team_row[2]
        del team_row[-1]
        del team_row[-1]
        del team_row[-1]

        # Add each team to a teams matrix.
        teams.append(team_row)

    computeStats(teams)

# Computes the power rankings and matchup predictions, and stores the values in a tuple.
def computeStats(teams):
    # Initialize the dictionary which will hold information about each team along with their "power rankings score".
    teamDict = {}
    for team in teams:
        teamDict[team[1]] = 0

    matchupsList = []
    for team1 in teams:
        for team2 in teams:
            score = calculateScore(team1[2:], team2[2:])
            if team1 != team2:
                # The value for the dictionary is the power rankings score. A win increases the score and a loss
                # decreases the "PR" score.
                if score[0] > score[1]:
                    teamDict[team1[1]] += 1
                elif score[0] < score[1]:
                    teamDict[team1[1]] -= 1
                # map(str, score) is for formatting the score tuple into a string.
                matchupsList.append(team1[1] + ' vs. ' + team2[1] + ' || SCORE (W-L-T): ' + '-'.join(map(str, score)))
        matchupsList.append('*' * 100)

    # Check if two keys in the dictionary have the same value (used to process ties in PR score).
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
        counter+=1

    global dataTuple
    dataTuple = [matchupsList, rankingsList]

# Calculates the score for individual matchups.
def calculateScore(teamA, teamB):
    wins = 0
    losses = 0
    ties = 0

    for i, (a, b) in enumerate(zip(teamA, teamB)):
        a = float(a)
        b = float(b)
        # When comparing turnovers, having a smaller value is a "win".
        if i == 7:
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

# Comment the if statement above and uncomment the line below to debug Python code.
# setup('http://games.espn.com/fba/standings?leagueId=224165&seasonId=2017')
