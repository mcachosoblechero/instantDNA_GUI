import pigpio
import struct
import time

class STM_Interface(object):
	def __init__(self):
		self.pi = pigpio.pi()
		self.spi_h = self.pi.spi_open(0, 5000000, 192) # Flag for SPI CH1&2 disable
		self.SamplingFreq = 84e6

		self.CalibFlag = False
		
		self.PrevDC = [0]*1024
		self.CalibValues = [1024]*1024
		self.DACSensValues = [0]*1024

		self.FrameMessage = [0x00, 0x00, 0x00,0x00]*3072

	def sendMessage(self, code, parameter):
		spi_message = [code] + list(bytearray(struct.pack("f",parameter)))
		(count, data) = self.pi.spi_xfer(self.spi_h, spi_message)

	def ReceiveFrame(self):
		(count,data) = self.pi.spi_xfer(self.spi_h, self.FrameMessage)
		data = struct.unpack("<" + ("f"*3072),data)
		#print(data)

		# Check if message is EoM
		# If EoM -> EoM = 1, empty the rest
		if data[0]==2863311616.0 or data[1]==2863311616.0:
			EoM = 1
			DC = []
			Freq = []
			Calib = []
			RefTemp = 0.0

		# If not EoM -> Process
		else:
			EoM = 0
			DC = list(data[:2048:2])
			Freq = list(data[1:2048:2])
			Calib = list(data[2048::1])
			RefTemp = 0.0
			for i in range(0,1023):
				if (DC[i] > 1) or (DC[i] < 0):
					print("Error in Pixel " + str(i) + " - DC Received " + str(DC[i]) + " - Substituted by " + str(self.PrevDC[i]))
					DC[i] = self.PrevDC[i]
			self.PrevDC = DC

		return [DC, Freq, Calib, RefTemp, EoM]


	def ReceivePixel(self):
		(count,data) = self.pi.spi_xfer(self.spi_h, [0x00, 0x00, 0x00,0x00]*2)
		data = struct.unpack("<" + ("f"*2),data)

		if data[0]==2863311616.0 or data[1]==2863311616.0:
			EoM = 1
			DC = []
			Freq = []
			Calib = []
			RefTemp = 0.0
		else:
			EoM = 0
			DC = data[0]
			Freq = data[1]
			Calib = []
			RefTemp = 0.0
			if (DC > 1) or (DC < 0):
				print("Error in Pixel - DC Received " + str(DC) + " - Substituted by " + str(self.PrevDC))
				DC = self.PrevDC
			self.PrevDC = DC

		return [DC, Freq, Calib, RefTemp, EoM]

	def ReceiveNoisePixel(self):
		(count,data) = self.pi.spi_xfer(self.spi_h, [0x00, 0x00, 0x00,0x00]*4)
		data = struct.unpack("<" + ("f"*4),data)
		#print(data)

		if data[0]==2863311616.0 or data[1]==2863311616.0:
			EoM = 1
			DC = []
			Freq = []
			Calib = []
			RefTemp = 0.0
		else:
			EoM = 0
			DC = list(data[:4:2])
			Freq = list(data[1:4:2])
			Calib = []
			RefTemp = 0.0
			for i in [0, 1]:
				if (DC[i] > 1) or (DC[i] < 0):
					print("Error in Pixel " + str(i) + " - DC Received " + str(DC[i]) + " - Substituted by " + str(self.PrevDC[i]))
					DC[i] = self.PrevDC[i]
			self.PrevDC = DC

		return [DC, Freq, Calib, RefTemp, EoM]

	def ReceiveRefTemp(self):
		(count,data) = self.pi.spi_xfer(self.spi_h, [0x00, 0x00, 0x00,0x00]*1)
		data = struct.unpack("<" + ("f"*1),data)

		# Check if message is EoM
		# If EoM -> EoM = 1, empty the rest
		if data[0] == -50.0:
			EoM = 1
			DC = []
			Freq = []
			Calib = []
			RefTemp = 0.0
			
		# If not EoM -> Process
		else:
			EoM = 0
			DC = []
			Freq = []
			Calib = []
			RefTemp = data[0]
			print("Ref Temp -> " + str(RefTemp))
		
		return [DC, Freq, Calib, RefTemp, EoM]

	def SendCalib(self):
		spi_message = list(bytearray(struct.pack("l"*1024,*self.CalibValues)))
		(count, data) = self.pi.spi_xfer(self.spi_h, spi_message)
		return [[], [], [], 0, 1]

	def SendDACSens(self):
		spi_message = list(bytearray(struct.pack("f"*1024,*self.DACSensValues)))
		(count, data) = self.pi.spi_xfer(self.spi_h, spi_message)
		return [[], [], [], 0, 1]

	def UpdateFrameMessage(self, newFrame):
		self.FrameMessage = newFrame

	def ResetFrameMessage(self):
		self.UpdateFrameMessage([0x00, 0x00, 0x00,0x00]*3072)

	def SendEndTestMessage(self):
		self.UpdateFrameMessage([0x00, 0x00, 0x80, 0xBF]*3072)

	def SendIncreaseRefElect(self):
		self.UpdateFrameMessage([0x00, 0x00, 0x00, 0xC0]*3072)

	def SendStepUpRefElect(self):
		self.UpdateFrameMessage([0x00, 0x00, 0x40, 0xC0]*3072)

	def SendStepDownRefElect(self):
		self.UpdateFrameMessage([0x00, 0x00, 0x80, 0xC0]*3072)

	def UpdateCalib(self, newCalib):
		self.CalibValues = newCalib

	def UpdateDACSens(self, newDACSens):
		self.DACSensValues = newDACSens

	def close(self):
		self.pi.spi_close(self.spi_h)
		self.pi.stop()
	#############################################################

