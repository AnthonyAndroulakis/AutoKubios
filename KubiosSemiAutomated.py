#this version gets the start and end times from the ibi_info.csv file

import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)

import os
import sys
import subprocess
import copy
import math
import csv
import time
import datetime
import _thread as thread

import pandas as pd
import pyautogui
import glob
import psutil

from pref import Preferences

#constants
##change these
inputdir = "/Users/anthonyandroulakis/Documents/autokubios/datafolder"
resultsdir = f"{inputdir}/results"
kubiosapp = "/Applications/KubiosHRVPremium/application/KubiosHRVPremium.app/Contents/MacOS/run_kubioshrv.sh"
ibiinfofile = "/Users/anthonyandroulakis/Documents/ibi_info_autokub.csv"
interval_length = 900
units = "ms" #change to "s" if in seconds
##don't change these
kubios_sample_header_lines = [['Kubios_Samples.csv;;'], ['File is used for the automatic sample generation. Kubios_Samples.csv file must be saved in the same folder as measurement file.;;'], [';;'], ['Column 1: File name e.g: polar_rr_data.hrm;;'], ['Column 2: 0 = Sample time is given in absolute time; 1 = Sample time is given relative to begining of the measurement;'], ['Column 3: Sample Label for first sample (e.g. "Sample 1") and optionally followed by an RGB color code for the sample (e.g. "Sample 1 #255 0 0");;'], ['Column 4: Start time of the sample in seconds (e.g. "600");" in hh:mm:ss format (e.g. ""00:10:00"")";" or ""START"" to indicate that sample starts from the beginning of the measurement"'], ['Column 5: End time of the sample in seconds (e.g. "600");" in hh:mm:ss format (e.g. ""00:10:00"")";" or ""END"" to indicate that the sample ends at the end of the measurement"'], ['Column 6-xx: Repeat columns 3-5 for Samples 2...N;;'], [';;'], ['File name', '0=Absolute time/1=Relative to beginnig of measurement', 'Label (Sample 1)', 'START (Sample 1)', 'END (Sample 1)', 'Label (Sample 2)', 'START (Sample 2)', 'END (Sample 2)', 'Label (Sample 3)', 'START (Sample 3)', 'END (Sample 3)', 'Label (Sample 4)', 'START (Sample 4)', 'END (Sample 4);;']]
sample_fn = f"{inputdir}/Kubios_Samples.csv"
epoch = datetime.datetime(1970,1,1)

#functions
##create a sample row for Kubios_Samples.csv
def create_sample_row(df_row):
	sdf_start_day = get_ibi_startday(df_row['Filename'])
	res = [os.path.basename(df_row['Filename']), '0']

	startsec = df_row['Time_to_Sleep'] - sdf_start_day
	endsec = df_row['Time_to_Wake'] - sdf_start_day

	sample = 0
	t1 = startsec
	t2 = t1 + interval_length
	while t2 <= endsec:
		res.extend([str(sample+1), str(t1), str(t2)])
		t1 = t2
		t2 = t1 + interval_length
		sample += 1

	return res

##open file in Kubios and save results into csv file
def run_Kubios(participantID):
	if 'KubiosHRVPremium' not in [p.name() for p in psutil.process_iter()]:
		process = subprocess.Popen(kubiosapp, stderr=subprocess.STDOUT, stdout=subprocess.PIPE) 
		wait_for_Kubios()
	print("Click on the first file under Recent files")
	print(f"After Kubios is finished processing, do ctrl-s, let it name the file, and save in this folder: {inputdir}/")
	for line in iter(process.stdout.readline, b''):
		fun = line.decode(sys.stdout.encoding)
		if fun.startswith("Results saved in"):
			pyautogui.hotkey('command', 'w')
			pyautogui.hotkey('ctrl', 'w')
			#input('Press ENTER to continue')
			os.remove(f'{inputdir}/wait.txt')
	return

##wait for Kubios to finish
def wait_for_Kubios():
	while 'KubiosHRVPremium' in [p.name() for p in psutil.process_iter()]:
		time.sleep(1)

##calculate needed smoothing param from cutoff frequency
#nvm dont know how to do this

