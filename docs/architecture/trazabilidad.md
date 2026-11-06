# Matriz de trazabilidad

Recorre el camino **necesidad (BN) → historia (US) y Gherkin → regla (RN) → componente → prueba**. Los escenarios Gherkin del BRD (sección 11) llevan etiquetas `@RN-xx`, así que buscar la etiqueta en el BRD lleva al escenario de cada regla.

**Estado:** `Implementada` tiene código y prueba; `Parcial` tiene código con una limitación indicada; `Diseñada` está analizada en el BRD, el BPMN y la Actividad 3, pero no programada ([ADR-008](adr/ADR-008-alcance-del-codigo.md)).

**Abreviaturas de pruebas**

| Clave | Archivo |
|---|---|
| `D/solicitud` | `tests/unit/domain/test_solicitud.py` |
| `D/specs` | `tests/unit/domain/test_specifications.py` |
| `D/estados` | `tests/unit/domain/test_state_machine.py` |
| `D/vo` | `tests/unit/domain/test_value_objects.py` |
| `A/servicio` | `tests/unit/application/test_servicio.py` |
| `I/sql` | `tests/unit/infrastructure/test_repositorios_sql.py` |
| `D/clase` | `tests/unit/domain/test_clase.py` |
| `D/faltas` | `tests/unit/domain/test_socio_faltas.py` |
| `A/clases` | `tests/unit/application/test_clases.py` |
| `I/clases` | `tests/unit/infrastructure/test_clases_sql.py` (SQLite y PostgreSQL) |
| `A/reportes` | `tests/unit/application/test_reportes.py` |
| `API/clases` | `tests/integration/test_api_clases.py` |
| `API` | `tests/integration/test_api.py` |
| `PKG` | `tests/integration/test_paquete_csv.py` (120 casos y 20 transiciones contra un oráculo independiente) |

## 1. Reglas implementadas o parciales

