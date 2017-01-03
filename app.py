from bs4 import BeautifulSoup
import requests
from operator import itemgetter
from flask import Flask, render_template, request, redirect, url_for
from urllib.parse import parse_qs, urlparse

# Create the Flask application.
app = Flask(__name__)
# app.debug = True

@app.route('/', methods=['GET', 'POST'])
def index():
    invalidURL = request.args.get('invalidURL') or False
    return render_template('index.html', invalidURL=invalidURL)

@app.route('/tools', methods=['GET', 'POST'])
def tools():
    if request.method == 'POST':
        url = request.form['url']
        query = parse_qs(urlparse(url).query, keep_blank_values=True)
        try:
            leagueId = str(query['leagueId'][0])
            seasonId = str(query['seasonId'][0])
            return redirect(url_for('tools', leagueId=leagueId, seasonId=seasonId))
        except:
            return redirect(url_for('index',invalidURL=True))
    else:
        leagueId = request.args.get('leagueId')
        seasonId = request.args.get('seasonId')
        url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    return render_template('tools.html', leagueId=leagueId, seasonId=seasonId)

@app.route('/season_rankings')
def season_rankings():
    leagueId = request.args.get('leagueId')
    seasonId = request.args.get('seasonId')
    url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories, seasonData = setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    season_rankings, season_matchups, season_analysis = computeStats(teams, categories, seasonData)
    return render_template('season_rankings.html', season_rankings=season_rankings, leagueId=leagueId, seasonId=seasonId)

@app.route('/season_matchups')
def season_matchups():
    leagueId = request.args.get('leagueId')
    seasonId = request.args.get('seasonId')
    url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories, seasonData = setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    season_rankings, season_matchups, season_analysis = computeStats(teams, categories, seasonData)
    return render_template('season_matchups.html', season_matchups=season_matchups, leagueId=leagueId, seasonId=seasonId)

@app.route('/season_analysis')
def season_analysis():
    leagueId = request.args.get('leagueId')
    seasonId = request.args.get('seasonId')
    url = 'http://games.espn.com/fba/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories, seasonData = setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    season_rankings, season_matchups, season_analysis = computeStats(teams, categories, seasonData)
    return render_template('season_analysis.html', season_matchups=season_matchups, season_analysis=season_analysis,
                           leagueId=leagueId, seasonId=seasonId)

@app.route('/weekly_rankings')
def weekly_rankings():
    leagueId = request.args.get('leagueId')
    seasonId = request.args.get('seasonId')
    url = 'http://games.espn.com/fba/scoreboard?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories, seasonData = setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    weekly_rankings, weekly_matchups, weekly_analysis = computeStats(teams, categories, seasonData)
    return render_template('weekly_rankings.html', weekly_rankings=weekly_rankings, leagueId=leagueId, seasonId=seasonId)

@app.route('/weekly_matchups')
def weekly_matchups():
    leagueId = request.args.get('leagueId')
    seasonId = request.args.get('seasonId')
    url = 'http://games.espn.com/fba/scoreboard?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories, seasonData = setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    weekly_rankings, weekly_matchups, weekly_analysis = computeStats(teams, categories, seasonData)
    return render_template('weekly_matchups.html', weekly_matchups=weekly_matchups, leagueId=leagueId, seasonId=seasonId)

@app.route('/weekly_analysis')
def weekly_analysis():
    leagueId = request.args.get('leagueId')
    seasonId = request.args.get('seasonId')
    url = 'http://games.espn.com/fba/scoreboard?leagueId={}&seasonId={}'.format(leagueId, seasonId)
    try:
        teams, categories, seasonData = setup(url)
    except:
        return redirect(url_for('index', invalidURL=True))
    weekly_rankings, weekly_matchups, weekly_analysis = computeStats(teams, categories, seasonData)
    return render_template('weekly_analysis.html', weekly_matchups=weekly_matchups, weekly_analysis=weekly_analysis,
                           leagueId=leagueId, seasonId=seasonId)

# Scrapes the "Season Stats" table from the ESPN Fantasy Standings page.
def setup(url):
    source_code = requests.get(url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text, 'lxml')
    teams = []
    # Season standings have a different URL than weekly scoreboard
    seasonData = url.startswith('http://games.espn.com/fba/standings')
    # Scrape table depending on whether it's season or weekly data.
    if seasonData:
        seasonStats = soup.find('table', {'id': 'statsTable'})
        categories = [link.string for link in seasonStats.findAll('tr')[2].findAll('a')]
        rows = seasonStats.findAll('tr')[3:]
    else:
        tableSubHead = soup.find_all('tr', class_='tableSubHead')
        tableSubHead = tableSubHead[0]
        listCats = tableSubHead.find_all('th')
        categories = []
        for cat in listCats:
            if 'title' in cat.attrs:
                categories.append(cat.string)
        rows = soup.findAll('tr', {'class': 'linescoreTeamRow'})

    # Creates a 2-D matrix which resembles the Season Stats table.
    for row in range(len(rows)):
        team_row = []
        # Season Data values always have 3 extra columns, weekly data always has 2 extra columns when scraping.
        if seasonData:
            columns = rows[row].findAll('td')[:(3 + len(categories))]
        else:
            columns = rows[row].findAll('td')[:(2 + len(categories))]
        for column in columns:
            team_row.append(column.getText())
        # Add each team to a teams matrix.
        teams.append(team_row)
    return teams, categories, seasonData

