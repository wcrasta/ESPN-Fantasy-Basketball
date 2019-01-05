import logging
import os
import sys
import urllib.parse as urlparse
from operator import itemgetter

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, session
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# Create the Flask application.
app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

# TODO: Logging and error handling. Don't catch exception.
# TODO: Break app into smaller portions.
# TODO: -- values
# TODO - Remov string hardcode
# TODO - PEP and formatting
# TODO: Pip freeze
# TODO: Private league

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/tools', methods=['GET', 'POST'])
def tools():
    if request.method == 'POST':
        url = request.form['url']
        logging.info('URL: ', url)
        parsed_url = urlparse.urlparse(url)
        try:
            league_id = (urlparse.parse_qs(parsed_url.query, strict_parsing=True)['leagueId'])[0]
        except Exception as ex:
            logging.error('Could not get league id.', ex)
            return render_template('index.html', league_id=None)
        return redirect(url_for('tools', leagueId=league_id))
    else:
        league_id = request.args.get('leagueId')
    return render_template('tools.html', league_id=league_id)

@app.route('/weekly_rankings', methods=['GET', 'POST'])
def weekly_rankings():
    weekly_values = endpoints_setup(False)
    return render_template('weekly_rankings.html', league_id=weekly_values[0], current_week=weekly_values[1],
                           weeks=weekly_values[2], rankings=weekly_values[3][0])

@app.route('/weekly_matchups', methods=['GET', 'POST'])
def weekly_matchups():
    weekly_values = endpoints_setup(False)
    return render_template('weekly_matchups.html', league_id=weekly_values[0], current_week=weekly_values[1],
                           weeks=weekly_values[2], matchups=weekly_values[3][1])

@app.route('/weekly_analysis', methods=['GET', 'POST'])
def weekly_analysis():
    weekly_values = endpoints_setup(False)
    return render_template('weekly_analysis.html', league_id=weekly_values[0], current_week=weekly_values[1],
                           weeks=weekly_values[2], analysis=weekly_values[3][1])

@app.route('/season_rankings')
def season_rankings():
    season_values = endpoints_setup(True)
    return render_template('season_rankings.html', league_id=season_values[0], rankings=season_values[3][0])

@app.route('/season_matchups', methods=['GET', 'POST'])
def season_matchups():
    season_values = endpoints_setup(True)
    return render_template('season_matchups.html', league_id=season_values[0], current_week=season_values[1],
                           weeks=season_values[2], matchups=season_values[3][1])

@app.route('/season_analysis', methods=['GET', 'POST'])
def season_analysis():
    season_values = endpoints_setup(True)
    return render_template('season_analysis.html', league_id=season_values[0], current_week=season_values[1],
                           weeks=season_values[2], analysis=season_values[3][1])

def endpoints_setup(is_season_data):
    league_id = request.args.get('leagueId')
    week = get_current_week(league_id)
    if is_season_data:
        url = 'http://fantasy.espn.com/basketball/league/standings?leagueId={}'.format(league_id)
    else:
        url = 'http://fantasy.espn.com/basketball/league/scoreboard?leagueId={}&matchupPeriodId={}'.format(league_id, week)
    teams, categories, weeks = setup(url)
    stats = compute_stats(teams, categories)
    endpoints_params = league_id, week, weeks, stats
    return endpoints_params

def get_current_week(leagueId):
    # First get it from the dropdown
    week = request.form.get('week_selection')
    # If it doesn't exist, get it from the session
    if week is None:
        week = session.get('current_week', None)
        # If that doesn't exist, get it from an API call
        if week is None:
            url = ("http://fantasy.espn.com/apis/v3/games/fba/seasons/{}/segments/0/leagues/{}?view=mMatchupScore&view"
                   "mScoreboard&view=mSettings&view=mTeam&view=modular&view=mNav").format(app.config.get("SEASON"), leagueId)
            r = requests.get(url)
            data = r.json()
            week = data['status']['currentMatchupPeriod']
    # Save the week to the session once we have it
    session['current_week'] = week
    return week

def runSelenium(url, is_season_data):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    capa = DesiredCapabilities.CHROME
    capa["pageLoadStrategy"] = "none"
    driver = webdriver.Chrome(chrome_options=options, desired_capabilities=capa)
    try:
        driver.get(url)
        # Season standings have a different URL than weekly scoreboard
        if is_season_data:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'Table2__sub-header')))
        else:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'Table2__header-row')))
        plain_text = driver.page_source
        driver.quit()
        soup = BeautifulSoup(plain_text, 'lxml')
    except Exception as ex:
        logging.error('Could not get page source.', ex)
        soup = None
        try:
            driver.quit()
        except WebDriverException:
            pass
    return soup

