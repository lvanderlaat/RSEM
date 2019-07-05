import numpy as np
import pandas as pd
from obspy import read, read_inventory, UTCDateTime
from optparse import OptionParser
from math import floor
from os import listdir
from scipy.signal import butter, lfilter

'''======================= Parse configuration file ======================'''

Usage= 'Usage: python3 rsem.py -c config_file'

parser = OptionParser(usage=Usage)
parser.add_option('-c', '--config_file', action='store',
		type='string', dest='config_file',help='Path to configuration file')
(options, args) = parser.parse_args()

cfg_path = options.config_file

config = read_config(cfg_path)

directory       = config['directory']
remove_response = config['remove_response']
if remove_response == 'True':
	inventory       = read_inventory(config['inventory'])
resampling_rate = float(config['resampling_rate'])
window_length   = int(config['window_length'])
freqmin         = float(config['freqmin'])
freqmax         = float(config['freqmax'])
order           = int(config['order'])

output = cfg_path.replace('.cfg','.csv')

'''============================== Functions =============================='''


def read_config(filepath):
	""" Reads the configuration file as a dictionary

	Parameters
	----------
	filepath: str
		txt file path

	Returns
	-------
	config: dict
	"""
	config_file = open(filepath)
	config = {}
	for line in config_file:
		line = line.strip()
		if line and line[0] is not "#" and line[-1] is not "=":
			variable,value = line.rsplit("=",1)
			config[variable] = value
			config[variable.strip()] = value.strip()
	return config


def butter_bandpass_filter(tr, freqmin, freqmax,order):
	sampling_rate = tr.stats['sampling_rate']
	nyquist = 0.5 * sampling_rate
	low = freqmin / nyquist
	high = freqmax / nyquist
	b, a = butter(order, [low, high], btype='band')
	tr.data = lfilter(b, a, tr.data)
	return


def pre_process(tr,freqmin,freqmax,order,resampling_rate):
	tr.detrend()
	sampling_rate = tr.stats['sampling_rate']
	tr.decimate(factor=int(sampling_rate/resampling_rate))
	butter_bandpass_filter(tr, freqmin, freqmax,order)


def tr2windowed_data(tr,window_length):

	""" Create a NumPy array with a trace windowed.

	Parameters
	----------
	tr: obspy tr
		Trace for analysis
	window: int
		Window of analysis [samples]

	Returns
	-------
	data_windowed: np array
		2D array (number of window, window length)
	total_length: int
		New length in samples to fit a integer number of windows
	"""

	npts = tr.stats['npts']
	starttime = tr.stats['starttime']
	sampling_rate = tr.stats['sampling_rate']

	n_windows = floor(npts/window_length)
	total_length = window_length * n_windows
	data_windowed = np.zeros((1,n_windows,window_length))

	tr_data = tr.data[:total_length]
	tr_data = np.reshape(tr_data,(n_windows,window_length))
	data_windowed = tr_data

	timestamps = np.arange(0,total_length/sampling_rate,
		window_length/sampling_rate) + starttime.timestamp
	utcdatetime = np.vectorize(UTCDateTime)(timestamps)

	return utcdatetime,data_windowed,total_length


'''============================== Processing ============================='''

columns = ['utcdatetime','rms']

df = pd.DataFrame(index=range(0),columns=columns)

for filename in listdir(directory):
	print('\n==============================================================')
	print('\nReading file {}...'.format(filename))
	tr = read(directory+filename)[0]

	if remove_response == 'True':
		print('\nRemoving instrument response...')
		tr.remove_response(inventory)
	print('\nPre-processing')
	pre_process(tr,freqmin,freqmax,order,resampling_rate)

	utcdatetime,data_windowed,total_length = tr2windowed_data(tr,
		window_length)

	rms = np.sqrt(np.mean(data_windowed**2,axis=1))

	df_trace = pd.DataFrame(np.vstack([utcdatetime,rms]).T,columns=columns)
	df = df.append(df_trace,ignore_index=True)

print('\n==============================================================')
print('\nWriting file...')
df.to_csv('test.csv',index=False)
