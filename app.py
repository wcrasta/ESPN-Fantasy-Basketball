from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for
from operator import itemgetter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from urllib.parse import parse_qs, urlparse


# Create the Flask application.
app = Flask(__name__)
app.debug = True


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
        except Exception as ex:
            print('Exception in tools:' + ex)
            return redirect(url_for('index', invalidURL=True))
    else:
        try:
            leagueId = request.args.get('leagueId')
            seasonId = request.args.get('seasonId')
            return render_template('tools.html', leagueId=leagueId, seasonId=seasonId)
        except Exception as ex:
            print('Exception in tools2:' + ex)
            return redirect(url_for('index', invalidURL=True))


@app.route('/season_rankings')
def season_rankings():
    try:
        leagueId = request.args.get('leagueId')
        seasonId = request.args.get('seasonId')
        url = 'http://fantasy.espn.com/basketball/league/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
        teams, categories = setup(url)
        season_rankings, season_matchups, season_analysis = computeStats(teams, categories)
        return render_template('season_rankings.html', season_rankings=season_rankings, leagueId=leagueId,
                               seasonId=seasonId)
    except Exception as ex:
        print('Exception in season rankings:' + ex)
        return redirect(url_for('index', invalidURL=True))


@app.route('/season_matchups')
def season_matchups():
    try:
        leagueId = request.args.get('leagueId')
        seasonId = request.args.get('seasonId')
        url = 'http://fantasy.espn.com/basketball/league/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
        teams, categories = setup(url)
        season_rankings, season_matchups, season_analysis = computeStats(teams, categories)
        return render_template('season_matchups.html', season_matchups=season_matchups, leagueId=leagueId,
                               seasonId=seasonId)
    except Exception as ex:
        print('Exception in season matchups:' + ex)
        return redirect(url_for('index', invalidURL=True))


@app.route('/season_analysis')
def season_analysis():
    try:
        leagueId = request.args.get('leagueId')
        seasonId = request.args.get('seasonId')
        url = 'http://fantasy.espn.com/basketball/league/standings?leagueId={}&seasonId={}'.format(leagueId, seasonId)
        teams, categories = setup(url)
        season_rankings, season_matchups, season_analysis = computeStats(teams, categories)
        return render_template('season_analysis.html', season_matchups=season_matchups, season_analysis=season_analysis,
                               leagueId=leagueId, seasonId=seasonId)
    except Exception as ex:
        print('Exception in season analysis:' + ex)
        return redirect(url_for('index', invalidURL=True))


@app.route('/weekly_rankings')
def weekly_rankings():
    try:
        leagueId = request.args.get('leagueId')
        seasonId = request.args.get('seasonId')
        url = 'http://fantasy.espn.com/basketball/league/scoreboard?leagueId={}&seasonId={}'.format(leagueId, seasonId)
        teams, categories = setup(url)
        weekly_rankings, weekly_matchups, weekly_analysis = computeStats(teams, categories)
        return render_template('weekly_rankings.html', weekly_rankings=weekly_rankings, leagueId=leagueId,
                               seasonId=seasonId)
    except Exception as ex:
        print('Exception in weekly rankings:' + ex)
        return redirect(url_for('index', invalidURL=True))


@app.route('/weekly_matchups')
def weekly_matchups():
    try:
        leagueId = request.args.get('leagueId')
        seasonId = request.args.get('seasonId')
        url = 'http://fantasy.espn.com/basketball/league/scoreboard?leagueId={}&seasonId={}'.format(leagueId, seasonId)
        teams, categories = setup(url)
        weekly_rankings, weekly_matchups, weekly_analysis = computeStats(teams, categories)
        return render_template('weekly_matchups.html', weekly_matchups=weekly_matchups, leagueId=leagueId,
                               seasonId=seasonId)
    except Exception as ex:
        print('Exception in weekly matchups:' + ex)
        return redirect(url_for('index', invalidURL=True))


@app.route('/weekly_analysis')
def weekly_analysis():
    try:
        leagueId = request.args.get('leagueId')
        seasonId = request.args.get('seasonId')
        url = 'http://fantasy.espn.com/basketball/league/scoreboard?leagueId={}&seasonId={}'.format(leagueId, seasonId)
        teams, categories = setup(url)
        weekly_rankings, weekly_matchups, weekly_analysis = computeStats(teams, categories)
        return render_template('weekly_analysis.html', weekly_matchups=weekly_matchups, weekly_analysis=weekly_analysis,
                               leagueId=leagueId, seasonId=seasonId)
    except Exception as ex:
        print('Exception in weekly analysis:' + ex)
        return redirect(url_for('index', invalidURL=True))


