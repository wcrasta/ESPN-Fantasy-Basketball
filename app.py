import logging
import sys
import urllib.parse as urlparse
from operator import itemgetter
import time

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, abort
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import config

import pprint


# Create the Flask application.
app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.config.from_object(config.ProductionConfig)


@app.errorhandler(500)
def abort_error():
    return render_template('error.html'), 500


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/tools', methods=['GET', 'POST'])
def tools():
    if request.method == 'POST':
        url = request.form['url']
        app.logger.info('URL: %s', url)
        try:
            parsed_url = urlparse.urlparse(url)
            league_id = int((urlparse.parse_qs(parsed_url.query, strict_parsing=True)['leagueId'])[0])
        except ValueError as ex:
            app.logger.error('Could not get league id.', ex)
            return render_template('index.html', league_id=None)
        data = call_espn_api(league_id)
        if 'status' not in data:
            app.logger.error('League %s is a private league.', str(league_id))
            return render_template('index.html', league_id=league_id, private_league=True)
        return redirect(url_for('tools', leagueId=league_id))
    else:
        league_id = request.args.get('leagueId')
        data = call_espn_api(league_id)
        if 'status' not in data:
            app.logger.error('League %s is a private league.', str(league_id))
            return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('tools.html', league_id=league_id)


@app.route('/weekly_rankings', methods=['GET', 'POST'])
def weekly_rankings():
    weekly_values = endpoints_setup(False)
    league_id = weekly_values[0]
    if weekly_values[1] == 'private':
        return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('weekly_rankings.html', league_id=league_id, current_week=weekly_values[1],
                           weeks=weekly_values[2], rankings=weekly_values[3][0])


@app.route('/weekly_matchups', methods=['GET', 'POST'])
def weekly_matchups():
    weekly_values = endpoints_setup(False)
    league_id = weekly_values[0]
    if weekly_values[1] == 'private':
        return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('weekly_matchups.html', league_id=league_id, current_week=weekly_values[1],
                           weeks=weekly_values[2], matchups=weekly_values[3][1])


@app.route('/weekly_analysis', methods=['GET', 'POST'])
def weekly_analysis():
    weekly_values = endpoints_setup(False)
    league_id = weekly_values[0]
    if weekly_values[1] == 'private':
        return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('weekly_analysis.html', league_id=league_id, current_week=weekly_values[1],
                           weeks=weekly_values[2], analysis=weekly_values[3][1])


@app.route('/season_rankings')
def season_rankings():
    season_values = endpoints_setup(True)
    league_id = season_values[0]
    if season_values[1] == 'private':
        return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('season_rankings.html', league_id=league_id, rankings=season_values[3][0])


@app.route('/season_matchups', methods=['GET', 'POST'])
def season_matchups():
    season_values = endpoints_setup(True)
    league_id = season_values[0]
    if season_values[1] == 'private':
        return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('season_matchups.html', league_id=league_id, current_week=season_values[1],
                           weeks=season_values[2], matchups=season_values[3][1])


@app.route('/season_analysis', methods=['GET', 'POST'])
def season_analysis():
    season_values = endpoints_setup(True)
    league_id = season_values[0]
    if season_values[1] == 'private':
        return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('season_analysis.html', league_id=league_id, current_week=season_values[1],
                           weeks=season_values[2], analysis=season_values[3][1])


@app.route('/season_sos', methods=['GET', 'POST'])
def season_sos():
    season_values = get_season_sos()
    league_id = season_values[0]
    if season_values[1] == 'private':
        return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('season_sos.html', league_id=league_id, current_week=season_values[1],
                           rankings=season_values[2])


@app.route('/overall_perf', methods=['GET', 'POST'])
def overall_perf():
    season_values = get_overall_perf()
    league_id = season_values[0]
    if season_values[1] == 'private':
        return render_template('index.html', league_id=league_id, private_league=True)
    return render_template('overall_perf.html', league_id=league_id, current_week=season_values[1],
                           rankings=season_values[2])


