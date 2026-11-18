import socket

def paquete(id_, offset, flag, mensaje):
  return (bytes([127,0,0,1]) + (8885).to_bytes(2,"big") + bytes([10])
    + id_.to_bytes(4,"big") + offset.to_bytes(4,"big")
    + len(mensaje).to_bytes(4,"big") + bytes([flag]) + mensaje)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
envios = [
  paquete(1, 5, 0, b"mundo"),
  paquete(2, 0, 1, b"abc"),
  paquete(1, 0, 1, b"hola "),
  paquete(2, 3, 0, b"def"),
]
for p in envios:
  s.sendto(p, ("127.0.0.1", 8885))
