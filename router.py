import sys
import socket

# guarda el próximo turno de round-robin de cada área
rutas_visitadas = {}

# lista de fragmentos recibidos de cada id
fragmentos_recibidos = {}

def parse_packet(IP_packet: bytes):
  # ip en los primeros 4 bytes
  ip = ".".join(str(byte) for byte in IP_packet[0:4])
  # puerto en los siguientes 2 bytes
  puerto = int.from_bytes(IP_packet[4:6], "big")
  # ttl en el siguiente byte
  ttl = IP_packet[6]
  id_paquete = int.from_bytes(IP_packet[7:11], "big")
  offset = int.from_bytes(IP_packet[11:15], "big")
  tamano = int.from_bytes(IP_packet[15:19], "big")
  flag = IP_packet[19]
  # mensaje en los bytes restantes
  mensaje = IP_packet[20:]
  # paquete parseado
  return {"ip": ip, "puerto": puerto, "ttl": ttl, "id": id_paquete, "offset": offset, "tamano": tamano, "flag": flag, "mensaje": mensaje}


def create_packet(parsed_IP_packet):
  # convierte la ip a 4 bytes
  ip_bytes = bytes(int(num) for num in parsed_IP_packet["ip"].split("."))
  # convierte el puerto a 2 bytes
  puerto_bytes = parsed_IP_packet["puerto"].to_bytes(2, "big")
  # convierte el ttl a 1 byte
  ttl_bytes = parsed_IP_packet["ttl"].to_bytes(1, "big")
  id_bytes = parsed_IP_packet["id"].to_bytes(4, "big")
  offset_bytes = parsed_IP_packet["offset"].to_bytes(4, "big")
  tamano_bytes = parsed_IP_packet["tamano"].to_bytes(4, "big")
  flag_bytes = parsed_IP_packet["flag"].to_bytes(1, "big")
  # paquete en bytes
  return ip_bytes + puerto_bytes + ttl_bytes + id_bytes + offset_bytes + tamano_bytes + flag_bytes + parsed_IP_packet["mensaje"]


def check_routes(routes_file_name: str, destination_address: tuple[str, int]) -> tuple[str, int]:
  destination_ip, destination_puerto = destination_address
  # ip de destino a entero
  destination_num = int.from_bytes(bytes(int(num) for num in destination_ip.split(".")), "big")


  rutas_posibles = []

  with open(routes_file_name) as archivo:
    for linea in archivo:
      campos = linea.split()
      # salta las líneas vacías
      if len(campos) == 0:
        continue
      # separa la red cidr en ip y prefijo
      red_ip, prefijo = campos[0].split("/")
      # ip de la red a entero
      red_num = int.from_bytes(bytes(int(num) for num in red_ip.split(".")), "big")
      # máscara a partir del prefijo
      mascara = (0xFFFFFFFF << (32 - int(prefijo))) & 0xFFFFFFFF
      # rango de puertos
      puerto_inicial = int(campos[1])
      puerto_final = int(campos[2])
      # si la ip está en la red y el puerto en el rango
      if (destination_num & mascara) == (red_num & mascara) and puerto_inicial <= destination_puerto <= puerto_final:
        # guarda la ruta que coincide
        rutas_posibles.append(campos)
  # none si no hay ruta
  if len(rutas_posibles) == 0:
    return None
  # área con red y rango de puertos de la primera coincidencia
  area = tuple(rutas_posibles[0][0:3])
  # rutas que pertenecen a esa área
  rutas_area = [ruta for ruta in rutas_posibles if tuple(ruta[0:3]) == area]
  turno = rutas_visitadas.get(area, 0) # turno actual
  ruta_elegida = rutas_area[turno % len(rutas_area)] #ruta correspondiente
  # avanza el turno del área
  rutas_visitadas[area] = turno + 1
  # siguiente salto y mtu
  return (ruta_elegida[3], int(ruta_elegida[4])), int(ruta_elegida[5])

def fragment_IP_packet(IP_packet, MTU):
  # si cabe en el mtu
  if len(IP_packet) <= MTU:
    # retorna el paquete sin fragmentar
    return [IP_packet]
  # parsea el paquete
  parsed_IP_packet = parse_packet(IP_packet)
  mensaje = parsed_IP_packet["mensaje"]
  tamano_header = len(IP_packet) - len(mensaje)
  tamano_trozo = MTU - tamano_header
  fragmentos = []
  # recorre el mensaje en trozos
  for inicio in range(0, len(mensaje), tamano_trozo):
    trozo = mensaje[inicio:inicio + tamano_trozo]
    # copia el header del paquete original
    fragmento = dict(parsed_IP_packet)
    # suma el offset original al del trozo
    fragmento["offset"] = parsed_IP_packet["offset"] + inicio
    # actualiza el tamaño y el mensaje
    fragmento["tamano"] = len(trozo)
    fragmento["mensaje"] = trozo
    # flag en 1 si quedan trozos después de este
    if inicio + tamano_trozo < len(mensaje):
      fragmento["flag"] = 1
    # en el último trozo conserva el flag original
    else:
      fragmento["flag"] = parsed_IP_packet["flag"]
    # guarda el fragmento en bytes
    fragmentos.append(create_packet(fragmento))
  return fragmentos