def endpoints_setup(is_season_data):
    league_id = request.args.get('leagueId')
    app.logger.info('League ID: %s', str(league_id))
    week = get_current_week(league_id)
    if is_season_data:
        url = 'https://fantasy.espn.com/basketball/league/standings?leagueId={}'.format(league_id)
    else:
        url = 'https://fantasy.espn.com/basketball/league/scoreboard?leagueId={}&matchupPeriodId={}' \
            .format(league_id, week)

    teams, categories, weeks = setup(url, league_id, week)
    stats = compute_stats(teams, categories, league_id)
    if not teams or not categories or not stats:
        app.logger.error('%s - Teams, categories, or stats list empty.', str(league_id))
        abort(500)
        sys.exit('Teams, categories, or stats list empty.')
    endpoints_params = league_id, week, weeks, stats
    return endpoints_params


def get_current_week(league_id):
    # First get it from the dropdown
    week = request.form.get('week_selection')
    if week is None:
        data = call_espn_api(league_id)
        if 'status' not in data:
            app.logger.error('League %s is a private league.', str(league_id))
            week = 'private'
        else:
            week = data['status']['currentMatchupPeriod']
    app.logger.info('%s - Week requested: %s', league_id, week)
    return week


def call_espn_api(league_id):
    app.logger.info('%s - Calling ESPN API', league_id)
    url = ("https://fantasy.espn.com/apis/v3/games/fba/seasons/{}/segments/0/leagues/{}?view=mMatchupScore&view"
           "mScoreboard&view=mSettings&view=mTeam&view=modular&view=mNav").format(app.config.get("SEASON"), league_id)
    try:
        r = requests.get(url)
    except requests.exceptions.RequestException as ex:
        app.logger.error('%s - Could not make ESPN API call', league_id, ex)
        abort(500)
        sys.exit('Could not make ESPN API call.')
    data = r.json()
    return data


def setup(url, league_id, week):
    is_season_data = 'standings' in url
    soup = run_selenium(url, is_season_data, league_id)
    if soup is None:
        abort(500)
        sys.exit('BeautifulSoup object is None.')

    app.logger.info('%s - Scraping list of weeks', league_id)
    weeks = None
    if not is_season_data:
        weeks = soup.find("select", class_='dropdown__select').find_all("option")
        weeks = [w.text for w in weeks]

    # try:
    #     table_rows, categories = get_table_rows_and_cats(soup, is_season_data, league_id)
    #     app.logger.info('%s - Successfully scraped table_rows and categories', league_id)
    # except Exception as ex:
    #     app.logger.error('%s - Could not get rows and categories', league_id, ex)
    #     abort(500)
    #     sys.exit('Could not get rows and categories')
    #
    # try:
    #     teams = create_teams_matrix(is_season_data, categories, table_rows, league_id)
    #     app.logger.info('%s - Successfully created teams matrix', league_id)
    # except Exception as ex:
    #     app.logger.error('%s - Could not create teams matrix', league_id, ex)
    #     abort(500)
    #     sys.exit('Could not create teams matrix')
    # try:
    #     append_team_names(soup, is_season_data, teams, league_id)
    #     app.logger.info('%s - Successfully appended team names', league_id)
    # except Exception as ex:
    #     app.logger.error('%s - Could not append team names', league_id, ex)
    #     abort(500)
    #     sys.exit('Could not append team names'))

    categories = ['FG%', 'FT%', '3PM', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PTS']
    teams = get_scoreboard(league_id, week)

    return teams, categories, weeks


def run_selenium(url, is_season_data, league_id):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')
    options.add_argument('disable-dev-shm-usage')
    capa = DesiredCapabilities.CHROME
    capa["pageLoadStrategy"] = "none"
    chromedriver_loc = 'chromedriver.exe'
    driver = webdriver.Chrome(chrome_options=options, desired_capabilities=capa, executable_path=chromedriver_loc)
    try:
        app.logger.info('%s - Starting selenium', league_id)
        driver.get(url)
        app.logger.info('%s - Waiting for element to load', league_id)
        # Season standings have a different URL than weekly scoreboard

        if is_season_data:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'Table__header-group')))
        else:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'Table__sub-header')))
        app.logger.info('%s - Element loaded. Sleeping started to get latest data.', league_id)
        time.sleep(5)
        plain_text = driver.page_source
        soup = BeautifulSoup(plain_text, 'html.parser')
        app.logger.info('%s - Got BeautifulSoup object', league_id)
    except Exception as ex:
        app.logger.error('%s - Could not get page source.', league_id, ex)
        soup = None
    finally:
        driver.quit()
    return soup