| Regla | Historia | Componente | Pruebas | Estado |
|---|---|---|---|---|
| **RN-03** una membresía activa por socio (409) | US-21 | `SinMembresiaActiva` (`specifications.py`); `SolicitudDeMembresia.activar`; `vigentes_del_socio` en los repositorios | `D/solicitud::test_activar_con_membresia_activa_es_409`; `D/specs::test_sin_membresia_activa`; `A/servicio::test_segunda_membresia_activa_del_mismo_socio_es_409`, `test_la_cancelada_no_cuenta_como_activa`; `API::test_segunda_membresia_activa_es_409_por_rn03` | Implementada |
| **RN-04** vencimiento sin gracia | US-03 | `SolicitudDeMembresia.vencer`; `POST /solicitudes/{id}/vencer`; evento `MembresiaVencida` | `D/solicitud::test_vencer_desde_activa_y_renovar`; `API::test_vencer_renovar_y_rn08` | Parcial: la transición existe y se dispara por llamada; no hay reloj que la ejecute al llegar la fecha |
| **RN-05** ingreso con membresía vigente (422) | US-02 | `ServicioDeClases.registrar_ingreso`; `POST /socios/{id}/ingresos`; `RepositorioIngresos` | `A/clases::test_membresia_vencida_no_reserva_ni_ingresa`; `API/clases::test_ingreso_sin_membresia_es_422` | Implementada |
| **RN-08** renovar con pago confirmado (422) | US-16 | `SolicitudDeMembresia.renovar`; `POST /solicitudes/{id}/renovar`; `MembresiaRenovada` | `D/solicitud::test_vencer_desde_activa_y_renovar`; `A/servicio::test_ciclo_completo_congelar_vencer_renovar_baja`; `API::test_vencer_renovar_y_rn08` | Implementada |
| **RN-09** congelar con aprobación del Administrador (422) | US-17 | `SolicitudDeMembresia.congelar`; `POST .../congelar`; `MembresiaCongelada` | `D/solicitud::test_congelar_exige_aprobacion_del_administrador`; `API::test_congelar_descongelar_y_rn09` | Parcial: la aprobación llega como el campo `aprobada`; el agregado `SolicitudExcepcion` no se programó |
| **RN-10** baja con aprobación del Administrador (422) | US-12, US-17 | `SolicitudDeMembresia.dar_de_baja`; `POST .../dar-de-baja`; `MembresiaDadaDeBaja` | `D/solicitud::test_baja_exige_aprobacion_y_es_final`; `API::test_baja_requiere_administrador_rn10` | Parcial: igual que RN-09 |
| **RN-11** capacidad (422) | US-01 | `Clase.lugares_libres`, `Clase.reservar` | `D/clase::test_capacidad_debe_ser_positiva`, `test_clase_llena_manda_a_lista_de_espera` | Implementada |
| **RN-13** elegibilidad para reservar (422) | US-01 | `ElegibleParaReservar`, `exigir_elegibilidad`; `POST /clases/{id}/reservas` | `D/clase::test_socio_no_elegible_se_rechaza`; `API/clases::test_sin_membresia_es_422_y_sin_socio_es_404` | Implementada |
| **RN-14** categorías y etiquetas | US-10 | `PlanIncluyeCategoria`; `ServicioDeClases.etiqueta`; `GET /clases?socio_id=` | `A/clases::test_etiqueta_segun_el_plan`; `API/clases::test_clase_premium_y_etiquetas` | Parcial: un socio Standard no puede reservar una clase Premium; no se cobra el costo adicional |
| **RN-15, RN-16** cancelación según anticipación | US-14 | `Clase.cancelar_reserva`; `TRANSICIONES_RESERVA` | `D/clase::test_cancelacion_segun_anticipacion`; `A/clases::test_cancelacion_tardia_registra_falta_en_el_socio` | Implementada |
| **RN-17, RN-18** tolerancia y "presente" | US-19 | `Clase.aplicar_tolerancia`; `presentes_el`; `POST /clases/procesar-reloj` | `D/clase::test_a_los_10_minutos_exactos_no_se_libera`; `A/clases::test_ingreso_de_otro_dia_no_cuenta_como_presente` | Parcial: la regla es completa, pero requiere una tarea externa que llame al reloj |
| **RN-19, RN-24** FIFO y sin duplicados (409) | US-05 | `Clase.en_espera`, `Clase.reservar` | `D/clase::test_el_orden_depende_solo_del_registro`, `test_registro_duplicado_conserva_la_posicion`; `API/clases::test_reservar_y_lista_de_espera` | Implementada |
| **RN-20, RN-22** oferta de 15 min, una por clase | US-04, US-20 | `Clase.confirmar_oferta`, `expirar_oferta`, `oferta_activa` | `D/clase::test_confirmar_a_los_15_minutos_exactos`, `test_oferta_vencida_pasa_al_siguiente`, `test_solo_una_oferta_activa_y_nadie_se_salta_la_lista`; `A/clases::test_reloj_expira_la_oferta_y_ofrece_al_siguiente` | Parcial: igual que RN-17; la oferta se publica como evento, sin aviso real (RN-34) |
| **RN-21, RN-23** asignación por retraso y lugar libre | US-19, US-20 | `Clase._asignar_a_presente` | `D/clase::test_retraso_mayor_a_10_minutos_asigna_al_presente`, `test_nadie_presente_deja_el_lugar_libre`; `A/clases::test_reloj_aplica_no_show_y_asigna_al_presente` | Implementada |
| **RN-25 a RN-28** faltas y sanción automática | US-06 | `Socio.registrar_falta`; suscriptor `ServicioDeClases._registrar_falta`; `SinSancionActiva` | `D/faltas::*`; `A/clases::test_tres_faltas_sancionan_y_bloquean_reservas_pero_no_el_acceso`; `I/clases::test_no_show_falta_sancion_e_ingresos_persisten` | Implementada |
| **RN-29** solicitud del instructor (422) | US-18 | `Clase.solicitar_cancelacion`; `POST /clases/{id}/cancelacion`; `TRANSICIONES_CLASE` | `D/clase::test_solicitud_con_aviso_suficiente`, `test_solicitud_rechazada_deja_la_clase_programada`; `API/clases::test_solicitud_de_cancelacion_invalida` | Parcial: el instructor se identifica por nombre, sin autenticación |
| **RN-30** resolución del Administrador | US-07, US-18 | `Clase.aprobar_cancelacion`, `rechazar_cancelacion`; `POST /clases/{id}/cancelacion/resolver` | `D/clase::test_aprobar_cancela_reservas_y_descarta_la_lista`, `test_rechazar_vuelve_a_programada_sin_avisar_a_los_socios`; `A/clases::test_cancelacion_aprobada_no_registra_faltas`; `I/clases::test_ciclo_de_cancelacion_persiste`; `API/clases::test_cancelacion_de_clase_aprobada` | Parcial: igual que RN-09, la aprobación llega como el campo `aprobada` |
| **RN-31** aviso a los inscritos | US-07 | `ClaseCancelada.socios_a_notificar` | `D/clase::test_aprobar_sin_inscritos_no_notifica_a_nadie`; `API/clases::test_cancelacion_de_clase_aprobada` | Parcial: el evento lleva a quién avisar; falta el canal real (RN-34) |
| **RN-34** notificaciones por puerto | US-04, US-07 | `PublicadorDeEventos` y `PublicadorEnMemoria.suscribir` (los eventos se publican; no hay suscriptor de push o correo) | `A/servicio::test_publicador_notifica_a_los_suscriptores`; `A/servicio::test_activar_persiste_y_publica_el_evento` | Parcial: el mecanismo existe, el canal real no |
| **RN-35** reporte de afluencia (422 con rango inválido) | US-08 | `ServicioDeReportes.afluencia`; `RepositorioIngresos.entre`; `GET /reportes/afluencia` | `A/reportes::test_afluencia_agrupa_por_hora_y_dia_de_la_semana`, `test_rango_sin_ingresos_sale_en_ceros`, `test_rango_invalido_se_rechaza`; `I/clases::test_reportes_leen_lo_persistido`; `API/clases::test_reporte_de_afluencia` | Implementada |
| **RN-36** reporte de demanda | US-09 | `ServicioDeReportes.demanda`; `GET /reportes/demanda` | `A/reportes::test_clase_llena_con_lista_de_espera`, `test_clase_sin_reservas`, `test_demanda_ordena_de_mayor_a_menor`; `API/clases::test_reporte_de_demanda` | Implementada |
| **RN-37** solicitud procesable (422) | US-21 | `SolicitudProcesable` = `SocioActivo & SolicitudConLineas & SolicitudValidada`; `GET .../procesable` | `D/specs::test_procesable_*` (4); `D/solicitud::test_activar_no_procesable_es_422`; `A/servicio::test_evaluar_procesable_explica_los_motivos`; `API::test_procesable_explica_los_motivos`, `test_activar_no_validada_es_422_por_rn37`; `PKG::test_120_casos_coinciden_con_el_oraculo` | Implementada |
| **RN-38** total con `Decimal`; cantidad entera ≥ 1; plan habilitado | US-21 | `Dinero`, `Cantidad`, `LineaSolicitud`; `SolicitudDeMembresia.total`; `PlanesHabilitados` | `D/vo::*`; `D/solicitud::test_total_es_suma_precio_por_cantidad_en_decimal`, `test_cantidad_invalida_al_agregar_linea`, `test_activar_con_plan_deshabilitado_es_422`; `D/specs::test_planes_habilitados`; `API::test_crear_devuelve_201_con_total_decimal`, `test_cantidad_cero_es_422_por_rn38`, `test_activar_con_plan_deshabilitado_es_422_por_rn38` | Implementada |
| **RN-39** cupo del plan (409) | US-21 | `CupoDisponible`; `CupoAgotado`; `vigentes_por_plan` | `D/solicitud::test_activar_sin_cupo_es_409`; `D/specs::test_cupo_disponible`; `A/servicio::test_cupo_agotado_es_409`; `I/sql::test_sql_y_memoria_dan_los_mismos_conteos_de_cupo` | Implementada |
| **RN-40** beneficio de referencia | US-22 | `BeneficioDeReferencia` = `SocioPremium & TotalMinimo & ~CortesiaActiva`; `GET .../beneficio-referencia` | `D/specs::test_beneficio_*` (4); `A/servicio::test_evaluar_beneficio_explica_los_motivos`; `API::test_beneficio_de_referencia`; `PKG::test_120_casos_coinciden_con_el_oraculo` | Implementada |
| **RN-41** estados y transiciones (409) | US-16, US-17, US-21 | `TRANSICIONES` y `siguiente_estado` (`state_machine.py`); `TransicionInvalida` | `D/estados::*` (4, incluida la prueba de todos los pares inválidos); `D/solicitud::test_repetir_aprobacion_es_409`, `test_saltar_estado_solicitada_a_vencida_es_409`; `API::test_activar_y_repetir_aprobacion`, `test_saltar_estado_es_409`, `test_cancelar_y_no_se_puede_dos_veces`; `PKG::test_20_transiciones_coinciden_con_el_oraculo` | Implementada |

