import configparser


class Options(object):

    def __init__(self, configfile):

        self.configfile = configfile

        config = configparser.ConfigParser()
        config.read(self.configfile)

        self.name            = config.get('DATA', 'name')

        self.directory       = config.get('DATA', 'directory')

        self.remove_resp     = config.getboolean('DATA', 'remove_resp') if\
                                config.has_option('DATA', 'remove_resp')\
                                else False

        self.inventory       = config.get('DATA', 'inventory') if\
                                config.has_option('DATA', 'inventory') else None

        self.resampling_rate = config.getfloat('DATA', 'resampling_rate')\
                                    if config.has_option('DATA',
                                                  'resampling_rate') else 50.

        self.window_length = config.getint('DATA', 'window_length') if\
                                    config.has_option('DATA',
                                                    'window_length') else 3000

        self.freqmin       = config.getfloat('FILTER','freqmin') if\
                                config.has_option( 'FILTER','freqmin') else 1.

        self.freqmax       = config.getfloat('FILTER','freqmax') if\
                                config.has_option( 'FILTER','freqmax') else 24.

        self.order         = config.getint('FILTER','order') if\
                                config.has_option( 'FILTER','order') else 4

