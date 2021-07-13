#This is the python code to interface specman to an agilent 6675A power supply connected to a prologix USB-GPIB converter via the TCP device in Specman

#Readme
# To use this program with specman
# 1. Make sure that the IP address of the server matches the one in the specman cfg file (should be @ port 1235)-- this is different from the prologix IP address
# 2. Make sure the prologix adapter IP address is correct (in this script). You can find the IP address by using the netfinder.exe program if the adapter is connected. Port should always be 1234
# 3. Run this script before activating the 6675A device in specman device configuration, also make sure that the console reads 'ready to accept TCP connection from Specman' before activating the device-- this will take ~30 seconds or more.
# 4. After the server (this script) is ready, reload the configuration file (need to do this or it wont work) and activate the device on specman and it should be green-- now it is ready to be used
# 5. Sometime this script throws an error when you try to start it-- this is most likely because the prologix adapter was not yet ready-- try to start it again and it should work
# 6. When the current is on the X axis in specman, the variable needs to be reloaded every time the device is restarted








import socket
import struct
import serial
import io
import time
import numpy as np
import matplotlib.pyplot as plt
import timeit
import sys


#-----------------------------------------------------------------------------------------------------------------------------------------------
def connect_ps():
    print('connecting to power supply')
                                                                                                    # Function to connect to power supply over TCP/GPIB Prologix adapter
    time.sleep(1)                                                                                   # Port to listen on (needs to be 1234 for prologix GPIB-Ethernet connector)
    s = serial.Serial('COM6', timeout =1)
    time.sleep(1)
    s.write(b"++auto 1\r\n"); time.sleep(0.3)                                                        # Set the prologix controller to read after write
    s.write(b"++addr 5\r\n"); time.sleep(0.3)                                                        # Set the GPIB address to 5 (default for 66753A power supply)
    s.write(b"++eoi 1\r\n"); time.sleep(0.3)                                                         # Set the end of interrupt signal to be set after every command
    s.write(b"++eos 3\r\n"); time.sleep(0.3)                                                         # Tell Prologix controller to not add /r or /n after every command (this script does it manually)
    s.write(b"*CLS\r\n"); time.sleep(0.3)                                                              # Clear buffer of 66753A
    print(s)
    return s
#-----------------------------------------------------------------------------------------------------------------------------------------------
def change_relay(s,state,pol):
    time.sleep(1)
                                                                                                    # Function for changing the state of the relay
#     print('changing relay')                                                                         # First we measure the state of the relay (not needed for current functionality)
#     time.sleep(1)
#     s.write(b'OUTP:REL?\n'); time.sleep(0.1)
#     current_state = s.read(16)
    
#     s.write(b'OUTP:REL:POL?\n'); time.sleep(0.1)
#     current_pol = s.read(16)
#     print('done reading relay')
                                                                                                    # Here we set the relay to on or off (1 or 0)
    if state == 1:
        s.write(b'OUTP:REL 1\n')
        print('relay turned on')
    elif state == 0:
        s.write(b'OUTP:REL 0\n')
        print('relay turned off')
                                                                                                    # Here we set the polarity of the relay (normal or reverse)
    if pol == 'NORM':
        s.write(b'OUTP:REL:POL NORM\n')
        print('polarity turned to normal')
    elif pol == 'REV':
        s.write(b'OUTP:REL:POL REV\n')
        print('polarity turned to reverse')
        
    print('done with relay change')
