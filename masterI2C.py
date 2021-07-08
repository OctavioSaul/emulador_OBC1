import smbus
import time
import math
from struct import pack, unpack

bus = smbus.SMBus(1)
time.sleep(1)

def sendData(slaveAddress, data):
        #pasar a binario
        #intsOfData = list(map(ord, data))
    bus.write_i2c_block_data(slaveAddress, 0xFF,data)
def readData(slaveAddress,reg):
    bytes=bus.read_i2c_block_data(slaveAddress,reg,16)
    return bytes
def llenar_comando(cont,send_list):
    #tipo comando
    send_list[0]=4
    #llenar cero espacios vacios
    for i in range(4, 14):
      send_list[i]=0
    #numero paquete a pedir
    send_list[1]=(cont & (0xFF<<16))>>16
    send_list[2]=(cont & (0xFF<<8))>>8
    send_list[3]=(cont & (0xFF))
    send_list[14]=sum(send_list[:14])&0xFF
    return send_list
valido=False
check_sum=0
total=0
print("inicio")
#comando pedir foto a OBC2
send_list= [3] + [1]*13 + [16] 
sendData(0x03,send_list)
while valido== False:
   #leer tamano foto
   bytes=readData(0x03, 0xFF)
  # time.sleep(0.001)
  #comprobar si es comando
   if bytes[0]==6:
      #si encontro la foto
      if bytes[1]==1:
         check_sum=sum(bytes[:15])&0xFF
         #comprobar checksum
         if check_sum==bytes[15]:
            #convertir numero de paquetes
            total=math.ceil(((bytes[2]<<24)+(bytes[3]<<16)+(bytes[4]<<8)+(bytes[5]))/14)
            print("total de paquetes: ", total)
            valido=True
         else:
            sendData(0x03,send_list)
valido=False
cont=0
inicioT=time.time()
#pedir primer paquete
send_list=llenar_comando(cont,send_list)
sendData(0x03,send_list)
print("enviando paquetes...")
while valido== False:
   #leer paquete
   bytes=readData(0x03, 0xFF)
   #time.sleep(0.001)
   #es un comando?
   if bytes[0]==6:
      check_sum=sum(bytes[:15])&0xFF
      #check sum es correcto?
      if check_sum==bytes[15]:
         cont+=1
         if cont>=total:
            valido=True
         else:
            send_list=llenar_comando(cont,send_list)
            sendData(0x03,send_list)
      else:
         sendData(0x03,send_list)
finT=time.time()
print("fin: ",finT-inicioT)

