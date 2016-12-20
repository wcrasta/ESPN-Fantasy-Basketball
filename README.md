# ESPN-Fantasy-Basketball

An application that calculates and displays various statistics for ESPN Fantasy Basketball leagues. The code/application works for (public) leagues of any size that use H2H Most Cat. scoring and a scoring system of FG%, FT%, 3PM, REB, AST, STL, BLK, TO, PTS.

A live demo of the app can be found at http://fantasybball-tools.herokuapp.com/.

## Installation

To develop, you need Python & Flask. For a list of Python dependencies, see `requirements.txt`.

## How It Works

The code uses BeautifulSoup to scrape the "Season Stats" table from the League Standings page. It then compares a team's stats for the whole season against the stats for every other team and computes the score. The result of all these comparsions are displayed for the user to see. Teams with more wins against their peers are ranked higher in the "Power Rankings". If you are confused about how to use the app, check the demo above -- everything is quite intuitive. 

## Improvements/Possible Added Features

Feel free to contribute to this project! There are many improvements that can be made, both in terms of code quality and in terms of whole new ideas that can be implemented. Both the front-end and back-end are very very simple and can be greatly enhanced. Thoughts I have for new features (may or may not ever be implemented):

1. Scrape the weekly scoreboard and display your score against every team in the league, not just against your opponent for that week.
2. Come up with a formula that lists teams on the Power Rankings page based on the difficulty of their schedule. For example, a win against the #1 team in the league might raise your "Power Rankings" score by 5 whereas a win against the worst team in the league might raise your score by 1. The current implementation is to raise everyone's score by 1 when they win, regardless of the strength of opponent.

## Instructions for contributing

1. Fork the repository!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

If you don't know how to implement something, but do have an idea that you would like to see implemented, feel free to shoot me an e-mail and I can try to implement it.

## Credits

Author: Warren Crasta (warrencrasta@gmail.com)