## 2. Reglas diseñadas, no programadas

| Regla | Tema | Historia | Dónde está el análisis y el diseño |
|---|---|---|---|
| RN-01, RN-02 | Edad mínima y deslinde | US-11, US-15 | BRD 7.1; BPMN 12.1; Gherkin US-11 y US-15 |
| RN-06, RN-07 | Upgrade, downgrade y cancelación anticipada | US-13 | BRD 7.1; Gherkin US-13; `CalculoDeCambioDePlan` (Act3) |
| RN-12 | Ajuste de aforo | US-17 | BRD 7.2; depende de `SolicitudExcepcion` |
| RN-32, RN-33 | Solicitudes de excepción | US-12, US-17 | BRD 7.5; BPMN 12.5; ciclo de la solicitud de excepción |

## 3. Necesidades de negocio

| BN | Necesidad | Reglas | Estado en el código |
|---|---|---|---|
| **BN-01** | Lista de espera automática | RN-19 a RN-24 | **Implementada** (ADR-002); falta el aviso real y la tarea programada |
| **BN-02** | Sanción por no-show | RN-15 a RN-18, RN-25 a RN-28 | **Implementada** (ADR-003) |
| **BN-03** | Aviso de cancelación de clase | RN-29 a RN-31, RN-34 | **Implementada**, sin canal real de aviso |
| **BN-04, BN-05** | Reportes de afluencia y demanda | RN-35, RN-36 | **Implementada** |
| BN-06 | Clases incluidas frente a costo adicional | RN-14 | Parcial: etiquetas y bloqueo, sin cobro |
| BN-07 | Deslinde de 16 y 17 años | RN-01, RN-02 | Diseñada |
| BN-08 | Excepciones solo del Administrador | RN-09, RN-10, RN-32, RN-33 | Parcial: RN-09 y RN-10 |
| **BN-09** | Ciclo de vida de la membresía | RN-03, RN-04, RN-08, RN-09, RN-10, RN-41 | **Implementada** |
| **BN-10** | Beneficio de referencia (paquete del PIA) | RN-37 a RN-40 | **Implementada** |

