import scipy.io as spio
import numpy as np

import platform
import os

def to_numpy(inputvar):
	if isinstance(inputvar, str):
		return np.array([inputvar], dtype=f'<U{len(inputvar)}')
	elif isinstance(inputvar, int):
		return np.array([[inputvar]], dtype=int)
	elif isinstance(inputvar, float):
		return np.array([[inputvar]], dtype=float)

class Preferences:
	__slots__ = ['preffile', 'data']
	def __init__(self, preffile=''):
		if preffile == '':
			if platform.system() == 'Darwin':
				preffile = '{}/Library/Preferences/Kubios/KubiosHRVPremium/KubiosHRVprefs.mat'.format(os.path.expanduser('~'))
			elif platform.system() == 'Linux':
				preffile = '{}/.kubios/KubiosHRVPremium/KubiosHRVprefs.mat'.format(os.path.expanduser('~'))
			elif platform.system() == 'Windows':
				preffile = 'C:/Users/{}/AppData/Roaming/Kubios/KubiosHRVPremium'.format(os.getenv('username'))
		self.preffile = preffile
		self.data = None

	def _loadprefs(self):
		self.data = spio.loadmat(self.preffile, mat_dtype=True)

	def _saveprefs(self):
		spio.savemat(self.preffile, self.data)

	def set_recent_file(self, filename):
		self._loadprefs()
		self.data['Preferences']['hrv'][0,0]['filenames'][0,0] = np.array([[to_numpy(filename), to_numpy('STE/SDF')]], dtype=object)
		self._saveprefs()

	def set_bands(self, vlf, lf, hf):
		self._loadprefs()
		self.data['Preferences']['KubiosHRV'][0,0]['Param'][0,0]['VLF_band'][0,0] = np.array(vlf)
		self.data['Preferences']['KubiosHRV'][0,0]['Param'][0,0]['LF_band'][0,0] = np.array(lf)
		self.data['Preferences']['KubiosHRV'][0,0]['Param'][0,0]['HF_band'][0,0] = np.array(hf)
		self._saveprefs()

	def set_detrending(self, method, smoothing):
		if method.lower() in ['none', '1st order', '2nd order']:
			method == method.lower()
			smoothing = []
		else:
			method = 'Smoothn priors'
			smoothing = float(smoothing)
		self._loadprefs()
		self.data['Preferences']['KubiosHRV'][0,0]['Param'][0,0]['Rm_trend'][0,0] = to_numpy(method)
		self.data['Preferences']['KubiosHRV'][0,0]['Param'][0,0]['alpha'][0,0] = smoothing
		self._saveprefs()

	def set_deartifacting(self, level, threshold=None):
		level = level.lower().replace(' ', '').replace('(', '').replace(')', '').replace('threshold', '').replace('correction', '').strip()
		input_levels =  ['none', 'automatic', 'verylow', 'low', 'medium', 'strong', 'verystrong', 'custom']
		output_levels = ['none', 'Automatic correction', 'Threshold (very low)', 'Threshold (low)', 'Threshold (medium)', 'Threshold (strong)', 'Threshold (very strong)', 'Threshold (custom)']
		set_level = output_levels[input_levels.index(level)]

		self._loadprefs()
		self.data['Preferences']['KubiosHRV'][0,0]['Param'][0,0]['BeatCorrection_method'][0,0] = to_numpy(set_level)
		if set_level == 'Threshold (custom)':
			self.data['Preferences']['KubiosHRV'][0,0]['Param'][0,0]['BeatCorrection_custom_level'][0,0] = to_numpy(str(float(threshold)))
		self._saveprefs()

	def set_denoising(self, level):
		level = level.lower().strip()
		levels = ['none', 'very low', 'low', 'medium', 'strong']
		
		lvl_num = levels.index(level)+1
		self._loadprefs()
		self.data['Preferences']['KubiosHRV'][0,0]['Param'][0,0]['QualitySensitivityLevel'][0,0] = to_numpy(lvl_num)
		self._saveprefs()
