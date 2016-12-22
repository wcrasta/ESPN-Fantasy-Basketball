from bs4 import BeautifulSoup
import requests
from operator import itemgetter
from flask import Flask, render_template, request, redirect, url_for
from urllib.parse import parse_qs, urlparse

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    invalidURL = request.args.get('invalidURL') or False
    return render_template('index.html', invalidURL=invalidURL)


@app.route('/matchups')
def matchups():
    leagueId = request.args.get('leagueId')
    seasonId = request.args.get('seasonId')
    url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories = setup(url)
    except:
        redirect(url_for('index', invalidURL=True))
    matchups, rankings, analysis = computeStats(teams, categories)
    return render_template('matchups.html', matchups=matchups, leagueId=leagueId, seasonId=seasonId)


@app.route('/analysis')
def analysis():
    leagueId = request.args.get('leagueId')
    seasonId = request.args.get('seasonId')
    url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories = setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    matchups, rankings, analysis = computeStats(teams, categories)
    return render_template('analysis.html', analysis=analysis, matchups=matchups)


@app.route('/rankings', methods=['GET', 'POST'])
def rankings():
    if request.method == 'POST':
        url = request.form['url']
        query = parse_qs(urlparse(url).query, keep_blank_values=True)
        try:
            leagueId = str(query['leagueId'][0])
            seasonId = str(query['seasonId'][0])
            return redirect(url_for('rankings', leagueId=leagueId, seasonId=seasonId))
        except:
            redirect(url_for('index',invalidURL=True))
    else:
        leagueId = request.args.get('leagueId')
        seasonId = request.args.get('seasonId')
        url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories = setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    matchups, rankings, analysis = computeStats(teams, categories)
    return render_template('results.html', rankings=rankings, leagueId=leagueId, seasonId=seasonId)

# Scrapes the "Season Stats" table from the ESPN Fantasy Standings page.
def setup(url):
    source_code = requests.get(url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text, 'html.parser')

    seasonStats = soup.find('table', {'id': 'statsTable'})
    teams = []
    categories = [link.string for link in seasonStats.findAll('tr')[2].findAll('a')]
  
    rows = seasonStats.findAll('tr')[3:]
    # Creates a 2-D matrix which resembles the Season Stats table.
    for row in range(len(rows)):
        team_row = []
        # The first 3 columns are always present.
        for column in rows[row].findAll('td')[:(3+len(categories))]:
            team_row.append(column.getText())

        # Add each team to a teams matrix.
        teams.append(team_row)
    return teams, categories


# Computes the power rankings and matchup predictions, and stores the
# values in a tuple.
def computeStats(teams, categories):
    # Initialize the dictionary which will hold information about each team
    # along with their "power rankings score".
    teamDict = {}
    for team in teams:
        teamDict[team[1]] = 0

    matchupsList = []
    analysisList = []
    for team1 in teams:
        for team2 in teams:
            score, wonList, lossList = calculateScore(team1[3:], team2[3:], categories)
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
                analysisList.append(team1[1] + ' vs. ' + team2[1] + ' -- ' + team1[1] + ' won ' + ', '.join(wonList) + '. '
                + team1[1] + ' lost ' + ', '.join(lossList) + '.')
        matchupsList.append('*' * 100)
        analysisList.append('*' * 100)

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

    return matchupsList, rankingsList, analysisList


# Calculates the score for individual matchups.
def calculateScore(teamA, teamB, categories):
    wins = 0
    losses = 0
    ties = 0
    wonList = []
    lossList = []

    turnoverCol = -1
    for category in categories:
        if category == 'TO':
            turnoverCol = categories.index(category)
            break

    for i, (a, b) in enumerate(zip(teamA, teamB)):
        # Ignore empty values.
        if a != '' and b != '':
            a = float(a)
            b = float(b)
            # When comparing turnovers, having a smaller value is a "win".
            if i == turnoverCol:
                if a < b:
                    wins += 1
                    wonList.append(categories[i] + ' (' + str(b-a) + ')')
                elif a == b:
                    ties += 1
                else:
                    losses += 1
                    lossList.append(categories[i] + ' (' + str(b-a) + ')')
            else:
                if a > b:
                    wins += 1
                    wonList.append(categories[i] + ' (' + str(round((a-b), 4)) +')')
                elif a == b:
                    ties += 1
                else:
                    losses += 1
                    lossList.append(categories[i] + ' (' + str(round((a-b), 4)) + ')')

    valuesTuple = ((wins, losses, ties), wonList, lossList)
    return valuesTuple

# Run the Flask app.
if __name__ == '__main__':
   app.run()

# Comment out the if statement above and uncomment the line below to debug Python code.
# teams, categories = setup('http://games.espn.com/fba/standings?leagueId=224165&seasonId=2017')
# matchups, rankings, list2 = computeStats(teams, categories)