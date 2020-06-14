import os
import time
from datetime import datetime
from PyQt5 import QtCore
from Driver.STM_Interface import STM_Interface
from Driver.IO_Plots import IO_Plots
from Driver.FSM import State, Transition, FSM
from Driver.Actions import List_Actions, Action
from Driver.Conditions import Condition, Condition_Empty, Cond_SA_Ready, Cond_SA_Operation, Cond_UniqueTransition, Cond_SingleOp, Cond_CheckEndDriftAnalysis, Cond_CheckFinishedTransfer, Cond_CheckInterrupt
from Driver.Drift_Analysis import Drift_Analysis

class ListControllers(object):
	def __init__(self):
		self.Controllers = {}

	def addController(self, controller):
		self.Controllers[controller.name] = controller

	def isBusy(self):
		for i in self.Controllers.keys():
			if self.Controllers[i].ControllerBusy == True:
				return True
		return False
		
	def FinishAllActions(self):
		# To be done
		pass

class Controller(object):
	def __init__(self, name, Interface, Timeout=10):

		#########################################
		# EACH CONTROLLER INCLUDES AT LEAST:	#
		# - A list of actions			#
		# - An FSM with:			#
		# 	-> States [Action + Condition]	#
		#	-> Transition [Action]		#
		# - A timer that ticks the FSM		#
		# - A pointer to the STM Interface	#
		#########################################
		self.name = name
		self.FSM = FSM(self)
		self.Plots = IO_Plots()
		self.Timer = QtCore.QTimer()
		self.Timer.timeout.connect(self.FSM.Execute)
		self.Timeout = Timeout
		self.Interface = Interface	

		#########################
		# Actions Definitions	#
		#########################
		self.Actions = List_Actions(self)
		self.Actions.Create_Action("STM", "Frame", 	"RequestFrame", 		6)
		self.Actions.Create_Action("STM", "Frame", 	"CharactCurves", 		7)
		self.Actions.Create_Action("STM", "Frame", 	"CalibArray", 			8)
		self.Actions.Create_Action("STM", "Frame", 	"LAMP", 			10)
		self.Actions.Create_Action("STM", "RefTemp", 	"PCR", 				11)
		self.Actions.Create_Action("STM", "RefTemp", 	"TempControl", 			12, 95.0)
		self.Actions.Create_Action("STM", "Frame", 	"TempCharact", 			13)
		self.Actions.Create_Action("STM", "RefTemp", 	"TempRefMeas", 			14)
		self.Actions.Create_Action("STM", "Pixel", 	"TempNoise", 			15)
		self.Actions.Create_Action("STM", "RefTemp", 	"TempCoilCharact", 		16)
		self.Actions.Create_Action("STM", "RefTemp", 	"TempCoilDynamics", 		17)
		self.Actions.Create_Action("STM", "Frame", 	"WaveGen", 			18)
		self.Actions.Create_Action("STM", "Pixel", 	"ChemNoise", 			19)
		self.Actions.Create_Action("STM", "Frame", 	"MultipleFrames", 		20, 10.0)
		self.Actions.Create_Action("STM", "Frame", 	"SampleFor10Minutes", 		21, 10.0)
		self.Actions.Create_Action("STM", "Frame", 	"SampleFor2Minutes", 		21, 2.0)
		self.Actions.Create_Action("STM", "Frame", 	"ExtractDACSensitivity", 	22)
		self.Actions.Create_Action("STM", "Calib", 	"UpdateCalib", 			23)
		self.Actions.Create_Action("STM", "DACSens", 	"UpdateDACSens", 		24)
		self.Actions.Create_Action("STM", "Frame", 	"CompensateAndSample", 		25)
		self.Actions.Create_Action("STM", "Pixel", 	"CharactCurve_Pixel",		26)
		self.Actions.Create_EmptyAction()

		self.ControllerBusy = False
		self.InterruptEnable = False
		self.InterruptAction = None
		self.InterruptReady = False

	#########################################################
	# Launch Controller - Define plots + Start FSM Timer	#
	#########################################################
	def LaunchController(self, cargo, Plot_3D, Plot_2D, Text = None):
		self.ControllerBusy = True
		self.Timer.start(self.Timeout)
		self.DefinePlots(Plot_3D, Plot_2D)
		self.ClearPlots()
		if Text != None:
			self.DefineTextBox(Text)

	######################################################
	# Stop Controller - Reset variables + Stop FSM Timer #
	######################################################
	def StopController(self):
		self.Timer.stop()
		self.ControllerBusy = False
		self.Actions.ClearAllData()
		self.Interface.ResetFrameMessage()

	###########################
	# Define plotting objects #
	###########################
	def DefinePlots(self, Plot_3D, Plot_2D):
		self.Plots.SetupPlots(Plot_3D, Plot_2D)

	def DefineTextBox(self, Text):
		self.Plots.SetupText(Text)

	def EnableInterrupt(self, Action):
		self.InterruptEnable = True

	def DisableInterrupt(self):
		self.InterruptEnable = False

	def DataTransferBetweenStates(self, StateName_Sender, StateName_Receiver):
		self.FSM.states[StateName_Receiver].Action.action_data = self.FSM.states[StateName_Sender].Action.action_data	

	def ClearDataAndPlots(self):
		self.Plots.ClearAllPlots()
		self.Actions.ClearAllData()

	def ClearPlots(self):
		self.Plots.ClearAllPlots()