def setup(url):
    is_season_data = 'standings' in url
    # soup = runSelenium(url, is_season_data)
    if is_season_data:
        with open('C:\\Users\\Warren\\Documents\\Software Engineering\\Python\\ESPN-Fantasy-Basketball\\season.txt', encoding="utf8") as myfile:
            plain_text = myfile.read().replace('\n', '')
    else:
        with open('C:\\Users\\Warren\\Documents\\Software Engineering\\Python\\ESPN-Fantasy-Basketball\\weekly.txt', encoding="utf8") as myfile:
            plain_text = myfile.read().replace('\n', '')
    soup = BeautifulSoup(plain_text, 'lxml')
    if soup is None:
        sys.exit('BeautifulSoup object is None.')

    weeks = None
    # Scrape objects depending on whether the user asked for season or weekly data.
    if is_season_data:
        categories = soup.find_all('thead', class_='Table2__sub-header Table2__thead')[1]
        categories = categories.find('tr', class_='Table2__header-row Table2__tr Table2__even').find_all('th')
        categories = [c.string for c in categories if c.string is not None]
        table_body = soup.find_all('table', class_='Table2__table-scroller Table2__right-aligned Table2__table')[0]
        table_rows = table_body.findAll('tr', {'class': 'Table2__tr Table2__tr--md Table2__even'})
    else:
        weeks = soup.find("select", class_='dropdown__select').find_all("option")
        weeks = [w.text for w in weeks]
        categories = soup.find_all('tr', class_='Table2__header-row Table2__tr Table2__even')[0].find_all('th')
        categories = [c.string for c in categories if c.string is not None]
        table_rows = soup.findAll('tr', {'class': 'Table2__tr Table2__tr--sm Table2__even'})

    teams = create_teams_matrix(is_season_data, categories, table_rows)
    if is_season_data:
        table_body = soup.find_all('section', class_='Table2__responsiveTable Table2__table-outer-wrap Table2--hasFixed-left Table2--hasFixed-right')[0]
        team_names = table_body.find_all('span', class_='teamName truncate')
    else:
        team_names = soup.find_all('div',
                                  {'class': 'ScoreCell__TeamName ScoreCell__TeamName--shortDisplayName truncate db'})

    team_names = [t.string for t in team_names]
    # Add team names for each team
    for idx, team in enumerate(teams):
        team.insert(0, team_names[idx])

    return teams, categories, weeks

def create_teams_matrix(is_season_data, categories, table_rows):
    # Creates a 2-D matrix which resembles the Weekly Scoreboard or Season Stats table.
    teams = []
    for row in range(len(table_rows)):
        # Season Data values always have 3 extra columns, weekly data always has 2 extra columns when scraping.
        if is_season_data:
            columns = table_rows[row].findAll('td')
        else:
            columns = table_rows[row].findAll('td')[1:len(categories)+1]

        team_row = [c.getText() for c in columns]
        # Add each team to a teams matrix.
        teams.append(team_row)
    return teams

# Computes the standings and matchups.
def compute_stats(teams, categories):
    # Initialize the dictionary which will hold information about each team along with their "standings score".
    team_dict = {}
    for team in teams:
        team_dict[team[0]] = 0
    matchups = []
    for team1 in teams:
        team_matchup = []
        for team2 in teams:
            if team1 != team2:
                score, won_margin, lost_margin, tied_margin = calculate_score(team1[1:], team2[1:], categories)
                # The value for the dictionary is the power rankings score. A win increases the score and a loss
                # decreases the "PR" score.
                if score[0] > score[1]:
                    team_dict[team1[0]] += 1
                elif score[0] < score[1]:
                    team_dict[team1[0]] -= 1
                team_matchup.append(list([team1[0], team2[0], score, won_margin, lost_margin, tied_margin]))
        matchups.append(team_matchup)

    # Check if two keys in the dictionary have the same value (used to process ties in standings score).
    result = {}
    for val in team_dict:
        if team_dict[val] in result:
            result[team_dict[val]].append(val)
        else:
            result[team_dict[val]] = [val]

    # Sort the dictionary by greatest standings score.
    rankings = sorted(result.items(), key=itemgetter(0), reverse=True)
    return rankings, matchups


# Calculates the score for individual matchups.
def calculate_score(team1, team2, categories):
    wins = 0
    losses = 0
    ties = 0
    won_margin = []
    lost_margin = []
    tied_margin = []

    try:
        to_idx = categories.index('TO')
    except ValueError:
        to_idx = -1

    for idx, (a, b) in enumerate(zip(team1, team2)):
        a = float(a)
        b = float(b)
        # When comparing turnovers, having a smaller value is a "win".
        if idx == to_idx:
            if a < b:
                wins += 1
                won_margin.append((categories[idx], b - a))
            elif a == b:
                ties += 1
                tied_margin.append((categories[idx], b - a))
            else:
                losses += 1
                lost_margin.append((categories[idx], b - a))
        else:
            if a > b:
                wins += 1
                won_margin.append((categories[idx], round((a - b), 4)))
            elif a == b:
                ties += 1
                tied_margin.append((categories[idx], round((a - b), 4)))
            else:
                losses += 1
                lost_margin.append((categories[idx], round((a - b), 4)))
    score = (wins, losses, ties), won_margin, lost_margin, tied_margin
    return score

# Run the Flask app.
if __name__ == '__main__':
    app.run()