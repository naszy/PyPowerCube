import time
import serial
import sys

from struct import *
from time import sleep

class opto_comm:
	def __init__(self, port = 'COM5', baud=1000000) :
		# configure the serial connections (the parameters differs on the device you are connecting to)
		self.ser = serial.Serial(
			port=port,
			baudrate=baud,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS,
			timeout=0
		)
		
		if self.ser.isOpen():
			print 'Opto is Alive'
		else :
			print 'Opto Port Error'
		
	def opto_read(self):
		sleep(0.5)
		buff = self.ser.read(100)
		
		bytes = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
		byte_str = ""
		header = 0
		for b in buff:
			b = unpack("B", b)
			b = b[0]
			
			if b == 170:
				header = 1
				
			if header == 1 and b == 7:
				header = 2
			if header == 2 and b == 8:
				header = 3
			if header == 3 and b == 16:
				header = 4
				i = 0
				continue
				
			if header == 4:
		
				byte_str += pack("B", b)
				bytes[i] = b
				i += 1
				if i == 17:
					header = 0
		print bytes
		
		print unpack(">h", byte_str[4:6])

class cube_comm :
	STX = 0x02
	ETX = 0x03
	buff = ''
	
	get_bin = lambda self, x, n: format(x, 'b').zfill(n)
	char = lambda self, x : str(unichr(x))
	
	def bit2int(self, bitlist) :
		out = 0
		for bit in bitlist:
			out = (out << 1) | bit
		return out
	
	def __init__(self, port = 'COM4', baud=57600) :
		# configure the serial connections (the parameters differs on the device you are connecting to)
		self.ser = serial.Serial(
			port=port,
			baudrate=baud,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS,
			timeout=0
		)
		
		if self.ser.isOpen():
			print 'Alive'
		else :
			print 'Error'
			
		self.cube_send(0x01, ['\x00'], 1)
		self.cube_send(0x02, ['\x00'], 1)
		self.cube_send(0x03, ['\x00'], 1)
	
	def cube_send(self, module_address, data, rw = 0) : 
		# rw: 0 - read
		#     1 - write
		M = self.get_bin(module_address,5)
		L = self.get_bin(len(data),4)
		TELID_H = [0, 0, 0, 0, int(not rw), int(rw), int(M[0]), int(M[1])]
		TELID_L = [int(M[2]), int(M[3]), int(M[4]), 0 , int(L[0]), int(L[1]), int(L[2]), int(L[3])]
		
			
		TELID_H = self.char(self.bit2int(TELID_H))
		TELID_L = self.char(self.bit2int(TELID_L))
		
		datasum = 0
		for d in data :
			#print ord(d)
			datasum += ord(d)
			
		BCC = ord(TELID_H) + ord(TELID_L) + datasum
		BCC = BCC + (BCC >> 8)
		# From the PowerCube manual: 
		# "The Block Check Character BCC is not checked due to compatibility reasons."
		BCC = 0x42
		
		send = [self.char(self.STX), TELID_H, TELID_L] + data + [self.char(BCC), self.char(self.ETX)]
		#print "data sent:"
		#print send
		#print "\r\n"
		
		self.ser.write(send)
		sleep(0.01) # 50 ms wait
		buff = self.ser.read(100)
		self.buff = self._decode(buff)
		
	def _decode(self, byte_str):	
		i = 0
		byte_str_new = ''
		next_step_off = False
		for b in byte_str:
			if next_step_off :
				next_step_off = False
				i+= 1
				continue
				
			if b == '\x10':
				x = unpack("B", byte_str[i+1])[0]-0x80
				byte_str_new += pack("B", x)
				next_step_off = True
				
			else:
				byte_str_new += b
			i += 1
			
		return byte_str_new
		
	def get_pos_data(self, xyz) :
		if xyz == 'x':
			cube_ID = 0x01
		elif xyz == 'y':
			cube_ID = 0x02
		elif xyz == 'z':
			cube_ID = 0x03
		else:
			print "nanana"
			return 
	
		# send request
		self.cube_send(cube_ID, ['\x0a', '\x3c'], 1)
		sleep(0.05) # 50 ms wait
		if len(self.buff) != 11 :
			return None
		else:
		
			NI, NI, NI, NI, NI, pos_data, NI, NI = unpack('<BBBBBfBB', self.buff)

			print xyz, ": ", pos_data
			return pos_data
	
		
	def wait_until_pos_reached(self, xyz, pos, epsilon = 0.01):
		while True:
			actual_position = plotter.get_pos_data(xyz)
			if actual_position > pos - epsilon  and \
			   actual_position < pos + epsilon :
			   break
				
		
	def _move_to(self, xyz, diff, vel, acc) :
	
		if xyz == 'x':
			cube_ID = 0x01
		elif xyz == 'y':
			cube_ID = 0x02
		elif xyz == 'z':
			cube_ID = 0x03
		else:
			print "nanana"
			return 
		
		command_ID = '\x0b' #SetMotion
		motion_ID = '\x04' #FRAMP_MODE
		#diff = -0.1 #float (32 bit)
		
		diff_byte = list(pack("!f", diff))
		vel_byte = list(pack("!f", vel))
		acc_byte = list(pack("!f", acc))

		data_vel = ['\x08', '\x4F'] + vel_byte[::-1]		
		data_acc = ['\x08', '\x50'] + acc_byte[::-1]
		data_diff = ['\x0b', '\x04'] + diff_byte[::-1]

		self.cube_send(cube_ID, data_vel, 1)
		self.cube_send(cube_ID, data_acc, 1)
		self.cube_send(cube_ID, data_diff, 1)
		
	def x_move_to(self, diff, vel, acc):

		if diff>-1 and diff<0:
			self._move_to('x', diff, vel, acc)
		else:
			print "x must be between -1 and 0"
	
	def y_move_to(self, diff, vel, acc):
	
		if diff>0 and diff<1:
			self._move_to('y', diff, vel, acc)
		else:
			print "x must be between 0 and 1"		
	
	def z_move_to(self, diff, vel, acc):
	
		if diff>0 and diff<0.2:
			self._move_to('z', diff, vel, acc)
		else:
			print "z must be between 0 and 0.2"
	

#diszk = opto_comm('COM5',1000000)

#while 1:
#	diszk.opto_read()

# csinaljuk!
plotter = cube_comm('COM4',57600)

## HANDLING ARGUMENTS
if len(sys.argv) == 2 and sys.argv[1] == "home":
	plotter.cube_send(3,['\x01'],rw = 1)
	plotter.cube_send(2,['\x01'],rw = 1)
	plotter.cube_send(1,['\x01'],rw = 1)
	print "Home..."

else:

	plotter.x_move_to(-0.1,0.05,0.05)
	print "Waiting for X..."
	plotter.wait_until_pos_reached('x', -0.1)

	plotter.y_move_to(0.2,0.05,0.05)
	print "Waiting for Y..."
	plotter.wait_until_pos_reached('y', 0.2)

	plotter.z_move_to(0.05,0.05,0.05)
	print "Waiting for Z..."
	plotter.wait_until_pos_reached('z', 0.05)