class debug_Controller(Controller):
	def __init__(self, name, Interface, Timeout=10):

		self.SavePath = "../../instantDNA_Results/Debug"
		if not os.path.exists(self.SavePath):
			os.makedirs(self.SavePath)
		super(debug_Controller, self).__init__(name,Interface,Timeout)

		self.FSM.AddState("Ready", 			"EmptyAction", 		Cond_SA_Ready())
		self.FSM.AddState("Single_RequestFrame",	"RequestFrame", 	Cond_SA_Operation())
		self.FSM.AddState("Single_CharactCurves",	"CharactCurves", 	Cond_SA_Operation())
		self.FSM.AddState("Single_CalibArray", 		"CalibArray", 		Cond_SA_Operation())
		self.FSM.AddState("Single_LAMP", 		"LAMP", 		Cond_SA_Operation())
		self.FSM.AddState("Single_PCR", 		"PCR", 			Cond_SA_Operation())
		self.FSM.AddState("Single_TempControl", 	"TempControl", 		Cond_SA_Operation())
		self.FSM.AddState("Single_TempCharact", 	"TempCharact", 		Cond_SA_Operation())
		self.FSM.AddState("Single_ObtainRefTemp",	"TempRefMeas", 		Cond_SA_Operation())
		self.FSM.AddState("Single_TempNoise", 		"TempNoise", 		Cond_SA_Operation())
		self.FSM.AddState("Single_TempCoilCharact", 	"TempCoilCharact", 	Cond_SA_Operation())
		self.FSM.AddState("Single_TempCoilDynamics", 	"TempCoilDynamics", 	Cond_SA_Operation())
		self.FSM.AddState("Single_WaveGen", 		"WaveGen", 		Cond_SA_Operation())
		self.FSM.AddState("Single_ChemNoise", 		"ChemNoise", 		Cond_SA_Operation())
		self.FSM.AddState("Single_MultipleFrames", 	"MultipleFrames", 	Cond_SA_Operation())
		self.FSM.AddState("Single_SampleFor10Minutes", 	"SampleFor10Minutes", 	Cond_SA_Operation())	
		self.FSM.AddState("Single_UpdateCalib", 	"UpdateCalib", 		Cond_SA_Operation())
		self.FSM.AddState("Single_CharactCurvePixel",	"CharactCurve_Pixel", 	Cond_SA_Operation())
		self.FSM.AddState("Done", 			"EmptyAction", 		Condition_Empty())
		self.FSM.SetState("Done")
		
		self.FSM.AddTransition("toRequestFrame",	Transition("Single_RequestFrame",self.ClearPlots))
		self.FSM.AddTransition("toCharactCurves",	Transition("Single_CharactCurves",self.ClearPlots))
		self.FSM.AddTransition("toCalibArray",		Transition("Single_CalibArray",self.ClearPlots))
		self.FSM.AddTransition("toLAMP",		Transition("Single_LAMP",self.ClearPlots))
		self.FSM.AddTransition("toPCR",			Transition("Single_PCR",self.ClearPlots))
		self.FSM.AddTransition("toTempControl",		Transition("Single_TempControl",self.ClearPlots))
		self.FSM.AddTransition("toTempCharact",		Transition("Single_TempCharact",self.ClearPlots))
		self.FSM.AddTransition("toObtainRefTemp",	Transition("Single_ObtainRefTemp",self.ClearPlots))
		self.FSM.AddTransition("toTempNoise",		Transition("Single_TempNoise",self.ClearPlots))
		self.FSM.AddTransition("toTempCoilCharact",	Transition("Single_TempCoilCharact",self.ClearPlots))
		self.FSM.AddTransition("toTempCoilDynamics",	Transition("Single_TempCoilDynamics",self.ClearPlots))
		self.FSM.AddTransition("toWaveGen",		Transition("Single_WaveGen",self.ClearPlots))
		self.FSM.AddTransition("toChemNoise",		Transition("Single_ChemNoise",self.ClearPlots))
		self.FSM.AddTransition("toMultipleFrames",	Transition("Single_MultipleFrames",self.ClearPlots))
		self.FSM.AddTransition("toSampleFor10Minutes",	Transition("Single_SampleFor10Minutes",self.ClearPlots))
		self.FSM.AddTransition("toUpdateCalib",		Transition("Single_UpdateCalib",self.ClearPlots))
		self.FSM.AddTransition("toCharactCurvePixel",	Transition("Single_CharactCurvePixel",self.ClearPlots))
		self.FSM.AddTransition("toDone",		Transition("Done",self.StopController))		

	def LaunchController(self, cargo, Plot_3D, Plot_2D, Text = None):
		self.StartTime = datetime.now()
		self.SavePath = "../../instantDNA_Results/Debug/" + self.StartTime.strftime("%Y-%d-%b_%H-%M-%S")
		if not os.path.exists(self.SavePath):
			os.makedirs(self.SavePath)

		self.FSM.SetSavePath(self.SavePath)
		self.FSM.SetCargo(cargo)
		self.FSM.SetState("Ready")
		super(debug_Controller, self).LaunchController(cargo, Plot_3D, Plot_2D, Text = None)

