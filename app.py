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

    teams, categories, weeks = setup(url, league_id)
    stats = compute_stats(teams, categories, league_id, False)
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


def setup(url, league_id):
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

    try:
        table_rows, categories = get_table_rows_and_cats(soup, is_season_data, league_id)
        app.logger.info('%s - Successfully scraped table_rows and categories', league_id)
    except Exception as ex:
        app.logger.error('%s - Could not get rows and categories', league_id, ex)
        abort(500)
        sys.exit('Could not get rows and categories')

    try:
        teams = create_teams_matrix(is_season_data, categories, table_rows, league_id)
        app.logger.info('%s - Successfully created teams matrix', league_id)
    except Exception as ex:
        app.logger.error('%s - Could not create teams matrix', league_id, ex)
        abort(500)
        sys.exit('Could not create teams matrix')
    try:
        append_team_names(soup, is_season_data, teams, league_id)
        app.logger.info('%s - Successfully appended team names', league_id)
    except Exception as ex:
        app.logger.error('%s - Could not append team names', league_id, ex)
        abort(500)
        sys.exit('Could not append team names')

    return teams, categories, weeks


def run_selenium(url, is_season_data, league_id):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')
    options.add_argument('disable-dev-shm-usage')
    capa = DesiredCapabilities.CHROME
    capa["pageLoadStrategy"] = "none"
    # chromedriver_loc = 'chromedriver.exe'
    # driver = webdriver.Chrome(chrome_options=options, desired_capabilities=capa, executable_path=chromedriver_loc)
    driver = webdriver.Chrome(chrome_options=options, desired_capabilities=capa)
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
def compute_stats(teams, categories, league_id, quiet):
    if not quiet:
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
    if not quiet:
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
    if not quiet:
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


# calculate player ranks for a week and return as dictionary
# uses average rank
# for consistent season ranking averages
def get_ranks_avg(raw_rank):
    ranks = {}
    current_rank = 1
    for row in raw_rank:
        num_teams = len(row[1])
        # if no ties, rank will be current_rank
        if num_teams == 1:
            ranks[row[1][0]] = current_rank
        # if ties need to find average rank
        else:
            # list of ranks that the tied players represent
            rank_list = list(range(current_rank, current_rank + num_teams))
            avg_rank = sum(rank_list) / float(num_teams)
            for player in row[1]:
                ranks[player] = avg_rank
        # update current rank
        current_rank += num_teams
    return ranks


# check if a week is a regular season week using playoffTierType key
# I don't think that key has a value aside from 'NONE' earlier in the season
def reg_season_check(matchup):
    reg_season = True
    if 'playoffTierType' in matchup:
        if matchup['playoffTierType'] != 'NONE':
            reg_season = False
    return reg_season