def get_table_rows_and_cats(soup, is_season_data, league_id):
    app.logger.info('%s - Starting scraping table_rows and categories', league_id)
    # Scrape objects depending on whether the user asked for season or weekly data.
    if is_season_data:
        categories_list = soup.find_all('thead', class_='Table__header-group Table__THEAD')[1]
        table_body = soup.find_all('table', class_='Table Table--align-right')[0]
        rows_class = 'Table__TR Table__TR--md Table__even'
    else:
        categories_list = soup
        table_body = soup
        rows_class = 'Table__TR Table__TR--sm Table__even'
    categories = categories_list.find('tr', class_='Table__sub-header Table__TR Table__even').find_all('th')
    categories = [c.string for c in categories if c.string is not None]
    table_rows = table_body.findAll('tr', {'class': rows_class})
    return table_rows, categories


def create_teams_matrix(is_season_data, categories, table_rows, league_id):
    app.logger.info('%s - Creating teams matrix', league_id)
    # Creates a 2-D matrix which resembles the Weekly Scoreboard or Season Stats table.
    teams = []
    for row in range(len(table_rows)):
        # Get rid of extra <td>
        if is_season_data:
            columns = table_rows[row].findAll('td')
        else:
            columns = table_rows[row].findAll('td')[1:len(categories) + 1]
        team_row = [c.getText() for c in columns]
        teams.append(team_row)
    return teams


def append_team_names(soup, is_season_data, teams, league_id):
    app.logger.info('%s - Appending team names', league_id)
    if is_season_data:
        table_body_class = 'Table Table--align-right Table--fixed Table--fixed-left'
        table_body = soup.find_all('table', class_=table_body_class)[0]
        team_names = table_body.find_all('span', class_='teamName truncate')
    else:
        team_names = soup.find_all('div',
                                   {'class': 'ScoreCell__TeamName ScoreCell__TeamName--shortDisplayName truncate db'})

    team_names = [t.string for t in team_names]
    # Add team names for each team
    for idx, team in enumerate(teams):
        team.insert(0, team_names[idx])


# Computes the standings and matchups.
def compute_stats(teams, categories, league_id):
    app.logger.info('%s - Starting to compute stats', league_id)
    # Initialize the dictionary which will hold information about each team along with their "standings score".
    team_dict = {}
    for team in teams:
        team_dict[team[0]] = 0
    matchups = []
    for team1 in teams:
        team_matchup = []
        for team2 in teams:
            if team1 != team2:
                try:
                    score, won_margin, lost_margin, tied_margin = calculate_score(team1[1:], team2[1:], categories, league_id)
                except Exception as ex:
                    app.logger.error('%s - Could not calculate score.', league_id, ex)
                    abort(500)
                    sys.exit('Could not calculate score.')
                # The value for the dictionary is the power rankings score. A win increases the score and a loss
                # decreases the "PR" score.
                if score[0] > score[1]:
                    team_dict[team1[0]] += 1
                elif score[0] < score[1]:
                    team_dict[team1[0]] -= 1
                team_matchup.append(list([team1[0], team2[0], score, won_margin, lost_margin, tied_margin]))
        matchups.append(team_matchup)
    app.logger.info('%s - Successfully created matchups/analysis list', league_id)
    # Check if two keys in the dictionary have the same value (used to process ties in standings score).
    result = {}
    for val in team_dict:
        if team_dict[val] in result:
            result[team_dict[val]].append(val)
        else:
            result[team_dict[val]] = [val]

    # Sort the dictionary by greatest standings score.
    rankings = sorted(result.items(), key=itemgetter(0), reverse=True)
    app.logger.info('%s - Successfully calculated rankings', league_id)
    return rankings, matchups


# Calculates the score for individual matchups.
def calculate_score(team1, team2, categories, league_id):
    wins = 0
    losses = 0
    ties = 0
    won_margin = []
    lost_margin = []
    tied_margin = []

    bad_categories = ['FGMI', 'FTMI', '3PMI', 'TO', 'EJ', 'FF', 'PF', 'TF', 'DQ']

    bad_categories_idx = []
    for bad_category in bad_categories:
        try:
            bad_categories_idx.append(categories.index(bad_category))
        except ValueError:
            pass

    for idx, (a, b) in enumerate(zip(team1, team2)):
        try:
            a, b = float(a), float(b)
        except ValueError as e:
            app.logger.error('%s - %s', league_id, str(e))
            a, b = 0.0, 0.0

        # When comparing turnovers, having a smaller value is a "win".
        if idx in bad_categories_idx:
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


