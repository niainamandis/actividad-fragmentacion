import re
import sys
from router import parse_packet

# mtu de cada enlace (puerto de origen, puerto de destino)
MTU = {(8881, 8882): 100, (8882, 8883): 50, (8882, 8884): 80, (8883, 8882): 50,
       (8883, 8885): 55, (8884, 8882): 80, (8884, 8885): 140}

def analizar_router(ruta_log, router, rangos):
  # lee las líneas del log
  lineas = open(ruta_log).read().splitlines()
  reenviados = 0
  sobre_mtu = 0
  ttl0 = 0
  completos = 0
  ttl_minimo = None
  for linea in lineas:
    # busca las líneas de forward
    m = re.match(r"redirigiendo paquete (.*) con destino final .* hacia \('([\d.]+)', (\d+)\)", linea)
    if m:
      # convierte el texto a bytes
      paquete = eval(m.group(1))
      p = parse_packet(paquete)
      reenviados += 1
      # guarda el rango de bytes del fragmento
      rangos.setdefault(p["id"], []).append((p["offset"], p["offset"] + p["tamano"]))
      # cuenta si el fragmento supera el mtu
      if len(paquete) > MTU[(8880 + router, int(m.group(3)))]:
        sobre_mtu += 1
      # guarda el ttl más bajo
      if ttl_minimo is None or p["ttl"] < ttl_minimo:
        ttl_minimo = p["ttl"]
    # cuenta los descartes por ttl
    elif "TTL 0" in linea:
      ttl0 += 1
    # cuenta los mensajes completos de r5
    elif router == 5 and re.fullmatch("a{129}", linea):
      completos += 1
  # muestra el resumen del router
  if router == 5:
    print("  R5: mensajes completos: {} | descartes por TTL 0: {}".format(completos, ttl0))
  else:
    print("  R{}: reenviados: {} | sobre mtu: {} | ttl minimo: {} | descartes por TTL 0: {}".format(router, reenviados, sobre_mtu, ttl_minimo, ttl0))

# carpeta con los logs
carpeta = sys.argv[1]

for test in range(1, 5):
  print("=== test {} (origen R{}) ===".format(test, test))
  rangos = {}
  for router in range(1, 6):
    analizar_router("{}/t{}_R{}.txt".format(carpeta, test, router), router, rangos)
  # busca fragmentos contenidos dentro de otro del mismo id
  for id_paquete, lista in sorted(rangos.items()):
    distintos = set(lista)
    refrag = any(a != b and a[0] <= b[0] and b[1] <= a[1] for a in distintos for b in distintos)
    print("  id {}: re-fragmentación: {}".format(id_paquete, "sí" if refrag else "no"))
