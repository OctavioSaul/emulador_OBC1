#import smbus
import time
import math
from struct import pack, unpack

#bus = smbus.SMBus(1)
time.sleep(1)

def sendData(slaveAddress, data):
   bus.write_i2c_block_data(slaveAddress, 0xFF,data)

def readData(slaveAddress,reg):
   bytes=bus.read_i2c_block_data(slaveAddress,reg,16)
   return bytes

def comando_checksum(offset, level,send_list):
   #comando para pedir checksum
   send_list[0]=5
   #numero de offset
   send_list[1]=(offset & (0xFF<<16))>>16
   send_list[2]=(offset & (0xFF<<8))>>8
   send_list[3]=(offset & (0xFF))
   #nivel
   send_list[4]=(level & (0xFF))
   #llenar cero espacios vacios
   for i in range(5, 13):
      send_list[i]=0
   #checksum
   send_list[13]=sum(send_list[:13])&0xFF
   sendData(0x03,send_list)

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

def skipped_checksum(offset,level,image):
   checksum_list= [0]*15  
   c_i=15*offset #index contenido 
   r_i=0 #index result
   separa=(pow(15,level)-1)*15
   size=len(image)
   while True:
      for i in range(15):
         if c_i < size:
            checksum_list[r_i]+=image[c_i]
            checksum_list[r_i]&=0xFF
            c_i+=1
         else:
            return checksum_list
      if r_i >= 14:
         r_i*=0
      else: 
         r_i+=1
      c_i+=separa
         
def get_skipped_checksum(offset,level,send_list):
   while True:
      #leer checksum de OBC1
      bytes=readData(0x03, 0xFF)
      #calcular checksum
      check_sum=sum(bytes[:15])
      #mantenemos ultimos 8 bits
      check_sum&=0xFF
      #si es igual al inicio de la cadena
      if check_sum==bytes[0]:
         check_sum+=1
         check_sum&=0xFF
      #check sum es correcto?
      if check_sum==bytes[15]:
         return bytes[:15]
      else:
         comando_checksum(offset,level,send_list)

  
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
            #comprobar checksum
            if check_sum==bytes[15]:
               #convertir numero de paquetes
               total=math.ceil(((bytes[2]<<24)+(bytes[3]<<16)+(bytes[4]<<8)+(bytes[5]))/15)
               return total
            else:
               sendData(0x03,send_list)
            
class Stepper:
   def __init__(self, img_size):
      self.img_size = img_size
      self.cont = 0 #contador paquetes
      self.lectura = 0 #contador lectura 
      self.mal_check = 0 #contador checksum incorrecto
      self.image = [0]*(int(img_size)*15) #lista para almacenar los paquetes
      self.send_list = [0 for i in range(14)]
      print("total de paquetes: ", img_size)

   def next(self):
      if self.cont >= self.img_size:
         print("Finito")
         return False
      llenar_comando(self.cont,self.send_list)
      sendData(0x03,self.send_list)
      #print("Pedi: ", self.send_list, self.cont)
      return True

   def read(self):
      #leer info de OBC2
      bytes=readData(0x03, 0xFF)
      self.lectura+=1
      #calcular checksum
      check_sum=sum(bytes[:15])
      #aumento el numero de paquete actual
      check_sum+=self.cont
      #mantenemos ultimos 8 bits
      check_sum&=0xFF
      #si es i
      if check_sum==bytes[0]:
         check_sum+=1
         check_sum&=0xFF
      #check sum es correcto?
      if check_sum==bytes[15]:
         #guardar datos para exportar la imagen
         for i in range(15):
            self.image[(self.cont*15)+i]=bytes[i]
         #print("Correcto: ", bytes, self.cont)
         self.cont+=1
      else:
         #print("Incorrecto: ", bytes, self.cont)
         self.mal_check+=1
   
   def correct_error(self,offset,level):
      print("offset: ",offset,"  level: ",level)
      #pedir checksum a OBC1
      comando_checksum(offset,level,self.send_list)
      #separación entre paquetes
      separa=15**(level+1)
      #separación entre paquetes del mismo tipo
      separa2=15**(level+2)
      #calcular checksum paquetes del mismo tipo
      own=skipped_checksum(offset,level,self.image[:self.img_size])
      #leer checksum de OBC1
      other=get_skipped_checksum(offset,level,self.send_list)
      for i in range(15):
         if own[i]!=other[i]:
            if (offset*15)+(i*separa)+separa2 >= len(image):
               #pedir paquete erroneo (offset+i*15**level)
               llenar_comando(offset+i*15**level,self.send_list)
               sendData(0x03,self.send_list)
               while True:
                  #leer nuevo paquete
                  bytes=readData(0x03, 0xFF)
                  #calcular checksum
                  check_sum=sum(bytes[:15])
                  #mantenemos ultimos 8 bits
                  check_sum&=0xFF
                  #si es igual al inicio
                  if check_sum==bytes[0]:
                     check_sum+=1
                     check_sum&=0xFF
                  #check sum es correcto?
                  if check_sum==bytes[15]:
                     #guardar datos para exportar la imagen
                     for j in range(15):
                        self.image[((offset*15)+(i*separa))+j]=bytes[j]
                     return
                  else: 
                     sendData(0x03,self.send_list)           
            else:
               self.correct_error(offset+i*15**level,level+1)
   return    

def main():
   inicioT=time.time()
   print("Recibiendo paquetes...")
   total = pedir_foto()
   stpr = Stepper(total)
   #stpr.read()
   total_time = 0
   event_count = 0
   min_time = 30
   max_time = 0
   while stpr.next():
      time.sleep(0.001)
      start = time.time()
      stpr.read()
      end = time.time()
      elapsed = end-start
      total_time += elapsed
      event_count += 1
      if elapsed < min_time:
         min_time = elapsed
      if elapsed > max_time:
         max_time = elapsed
   start = time.time()
   stpr.correct_error(0,0)
   end = time.time()
   print("tiempo lista checksum imagen:",end-start)
   print("Event stats:")
   print("Event count: {}".format(event_count))
   print("Min time: {} us".format(1000000*min_time))
   print("Max time: {} us".format(1000000*max_time))
   print("Avg. time: {} us".format(1000000*total_time/event_count))

   finT=time.time()
   print("fin: ",finT-inicioT)
   print("lectura: ",stpr.lectura)
   print("mal checksum: ",stpr.mal_check)
   f=open("image10.jpg","wb")
   Aarray=bytearray(stpr.image)
   f.write(Aarray)
   f.close()
   print("FIN")
   
main()
#total = pedir_foto()
#s = Stepper(total)
#image =list(open("test2.jpg","rb").read())
#l = [i&0xFF for i in range(1001)]
#print(image[:100])
#print("-----------------------")
#print(skipped_checksum(0,0,image))
