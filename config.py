import os

class Config(object):
    DEBUG = False
    SECRET_KEY = 'secret-key'
    SEASON = '2019'


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ['SECRET_KEY']


class DevelopmentConfig(Config):
    DEBUG = False
