# Politica de datos (extracto)

- Nunca se envian datos de clientes a servicios externos sin contrato de tratamiento.
- Los campos que NO pueden salir de la red interna son: documento de identidad,
  numero de tarjeta, direccion postal completa y telefono personal.
- Los logs no pueden contener tokens de sesion ni credenciales.
- La clave de una entrada de cache debe incluir el ambito de permisos del usuario.
- Toda accion irreversible ejecutada por un sistema automatico requiere confirmacion
  humana registrada con nombre y fecha.
