class Config(object):
    DEBUG = False
    SEASON = '2020'

class ProductionConfig(Config):
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True
