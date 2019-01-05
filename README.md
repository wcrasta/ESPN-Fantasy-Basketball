# ESPN-Fantasy-Basketball

An application that calculates and displays various statistics for ESPN Fantasy Basketball leagues. The code/application works for (public) leagues of any size that use H2H Most Cat. scoring. It may or may not work for other scoring systems.

A live demo of the app can be found at http://fantasy.warrencrasta.com/. If you liked this project, please consider starring the repository.

## Installation
1. Create a virtual environment using [venv and Python 3.5](https://docs.python.org/3/library/venv.html) (optional, but highly recommended). Activate the virtual environment.
2. Run **pip install -r requirements.txt** to install the dependencies for this project.
3. Open your favorite IDE and configure the project so that the Python interpreter + package sources comes from your virtual environment (optional, but highly recommended).
4. In `app.py`, find this line: `app.config.from_object(os.environ['APP_SETTINGS'])`. Either set your APP_SETTINGS environment variable to `config.DevelopmentConfig` or hard code `config.DevelopmentConfig`. 
5. Download [ChromeDriver](http://chromedriver.chromium.org/downloads) and put it in your path, preferably somewhere within your virtual environment. Instructions vary by OS. You might have to Google where to properly place ChromeDriver to get it working.
6. Run or debug the program!

## Improvements/Possible Added Features
**NOTE:** I'm fully aware that the `app.py` code is a bit of a mess. Best practices were certainly not followed, as this was something I did for fun and created quickly. Over the years, ESPN has changed its website layout and I've correspondingly made the minimal amount of changes needed to get things working again, regardless of how "ugly" my fixes may be.

Feel free to contribute to this project! There are many improvements that can be made, both in terms of code quality and in terms of whole new ideas that can be implemented. Both the front-end and back-end are simple and can be greatly enhanced.

If you do contribute, be advised that it may take some time to get your PR merged in. If you're interested in being a collaborator, e-mail me. If you don't know how to implement something, but do have an idea that you would like to see implemented, feel free to shoot me an e-mail and I can try to implement it.

## Credits

Author: Warren Crasta (warrencrasta@gmail.com), Wayne Crasta