# generates season strength of schedule for each player
def get_season_sos():
    league_id = request.args.get('leagueId')
    app.logger.info('League ID: %s', str(league_id))
    current_week = get_current_week(league_id)
    categories = ['FG%', 'FT%', '3PM', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PTS']
    # get all scoreboard data from ESPN api
    data = get_scoreboards(league_id)

    # look through matchups to see if there are any active playoff weeks and to store the max regular season week
    # if there are active playoff weeks we use max regular season week as the final week
    # else we can just use the current week
    is_reg_season = True
    max_reg_season = 0
    for matchup in data:
        if matchup['matchupPeriodId'] > max_reg_season and reg_season_check(matchup):
            max_reg_season = matchup['matchupPeriodId']
        if not reg_season_check(matchup):
            is_reg_season = False

    if is_reg_season:
        final_week = current_week
    else:
        final_week = max_reg_season

    # store opponent rank sums for each player
    player_opp_rank_sums = {}

    for week in range(1, final_week + 1):
        # get scoreboard stats for current week
        teams = get_week_scoreboard(league_id, week, data)
        stats = compute_stats(teams, categories, league_id, True)
        # returns a dictionary with player key and avg rank value
        ranks = get_ranks_avg(stats[0])
        if not teams or not stats or not ranks:
            app.logger.error('%s - Teams, categories, or stats list empty.', str(league_id))
            abort(500)
            sys.exit('Teams, categories, or stats list empty.')
        team_names = [team[0] for team in teams]
        matchups = get_week_matchups(teams)
        # update player dictionary key with weekly opponent rank
        update_player_opp_rank_sums(player_opp_rank_sums, team_names, matchups, ranks)
    # get weekly average
    avg_opp_rank = {player: (round(sum_ranks / float(final_week), 2)) for (player, sum_ranks) in player_opp_rank_sums.items()}
    # convert into rankings to output in html
    sos_rankings = build_rankings(avg_opp_rank)
    return [league_id, current_week, sos_rankings]


# calculates personal performance for each player using average weekly rank
def get_overall_perf():
    league_id = request.args.get('leagueId')
    app.logger.info('League ID: %s', str(league_id))
    current_week = get_current_week(league_id)
    categories = ['FG%', 'FT%', '3PM', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PTS']
    data = get_scoreboards(league_id)

    # look through matchups to see if there are any active playoff weeks and to store the max regular season week
    # if there are active playoff weeks we use max regular season week as the final week
    # else we can just use the current week
    is_reg_season = True
    max_reg_season = 0
    for matchup in data:
        if matchup['matchupPeriodId'] > max_reg_season and reg_season_check(matchup):
            max_reg_season = matchup['matchupPeriodId']
        if not reg_season_check(matchup):
            is_reg_season = False

    if is_reg_season:
        final_week = current_week
    else:
        final_week = max_reg_season

    player_rank_sums = {}

    for week in range(1, final_week + 1):
        teams = get_week_scoreboard(league_id, week, data)
        stats = compute_stats(teams, categories, league_id, True)
        # returns a dictionary with player key and avg rank value
        ranks = get_ranks_avg(stats[0])
        if not teams or not stats or not ranks:
            app.logger.error('%s - Teams, categories, or stats list empty.', str(league_id))
            abort(500)
            sys.exit('Teams, categories, or stats list empty.')
        team_names = [team[0] for team in teams]
        # update player dictionary key with weekly player rank
        update_player_rank_sums(player_rank_sums, team_names, ranks)

    # get weekly average
    avg_player_rank = {player: (round(sum_ranks / float(final_week), 2)) for (player, sum_ranks) in player_rank_sums.items()}
    # convert into rankings to output in html
    perf_rankings = build_rankings(avg_player_rank)
    return [league_id, current_week, perf_rankings]


# convert dictionary with average player ranks to table with general rank, team, and avg rank
def build_rankings(avg_ranks):
    sorted_avg_rank = sorted(avg_ranks.items(), key=lambda kv:[kv[1], kv[0]], reverse=False)
    rankings = []
    rank = 1
    for team in sorted_avg_rank:
        rankings.append([rank, team[0], team[1]])
        rank += 1
    return rankings


# update player dictionary with current week opponent rank info
def update_player_opp_rank_sums(player_opp_rank_sums, team_names, matchups, ranks):
    for player in team_names:
        if player in player_opp_rank_sums:
            player_opp_rank_sums[player] += ranks[matchups[player]]
        # if player doesn't have opponent rank values, store to dict
        else:
            player_opp_rank_sums[player] = ranks[matchups[player]]
    return


# update player dictionary with current week player rank info
def update_player_rank_sums(player_rank_sums, team_names, ranks):
    for player in team_names:
        if player in player_rank_sums:
            player_rank_sums[player] += ranks[player]
        # if player doesn't have opponent rank values, store to dict
        else:
            player_rank_sums[player] = ranks[player]
    return


# since scoreboard info is written in pairs, weekly matchups should be adjacent
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
        app.logger.error('Could not make ESPN API call.', ex)
        abort(500)
        sys.exit('Could not make ESPN API call.')
    data = r.json()
    return data


# check if val exists, otherwise return 0
def key_check(stats, key):
    try:
        return stats[key]['score']
    except KeyError:
        pass
    return 0


# format espn api call info into 9-cat team info
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


# filter all scoreboards for current week scoreboard and format
def get_week_scoreboard(league_id, week, data):
    team_dict = get_team_dict(league_id)
    matchups = [matchup for matchup in data if matchup['matchupPeriodId'] == week or matchup['matchupPeriodId'] == int(week)]
    scoreboard = []
    for matchup in matchups:
        team1 = format_team(matchup['away'], team_dict)
        team2 = format_team(matchup['home'], team_dict)
        scoreboard.append(team1)
        scoreboard.append(team2)
    return scoreboard


# ESPN scoreboard api call, mMatchupScore param is necessary to get the important 'matchupPeriodId' key
def get_scoreboards(league_id):
    params = (('view', ['mScoreboard', 'mMatchupScore']),)
    data = call_api(f'http://fantasy.espn.com/apis/v3/games/fba/seasons/{app.config.get("SEASON")}/segments/0/leagues/{league_id}',
                    params=params)
    data = data['schedule']
    return data


# Run the Flask app.
if __name__ == '__main__':
    app.run()
