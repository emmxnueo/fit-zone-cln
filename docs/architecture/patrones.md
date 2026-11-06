# Patrones de diseño

Cada patrón responde a una necesidad concreta de FitZone. La columna "Descartado" dice contra qué se comparó.

## 1. Patrón de lógica de negocio

Se comparó Transaction Script, Table Module y Domain Model con los criterios del caso (cantidad de reglas, interacción entre conceptos, cambios esperados, estados e invariantes, reportes). La tabla completa está en el reporte de la Actividad 3 y la decisión en [ADR-001](adr/ADR-001-patron-de-logica-de-negocio.md).

| Patrón | Decisión | Razón en FitZone |
|---|---|---|
| **Domain Model** | Núcleo del sistema | Más de diez reglas encadenadas con límites ajustables (1 h, 2 h, 10 min, 15 min, 3 faltas, 7 días); cada regla vive en el concepto dueño |
| **Table Module** | Solo reportes (BN-04, BN-05) | Son lecturas sin cambio de estado; fuera del alcance del código |
| Transaction Script | Descartado | Duplicaría la cadena de lista de espera y la sanción entre flujos |

## 2. Patrones aplicados en el código

| Patrón | Dónde | Qué problema resuelve | Descartado |
|---|---|---|---|
| **Aggregate Root** | `SolicitudDeMembresia` en `domain/solicitud.py` | Una sola puerta para cambiar estado y proteger invariantes (total, estado, eventos) | Servicio que modifica campos sueltos de la solicitud |
| **Value Object** | `Dinero`, `Cantidad`, `LineaSolicitud` en `domain/value_objects.py` | Dinero siempre `Decimal` con 2 decimales, nunca `float`; cantidad entera de 1 o más (RN-38). Son inmutables | Usar `float` e `int` sueltos y validar en cada flujo |
| **Specification** | `domain/specifications.py` | Reglas de negocio como objetos que se combinan con AND (`&`), OR (`\|`) y NOT (`~`): RN-37 = `SocioActivo & SolicitudConLineas & SolicitudValidada`; RN-40 = `SocioPremium & TotalMinimo & ~CortesiaActiva` ([ADR-004](adr/ADR-004-specification.md)) | `if` anidados repetidos en cada caso de uso |
| **State Machine** | `domain/state_machine.py` | RN-41 en una tabla de transiciones; lo que no está en la tabla se rechaza con 409 ([ADR-005](adr/ADR-005-state-machine-por-tabla.md)) | Comparaciones de estado dispersas en los métodos |
| **Domain Events** | `domain/events.py`, `pull_events()` | El agregado registra lo que pasó; los suscriptores reaccionan sin que el dominio los conozca (RN-34) | Que el dominio llame directo al envío de avisos |
| **Repository** | Puertos en `application/puertos.py`; adaptadores en `infrastructure/` | El dominio y los casos de uso no saben si hay PostgreSQL o memoria | Consultas SQL dentro de los casos de uso |
| **Ports and Adapters (hexagonal)** | `Protocol` + `composicion.py` | Cambiar la base de datos sin tocar el negocio; probar sin base ([ADR-006](adr/ADR-006-puertos-y-adaptadores.md)) | Dependencia directa de SQLAlchemy desde la aplicación |
| **Service Layer** | `ServicioDeMembresias` | Un método por caso de uso: carga, ejecuta el comando de dominio, guarda y publica. No contiene reglas | Reglas dentro de los routers |
| **DTO** | `api/schemas.py` (Pydantic) | Contratos de entrada y salida de la API, separados de las entidades | Exponer las entidades directamente |
| **Publisher / Observer** | `PublicadorEnMemoria.suscribir()` | Suscribir manejadores por tipo de evento | Acoplar cada caso de uso a sus efectos |
| **Dependency Injection** | `api/dependencias.py` con `Depends` | Reemplazar el servicio en pruebas (`dependency_overrides`) | Singletons globales fijos |

Traducción de errores: los errores de dominio llevan su código HTTP y un manejador único los convierte en respuesta ([ADR-007](adr/ADR-007-errores-de-dominio-a-http.md)).

## 3. Patrones de la Actividad 3 que no se programaron

| Patrón | Estado |
|---|---|
| Unit of Work explícito | No se implementó: cada `guardar` abre y cierra su propia sesión. Es suficiente porque cada caso de uso modifica un solo agregado |
| CQRS básico (Commands, Queries, DTO de lectura) | Aplicado de forma ligera: las consultas (`obtener`, `listar`, `evaluar_*`) no cambian estado; no hay modelos de lectura separados |
| Domain Services (ElegibilidadDeReserva, CalculoDeCambioDePlan) | Diseñados para reservas y cambios de plan, que están fuera del alcance del código |
| Table Module para reportes | Diseñado; fuera del alcance del código |
