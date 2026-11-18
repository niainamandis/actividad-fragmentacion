# Actividad: Fragmentación 

Mini-Internet UDP que fragmenta y reensambla datagramas IP según el MTU de cada enlace, además de mantener el forwarding con TTL y round-robin.

## Estructura del repositorio

```
├── router.py              # router: parse/create de paquetes, rutas, fragmentación y reensamblaje
├── prueba_router.py       # script que envía los paquetes de prueba a un router
├── analizar.py            # analiza los logs de la prueba 2
├── rutas_R{1-5}_v3_mtu.txt  # tablas de rutas con MTU de los 5 routers
├── mensajes.txt           # mensajes pequeños (prueba 1)
├── mensaje150.txt         # mensajes para paquetes de 150 bytes (prueba 2)
├── test7.py               # script de prueba de reensamblaje
├── prueba_2/              # logs de la prueba 2 (TTL 10)
└── prueba_2_ttl30/        # logs de la prueba 2 (TTL 30)
```

## Requisitos

- Python 3 (probado con 3.13)
- Terminal con bash (los comandos usan `pkill` y `&`)

## Ejecución

Levantar los 5 routers, cada uno en su terminal:

```
python3 router.py 127.0.0.1 8881 rutas_R1_v3_mtu.txt
python3 router.py 127.0.0.1 8882 rutas_R2_v3_mtu.txt
python3 router.py 127.0.0.1 8883 rutas_R3_v3_mtu.txt
python3 router.py 127.0.0.1 8884 rutas_R4_v3_mtu.txt
python3 router.py 127.0.0.1 8885 rutas_R5_v3_mtu.txt
```

Enviar paquetes con formato `ip;puerto;ttl;id`, indicando el router inicial y el archivo con los mensajes (cada línea es un paquete y el ID aumenta en 1 por línea):

```
python3 prueba_router.py "127.0.0.1;8885;10;700" 127.0.0.1 8881 mensaje150.txt
```

Analizar los logs guardados:

```
python3 analizar.py prueba_2 > prueba_2/analisis.txt
```

## Notas

- Header de 20 bytes: IP (4), puerto (2), TTL (1), ID (4), offset (4), tamaño (4) y FLAG (1).
- Usar un ID distinto en cada envío, o reiniciar los routers entre pruebas, porque los routers guardan los fragmentos por ID.
