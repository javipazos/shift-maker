# Prompt: Shift Scheduler — Web App

## Contexto

Necesito una aplicación web local para gestionar horarios de turnos rotativos de equipos pequeños (2-6 personas). La app debe ser genérica: no asume un sector, número fijo de personas ni reglas concretas. Todo es configurable. La uso yo para generar los horarios de cada mes y exportarlos.

## Stack técnico

- **Frontend**: TypeScript + React (Vite), Tailwind CSS
- **Backend**: Python (FastAPI) — elegido porque OR-Tools (el solver) es nativo en Python, y meter un subprocess Python desde Node añade complejidad innecesaria
- **Solver**: Google OR-Tools CP-SAT (`ortools.sat.python.cp_model`) — referencia: https://developers.google.com/optimization/scheduling/employee_scheduling
- **Base de datos**: SQLite (vía SQLAlchemy o similar)
- **Sin autenticación** — es una herramienta local/personal
- **Export**: xlsx (vía openpyxl)

## Modelo de datos

### Empleados (`employees`)
- Nombre
- Horas por jornada (ej: 7.5h, 8h) — configurable por persona
- Horas máximas por semana (ej: 37.5h, 40h)
- Tipo de contrato: jornada completa / parcial (informativo, las horas reales las definen los campos anteriores)
- Preferencia de turno: mañana / tarde / flexible / sin preferencia
- Fuerza de la preferencia: obligatoria / deseable (si es "deseable", el scheduler puede romperla si es necesario; si es "obligatoria", nunca la rompe)
- Estado: activa / baja

### Tipos de turno (`shift_types`)
- Nombre (ej: "Mañana", "Tarde", "Media mañana")
- Hora inicio (ej: "07:00")
- Hora fin (ej: "14:30")
- Duración efectiva en horas (calculable, pero almacenar para permitir override si hay pausa descontada)
- **Orden de prioridad** (1 = más prioritario). Define qué turno es más importante cubrir cuando no hay suficiente personal. Ejemplo: si mañana=1, tarde=2, media mañana=3 → cuando solo hay 1 persona disponible, se asigna al turno de mañana. Si hay 2, se cubren mañana y tarde. El turno menos prioritario es el que se sacrifica primero.
- Color para UI
- Activo/inactivo

### Ausencias (`absences`)
- Empleado
- Fecha inicio / fecha fin (inclusive)
- Tipo: vacaciones / baja médica / formación (cuenta como trabajo) / permiso personal / otro
- Cuenta como jornada laboral: sí / no (la formación tipo SOAD cuenta como horas trabajadas aunque no esté en tienda)
- Notas

### Reglas (`rules`) — el corazón del sistema
Cada regla tiene:
- Nombre descriptivo
- Categoría: `descanso` / `cobertura` / `equidad` / `límites` / `custom`
- Prioridad: `obligatoria` (hard constraint) / `deseable` (soft constraint)
- Peso (1-10) — cuánto penaliza romperla en el score

**Importante: ninguna regla bloquea la generación del horario.** El sistema siempre genera una propuesta, incluso si viola reglas obligatorias. La diferencia entre prioridades es cómo se muestran y cómo afectan al generador:
- `obligatoria`: el generador se esfuerza al máximo por cumplirla. Si no puede, genera igualmente pero marca la violación como **falta grave** (✗ rojo). El humano decide qué hacer: ajustar manualmente, aceptar el riesgo, o buscar refuerzo.
- `deseable`: el generador intenta cumplirla pero la sacrifica antes que una obligatoria. Se marca como **advertencia** (⚠ naranja).

La decisión final siempre es humana. El sistema informa, no bloquea.
- Parámetros configurables (JSON flexible)
- Activa/inactiva

#### Reglas predefinidas que el sistema debe soportar de serie:

**Categoría: Descanso**
1. **Descanso mínimo entre jornadas** — Mínimo N horas entre el fin de un turno y el inicio del siguiente (default: 12h). Esto es lo que impide ir de un turno de tarde a uno de mañana al día siguiente.
2. **Máximo días consecutivos trabajados** — No más de N días seguidos (default: 6). Las ausencias que cuentan como trabajo (formación) suman al contador.
3. **Días libres consecutivos mínimos** — Cada bloque de descanso debe ser de al menos N días (default: 2). Evitar días libres sueltos.
4. **Descanso semanal mínimo** — Al menos N días libres por semana o cada 7 días (default: 1.5, según Estatuto de los Trabajadores).

