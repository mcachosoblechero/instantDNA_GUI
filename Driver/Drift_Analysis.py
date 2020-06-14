import numpy as np
import numpy.polynomial.polynomial as poly

import pandas as pd
import time
import math
from datetime import datetime
from collections import deque

class Sinusoid:
	def __init__(self):
		self.fs = None
		self.counter = 0
	
	def fit(self):
		time.sleep(1)
		self.fs = 0.3 

	def predict(self):
		self.counter += 1
		return int(25*np.sin(self.fs*self.counter))

class polyApprox:
	def __init__(self, order=1):
		self.order=order
		self.coefs=None

	def fit(self, time, X):
		self.coefs = np.apply_along_axis(lambda x: poly.polyfit(time, x, self.order), axis=0, arr=X)

	def predict(self, time):
		return np.apply_along_axis(lambda x: poly.polyval(time, x), axis=0, arr=self.coefs)

class Drift_Analysis(object):
	def __init__(self, controller):

		# Drift Analysis constants
		self.NumPixels = 1024
		
		self.controller = controller
		self.linearRegresion = []

		self.BaselineCalib = None

		self.drift = polyApprox(order=1)

		self.ActiveAnalysis = 0
		
		###############################
		# FAKE PH REACTION PARAMETERS #
		###############################
		self.pHSens = 11.8e-3							# Reference Electrode pH Sensitivity
		self.TotalpHChange = 2.0						# Total pH change
		self.TotalRefChange = self.TotalpHChange * self.pHSens			# Total pH Change referred to the Ref Elect.
		self.TotalTimeChange = 1 						# Minutes - How long the reaction lasts
		self.StartTimeChange = 1						# Minutes - When reaction starts
		self.TotalTestTime = 10							# Minutes - When test finishes
		self.pHSlopeWithTime = self.TotalRefChange / self.TotalTimeChange	# pH Change per minute
		self.PrevSampleTime = 0							# Aux variable
		self.AccChange = 0							# Aux variable 
		self.NumSteps = 0							# Aux variable - Number of steps done so far
		self.IncreasepH = 1.0							# Aux variable - Direction of increase
		self.CurrentpH = 0.0							# Aux variable - Current pH State
		
	def ExtractSTMData(self, action):
		actionData = self.controller.Actions.Action[action].ActionData
		return actionData
	
	def CalculateDACSensitivity(self):
		######################################################
		############ CALCULATE DAC SENSITIVITY ###############
		######################################################	
		DACInfo = pd.read_csv(self.controller.SavePath+'/FindDACSens.csv', 
						 header=None).values[:, 1:self.NumPixels+1]
		DAC_Stable = DACInfo[:4,:]
		DAC_Plus10 = DACInfo[5:9,:]
		DAC_Minus10 = DACInfo[10:14,:]

		DAC_Stable = np.median(DAC_Stable, axis=0)
		DAC_Plus10 = np.median(DAC_Plus10, axis=0)
		DAC_Minus10 = np.median(DAC_Minus10, axis=0)

		self.DACSens = np.mean([10/abs(DAC_Plus10 - DAC_Stable), 10/abs(DAC_Minus10 - DAC_Stable)], axis=0)
		print(np.mean(self.DACSens))
		print(np.std(self.DACSens))
		self.controller.Interface.UpdateDACSens(self.DACSens)

	def CalculateDriftTrend(self):
		######################################################
		############ CALCULATE MODEL FOR DRIFT ###############
		######################################################		
		DriftInfo = pd.read_csv(self.controller.SavePath+'/InitialDriftSampling.csv', 
						 header=None).values[:, :self.NumPixels+1]

		DriftTime, DriftDC = DriftInfo[:, 0], DriftInfo[:, -self.NumPixels:]		
		DriftTime = DriftTime - DriftTime[0]
		DriftTime = DriftTime - DriftTime[-1]

		self.reference_time = datetime.now()

		self.drift.fit(DriftTime, DriftDC)
		self.BaselineCalib = pd.read_csv(self.controller.SavePath+'/InitialCalibration.csv', 
						 header=None).values[-1, -self.NumPixels:].astype(int)
		
	def dc_to_dac(self, dc):
		return self.DACSens*dc
		#return 100*dc/0.9

	def CalculateNewCalib(self):
		############################################################################
		############ CALCULATE NEW CALIBRATION VALUES BASED ON MODEL ###############
		############################################################################
		time = (datetime.now() - self.reference_time).total_seconds()

		dc_compensation = 0.5 - self.drift.predict(time)

		output = (self.dc_to_dac(dc_compensation).astype(int) + self.BaselineCalib).tolist()
		
		self.controller.Interface.UpdateCalib(output)

	def StartDriftAnalysis(self):
		self.StartTime = datetime.now()
		self.ActiveAnalysis = 1

	def FrameProcessing(self):
		##########################################
		# Extract test time and determine action #
		##########################################
		time = (datetime.now() - self.StartTime).total_seconds()/60
	
		#################################################
		# TEST 1 - Single pH change during certain time #
		#################################################
		# If time is during reaction - check time elapsed and change pH accordingly in steps of 0.001 V
		#if time > self.StartTimeChange and time < (self.StartTimeChange + self.TotalTimeChange):
		#	self.AccChange += (time - self.PrevSampleTime) * self.pHSlopeWithTime
		#
		#	if self.AccChange > 0.001:
		#		self.controller.Interface.SendIncreaseRefElect()
		#		self.AccChange -= 0.001
		#	else:
		#		self.controller.Interface.ResetFrameMessage()

		####################################################
		# TEST 2 - Multiple pH changes during certain time #
		####################################################
		if time > (self.StartTimeChange + self.TotalTimeChange*self.NumSteps):
			if self.IncreasepH == 1.0:
				self.controller.Interface.SendStepUpRefElect()
				self.CurrentpH += self.IncreasepH
				print("Increasing pH to " + str(self.CurrentpH))	
				if self.CurrentpH == 3.0:
					self.IncreasepH = -1.0

			elif self.IncreasepH == -1.0:
				self.controller.Interface.SendStepDownRefElect()
				self.CurrentpH += self.IncreasepH
				print("Decreasing pH to " + str(self.CurrentpH))
				if self.CurrentpH == -3.0:
					self.IncreasepH = 1.0
	
			self.NumSteps += 1

		else:
			self.controller.Interface.ResetFrameMessage()

		# If reached the end of the test - Send end message
		if time > self.TotalTestTime:
			self.ActiveAnalysis = 0
			self.PrevSampleTime = 0
			self.AccChange = 0
			self.NumSteps = 0
			self.IncreasepH = 1.0		
			self.CurrentpH = 0.0	
			self.controller.Interface.SendEndTestMessage()
		
		# Store time for next iteration
		self.PrevSampleTime = time

	def IsActive(self):
		return self.ActiveAnalysis