#-----------------------------------------------------------------------------------------------------------------------------------------------
def ramp_current(s,i,cout,pol):
                                                                                                        # Function for ramping the current slowly on the power supply
    print('ramping current')
    time.sleep(1)
    if np.abs(i-cout) > 0.05:
        print('step too large, need to ramp current')
        print('set current: ' + str(i))
        print('starting current: ' + str(pol*cout))
        if i > cout:
            cramp = np.arange(cout,i,.05)
        elif i < cout:
            cramp = np.arange(i,cout,.05); cramp = cramp[::-1]
        np.append(cramp, i)
        for c_ in cramp:
            time.sleep(2)
            s.readline()
            s.write(b"MEAS:CURR?\n")
            cout_ = s.readline()
            cout_ = cout_.decode('utf-8')
            cout_ =cout_.rstrip()
            cout_ = float(cout_)
            s.readline()
            s.write(b"CURRENT:LEVEL:IMMEDIATE:AMPLITUDE %s\n" % bytes(str(c_),'utf-8'))
            time.sleep(0.1)
            print('intermediate current: '+str(pol*cout_))
    else:
        print('Current values too close')
        s.readline()
        s.write(b"CURRENT:LEVEL:IMMEDIATE:AMPLITUDE %s A\n" % bytes(str(i),'utf-8'))
    time.sleep(1)
    s.readline()
    s.write(b"CURRENT:LEVEL:IMMEDIATE:AMPLITUDE %s\n" % bytes(str(i),'utf-8'))
    print('done ramping current')
#-----------------------------------------------------------------------------------------------------------------------------------------------          
def change_field(i):
    time.sleep(1)
    print('trying to change current to %s A' % str(i))
                                                                                                        # accept input (from specman) and then ramp the current from the present value to inputted value (change current by 0.05A every ~2 second)
    s = connect_ps()
    s.write(b"OUTP 1\r\n"); time.sleep(0.1); s.readline()
    s.write(b"OUTP?\r\n"); time.sleep(0.1); s.readline()
               
    s.readline()                                                                                                    # Measure Polarity of Relay           
    s.write(b'OUTP:REL:POL?\r\n'); time.sleep(0.1)
    current_pol = s.readline()
    
    s.readline()                                                                                                    # Measure Initial Current and give sign (neg or pos) based on polarity of relay
    s.write(b"MEAS:CURR?\n")
    cout = s.readline()
    cout = cout.decode('utf-8')
    cout =cout.rstrip()
    if current_pol == b'NORM\n':
            cout = float(cout)
            pol = 1
    if current_pol == b'REV\n':
            cout = -float(cout)
            pol = -1
        
                                                                                                        # If the desired polarity and current polarity are the same, simply ramp the current          
    if (i > 0 and pol==1) or (i < 0 and pol==-1):      
        ramp_current(s,np.abs(i),np.abs(cout),pol)
     
                                                                                                        # If the desired polarity and current polarity are different, ramp the current to 0, change polarity, then ramp to desired current
    elif (i < 0 and pol==1):
        ramp_current(s,0,np.abs(cout),pol)
        change_relay(s,1,'REV')
        pol = -1
        ramp_current(s,np.abs(i),0,pol)
        
    elif (i > 0 and pol==-1):
        ramp_current(s,0,np.abs(cout),pol)
        change_relay(s,1,'NORM')
        pol = 1
        ramp_current(s,np.abs(i),0,pol)

    elif (i == 0):
        ramp_current(s,0,np.abs(cout),pol)
        change_relay(s,1,'NORM')
        pol = 1    
        
    s.readline()                                                                                                         # Measure Polarity of Relay           
    s.write(b'OUTP:REL:POL?\n'); time.sleep(5)
    current_pol = s.readline()
               
    s.readline()                                                                                                    # Measure Initial Current and give sign (neg or pos) based on polarity of relay
    s.write(b"MEAS:CURR?\n")
    cout = s.readline()
    cout = cout.decode('utf-8')
    cout =cout.rstrip()
    if current_pol == b'NORM\n':
            cout = float(cout)
    if current_pol == b'REV\n':
            cout = -float(cout)
    s.close()
    
    print('current = '+str(cout))
    return cout
