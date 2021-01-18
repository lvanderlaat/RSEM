import numpy as np
import pandas as pd
from obspy import read, read_inventory, UTCDateTime
from optparse import OptionParser
from math import floor
from os import listdir, path
import time
from obspy_tools.obspy2numpy import tr2windowed_data
from obspy_tools.filter import butter_bandpass_filter
from config import Options
from obspy_tools.stream_request import read_st

t0 = time.time()

# Parse options
Usage= 'Usage: python3 rsem.py -c config_file'

parser = OptionParser(usage=Usage)
parser.add_option('-c', '--config_file', action='store',
        type='string', dest='config_file', help='Path to configuration file')
options, args = parser.parse_args()

config_file = options.config_file

opt = Options(config_file)

csv_path = path.split(config_file)[0]+'/'+opt.name+'.csv'

if opt.remove_resp:
    inventory = read_inventory(opt.inventory)
else:
    inventory = None

def pre_process(tr, inventory, freqmin, freqmax, order, factor):

    print('\nPre-processing')

    # Decimate
    if not opt.remove_resp:
        tr.detrend()
    tr.decimate(factor=factor)

    # Remove response
    if opt.remove_resp:
        print('\nRemoving instrument response...')
        tr.remove_response(inventory)
        tr.detrend()

    # Filter 
    butter_bandpass_filter(tr, freqmin, freqmax, order)

columns = ['utcdatetime','rms']

df = pd.DataFrame(index=range(0),columns=columns)

count = 0
for filename in listdir(opt.directory):
    t1 = time.time()

    print('\n==============================================================')
    print('\nReading file {}...'.format(filename))
    tr = read(opt.directory+filename)[0]

    pre_process(tr, inventory,  opt.freqmin, opt.freqmax, opt.order,
                opt.factor)

    try:
        utcdatetime, data_windowed, total_length = tr2windowed_data(tr,
                                                       opt.window_length)
        rms = np.sqrt(np.mean(data_windowed**2, axis=1))
        df_trace = pd.DataFrame(np.vstack([utcdatetime, rms]).T,
                                 columns=columns)
        df = df.append(df_trace, ignore_index=True)
    except:
       pass

    t2 = time.time()
    time_per_file = t2 - t1
    print('\nElapsed time with this file: {} s'.format(round(t2-t1, 0)))
    count += 1

    remaining_files = len(listdir(opt.directory)) - count
    remaining_time  = time_per_file * remaining_files
    if remaining_time <= 60:
        remaining_time = round(remaining_time, 0)
        time_unit = 'seconds'
    if remaining_time > 60 and remaining_time <= 3600:
        remaining_time = round(remaining_time/60, 0)
        time_unit = 'minutes'
    elif remaining_time > 3660:
        remaining_time = round(remaining_time/3600, 2)
        time_unit = 'hours'
    print('\nEstimated remaining time: {} {}'.format(remaining_time,
                                                       time_unit))

print('\n==============================================================')
print('\nWriting file...')
df.to_csv(csv_path, index=False)

t1 = time.time()
print('Total time elapsed: {} s'.format(round(t1-t0, 0)))
