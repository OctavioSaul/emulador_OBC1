import os
# -------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------
# funcion para abrir los archivos de un directorio
def devolverArchivos(carpeta, id):
    for archivo in os.listdir(carpeta):
        # print(".................................................\n")
        # print(os.path.join(carpeta, archivo))
        leerArchivo(os.path.join(carpeta, archivo), id)
        if os.path.isdir(os.path.join(carpeta, archivo)):
            devolverArchivos(os.path.join(carpeta, archivo))
# -------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------
def leerArchivo(direc, id):
    f = open(direc, 'rb')
    # 2 bytes numero de la imagen
    byte = f.read(2)
    tmp = int.from_bytes(byte, byteorder='big')
    #print("id: %d", tmp)
    if tmp == id:
        # 2 bytes no del archivo actual
        byte = f.read(2)
        arch = int.from_bytes(byte, byteorder='big')
        #print("archivo: ", arch)
        if arch == 0:
            # 2 bytes cantidad de paquetes de toda la imagen
            byte = f.read(2)
            total = int.from_bytes(byte, byteorder='big')
            print("-----------------total de paquetes:", total)
        # doc tiene la info de la imagen, con esto se inicializa
        doc = f.read(1)
        while True:
            byte = f.read(1)
            if (len(byte) == 0):
                break
            doc += byte
        f.close()
        image[arch] = doc
# -------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------- main
# -------------------------------------------------------------------------------------------------
# todos tienen 340 bytes
# los primeros 4 sirven para la posición
image = {}  # diccionario con los datos de las imagenes
id = 50  # numero de la imagen que desea reconstruir
my_path = "C:/Users/52553/Documents/K'OTO/Iridium/Test_3"
devolverArchivos(my_path, id)
mi_path = "image_" + str(id) + ".jpg"
max=0
for key in image:
    if max<key:
        max=key
with open(os.path.join(my_path, mi_path), 'wb') as f:
    for key in range (0,max,1):
        f.write(image[key])