def reassemble_IP_packet(fragment_list):
  parsed_fragmentos = [parse_packet(fragmento) for fragmento in fragment_list]
  # ordena los fragmentos por offset
  parsed_fragmentos.sort(key=lambda fragmento: fragmento["offset"])
  # si el primer fragmento no empieza en offset 0
  if parsed_fragmentos[0]["offset"] != 0:
    return None
  # si el último fragmento tiene flag 1
  if parsed_fragmentos[-1]["flag"] != 0:
    return None
  mensaje = b""
  for fragmento in parsed_fragmentos:
    # si falta un fragmento
    if fragmento["offset"] != len(mensaje):
      return None
    # agrega el trozo al mensaje
    mensaje += fragmento["mensaje"]
  # header del primer fragmento
  paquete = dict(parsed_fragmentos[0])
  # actualiza tamaño, flag y mensaje
  paquete["tamano"] = len(mensaje)
  paquete["flag"] = 0
  paquete["mensaje"] = mensaje
  return create_packet(paquete)

if __name__ == "__main__":
  
  router_IP = sys.argv[1]
  router_puerto = sys.argv[2]
  router_rutas = sys.argv[3]

  print("router_IP:", router_IP)
  print("router_puerto:", router_puerto)
  print("router_rutas:", router_rutas)

  # fragmentación: paquete de 150 bytes con mtu 50
  IP_packet_v1 = (bytes([127, 0, 0, 1])
    + (8885).to_bytes(2, "big")   # puerto
    + (10).to_bytes(1, "big")     # ttl
    + (347).to_bytes(4, "big")    # id
    + (0).to_bytes(4, "big")      # offset
    + (130).to_bytes(4, "big")    # tamaño
    + (0).to_bytes(1, "big")      # flag
    + b"a" * 130)
  fragment_list = fragment_IP_packet(IP_packet_v1, 50)

  # test de reensamblaje: fragmenta y reensambla el paquete de 150 bytes
  IP_packet_v2 = reassemble_IP_packet(fragment_list)
  # print("IP_packet_v1 = IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))

  # crea el socket udp
  router_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  # asocia el socket al par (ip, puerto)
  router_socket.bind((router_IP, int(router_puerto)))

  router_address = (router_IP, int(router_puerto))

  while True:
    IP_packet, sender_address = router_socket.recvfrom(1024)
    parsed_IP_packet = parse_packet(IP_packet)
    destination_address = (parsed_IP_packet["ip"], parsed_IP_packet["puerto"])

    # si el ttl no es mayor a 0
    if parsed_IP_packet["ttl"] <= 0:
      # ignora el paquete
      print("Se recibió paquete {} con TTL 0".format(IP_packet))
    # si el paquete es para este router
    elif destination_address == router_address:
      # guarda el paquete 
      fragmentos_recibidos.setdefault(parsed_IP_packet["id"], []).append(IP_packet)
      # imprime mensaje sin headers
      print(parsed_IP_packet["mensaje"].decode())
    else:
      # busca la ruta con siguiente salto y mtu
      ruta = check_routes(router_rutas, destination_address)
      # si no existe una ruta
      if ruta is None:
        # ignora el paquete
        print("No hay rutas hacia {} para paquete {}".format(destination_address, IP_packet))
      else:
        # separa el siguiente salto y el mtu
        next_hop_address, MTU = ruta
        # decrementa el ttl en 1 antes del forward
        parsed_IP_packet["ttl"] -= 1
        # recrea el paquete con el nuevo ttl
        IP_packet = create_packet(parsed_IP_packet)
        # fragmenta el paquete según el mtu de la ruta
        fragment_list = fragment_IP_packet(IP_packet, MTU)
        # recorre cada fragmento
        for fragmento in fragment_list:
          # informa el forward
          print("redirigiendo paquete {} con destino final {} desde {} hacia {}".format(fragmento, destination_address, router_address, next_hop_address))
          # reenvía el fragmento al siguiente salto
          router_socket.sendto(fragmento, next_hop_address)