##read _hrv.csv summary file and extract wanted values
def read_summary_hrv(participantID, which_rows):
	#read csv. the csv is weird but ok whatever
	sample_times_curr = next(row for row in sample_times if len(row)>0 and row[0] == participantID+'.sdf')
	num_bins = int((len(sample_times_curr)-2)/3)
	target = f'{inputdir}/{participantID}_hrv.csv'
	df = pd.read_csv(target, header=None, names=[str(i) for i in range(1, num_bins*2+1)])
	
	#update results
	res = {}
	which_rows = [i.strip() for i in which_rows]
	target_row_inds = []
	for w in which_rows: ##what data to extract, according to row headers
		target_row_i = df['1'][df['1'].str.strip() == w]
		target_row_inds.append(int(target_row_i.index[0]))

	#2n is the column index bc indexes start at 1 here
	for b in range(1, num_bins+1):
		col = df[str(b*2)]
		next_row = [col[i] for i in target_row_inds]
		res[str(b)] = next_row

	#remove csv file
	os.remove(target)

	return res

##read 1st sample from summary hrv
def read_1sample_summary_hrv(participantID, which_rows):
	target = f'{inputdir}/{participantID}_hrv.csv'
	df = pd.read_csv(target, header=None, names=['1', '2'])

	#update results
	res = {}
	which_rows = [i.strip() for i in which_rows]
	target_row_inds = []
	for w in which_rows: ##what data to extract, according to row headers
		target_row_i = df['1'][df['1'].str.strip() == w]
		target_row_inds.append(int(target_row_i.index[0]))

	#2n is the column index bc indexes start at 1 here
	for b in range(1, 2):
		col = df[str(b*2)]
		next_row = [col[i] for i in target_row_inds]
		res[str(b)] = next_row

	#remove csv file
	os.remove(target)

	return res

##check if str is float
def isfloat(num):
	try:
		#also filters out nans
		if float(num)+1==float(num)+1:
			return True
		else:
			return False
	except ValueError:
		return False

##get seconds from 1/1/1970
def utc_ts(dt):
	t = (dt - epoch).total_seconds()
	return t

##round to 5 sig figs
def round_5_sigfigs(num):
	if isfloat(num):
		num = float(num) #just in case
		return float('%s' % float('%.5g' % num))
	else:
		return num

##calculate the Peak Power / Peak Band Power for each interval
def get_mcc_peak_band_power(participantID, freqMCC1res):
	#find number of samples
	sample_times_curr = next(row for row in sample_times if len(row)>0 and row[0] == participantID+'.sdf')[2:]
	
	res = {}
	for b in range(int(len(sample_times_curr)/3)):
		curr_row = [participantID+'.sdf', '0', str(sample_times_curr[3*b]), str(sample_times_curr[3*b+1]), str(sample_times_curr[3*b+2])]

		#modify samples for speed
		with open(sample_fn, 'w+') as f:
			writer = csv.writer(f)
			for row in sample_times:
				if len(row)>0 and row[0] == participantID+'.sdf':
					writer.writerow(curr_row)
				else:
					writer.writerow(row)

		#calculate new bands
		mcc_peak = float(freqMCC1res[str(b+1)][0])
		HF_lower = max(0.04, mcc_peak-0.015)
		HF_upper = min(0.26, mcc_peak+0.015)
		##truncate to 5 sig figs
		HF_lower = round_5_sigfigs(HF_lower)
		HF_upper = round_5_sigfigs(HF_upper)

		prefs.set_bands([0.0033, 0.02],
						[0.02   , 0.04],
						[HF_lower, HF_upper])

		#run kubios
		with open(f'{inputdir}/wait.txt', 'w+') as f:
			f.write(' ')
		while len(glob.glob(f'{inputdir}/wait.txt'))>0:
			time.sleep(1)

		#analyze summary csv
		#										Peak_power
		#res[str(b+1)] = read_summary_hrv(pID, ['HF (ms^2):'])[str(b+1)]
		res[str(b+1)] = read_1sample_summary_hrv(pID, ['HF (ms^2):'])['1']

	return res

##calculate hrv coherence using the 1st and 3rd freq results
def calculate_hrv_coh(freq1res, freqMCC2res):
	res = {}
	for istr in freq1res:
		total_power = sum([round_5_sigfigs(i) for i in freq1res[istr]])
		mcc_peak_band_power = round_5_sigfigs(freqMCC2res[istr][0])
		hrv_coh = mcc_peak_band_power/(total_power - mcc_peak_band_power)
		res[istr] = hrv_coh
	return res

##get ibi start time
def get_ibi_startday(ibifile):
	with open(ibifile) as f:
		data = f.read().splitlines()
		for d in data:
			if d.startswith('STARTTIME='):
				starttimestr = d[10:-9]
				res = datetime.datetime.strptime(starttimestr, '%d.%m.%Y')
	return utc_ts(res)

