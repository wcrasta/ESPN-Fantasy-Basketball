class Config(object):
    DEBUG = False
    SEASON = '2025'

class ProductionConfig(Config):
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True
