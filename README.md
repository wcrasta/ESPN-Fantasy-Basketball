# ESPN-Fantasy-Basketball

An application that calculates and displays various statistics for ESPN Fantasy Basketball leagues. The code/application works for (public) leagues of any size that use H2H Most Cat. scoring. It may or may not work for other scoring systems.

A live demo of the app can be found at http://fantasybball-tools.herokuapp.com/.

## Installation

To develop, you need Python & Flask. For a list of Python dependencies, see `requirements.txt`.

## Improvements/Possible Added Features

Feel free to contribute to this project! There are many improvements that can be made, both in terms of code quality and in terms of whole new ideas that can be implemented. Both the front-end and back-end are simple and can be greatly enhanced. Thoughts I have for new features (may or may not ever be implemented):

1. Come up with a formula that lists teams on the Standings page based on the difficulty of their schedule. For example, a win against the #1 team in the league might raise your "Standings" score by 5 whereas a win against the worst team in the league might raise your score by 1. The current implementation is to raise everyone's score by 1 when they win, regardless of the strength of opponent.
2. Use Selenium or the ESPN API (?) to make this tool available for private leagues.

## Instructions for contributing

1. Fork the repository!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

If you don't know how to implement something, but do have an idea that you would like to see implemented, feel free to shoot me an e-mail and I can try to implement it.

## Credits

Author: Warren Crasta (warrencrasta@gmail.com)

Contributor: Wayne Crasta