##save all to file
def save(pID, starttime, freq1res, freqMCC1res, freqMCC2res, hrvcrres):
	rows = [['ID', 'Time', 'VLF_Power', 'LF_Power', 'HF_Power', 'Total_Power', 'MCC_Peak', 'MCC_Band_Power', 'MCC_Peak_Band_Power', 'Coherence']]
	outputfn = f'{resultsdir}/{pID}.csv'

	#get number of bins
	bin_num = len(freq1res)

	for b in range(bin_num):
		m, s = divmod(float(starttime)+b*interval_length, 60)
		h, m = divmod(m, 60)
		hour = int(h%24)
		minute = int(m)
		second = int(s)
		timestr = f'{hour:d}:{minute:02d}:{second:02d}'
		key = str(b+1)
		curr_row = [
			pID,
			timestr,
			round_5_sigfigs(freq1res[key][0]),
			round_5_sigfigs(freq1res[key][1]),
			round_5_sigfigs(freq1res[key][2]),
			sum([round_5_sigfigs(i) for i in freq1res[key]]),
			round_5_sigfigs(freqMCC1res[key][0]),
			round_5_sigfigs(freqMCC1res[key][1]),
			round_5_sigfigs(freqMCC2res[key][0]),
			hrvcrres[key]
		]
		rows.append(curr_row)

	#save to file
	with open(outputfn, 'w+') as f:
		writer = csv.writer(f)
		for row in rows:
			if isfloat(str(row[-1])) or row[-1] == 'Coherence': #remove nans (ie, segments that are filled with noise)
				writer.writerow(row)

#program starts here
prefs = Preferences()

##create sample file
sample_times = list(kubios_sample_header_lines) #will contain backup of sample times
ibi_info_df = pd.read_csv(ibiinfofile)
ibi_info_df['Filename'] = [inputdir+'/'+i.split('/')[-1] for i in ibi_info_df['Filename']]

for df_row in ibi_info_df.iloc():
	row = create_sample_row(df_row)
	sample_times.append(row)

with open(sample_fn, 'w+') as f:
	writer = csv.writer(f)
	for row in sample_times:
		writer.writerow(row)

##find run_kubios.sh/run_kubios.bat file
if not "run_kubioshrv" in kubiosapp:
	for f in glob.glob(kubiosapp, recursive=True):
		if "run_kubioshrv" in f:
			kubiosapp = f
			break

##change filename history and bands in pref file
for r in ibi_info_df.iloc():
	s = str(r['Filename'])
	pID = s.split('/')[-1][:-4]
	renamed = str(r['Renamed'])
	prefs.set_recent_file(s)
	prefs.set_detrending('none', [])
	prefs.set_denoising('Medium')
	prefs.set_deartifacting('Strong')
	prefs.set_bands([0.0033, 0.04],
					[0.04  , 0.15],
					[0.15  , 0.4 ])

	#run Kubios
	with open(f'{inputdir}/wait.txt', 'w+') as f:
		f.write(' ')
	if 'KubiosHRVPremium' not in [p.name() for p in psutil.process_iter()]:
		thread.start_new_thread(run_Kubios, (pID,))
	while len(glob.glob(f'{inputdir}/wait.txt'))>0:
		time.sleep(1)
	#								VLF_Power      LF_Power      HF_Power
	freq1 = read_summary_hrv(pID, ['VLF (ms^2):', 'LF (ms^2):', 'HF (ms^2):'])

	prefs.set_bands([0.0033, 0.02],
					[0.02  , 0.04],
					[0.04  , 0.26 ])

	#run Kubios
	with open(f'{inputdir}/wait.txt', 'w+') as f:
		f.write(' ')
	while len(glob.glob(f'{inputdir}/wait.txt'))>0:
		time.sleep(1)
	#									Peak        Band_Power
	freq_MCC1 = read_summary_hrv(pID, ['HF (Hz):', 'HF (ms^2):'])

	freq_MCC2 = get_mcc_peak_band_power(pID, freq_MCC1)

	hrv_coherences = calculate_hrv_coh(freq1, freq_MCC2)

	starttime = next(row for row in sample_times if len(row)>0 and row[0] == pID+'.sdf')[3]
	save(renamed, starttime, freq1, freq_MCC1, freq_MCC2, hrv_coherences)

print("Auto-Kubios finished. Exiting...")

for proc in psutil.process_iter():
	if proc.name() == 'KubiosHRVPremium':
		proc.kill()