**Categoría: Cobertura**
5. **Cobertura mínima por día** — Al menos N personas trabajando cada día (configurable por día de semana: entre semana vs fin de semana).
6. **Cobertura por turno en fin de semana** — Los fines de semana deben tener al menos 1 persona en turno de mañana Y 1 en turno de tarde (configurable: qué turnos se requieren y qué días).
7. **Cobertura mínima por turno** — Cada turno activo del día debe tener al menos N personas.
8. **Cobertura por prioridad de turno** — El turno más prioritario (prioridad=1) debe estar cubierto SIEMPRE que haya al menos 1 persona disponible ese día. Si solo hay 1 persona, va al turno prioritario. Si hay 2, se cubren los 2 turnos más prioritarios. Y así sucesivamente. En la práctica: si el turno de mañana es prioridad 1, nunca puede haber un día con alguien en turno de tarde y nadie en turno de mañana. Esta regla interactúa con la de descanso mínimo (12h), ya que a veces la persona disponible no puede hacer el turno prioritario por restricción de descanso — en ese caso se marca como violación estructural.

**Categoría: Equidad**
9. **Fin de semana libre mensual** — Cada empleado debe tener al menos N fines de semana libres completos (sáb+dom) al mes (default: 1).
10. **Distribución equitativa de fines de semana** — Distribuir los fines de semana trabajados lo más equitativamente posible entre empleados.
11. **Distribución equitativa de horas** — Las horas totales trabajadas deben ser proporcionales al contrato de cada persona (no sobrecargar a nadie).

**Categoría: Límites**
12. **Horas máximas semanales** — No superar las horas/semana configuradas por empleado. Importante: las ausencias tipo "formación" suman horas.
13. **Horas máximas diarias** — Máximo N horas por jornada (default: 9h según Estatuto de los Trabajadores).
14. **Días libres pedidos** — Respetar días específicos que un empleado ha pedido libres (se configuran como ausencias de tipo "permiso personal").

**Extensibilidad**: el sistema de reglas debe ser extensible. Cada regla es una función que recibe el schedule completo y devuelve una lista de violaciones (con severidad y descripción). Esto permite añadir reglas custom sin tocar el core.

#### Violaciones estructurales vs corregibles

Concepto clave: no todas las violaciones son iguales. El sistema debe distinguir entre:

- **Violación corregible**: se puede resolver reordenando los turnos. Ejemplo: "el lunes 12 solo hay 1 persona, pero hay 2 empleados disponibles ese día — falta asignar a alguien". Es un error del schedule.
- **Violación estructural**: es matemáticamente imposible de resolver con la plantilla disponible. Ejemplo: "el sábado 16 solo hay 1 persona disponible porque las otras dos están de vacaciones/baja — no se puede cumplir la cobertura mínima de 2 hagas lo que hagas". No es un error del schedule, es una limitación de recursos.

**Implementación**: antes de ejecutar la validación de cada regla, el sistema calcula la **capacidad disponible por día** (empleados activos que no tienen ausencia ese día). Cada violación lleva un campo `resolvable: boolean`:
- `true` → hay margen para reasignar y resolver la violación
- `false` → no hay suficientes recursos, la violación es inevitable

En la UI:
- Las violaciones corregibles se muestran con fondo rojo / naranja (según prioridad) — son accionables
- Las violaciones estructurales se muestran con fondo gris y un icono informativo (ℹ) — son avisos, no errores
- El panel de validación agrupa y cuenta por separado: "3 violaciones corregibles, 2 estructurales"
- El score del horario solo penaliza las violaciones corregibles, no las estructurales

El generador automático también usa esta distinción: no gasta ciclos intentando resolver lo que es imposible, y reporta al final las limitaciones estructurales como información ("estos días no se pueden cubrir con la plantilla actual — considerar refuerzo externo").

### Horario mensual (`schedules`)
- Mes/año
- Estado: borrador / publicado
- Array de asignaciones: fecha + empleado + tipo de turno asignado (o null = libre)

## Funcionalidades

