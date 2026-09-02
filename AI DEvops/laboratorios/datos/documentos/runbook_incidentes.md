# Runbook de incidentes - Plataforma (extracto)

## Severidades y tiempos de respuesta
- Critica: primera respuesta en 15 minutos, guardia despertada, canal de incidente abierto.
- Alta: primera respuesta en 1 hora en horario laboral.
- Media: primera respuesta en 4 horas laborables.
- Baja: se atiende en el siguiente sprint.

## Rollback de un despliegue
El rollback se hace cambiando la version fijada en el archivo de configuracion del
entorno y volviendo a aplicar. No se despliega de nuevo desde el pipeline.
El objetivo acordado es completar un rollback en menos de 5 minutos.

## Retencion de trazas
Las trazas de llamadas a modelos se guardan 30 dias en caliente y 12 meses en frio.

## Presupuesto de gasto
Cada entorno tiene un tope mensual. Se alerta al 80 por ciento y se corta al 100 por ciento.
El tope de produccion vigente es de 400 USD al mes.

## Contacto
La guardia de plataforma se contacta por el canal #incidentes-plataforma.
