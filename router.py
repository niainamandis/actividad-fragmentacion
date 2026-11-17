import sys
import socket

# guarda el próximo turno de round-robin de cada área
rutas_visitadas = {}

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

if __name__ == "__main__":
  
  router_IP = sys.argv[1]
  router_puerto = sys.argv[2]
  router_rutas = sys.argv[3]

  print("router_IP:", router_IP)
  print("router_puerto:", router_puerto)
  print("router_rutas:", router_rutas)

  """
  # paquete de prueba manual
  IP_packet_v1 = (bytes([127, 0, 0, 1])
    + (8881).to_bytes(2, "big")   # puerto
    + (10).to_bytes(1, "big")     # ttl
    + (347).to_bytes(4, "big")    # id
    + (0).to_bytes(4, "big")      # offset
    + (4).to_bytes(4, "big")      # tamaño
    + (0).to_bytes(1, "big")      # flag
    + b"hola")
  parsed_IP_packet = parse_packet(IP_packet_v1)
  IP_packet_v2 = create_packet(parsed_IP_packet)
  # verificar que ambos paquetes sean iguales
  print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))
  """

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
        # informa el forward
        print("redirigiendo paquete {} con destino final {} desde {} hacia {}".format(IP_packet, destination_address, router_address, next_hop_address))
        # reenvía el paquete al siguiente salto
        router_socket.sendto(IP_packet, next_hop_address)
