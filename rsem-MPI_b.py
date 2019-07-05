from numpy import mean, sqrt
import pandas as pd
from obspy import read, read_inventory
from mpi4py import MPI
from optparse import OptionParser
from math import floor
from os import listdir
import numpy as np

import time
timestart = time.time()

'''=================== Parse configuration file ========================= '''

Usage= 'Usage: python3 rsem-MPI.py -c config_file'

parser = OptionParser(usage=Usage)
parser.add_option('-c', '--config_file', action='store',
		type='string', dest='config_file',help='Path to configuration file')
(options, args) = parser.parse_args()

cfg_path = options.config_file

def read_config(filepath):
	
	'''
	READ_CONFIG
	Reads the configuration file as a dictionary
		Variables:
	 		- Path of the configuration file 
	'''
	
	config_file = open(filepath)
	config = {}
	for line in config_file:
		line = line.strip()
		if line and line[0] is not "#" and line[-1] is not "=":
			variable,value = line.rsplit("=",1)
			config[variable] = value
			config[variable.strip()] = value.strip()
	return config

config = read_config(cfg_path)

directory = config['directory']
inventory = config['inventory']
resampling_rate = float(config['resampling_rate'])
window_length = float(config['window_length'])
filter_window_length = float(config['filter_window_length'])
freqmin = float(config['freqmin'])
freqmax = float(config['freqmax'])

output = cfg_path.replace('.cfg','.csv')

''' ======================================================================'''

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

n_files = len(listdir(directory))

def distribute_processes(comm,rank,size,length):
	share = floor(length/size)

	if rank < length % size:
		share = share + 1

	displacements = np.zeros(size,dtype=int)
	shares = comm.gather(share,root=0)
	if rank == 0:	
		for i in range(1,size):
			displacements[i] = displacements[i-1] + shares[i-1]

	displacements = comm.bcast(displacements,root=0)
	
	return displacements,shares,share

displacements,shares,share = distribute_processes(comm,rank,size,n_files)

''' ======================================================================'''

inventory = read_inventory(inventory)

''' ======================================================================'''

def pre_process(tr,resampling_rate,inventory,freqmin,freqmax):
	tr.remove_response(inventory)
	tr.detrend()

	tr.filter('bandpass',freqmin=freqmin,freqmax=freqmax)
	return

def compute_rsem(tr,window_length):
	
	columns = ['utcdatetime','rms']
	df = pd.DataFrame(index=range(0),columns=columns)
	
	for window in tr.slide(window_length=window_length,step=window_length):
		
		time = str(window.stats['starttime']+window_length/2)
		rms = sqrt(mean(window.data**2))
		
		df_window = pd.DataFrame([[time,rms]],columns=columns)
		df = df.append(df_window,ignore_index=True)
	
	return df

def filter_rsem(df,window_length,filter_window_length):
	filter_window_length /=  window_length
	df['rms'] = df['rms'].rolling(window=int(filter_window_length)).mean()
	return

''' ======================================================================'''

columns = ['utcdatetime','rms']
df_rank = pd.DataFrame(index=range(0),columns=columns)
	
start_position = displacements[rank]
for i in range(start_position,start_position+share):
	
	print('\n========================================================================\n')
	print('Rank',rank,'processing file',i+1-start_position,
		 'of its',share,'files share.')
		 
	filename = listdir(directory)[i]
	print(filename)
	tr = read(directory+filename)[0]
	
	''' Cambiar metadatos para poder corregir por instrumento '''
	tr.stats['network'] = 'TC'
	tr.stats['station'] = 'CIMA'
	tr.stats['channel'] = 'BH Z'
	
	pre_process(tr,resampling_rate,inventory,freqmin,freqmax)
	
	df_trace = compute_rsem(tr,window_length)
	
	df_rank = df_rank.append(df_trace,ignore_index=True)

print('\n========================================================================\n')
print('Rank 0 gathering data from rank {}'.format(rank))
df_ranks = comm.gather(df_rank,root=0)

if rank == 0:
	
	print('\n========================================================================\n')
	print('Rank 0 merging all data together and writing data file.')
	
	df = pd.DataFrame(index=range(0),columns=columns)
	
	for df_rank in df_ranks:
		df = df.append(df_rank,ignore_index=True)
	
	df = df.sort_values(by='utcdatetime')	
	
	df.to_csv(output,index=False)
	
	print('\n========================================================================\n')
	timeend = time.time()
	print('\n========================================================================\n')
	print('Total time of execution (without importing modules) {} s'.format(round(timeend-timestart)))