class DriftAnalysis_Controller(Controller):
	def __init__(self, name, Interface, Timeout=10):
		
		self.SavePath = "../../instantDNA_Results/Drift"
		if not os.path.exists(self.SavePath):
			os.makedirs(self.SavePath)
		super(DriftAnalysis_Controller, self).__init__(name,Interface,Timeout)

		## FUNCTIONS SPECIALISED FOR DRIFT ANALYSIS ##
		self.DriftAnalysis = Drift_Analysis(self)

		## ADDITIONAL ACTIONS FOR RPi PROCESSING ##
		self.Actions.Create_Action("RPi", "Drift_Start",	"StartDrift",		0, 0)
		self.Actions.Create_Action("RPi", "Drift_Analysis", 	"AnalyseTrend", 	0, 0)
		self.Actions.Create_Action("RPi", "Drift_DACSens", 	"CalculateDACSens", 	0, 0)
		#self.Actions.Create_Action("RPi", "Drift_DriftTrend", 	"CalculateDriftTrend", 	0, 0)
		#self.Actions.Create_Action("RPi", "Drift_CalibUpdate", 	"CalculateNewCalib", 	0, 0)

		## STATES ##
		self.FSM.AddState("Ready",			"EmptyAction", 		Cond_SingleOp("InitialCalibration"))
		self.FSM.AddState("InitialCalibration", 	"CalibArray", 		Cond_UniqueTransition("StartDriftAnalysis"))
		#self.FSM.AddState("FindDACSens", 		"ExtractDACSensitivity",Cond_UniqueTransition("CalcDACSens"))
		#self.FSM.AddState("CalcDACSens", 		"CalculateDACSens", 	Cond_SingleOp("SendDACSens"))
		#self.FSM.AddState("SendDACSens", 		"UpdateDACSens", 	Cond_UniqueTransition("StartDriftAnalysis"))
		self.FSM.AddState("StartDriftAnalysis",		"StartDrift",		Cond_SingleOp("StartCompensateAndSample"))
		self.FSM.AddState("StartCompensateAndSample", 	"CompensateAndSample", 	Cond_SingleOp("ExtractSample"), 			"OnlyEnter")
		self.FSM.AddState("ExtractSample", 		"CompensateAndSample", 	Cond_CheckInterrupt("AnalyseSample"), 			"OnlyExecute")
		self.FSM.AddState("AnalyseSample", 		"AnalyseTrend", 	Cond_CheckEndDriftAnalysis("ExtractSample", "EndSample"))
		self.FSM.AddState("EndSample", 			"CompensateAndSample", 	Cond_CheckInterrupt("Done"), 				"OnlyExecute")
		self.FSM.AddState("Done", 			"EmptyAction", 		Condition_Empty())
		self.FSM.SetState("Done")

		## TRANSITIONS ##
		self.FSM.AddTransition("toInitialCalibration",		Transition("InitialCalibration",self.ClearPlots))
		self.FSM.AddTransition("toFindDACSens",			Transition("FindDACSens",self.ClearPlots))
		self.FSM.AddTransition("toCalcDACSens",			Transition("CalcDACSens",self.ClearPlots))
		self.FSM.AddTransition("toSendDACSens",			Transition("SendDACSens",self.ClearPlots))
		self.FSM.AddTransition("toStartDriftAnalysis",		Transition("StartDriftAnalysis",self.ClearPlots))
		self.FSM.AddTransition("toStartCompensateAndSample",	Transition("StartCompensateAndSample",self.ClearPlots))
		self.FSM.AddTransition("toExtractSample",		Transition("ExtractSample",None))
		self.FSM.AddTransition("toAnalyseSample",		Transition("AnalyseSample",None))
		self.FSM.AddTransition("toEndSample",			Transition("EndSample",None))
		self.FSM.AddTransition("toDone",			Transition("Done",self.StopController))		

	def LaunchController(self, cargo, Plot_3D, Plot_2D, Text = None):
		self.StartTime = datetime.now()
		self.SavePath = "../../instantDNA_Results/Drift/" + self.StartTime.strftime("%Y-%d-%b_%H-%M-%S")
		if not os.path.exists(self.SavePath):
			os.makedirs(self.SavePath)

		self.FSM.SetSavePath(self.SavePath)
		self.FSM.SetCargo(cargo)
		self.FSM.SetState("Ready")

		super(DriftAnalysis_Controller, self).LaunchController(cargo, Plot_3D, Plot_2D, Text = None)
