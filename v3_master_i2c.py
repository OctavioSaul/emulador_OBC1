import smbus
import time
import math

SLAVE_ADDRESS = 0x03
FILL_REGISTER = 0xFF
PHOTO_NUMBER = 12

bus = smbus.SMBus(1)
time.sleep(1)

def send_data(data):
   bus.write_i2c_block_data(SLAVE_ADDRESS, FILL_REGISTER,data)

def read_data():
   return bus.read_i2c_block_data(SLAVE_ADDRESS,FILL_REGISTER,16)

def get_reply_reps(time_between, max_reps, validator):
   for i in range(max_reps):
      time.sleep(time_between)
      received = read_data()
      if validator(received):
         return received
   return []

def get_reply_timed(time_between, max_time, validator):
   start = time.time()
   while time.time() - start < max_time:
      time.sleep(time_between)
      received = read_data()
      if validator(received):
         return received
   return []

def checksum(l):
   return sum(l)&0xFF

def command_photo():
   to_send = [0]*14
   to_send[0] = 3
   to_send[13] = checksum(to_send[:13]) 
   return to_send

def command_checksum(offset, level):
   to_send = [0]*14
   #comando para pedir checksum
   to_send[0]=5
   #numero de offset
   to_send[1]=(offset & (0xFF<<16))>>16
   to_send[2]=(offset & (0xFF<<8))>>8
   to_send[3]=(offset & (0xFF))
   #nivel
   to_send[4]=(level & (0xFF))
   to_send[13] = checksum(to_send[:13]) 
   return to_send

def command_packet(n):
   to_send = [0]*14
   #tipo comando(4 para indicar que paquete de la imagen se pide)
   to_send[0]=4
   #numero paquete a pedir
   to_send[1]=(n & (0xFF<<16))>>16
   to_send[2]=(n & (0xFF<<8))>>8
   to_send[3]=(n & (0xFF))
   to_send[13] = checksum(to_send[:13]) 
   #regresa el comando listo para enviar
   return to_send


def valid_reply(l):
   if l[0] != 0x06:
      return False
   cs = checksum(l[:15])
   if cs == 0x06:
      cs = 0x07
   if cs != l[15]:
      return False
   return True

def valid_packet(l, n):
   cs = checksum(l[:15])+n
   cs &= 0xFF
   if cs == l[0]:
      cs += 1
      cs &= 0xFF
   if cs != l[15]:
      return False
   return True

def skipped_checksum(offset,level,image):
   checksum_list= [0]*15  
   c_i=15*offset #index contenido 
   r_i=0 #index result
   separa=(15**level-1)*15
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
         
def get_skipped_checksum(offset,level):
   for i in range(5):
      reply = get_reply_timed(0.1*(5-i), 10, lambda l: valid_packet(l, 0))
      if reply:
         return reply
   return []

  
def pedir_foto():
   print("inicio")
   #comando pedir foto a OBC2
   while True:
      send_data(command_photo())
      reply = get_reply_timed(0.001, 30, valid_reply)
      if reply:
         #convertir numero de paquetes
         total=math.ceil(((reply[2]<<24)+(reply[3]<<16)+(reply[4]<<8)+(reply[5]))/15)
         return total
            
class Stepper:
   def __init__(self, img_size):
      self.img_size = img_size
      self.cont = 0 #contador paquetes
      self.lectura = 0 #contador lectura 
      self.no_reply = 0 #contador checksum incorrecto
      self.image = [0]*(int(img_size)*15) #lista para almacenar los paquetes
      print("total de paquetes: ", img_size)

   def next(self):
      if self.cont >= self.img_size:
         print("Finito")
         return False
      send_data(command_packet(self.cont))
      return True

   def read(self):
      reply = get_reply_reps(0.001, 1, lambda l: valid_packet(l, self.cont))
      self.lectura += 1
      if reply:
         #guardar datos para exportar la imagen
         print(self.cont)
         for i in range(15):
            self.image[(self.cont*15)+i]=reply[i]
         self.cont += 1
      else:
         self.no_reply += 1
   
   def correct_error(self,offset,level):
      print("offset: ",offset,"  level: ",level)
      #pedir checksum a OBC1
      send_data(command_checksum(offset, level))
      #separación entre paquetes
      separa=15**(level+1)
      #separación entre paquetes del mismo tipo
      separa2=15**(level+2)
      #calcular checksum paquetes del mismo tipo
      own=skipped_checksum(offset,level,self.image[:self.img_size])
      print("Calculated skipped checksum: ", own)
      #leer checksum de OBC1
      other=get_skipped_checksum(offset,level)
      for i in range(3):
         print("Asking for skipped checksum offset: {}, level: {}, for the {}th time".format(offset, level, i+2))
         send_data(command_checksum(offset, level))
         other=get_skipped_checksum(offset,level)
         if other:
            print("Got it")
            break

      if not other:
         print("skipped checksum not returned")
         return

      for i in range(15):
         if own[i]!=other[i]:
            if (offset*15)+(i*separa)+separa2 >= len(image):
               #pedir paquete erroneo (offset+i*15**level)
               print("Asking for packet {}".format(offset+i*15**level))
               send_data(command_packet(offset+i*15**level))
               reply = get_reply_timed(0.001, 5, lambda l: valid_packet(l, offset+i*15**level))
               if reply:
                  print("Got it")
                  #guardar datos para exportar la imagen
                  for j in range(15):
                     self.image[((offset*15)+(i*separa))+j]=reply[j]
                  return
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

   finT=time.time()

   print("Event stats:")
   print("Event count: {}".format(event_count))
   print("Min time: {} us".format(1000000*min_time))
   print("Max time: {} us".format(1000000*max_time))
   print("Avg. time: {} us".format(1000000*total_time/event_count))

   print("Tiempo total: ",finT-inicioT)
   print("lectura: ",stpr.lectura)
   print("no reply: ",stpr.no_reply)

   f=open("image{}.jpg".format(PHOTO_NUMBER),"wb")
   Aarray=bytearray(stpr.image)
   f.write(Aarray)
   f.close()

   print("Attempting to correct")
   start = time.time()
   stpr.correct_error(0,0)
   end = time.time()

   f=open("image_corrected{}.jpg".format(PHOTO_NUMBER),"wb")
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