# Computes the standings and matchups.
def computeStats(teams, categories, seasonData):
    # Initialize the dictionary which will hold information about each team along with their "standings score".
    teamDict = {}
    for team in teams:
        if seasonData:
            teamDict[team[1]] = 0
        else:
            teamDict[team[0]] = 0

    matchupsList = []
    analysisList = []
    for team1 in teams:
        for team2 in teams:
            if seasonData:
                score, wonList, lossList, tiesList = calculateScore(team1[3:], team2[3:], categories)
            else:
                score, wonList, lossList, tiesList = calculateScore(team1[2:], team2[2:], categories)
            if team1 != team2:
                # The value for the dictionary is the power rankings score. A win increases the score and a loss
                # decreases the "PR" score.
                if score[0] > score[1]:
                    if seasonData:
                        teamDict[team1[1]] += 1
                    else:
                        teamDict[team1[0]] += 1
                elif score[0] < score[1]:
                    if seasonData:
                        teamDict[team1[1]] -= 1
                    else:
                        teamDict[team1[0]] -= 1
                # map(str, score) is for formatting the score tuple into a string.
                if seasonData:
                    matchupsList.append(
                        team1[1] + ' vs. ' + team2[1] + ' || SCORE (W-L-T): ' + '-'.join(map(str, score)))
                    analysisList.append(team1[1] + ' vs. ' + team2[1] + ' -- ' + team1[1] + ' won ' + ', '.join(wonList) + '. '
                    + team1[1] + ' lost ' + ', '.join(lossList) + '. ' + team1[1] +' tied ' + ', '.join(tiesList) + '.')
                else:
                    matchupsList.append(
                        team1[0] + ' vs. ' + team2[0] + ' || SCORE (W-L-T): ' + '-'.join(map(str, score)))
                    analysisList.append(
                        team1[0] + ' vs. ' + team2[0] + ' -- ' + team1[0] + ' won ' + ', '.join(wonList) + '. '
                        + team1[0] + ' lost ' + ', '.join(lossList) + '. ' + team1[0] + ' tied ' + ', '.join(
                            tiesList) + '.')
        matchupsList.append('*' * 100)
        analysisList.append('*' * 100)

    # Check if two keys in the dictionary have the same value (used to process
    # ties in standings score).
    result = {}
    for val in teamDict:
        if teamDict[val] in result:
            result[teamDict[val]].append(val)
        else:
            result[teamDict[val]] = [val]

    # Sort the dictionary by greatest standings score.
    sortedDict = sorted(result.items(), key=itemgetter(0), reverse=True)

    # Contains the standings.
    rankingsList = []
    counter = 1
    # Keys are the standings score, values are the team names.
    for k, v in sortedDict:
        rankingsList.append(str(counter) + '. ' + ', '.join(v))
        counter += 1

    return rankingsList, matchupsList, analysisList

# Calculates the score for individual matchups.
def calculateScore(teamA, teamB, categories):
    wins = 0
    losses = 0
    ties = 0
    wonList = []
    lossList = []
    tiesList = []

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
                    tiesList.append(categories[i] + ' (' + str(b-a) + ')')
                else:
                    losses += 1
                    lossList.append(categories[i] + ' (' + str(b-a) + ')')
            else:
                if a > b:
                    wins += 1
                    wonList.append(categories[i] + ' (' + str(round((a-b), 4)) +')')
                elif a == b:
                    ties += 1
                    tiesList.append(categories[i] + ' (' + str(round((a - b), 4)) + ')')
                else:
                    losses += 1
                    lossList.append(categories[i] + ' (' + str(round((a-b), 4)) + ')')

    valuesTuple = ((wins, losses, ties), wonList, lossList, tiesList)
    return valuesTuple

# Run the Flask app.
if __name__ == '__main__':
    app.run()

# Comment out the if statement above and uncomment the line below to debug Python code.
# teams, categories, seasonData = setup('http://games.espn.com/fba/standings?leagueId=224165&seasonId=2017')
# rankingsList, matchupsList, analysisList = computeStats(teams, categories, seasonData)