# generates season strength of schedule for each player
def get_season_sos():
    league_id = request.args.get('leagueId')
    app.logger.info('League ID: %s', str(league_id))
    current_week = get_current_week(league_id)
    cumulative_opp_wins = {}
    cumulative_opp_losses = {}
    cumulative_opp_draws = {}
    # add 1 to current_week
    current_week -= 1
    for week in range(1, current_week + 1):
        app.logger.info('Fetching SOS stats for week %s', str(week))
        url = 'http://fantasy.espn.com/basketball/league/scoreboard?leagueId={}&matchupPeriodId={}' \
            .format(league_id, week)
        teams, categories, weeks = setup(url, league_id, week)
        matchups = get_week_matchups(teams)
        team_stats = compute_stats(teams, categories, league_id)[1]
        if not teams or not categories or not team_stats:
            app.logger.error('%s - Teams, categories, or stats list empty.', str(league_id))
            abort(500)
            sys.exit('Teams, categories, or stats list empty.')
        team_scores = get_team_scores(team_stats)
        player_opp_scores = get_player_opp_scores(matchups, team_scores)
        for player in matchups.keys():
            if player in cumulative_opp_wins:
                cumulative_opp_wins[player] += player_opp_scores[0][player]
            else:
                cumulative_opp_wins[player] = player_opp_scores[0][player]
            if player in cumulative_opp_losses:
                cumulative_opp_losses[player] += player_opp_scores[1][player]
            else:
                cumulative_opp_losses[player] = player_opp_scores[1][player]
            if player in cumulative_opp_draws:
                cumulative_opp_draws[player] += player_opp_scores[2][player]
            else:
                cumulative_opp_draws[player] = player_opp_scores[2][player]
    avg_opp_wins = {player: (round(wins / current_week, 2)) for (player, wins) in cumulative_opp_wins.items()}
    avg_opp_losses = {player: (round(losses / current_week, 2)) for (player, losses) in cumulative_opp_losses.items()}
    avg_opp_draws = {player: (round(draws / current_week, 2)) for (player, draws) in cumulative_opp_draws.items()}
    sorted_avg_opp_wins = sorted(avg_opp_wins.items(), key=lambda kv:[kv[1], kv[0]], reverse=True)
    sos_rankings = build_rankings(sorted_avg_opp_wins, avg_opp_losses, avg_opp_draws)
    return [league_id, current_week, sos_rankings]


# calculates personal performance for each player
def get_overall_perf():
    league_id = request.args.get('leagueId')
    app.logger.info('League ID: %s', str(league_id))
    current_week = get_current_week(league_id)
    cumulative_wins = {}
    cumulative_losses = {}
    cumulative_draws = {}
    # add 1 to current_week
    current_week -= 1
    for week in range(1, current_week + 1):
        app.logger.info('Fetching season performance stats for week %s', str(week))
        url = 'http://fantasy.espn.com/basketball/league/scoreboard?leagueId={}&matchupPeriodId={}' \
            .format(league_id, week)
        teams, categories, weeks = setup(url, league_id, week)
        matchups = get_week_matchups(teams)
        team_stats = compute_stats(teams, categories, league_id)[1]
        if not teams or not categories or not team_stats:
            app.logger.error('%s - Teams, categories, or stats list empty.', str(league_id))
            abort(500)
            sys.exit('Teams, categories, or stats list empty.')
        team_scores = get_team_scores(team_stats)
        for player in matchups.keys():
            if player in cumulative_wins:
                cumulative_wins[player] += team_scores[0][player]
            else:
                cumulative_wins[player] = team_scores[0][player]
            if player in cumulative_losses:
                cumulative_losses[player] += team_scores[1][player]
            else:
                cumulative_losses[player] = team_scores[1][player]
            if player in cumulative_draws:
                cumulative_draws[player] += team_scores[2][player]
            else:
                cumulative_draws[player] = team_scores[2][player]
    avg_wins = {player: (round(wins / current_week, 2)) for (player, wins) in cumulative_wins.items()}
    avg_losses = {player: (round(losses / current_week, 2)) for (player, losses) in cumulative_losses.items()}
    avg_draws = {player: (round(draws / current_week, 2)) for (player, draws) in cumulative_draws.items()}
    sorted_avg_wins = sorted(avg_wins.items(), key=lambda kv:[kv[1], kv[0]], reverse=True)
    perf_rankings = build_rankings(sorted_avg_wins, avg_losses, avg_draws)
    return [league_id, current_week, perf_rankings]