### 1. Configuración (CRUD)
- Gestionar empleados, tipos de turno, y reglas
- Las reglas se activan/desactivan y se configuran sus parámetros sin tocar código
- UI: formularios simples, nada fancy

### 2. Gestión de ausencias
- Calendario visual donde se marcan vacaciones, formaciones, bajas, días pedidos
- Al generar el schedule, las ausencias se respetan como restricciones inamovibles

### 3. Generación del horario mensual
- Seleccionar mes y año
- El sistema genera una propuesta automática que maximiza el cumplimiento de reglas
- **Solver**: Google OR-Tools CP-SAT. Referencia directa: https://developers.google.com/optimization/scheduling/employee_scheduling
  
  El modelo CP-SAT se mapea naturalmente a nuestro sistema de reglas:
  
  **Variables de decisión**: para cada (empleado, día, turno), una variable booleana que indica si esa persona trabaja ese turno ese día.
  
  **Hard constraints** (reglas obligatorias) → se modelan como restricciones del solver. Si no se pueden satisfacer todas simultáneamente, el solver reporta INFEASIBLE y se relajan progresivamente (empezando por las de menor peso) hasta encontrar una solución. Esto da visibilidad de qué reglas obligatorias se violaron y por qué.
  
  **Soft constraints** (reglas deseables) → se modelan como términos de la función objetivo. Cada regla deseable suma o resta al score según su peso. El solver maximiza el cumplimiento ponderado.
  
  **Constraints fijas** (ausencias, días pedidos) → variables fijadas a 0 o 1 antes de resolver.
  
  **Prioridad de turno** → se modela como soft constraint con peso alto: penalizar fuertemente que un turno de baja prioridad esté cubierto mientras uno de alta prioridad no lo está.
  
  **Preferencias de empleado** → soft constraint: bonificar cuando el turno asignado coincide con la preferencia. Si la preferencia es "obligatoria", se modela como hard constraint en vez de soft.

  **Violaciones estructurales** → tras resolver, comparar la capacidad disponible por día contra lo que exige cada regla. Si el solver viola una regla en un día donde matemáticamente no hay suficiente gente, marcarla como `resolvable: false`.

  Para equipos de 2-6 personas con 31 días y 2-3 turnos, el espacio de búsqueda es pequeño — CP-SAT lo resuelve en milisegundos.

### 4. Edición manual
- Vista de cuadrícula mensual (filas = empleados, columnas = días)
- Click en celda para asignar/cambiar turno (dropdown con tipos de turno disponibles)
- Al editar manualmente, **validación en tiempo real**: el sistema muestra inmediatamente qué reglas se están violando (con iconos/colores)
- Indicadores visuales:
  - Fondo de celda por tipo de turno (colores configurados)
  - Fines de semana distinguidos visualmente
  - Celdas con violaciones marcadas en rojo con tooltip explicativo
  - Ausencias con su color/icono según tipo
  - Fila de cobertura por día (cuántas personas hay)

### 5. Panel de validación
- Lista de todas las reglas activas
- Para cada una: ✓ cumplida / ✗ falta grave (obligatoria violada) / ⚠ advertencia (deseable violada) / ℹ limitación estructural (imposible con la plantilla)
- Separar visualmente: faltas graves arriba (requieren atención humana), advertencias en medio, estructurales abajo (informativas)
- Detalle de cada violación: qué empleado, qué día, qué regla, explicación en texto claro, si es corregible o estructural
- Score general del horario (% de cumplimiento, excluyendo estructurales del cálculo)
- El panel no tiene botón de "bloquear" ni impide publicar el horario — solo informa. El humano siempre tiene la última palabra

### 6. Resumen / métricas
- Por empleado: días trabajados, horas totales, horas/semana, fines de semana libres, máx días consecutivos, % de preferencia de turno cumplida
- General: días con cobertura mínima, días con cobertura completa, días con limitación estructural (para que quede claro dónde habría que considerar refuerzo externo)

### 7. Exportar a .xlsx
- Formato similar al que se usa manualmente: semanas como bloques, filas por empleado, celdas con el horario (ej: "7 - 14:30"), fila de cobertura
- Incluir hoja de resumen con las métricas
- Colores que reflejen los de la UI