## 4. API → regla → prueba

| Endpoint | Caso de uso | Reglas | Códigos | Prueba principal |
|---|---|---|---|---|
| `POST /solicitudes` | Crear solicitud | RN-38 | 201, 400, 404, 422 | `API::test_crear_devuelve_201_con_total_decimal`, `test_formato_invalido_es_400` |
| `GET /solicitudes`, `GET /solicitudes/{id}` | Listar y consultar | | 200, 404 | `API::test_consultar_y_listar` |
| `GET /solicitudes/{id}/procesable` | Evaluar RN-37 | RN-37 | 200, 404 | `API::test_procesable_explica_los_motivos` |
| `GET /solicitudes/{id}/beneficio-referencia` | Evaluar RN-40 | RN-40 | 200, 404 | `API::test_beneficio_de_referencia` |
| `POST /solicitudes/{id}/activar` | SOLICITADA → ACTIVA | RN-41, RN-03, RN-37, RN-38, RN-39 | 200, 404, 409, 422 | `API::test_activar_y_repetir_aprobacion` |
| `POST /solicitudes/{id}/cancelar` | SOLICITADA → CANCELADA | RN-41 | 200, 404, 409 | `API::test_cancelar_y_no_se_puede_dos_veces` |
| `POST /solicitudes/{id}/congelar` | ACTIVA → SUSPENDIDA | RN-09, RN-41 | 200, 400, 404, 409, 422 | `API::test_congelar_descongelar_y_rn09` |
| `POST /solicitudes/{id}/descongelar` | SUSPENDIDA → ACTIVA | RN-41 | 200, 404, 409 | `API::test_congelar_descongelar_y_rn09` |
| `POST /solicitudes/{id}/vencer` | ACTIVA o SUSPENDIDA → VENCIDA | RN-04, RN-41 | 200, 404, 409 | `API::test_vencer_renovar_y_rn08` |
| `POST /solicitudes/{id}/renovar` | VENCIDA → ACTIVA | RN-08, RN-41 | 200, 400, 404, 409, 422 | `API::test_vencer_renovar_y_rn08` |
| `POST /solicitudes/{id}/dar-de-baja` | ACTIVA o SUSPENDIDA → CANCELADA | RN-10, RN-41 | 200, 400, 404, 409, 422 | `API::test_baja_requiere_administrador_rn10` |
| `POST /clases`, `GET /clases`, `GET /clases/{id}` | Crear, catálogo y consulta | RN-11, RN-14 | 200, 201, 400, 404, 422 | `API/clases::test_formato_y_reglas_al_crear_clase`, `test_clase_premium_y_etiquetas` |
| `POST /clases/{id}/reservas` | Reservar o entrar a la lista | RN-11, RN-13, RN-19, RN-24, RN-26 | 201, 400, 404, 409, 422 | `API/clases::test_reservar_y_lista_de_espera` |
| `POST /clases/{id}/reservas/{rid}/cancelar` | Cancelar | RN-15, RN-16, RN-20 | 200, 404, 409 | `API/clases::test_cancelar_ofrecer_y_confirmar` |
| `POST /clases/{id}/oferta/confirmar` | Confirmar oferta | RN-20, RN-13 | 200, 400, 404, 409, 422 | `API/clases::test_cancelar_ofrecer_y_confirmar` |
| `POST /clases/procesar-reloj` | Actor Sistema | RN-17, RN-20, RN-21, RN-23 | 200, 400 | `API/clases::test_ingreso_y_tolerancia_con_el_reloj` |
| `POST /clases/{id}/cancelacion` | Solicitar cancelación | RN-29 | 200, 400, 404, 409, 422 | `API/clases::test_cancelacion_de_clase_aprobada`, `test_solicitud_de_cancelacion_invalida` |
| `POST /clases/{id}/cancelacion/resolver` | Aprobar o rechazar | RN-30, RN-31 | 200, 400, 404, 409 | `API/clases::test_cancelacion_de_clase_aprobada`, `test_cancelacion_de_clase_rechazada` |
| `GET /reportes/afluencia` | Afluencia por hora y día | RN-35 | 200, 400, 422 | `API/clases::test_reporte_de_afluencia`, `test_reporte_de_afluencia_con_rango_invalido` |
| `GET /reportes/demanda` | Ocupación y lista de espera | RN-36 | 200 | `API/clases::test_reporte_de_demanda` |
| `GET /socios/{id}`, `POST /socios/{id}/ingresos` | Faltas, sanción e ingreso | RN-05, RN-18, RN-26 | 200, 201, 404, 422 | `API/clases::test_ingreso_sin_membresia_es_422` |
| `GET /planes`, `GET /eventos`, `GET /health` | Catálogo, eventos y estado | | 200 | `API::test_catalogo_de_planes`, `test_health` |

## 5. Evidencia del paquete del profesor

| Evidencia | Qué prueba | Archivo |
|---|---|---|
| 120 casos (`validar_operacion` y `evaluar_beneficio`) | RN-37, RN-38, RN-40 contra un oráculo independiente | `docs/evidencia/resultados_casos.csv` |
| 20 transiciones | RN-41, RN-03, RN-39, RN-37, RN-08, RN-09, RN-10 con su evento o error | `docs/evidencia/resultados_transiciones.csv` |
| Carga del paquete | 40 socios, 20 planes, 60 solicitudes, 117 líneas | `PKG::test_el_paquete_se_carga_completo` |
