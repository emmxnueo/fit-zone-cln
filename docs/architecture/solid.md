# Aplicación de los principios SOLID

Cada fila apunta al código que lo demuestra. La última sección lista lo que se detectó y queda pendiente.

| Principio | Cómo se aplica | Evidencia |
|---|---|---|
| **S** Responsabilidad única | Las reglas viven en el dominio; el servicio solo coordina (cargar, ejecutar, guardar, publicar); los routers solo traducen HTTP; los repositorios solo persisten | `domain/solicitud.py` y `domain/clase.py` (reglas), `application/servicio.py` (`_ejecutar`), `application/clases.py`, `api/routers/solicitudes.py`, `infrastructure/repositorios_sql.py` |
| **O** Abierto/cerrado | Una regla nueva es una Specification nueva, sin tocar las existentes; una transición nueva es una fila nueva en `TRANSICIONES`; un error nuevo hereda de `ErrorDeDominio` y el manejador de `main.py` ya lo traduce | `domain/specifications.py` (`SolicitudProcesable` compone otras tres), `domain/state_machine.py`, `domain/errors.py` |
| **L** Sustitución de Liskov | Los repositorios en memoria y SQL respetan el mismo contrato y son intercambiables sin que el servicio lo note | `tests/unit/infrastructure/test_repositorios_sql.py::test_sql_y_memoria_dan_los_mismos_conteos_de_cupo`; las pruebas del servicio corren con memoria y la API con cualquiera |
| **I** Segregación de interfaces | Puertos pequeños, uno por agregado o rol: `RepositorioSocios` `obtener` y `guardar`; `RepositorioPlanes` `obtener` y `todos`; `RepositorioIngresos` `registrar` y `presentes_el`; `Reloj` solo `ahora` | `application/puertos.py` |
| **D** Inversión de dependencias | `domain` no importa ninguna otra capa; `application` depende de `Protocol`, no de SQLAlchemy; `composicion.py` es la única que conoce las clases concretas | `application/puertos.py`, `infrastructure/composicion.py`, `api/dependencias.py` |

## Hallazgos y cambios

| Hallazgo | Principio | Estado |
|---|---|---|
| Un solo servicio para todo habría mezclado membresías, reservas, clases y excepciones; la Act3 propuso dividirlo en cinco servicios | S | **Resuelto**: `ServicioDeMembresias` y `ServicioDeClases` están separados y comparten solo repositorios y publicador. La división en más servicios queda para cuando se programen excepciones y reportes |
| La regla "una sola membresía activa" cruza dos agregados y podía esconderse en el servicio | S, D | **Resuelto**: la decide `SinMembresiaActiva` dentro del dominio; el servicio solo calcula `vigentes_del_socio` y se lo pasa en el `ContextoSolicitud` |
| Los límites de negocio deben poder cambiar sin editar condicionales | O | **Parcial**: `BeneficioDeReferencia.UMBRAL = 1500` es una constante de clase. Pendiente: leerla de configuración |
| `servicio.py` repite la lista de las tres condiciones de RN-37 (`_CONDICIONES_PROCESABLE`) para explicar los motivos | O | Pendiente: duplicación menor aceptada, porque cada condición necesita su etiqueta; si cambia RN-37 hay que tocar ambos lugares |
| Las notificaciones salen del servicio vía eventos, no por llamadas directas | D | **Aplicado**: el servicio publica; los suscriptores se enganchan con `PublicadorEnMemoria.suscribir`. No hay suscriptor de push o correo (RN-34 queda fuera del alcance del código) |