### 8. Histórico
- Guardar horarios de meses anteriores
- Al generar un nuevo mes, poder ver el último día del mes anterior para respetar la continuidad (ej: si alguien acabó el mes con 5 días consecutivos, no empezar el nuevo mes con más días seguidos)

## UI/UX

- **Vista principal**: calendario mensual en cuadrícula, similar a un spreadsheet
- **Sidebar o tabs**: configuración, ausencias, validación, resumen
- Responsive no es prioridad — se usa en desktop
- Tono visual: limpio, funcional, sin decoración innecesaria. Inspiración: Google Sheets / Notion calendar view
- Los colores de los turnos deben ser configurables pero tener defaults legibles
- Dark mode no es necesario

## Consideraciones técnicas

### Arquitectura
- **Backend (Python/FastAPI)**: CRUD, solver (OR-Tools), validación autoritativa, export xlsx
- **Frontend (React/TS)**: UI, validación client-side para feedback instantáneo al editar manualmente
- La validación corre en ambos lados: client-side es "preview" rápido, server-side es la fuente de verdad. Las reglas se definen una vez en Python y el frontend replica la lógica de las más críticas para UX inmediato.

### Motor de reglas (Python)
Cada regla vive en un módulo separado (`/rules/`) y tiene dos facetas:
1. **Validador**: recibe el schedule y devuelve violaciones (para validación post-edición y panel de validación)
2. **Constraint builder**: traduce la regla a constraints de OR-Tools CP-SAT (para el generador automático)

```python
class Rule(ABC):
    id: str
    name: str
    category: RuleCategory  # descanso | cobertura | equidad | limites | custom
    priority: Literal["mandatory", "desirable"]
    weight: int  # 1-10, usado para soft constraints en el solver

    @abstractmethod
    def validate(self, schedule: MonthSchedule, config: AppConfig) -> list[Violation]:
        """Validate a completed or partial schedule. Used for manual edit feedback."""

    @abstractmethod
    def add_constraints(self, model: cp_model.CpModel, vars: ScheduleVars, config: AppConfig) -> None:
        """Add this rule's constraints to the CP-SAT model. Hard rules add strict constraints,
        soft rules add penalty terms to the objective function."""

@dataclass
class Violation:
    rule_id: str
    date: str           # ISO date
    employee_id: str | None  # None for global violations like coverage
    severity: Literal["grave", "warning"]  # grave = mandatory violated, warning = desirable violated
    resolvable: bool    # False = structural (impossible given available staff)
    message: str        # human-readable explanation
```
- `severity: 'grave'` + `resolvable: True` → ✗ rojo, accionable, requiere atención humana
- `severity: 'grave'` + `resolvable: False` → ℹ gris, imposible con la plantilla actual
- `severity: 'warning'` + `resolvable: True` → ⚠ naranja, mejorable
- `severity: 'warning'` + `resolvable: False` → ℹ gris, informativo

- Cada regla es un archivo independiente que implementa la clase abstracta
- El generador usa `add_constraints()`, la validación manual usa `validate()` — misma regla, dos modos
- SQLite para persistencia simple, sin necesidad de migraciones complejas — una tabla de configuración JSON si es más práctico para las reglas

## Lo que NO necesito
- Multi-usuario / roles / permisos
- Notificaciones a empleados
- App móvil
- Integración con nóminas o RRHH
- Internacionalización (solo español está bien, pero los comentarios del código en inglés)
- Deploy en la nube — corre local

## Orden de implementación sugerido
1. Modelo de datos + seed con datos de ejemplo
2. Backend: CRUD de empleados y tipos de turno (FastAPI + SQLite)
3. Frontend: Vista de calendario mensual (solo visualización, datos hardcodeados)
4. Edición manual de celdas + persistencia
5. Motor de reglas: las 3-4 reglas más críticas con su `validate()` (descanso 12h, máx consecutivos, cobertura mínima, horas semanales)
6. Panel de validación en tiempo real (llamada al backend → `validate()`)
7. OR-Tools: integrar CP-SAT solver con `add_constraints()` para las reglas existentes — este es el paso que reemplaza el generador greedy
8. Gestión de ausencias
9. Resto de reglas (prioridad de turno, equidad fines de semana, etc.)
10. Export xlsx
11. Resumen/métricas
12. Histórico y continuidad entre meses
