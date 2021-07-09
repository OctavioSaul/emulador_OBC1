import smbus
import time
import math
from struct import pack, unpack

bus = smbus.SMBus(1)
time.sleep(1)

def sendData(slaveAddress, data):
   bus.write_i2c_block_data(slaveAddress, 0xFF,data)
def readData(slaveAddress,reg):
   bytes=bus.read_i2c_block_data(slaveAddress,reg,16)
   return bytes
def llenar_comando(cont,send_list):
   #tipo comando(4 para indicar que paquete de la imagen se pide)
   send_list[0]=4
   #llenar cero espacios vacios
   for i in range(4, 14):
      send_list[i]=0
   #numero paquete a pedir
   send_list[1]=(cont & (0xFF<<16))>>16
   send_list[2]=(cont & (0xFF<<8))>>8
   send_list[3]=(cont & (0xFF))
   send_list[14]=sum(send_list[:14])&0xFF
   #regresa el comando listo para enviar
   return send_list
#condicion termino whiles
valido=False
#checksum comandos recibidos
check_sum=0
#contador paquetes recibidos 
total=0
print("inicio")
#comando pedir foto a OBC2
send_list= [3] + [1]*13 + [16] 
sendData(0x03,send_list)
while valido== False:
   #leer tamano foto
   bytes=readData(0x03, 0xFF)
   time.sleep(0.01)
   #comprobar si es comando
   if bytes[0]==6:
      #si OBC 2 encontro la foto que pedi
      #1 es si, 0 es no
      if bytes[1]==1:
         #calcula checksum del comando recibido
         check_sum=sum(bytes[:15])&0xFF
         #si checksum es igual a 6
         if check_sum==6:
            check_sum=7
            print("se cambio el check sum a 07")
         #comprobar checksum
         if check_sum==bytes[15]:
            #convertir numero de paquetes
            total=math.ceil(((bytes[2]<<24)+(bytes[3]<<16)+(bytes[4]<<8)+(bytes[5]))/14)
            valido=True
         else:
            sendData(0x03,send_list)
valido=False
#contador paquetes
cont=0
#contador lectura 
lectura=0
#contador checksum incorrecto
mal_check=0
#no se reconocio comando
no_coman=0
print("total de paquetes: ", total)
#lista para almacenar los paquetes
image = [1]*(int(total)*14)
inicioT=time.time()
#pedir primer paquete
send_list=llenar_comando(cont,send_list)
sendData(0x03,send_list)
print("enviando paquetes...")
while valido== False:
   #leer paquete
   bytes=readData(0x03, 0xFF)
   lectura+=1
   #time.sleep(0.001)
   #es un comando?
   if bytes[0]==6:
      check_sum=sum(bytes[:15])&0xFF
      #si checksum es igual a 06
      if check_sum==6:
         check_sum=7
         #print("se cambio el check sum a 07")
      #check sum es correcto?
      if check_sum==bytes[15]:
              #print(cont)
         if cont>=total:
            valido=True
         else:
            for i in range(14):
               image[(cont*14)+i]=bytes[1+i]
            cont+=1
            send_list=llenar_comando(cont,send_list)
            sendData(0x03,send_list)
            #print(send_list)
      else:
         mal_check+=1
         sendData(0x03,send_list)
         print("check malo",send_list)
   else:
      no_coman+=1
      print(bytes)
finT=time.time()
print("fin: ",finT-inicioT)
print("lectura: ",lectura)
print("mal checksum: ",mal_check)
print("no se reconoce comando: ",no_coman)
f=open("image.jpg","wb")
Aarray=bytearray(image)
f.write(Aarray)
f.close()
print("FIN")
