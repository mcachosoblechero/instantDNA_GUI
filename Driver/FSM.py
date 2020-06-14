from Driver.IO_File import IO_File

###########################################

class Transition(object):
	def __init__(self,toState, Action):
		self.toState = toState 
		self.Action = Action
	
	def Execute(self):
		if self.Action != None:
			self.Action()
		#print("Transitioning to..." + self.toState)

class State(object):
	def __init__(self, FSM, stateName, Action, Condition):
		self.FSM = FSM
		self.Plots = FSM.control.Plots
		self.stateName = stateName
		self.Action = Action
		self.Condition = Condition
		self.IO_Handle = IO_File(FSM.control.SavePath, stateName)

	def Enter(self):
		print("State -> '" + self.stateName + "'")
		self.Action.Enter()
		self.IO_Handle.OpenFile()

	def Execute(self):
		self.Action.Execute(self.IO_Handle, self.Plots)
		self.Condition.Execute(self)
		
	def Exit(self):
		#print("State '" + self.stateName + "' finalised")
		self.Action.Exit()
		self.IO_Handle.CloseFile()

	def Reset(self):
		pass

#################################################
# SPECIAL CLASSES OF STATE		   	#
# State_OnlyEnter 	-> Only Enter & Exit	#
# State_OnlyExecute     -> Only Execute & Exit	#
#################################################
class State_OnlyEnter(State):
	def __init__(self, FSM, stateName, Action, Condition):
		super(State_OnlyEnter, self).__init__(FSM, stateName, Action, Condition)

	def Enter(self):
		super(State_OnlyEnter, self).Enter()
		
	def Execute(self):
		# No Action		
		self.Condition.Execute(self)

	def Exit(self):
		super(State_OnlyEnter, self).Exit()


class State_OnlyExecute(State):
	def __init__(self, FSM, stateName, Action, Condition):
		super(State_OnlyExecute, self).__init__(FSM, stateName, Action, Condition)

	def Enter(self):
		print("State -> '" + self.stateName + "'")
		# No Action - Only required 
		self.Action.ActionControl.EnableInterrupt(self)
		self.IO_Handle.OpenFile()
		
	def Execute(self):
		super(State_OnlyExecute, self).Execute()

	def Exit(self):
		super(State_OnlyExecute, self).Exit()


############################################

class FSM(object):
	def __init__(self,char):
		self.control = char
		self.states = {}
		self.transitions = {}
		self.curState = None
		self.prevState = None
		self.trans = None
		self.cargo = ""

	def AddTransition(self,transName,transition):
		self.transitions[transName] = transition

	def AddState(self,stateName,ActionName,Condition, StateType = ""):
		Action = self.control.Actions.Assing(ActionName)
		if StateType == "":
			self.states[stateName] = State(self, stateName,Action,Condition)
		elif StateType == "OnlyEnter":
			self.states[stateName] = State_OnlyEnter(self, stateName,Action,Condition)
		elif StateType == "OnlyExecute":
			self.states[stateName] = State_OnlyExecute(self, stateName,Action,Condition)

	def SetState(self, stateName):
		self.curState = self.states[stateName]

	def SetCargo(self, cargo):
		self.cargo = cargo

	def SetSavePath(self, Path):
		for key in self.states:
			self.states[key].IO_Handle.UpdatePath(Path) 

	def Transition(self, transName):
		self.trans = self.transitions[transName]

	def Execute(self):
		self.curState.Execute()
		if (self.trans):
			self.curState.Exit()
			self.trans.Execute()
			self.SetState(self.trans.toState)
			self.curState.Enter()
			self.trans = None