#-----------------------------------------------------------------------------------------------------------------------------------------------
def zero_field():
    time.sleep(1)
    print('trying to zero field')
                                                                                                        #Zero the field by ramping the current to 0; also put the power supply in CC mode by setting voltage to higher than needed for current draw
                                                                                                        #Also turn on the relay and set it to normal polarity            
    s = connect_ps()    
                                                                                                        # Determine if  power supply output in on, and measure current
    s.write(b"OUTP?\r\n"); time.sleep(0.3)
    outp = s.readline()
    outp = outp.decode('utf-8')
    outp = outp.rstrip()
    outp = int(outp)
    if outp == 0:
        print('output is off')
    else:
        print('output is on')
                                                                                          # If the output is on, ramp current down to 0 slowly, else just set current to 0.
    if outp == 1:
        s.readline()
        s.write(b"MEAS:CURR?\r\n"); time.sleep(0.3)
        cout = s.readline()
        print(cout)
        cout = cout.decode('utf-8')
        cout =cout.rstrip()
        cout = float(cout)
        ramp_current(s,0,cout,1)
    else:
        s.write(b"CURRENT:LEVEL:IMMEDIATE:AMPLITUDE %s A\n" % bytes(str(0),'utf-8'))
        
                                                                                                        # Set Current to 0 and then turn off output
    time.sleep(1)
    s.write(b"CURRENT:LEVEL:IMMEDIATE:AMPLITUDE %s A\n" % bytes(str(0),'utf-8'))
    time.sleep(1)
    s.write(b"OUTP 0\n")
    time.sleep(1)
    
                                                                                                        # Put power supply into CC mode by making voltage higher than is needed (5V) for current draw of 0
    s.write(b"VOLTAGE:LEVEL:IMMEDIATE:AMPLITUDE %s\n" % bytes(str(5),'utf-8'))
    time.sleep(1)
    s.write(b"CURRENT:LEVEL:IMMEDIATE:AMPLITUDE %s A\n" % bytes(str(0),'utf-8'))
    time.sleep(1)    
    s.write(b"OUTP 1\r\n")
    time.sleep(1)
               
                                                                                                       # Turn output back off, change voltage to higher than is needed for full current draw (100V)
    s.write(b"OUTP 0\n")
    time.sleep(1)
    s.write(b"VOLTAGE:LEVEL:IMMEDIATE:AMPLITUDE %s\n" % bytes(str(100),'utf-8'))
    time.sleep(1)
    s.write(b"MEAS:VOLT?\n")
    time.sleep(1)
    s.write(b"CURRENT:LEVEL:IMMEDIATE:AMPLITUDE %s A\n" % bytes(str(0),'utf-8'))
    time.sleep(1)    
    s.write(b"OUTP 1\n")
               
    change_relay(s,1,'NORM')                                                                            # Change relay  to on, and normal polarity
               
    s.close()
################################################################################################################################################################## 
                                                                                                        # Here is the server to connect to specman (echo server)
                                                                                                        # This server recieves a packet from specman corresponding to a current value, and then ramps the power supply to that value slowly
                                                                                                        # Zero the field at startup (of python script)
zero_field()  
previous_setpoint = 0.00
print('ready to accept TCP connection from Specman')
conn_count = 0                                                                                                     # Start server to listen for specman 
HOST = '128.111.114.151'                                                                                # Standard loopback interface address (localhost)
PORT = 1235                                                                                             # Port to listen on (non-privileged ports are > 1023)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print('Connected by', addr)
        while True:
            parnum = 1
            try:
                del(data)
            except:
                pass
            while parnum != 0:                                                                          # Need to respond to specman TCP client, but only for first starting up. Do not want to send data unless current is changed, otherwise specman will scan over x axis parameter without waitng for current
                data = conn.recv(16)                                                                                       # Try to read data from specman
                conn_count = conn_count + 1
                print(data)
                data_ = struct.unpack('2d',data)                                                        # this is reading the current data (data_[1])
                parnum = struct.unpack('4I',data)[0]                                                    # This is reading the parameter number (for future implementation of more parameters)
                if conn_count == 1:
                    conn.send(data)
                    print('data sent parnum ' + str(struct.unpack('4I',data)[0]))


                                                                                                        # when specman changes current value, ramp the present current value to the desired one

            current = change_field(data_[1])
                                                                                                    # Need to send a packet that has the structure: (parnumber + flag (0x40000000) + data value)
            data = struct.pack('1I',0)+struct.pack('1I',0x40000000)+struct.pack('1d',float(current))
            previous_setpoint = data_[1] 
            conn.send(data); print('data sent parnum ' + str(struct.unpack('4I',data)[0]))

#####################################################################

