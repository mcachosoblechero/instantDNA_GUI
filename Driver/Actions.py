##########################################################################################
class List_Actions(object):
	def __init__(self, Control):
		self.Action = {}
		self.Control = Control
	
	def Create_Action(self, ActionSource, ActionType, ActionName, ActionCode, parameter=1.0):
		self.Action[ActionName] = Action(ActionSource, ActionType, ActionName, ActionCode, self.Control, parameter)

	def Create_EmptyAction(self):
		self.Action["EmptyAction"] = EmptyAction()

	def Assing(self, ActionName):
		return self.Action[ActionName]

	def ClearAllData(self):
		for keys in self.Action:
			if self.Action[keys].ActionData != None:
				self.Action[keys].ActionData.Clear()

##########################################################################################
class Action(object):
	def __init__(self, ActionSource, ActionType, ActionName, ActionCode, Control, parameter = 0.0):
		self.ActionSource = ActionSource
		self.ActionType = ActionType
		self.ActionCode = ActionCode
		self.ActionName = ActionName
		self.ActionData = Action_Data(self)
		self.ActionParameter = parameter
		self.ActionControl = Control

		if self.ActionSource == "STM":
			if self.ActionType == "Frame":
				self.ActionHandler = self.ActionControl.Interface.ReceiveFrame
			elif self.ActionType == "Pixel":
				self.ActionHandler = self.ActionControl.Interface.ReceivePixel
			elif self.ActionType == "NoisePixel":
				self.ActionHandler = self.ActionControl.Interface.ReceiveNoisePixel
			elif self.ActionType == "RefTemp":
				self.ActionHandler = self.ActionControl.Interface.ReceiveRefTemp
			elif self.ActionType == "Calib":
				self.ActionHandler = self.ActionControl.Interface.SendCalib
			elif self.ActionType == "DACSens":
				self.ActionHandler = self.ActionControl.Interface.SendDACSens
	
		elif self.ActionSource == "RPi":
			if self.ActionType == "Drift_Start":
				self.ActionHandler = self.ActionControl.DriftAnalysis.StartDriftAnalysis
			elif self.ActionType == "Drift_Analysis":
				self.ActionHandler = self.ActionControl.DriftAnalysis.FrameProcessing
			elif self.ActionType == "Drift_DACSens":
				self.ActionHandler = self.ActionControl.DriftAnalysis.CalculateDACSensitivity
			elif self.ActionType == "Drift_DriftTrend":
				self.ActionHandler = self.ActionControl.DriftAnalysis.CalculateDriftTrend
			elif self.ActionType == "Drift_CalibUpdate":
				self.ActionHandler = self.ActionControl.DriftAnalysis.CalculateNewCalib


	def Enter(self):
		if self.ActionSource == "STM":
			self.ActionControl.Interface.sendMessage(self.ActionCode, self.ActionParameter)
			self.ActionControl.EnableInterrupt(self)

	def Execute(self, File, Plots):
		if self.ActionSource == "STM" and self.ActionControl.InterruptReady == True:
			self.ManageInterrupt(File, Plots)
		elif self.ActionSource == "RPi":
			self.ActionHandler()


	def Exit(self):
		self.ActionControl.DisableInterrupt()

	def ManageInterrupt(self, File, Plots):
		self.ActionControl.InterruptReady = False
		[DC, Freq, Calib, RefTemp, EoM] = self.ActionHandler()
		self.UpdateActionData(DC, Freq, Calib, RefTemp, EoM)
		if self.ActionData.EoM == 0:
			self.UpdatePlotsAndData(File, Plots)

	def UpdatePlotsAndData(self, File, Plots):
		if self.ActionType == "Frame":
			Plots.PlotFrame(self.ActionData.DC, self.ActionData.Av_DC)
			File.SaveData(self.ActionData)
		elif self.ActionType == "Pixel":
			Plots.PlotPixel(self.ActionData.Av_DC)
			File.SaveData(self.ActionData)
		elif self.ActionType == "NoisePixel":
			Plots.PlotPixel(self.ActionData.Av_DC)
			File.SaveData(self.ActionData)
		elif self.ActionType == "RefTemp":
			Plots.PlotPixel(self.ActionData.RefTemp)
			File.SaveData(self.ActionData)

	
	def UpdateActionData(self,DC, Freq, Calib, RefTemp, EoM):
		self.ActionData.NewData = 1
		self.ActionData.EoM = EoM		
		if self.ActionData.EoM == 0:
			if self.ActionType == "Frame":
				if DC != []:
					self.ActionData.DC = DC
					self.ActionData.Av_DC.append(sum(DC)/len(DC))
				if Freq != []:
					self.ActionData.Freq = Freq				
					self.ActionData.Av_Freq.append(sum(Freq)/len(Freq))
				if Calib != []:
					self.ActionData.Calib = Calib

			elif self.ActionType == "Pixel":
				if DC != []:
					self.ActionData.DC = DC
					self.ActionData.Av_DC.append(DC)
				if Freq != []:
					self.ActionData.Freq = Freq				
					self.ActionData.Av_Freq.append(Freq)
				if Calib != []:
					self.ActionData.Calib = Calib

			elif self.ActionType == "NoisePixel":
				if DC != []:
					self.ActionData.DC = DC
					self.ActionData.Av_DC.append(sum(DC)/len(DC))
				if Freq != []:
					self.ActionData.Freq = Freq				
					self.ActionData.Av_Freq.append(sum(Freq)/len(Freq))
				if Calib != []:
					self.ActionData.Calib = Calib
			

			elif self.ActionType == "RefTemp":
				if RefTemp != 0.0:
					self.ActionData.RefTemp.append(RefTemp)

class EmptyAction(Action):
	def __init__(self):
		self.ActionData = None

	def Enter(self):
		pass

	def Execute(self, File, Plots):
		pass

	def Exit(self):
		pass

##########################################################################################
class Action_Data(object):
	def __init__(self, Action):
		self.DC = []
		self.Freq = []
		self.Calib = []
		self.Av_DC = list()
		self.Av_Freq = list()
		self.RefTemp = list()
		self.data_type = Action.ActionType
		self.EoM = 0
		self.NewData = 0

	def Clear(self):
		self.DC = []
		self.Freq = []
		self.Calib = []
		self.Av_DC = list()
		self.Av_Freq = list()
		self.RefTemp = list()
		self.EoM = 0
		self.NewData = 0
