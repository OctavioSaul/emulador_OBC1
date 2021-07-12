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
   for i in range(4, 13):
      send_list[i]=0
   #numero paquete a pedir
   send_list[1]=(cont & (0xFF<<16))>>16
   send_list[2]=(cont & (0xFF<<8))>>8
   send_list[3]=(cont & (0xFF))
   send_list[13]=sum(send_list[:13])&0xFF
   #regresa el comando listo para enviar
   return send_list

def pedir_foto():
   #condicion termino whiles
   valido=False
   #checksum comandos recibidos
   check_sum=0
   #contador paquetes recibidos 
   total=0
   print("inicio")
   #comando pedir foto a OBC2
   send_list= [3] + [1]*12 + [15] 
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
               #print("se cambio el check sum a 07")
            #comprobar checksum
            if check_sum==bytes[15]:
               #convertir numero de paquetes
               total=math.ceil(((bytes[2]<<24)+(bytes[3]<<16)+(bytes[4]<<8)+(bytes[5]))/14)
               return total
            else:
               sendData(0x03,send_list)
            
class Stepper:
   def __init__(self, img_size):
      self.img_size = img_size
      self.cont = 0 #contador paquetes
      self.lectura = 0 #contador lectura 
      self.mal_check = 0 #contador checksum incorrecto
      self.no_cmd = 0 #no se reconocio comando
      self.image = [1]*(int(img_size)*14) #lista para almacenar los paquetes
      self.send_list = [0 for i in range(14)]
      print("total de paquetes: ", img_size)

   def next(self):
      if self.cont >= self.img_size:
         return False
      llenar_comando(self.cont,self.send_list)
      sendData(0x03,self.send_list)
      #print(self.send_list)
      return True

   def read(self):
      bytes=readData(0x03, 0xFF)
      self.lectura+=1
      if bytes[0]==6:
         check_sum=sum(bytes[:15])&0xFF
         #si checksum es igual a 06
         if check_sum==6:
            check_sum=7
            #print("se cambio el check sum a 07")
         #check sum es correcto?
         if check_sum==bytes[15]:
            if self.cont >= self.img_size:
               print("Finito")
            else:
               for i in range(14):
                  self.image[(self.cont*14)+i]=bytes[1+i]
               #print(bytes)
               #print(self.cont)
               self.cont+=1
               return True
         else:
            self.mal_check+=1
            #print("check malo",bytes)
            return False
      else:
         self.no_cmd+=1
         #print(bytes)
         return False


def main():
   inicioT=time.time()
   print("Recibiendo paquetes...")
   total = pedir_foto()
   stpr = Stepper(total)
   while stpr.next():
         #time.sleep(0.01)
      while not stpr.read():
         5
         #time.sleep(0.003)
         #print(".", end="")
   finT=time.time()
   print("fin: ",finT-inicioT)
   print("lectura: ",stpr.lectura)
   print("mal checksum: ",stpr.mal_check)
   print("no se reconoce comando: ",stpr.no_cmd)
   f=open("image4.jpg","wb")
   Aarray=bytearray(stpr.image)
   f.write(Aarray)
   f.close()
   print("FIN")
   
main()
#total = pedir_foto()
#s = Stepper(total)