# Scrapes the "Season Stats" table from the ESPN Fantasy Standings page.
def setup(url):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        capa = DesiredCapabilities.CHROME
        capa["pageLoadStrategy"] = "none"
        driver = webdriver.Chrome(chrome_options=options, desired_capabilities=capa)
        driver.get(url)

        # Season standings have a different URL than weekly scoreboard
        seasonData = url.startswith('http://fantasy.espn.com/basketball/league/standings')
        if seasonData:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'Table2__sub-header')))
        else:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'Table2__header-row')))

        plain_text = driver.page_source
        driver.close()
        soup = BeautifulSoup(plain_text, 'lxml')
        teams = []
        # Scrape table depending on whether it's season or weekly data.
        if seasonData:
            table = soup.find_all('thead', class_='Table2__sub-header Table2__thead')[1]
            tableSubHead = table.find('tr', class_='Table2__header-row Table2__tr Table2__even')
            listCats = tableSubHead.find_all('th')
            categories = []
            for cat in listCats:
                categories.append(cat.string)
            tableBody = soup.find_all('table', class_='Table2__table-scroller Table2__right-aligned Table2__table')[0]
            rows = tableBody.findAll('tr', {'class': 'Table2__tr Table2__tr--md Table2__even'})
        else:
            tableSubHead = soup.find_all('tr', class_='Table2__header-row Table2__tr Table2__even')
            tableSubHead = tableSubHead[0]
            listCats = tableSubHead.find_all('th')
            categories = []
            for cat in listCats:
                if cat.string is not None:
                    categories.append(cat.string)
            rows = soup.findAll('tr', {'class': 'Table2__tr Table2__tr--sm Table2__even'})

        # Creates a 2-D matrix which resembles the Season Stats table.
        for row in range(len(rows)):
            team_row = []
            # Season Data values always have 3 extra columns, weekly data always has 2 extra columns when scraping.
            if seasonData:
                columns = rows[row].findAll('td')[:(3 + len(categories))]
            else:
                columns = rows[row].findAll('td')[1:(2 + len(categories))]
            for column in columns:
                team_row.append(column.getText())
            # Add each team to a teams matrix.
            teams.append(team_row)
        if seasonData:
            tableBody = soup.find_all('section', class_='Table2__responsiveTable Table2__table-outer-wrap Table2--hasFixed-left Table2--hasFixed-right')[0]
            teamNamesList = tableBody.find_all('span', class_='teamName truncate')
        else:
            teamNamesList = soup.find_all('div', {'class': 'ScoreCell__TeamName ScoreCell__TeamName--shortDisplayName truncate db'})

        teamNames = []

        for teamName in teamNamesList:
            teamNames.append(teamName.string)

        namedTeams = []
        count = 0
        for team in teams:
            team.insert(0, teamNames[count])
            namedTeams.append(team)
            count += 1
    except Exception as ex:
        driver.close()
        print("Exception in setup" + ex)
    return namedTeams, categories


# Computes the standings and matchups.
def computeStats(teams, categories):
    try:
        # Initialize the dictionary which will hold information about each team along with their "standings score".
        teamDict = {}
        for team in teams:
            teamDict[team[0]] = 0

        matchupsList = []
        analysisList = []
        for team1 in teams:
            for team2 in teams:
                score, wonList, lossList, tiesList = calculateScore(team1[1:], team2[1:], categories)
                if team1 != team2:
                    # The value for the dictionary is the power rankings score. A win increases the score and a loss
                    # decreases the "PR" score.
                    if score[0] > score[1]:
                        teamDict[team1[0]] += 1
                    elif score[0] < score[1]:
                        teamDict[team1[0]] -= 1
                    # map(str, score) is for formatting the score tuple into a string.
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
    except Exception as ex:
        print("Exception in compute " + ex)

    return rankingsList, matchupsList, analysisList


# Calculates the score for individual matchups.
def calculateScore(teamA, teamB, categories):
    try:
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
                        wonList.append(categories[i] + ' (' + str(b - a) + ')')
                    elif a == b:
                        ties += 1
                        tiesList.append(categories[i] + ' (' + str(b - a) + ')')
                    else:
                        losses += 1
                        lossList.append(categories[i] + ' (' + str(b - a) + ')')
                else:
                    if a > b:
                        wins += 1
                        wonList.append(categories[i] + ' (' + str(round((a - b), 4)) + ')')
                    elif a == b:
                        ties += 1
                        tiesList.append(categories[i] + ' (' + str(round((a - b), 4)) + ')')
                    else:
                        losses += 1
                        lossList.append(categories[i] + ' (' + str(round((a - b), 4)) + ')')

        valuesTuple = ((wins, losses, ties), wonList, lossList, tiesList)
    except Exception as ex:
       print("Exception in calculateScore " + ex)
    return valuesTuple


# Run the Flask app.
if __name__ == '__main__':
    app.run()

# Comment out the if statement above and uncomment the line below to debug Python code.
# teams, categories = setup('http://fantasy.espn.com/basketball/league/standings?leagueId=224165&seasonId=2019')
# rankingsList, matchupsList, analysisList = computeStats(teams, categories)