def build_rankings(sorted_wins, losses, draws):
    sos_rankings = []
    rank = 1
    for team in sorted_wins:
        team_name = team[0]
        avg_opp_losses = losses[team_name]
        avg_opp_draws = draws[team_name]
        sos_rankings.append([rank, team_name, team[1], avg_opp_losses, avg_opp_draws])
        rank += 1
    return sos_rankings


# find every player's opponent's win/loss/draw for a week
def get_player_opp_scores(matchups, team_scores):
    player_opp_wins = {}
    player_opp_losses = {}
    player_opp_draws = {}
    for player in matchups.keys():
        player_opp_wins[player] = team_scores[0][matchups[player]]
        player_opp_losses[player] = team_scores[1][matchups[player]]
        player_opp_draws[player] = team_scores[2][matchups[player]]
    return [player_opp_wins, player_opp_losses, player_opp_draws]


# create dictionary of team with win/loss/draw value for a week
def get_team_scores(team_stats):
    team_scores_wins = {}
    team_scores_losses = {}
    team_scores_draws = {}
    for team in team_stats:
        team_name = team[0][0]
        wins = 0
        losses = 0
        draws = 0
        for matchup in team:
            score = matchup[2]
            if score[0] > score[1]:
                wins += 1
            elif score[0] < score[1]:
                losses += 1
            elif score[0] == score[1]:
                draws += 1
        team_scores_wins[team_name] = wins
        team_scores_losses[team_name] = losses
        team_scores_draws[team_name] = draws
    return [team_scores_wins, team_scores_losses, team_scores_draws]


def get_week_matchups(teams):
    matchup_dict = {}
    for i in range(round(len(teams) / 2)):
        team1 = teams[2*i][0]
        team2 = teams[2*i+1][0]
        matchup_dict[team1] = team2
        matchup_dict[team2] = team1
    return matchup_dict


# create two way dictionary of team id and team name
def get_team_dict(league_id):
    url = f'https://fantasy.espn.com/apis/v3/games/fba/seasons/{app.config.get("SEASON")}/segments/0/leagues/{league_id}'
    data = call_api(url)
    team_dict = {}
    for team in data['teams']:
        team_dict[team['location'] + ' ' + team['nickname']] = team['id']
        team_dict[team['id']] = team['location'] + ' ' + team['nickname']
    return team_dict


# call espn api allowing for params
def call_api(url, params=None):
    try:
        if params is None:
            r = requests.get(url)
        else:
            r = requests.get(url, params=params)
    except requests.exceptions.RequestException as ex:
        print('Could not make ESPN API call')
    data = r.json()
    return data


# check if val exists, otherwise return 0
def key_check(stats, key):
    try:
        return stats[key]['score']
    except KeyError:
        pass
    return 0


def format_team(team_raw, team_dict):
    team = []
    team.append(team_dict[team_raw['teamId']])
    scores = team_raw['cumulativeScore']['scoreByStat']
    # FG%
    team.append(key_check(scores, '19'))
    # FT%
    team.append(key_check(scores, '20'))
    # 3PM
    team.append(key_check(scores, '17'))
    # REB
    team.append(key_check(scores, '6'))
    # AST
    team.append(key_check(scores, '3'))
    # STL
    team.append(key_check(scores, '2'))
    # BLK
    team.append(key_check(scores, '1'))
    # TO
    team.append(key_check(scores, '11'))
    # PTS
    team.append(key_check(scores, '0'))
    return team


def get_scoreboard(league_id, week):
    params = (('view', ['mScoreboard', 'mMatchupScore']),)
    data = call_api(f'http://fantasy.espn.com/apis/v3/games/fba/seasons/{app.config.get("SEASON")}/segments/0/leagues/{league_id}',
                    params=params)
    team_dict = get_team_dict(league_id)
    data = data['schedule']

    matchups = [matchup for matchup in data if matchup['matchupPeriodId'] == week or matchup['matchupPeriodId'] == int(week)]
    scoreboard = []
    for matchup in matchups:
        team1 = format_team(matchup['away'], team_dict)
        team2 = format_team(matchup['home'], team_dict)
        scoreboard.append(team1)
        scoreboard.append(team2)

    return scoreboard


# Run the Flask app.
if __name__ == '__main__':
    app.run()
