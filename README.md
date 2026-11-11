# HCM Countermeasure Roll-out 2027

App web (Streamlit) para controlar la ejecución de las **20 contramedidas HCM** en la flota FQM (**EH4000AC-3, EH3500AC-2 y EX5600-7**, unas 100 máquinas). La interfaz está en **inglés y japonés**. Misma estructura, estilo LANDCROS y forma de guardar datos que `App-Modification-HMCZ-`.

- **Supervisores:** registran el avance de cada camión en cada contramedida: planificado, pasos ejecutados (p. ej. RHS / LHS), FIR subido, reporte / hojas de tiempo, fechas, orden de trabajo y notas. Pueden trabajar **por contramedida** (todos los camiones en una tabla) o **por camión** (todas sus contramedidas).
- **Administradores:** ven el resumen y las alertas, la matriz **Top Page** (camión × contramedida), editan el plan de acción (responsable, fecha meta, duración, acción), agregan o quitan contramedidas y camiones, marcan N/A y generan el reporte en Excel, CSV y PDF.

---

## Cómo funciona

| Tema | Regla |
| --- | --- |
| **Registro** | Un camión × una contramedida. Pasos: *Planned*, pasos de ejecución de la contramedida, *FIR uploaded*, *Report / timesheets* |
| **Avance de un registro** | Pasos marcados ÷ pasos totales (igual que la columna *Progress* del Excel) |
| **Estado de un registro** | *Closed out* (ejecutado + FIR + reporte) · *Executed · docs open* (ejecutado, falta FIR o reporte) · *In progress* · *Not started* · *N/A* (no aplica, no cuenta) |
| **% de la flota** | Camiones ejecutados ÷ camiones aplicables. Es el *Fleet % complete* del plan de acción |
| **Estado de una contramedida** | *Done* (100 %) · *Overdue* (pasó la fecha meta) · *Due soon* (faltan 45 días o menos, configurable) · *On track* · *No target* |
| **Alertas** | Contramedidas vencidas o por vencer, camiones con fecha planificada pasada sin ejecutar y camiones ejecutados sin FIR o reporte |
| **Fecha de ejecución** | Al marcar todos los pasos de ejecución, si está vacía se completa con la fecha de hoy y se marca *Planned* |
| **N/A** | Solo el administrador lo cambia. Los camiones sin estado en el Excel (p. ej. RD220–RD227 en algunas hojas) empiezan como N/A |

Todas las reglas están en `core/project.py`. Los valores por defecto están en `core/config.py`.

---

## Estructura

```text
App-Project managment 2027 Countermeasure/
├── app.py                    ← Punto de entrada: vista pública, inicio de sesión, barra lateral y rutas
├── core/                     ← Lógica del negocio (sin interfaz)
│   ├── config.py             ← Estados, colores, rutas y valores por defecto
│   ├── project.py            ← Calcula el estado actual: avance, estados y alertas
│   ├── events.py             ← Registro de cambios (un archivo JSON por acción)
│   ├── auth.py               ← Usuarios y contraseñas (bcrypt)
│   ├── reports.py            ← Exportación en Excel (incluye hoja Top Page) y CSV
│   ├── executive_report.py   ← Plan de acción en PDF con membrete LANDCROS (fpdf2)
│   └── i18n.py               ← Textos en inglés y japonés
├── storage/                  ← Dónde se guardan los datos
│   ├── github_store.py       ← Rama `data` del repositorio (producción)
│   └── local_store.py        ← Carpeta local_data/ (pruebas, sin token)
├── ui/                       ← Interfaz de Streamlit
│   ├── supervisor.py         ← Registro de avance (por contramedida o por camión)
│   ├── admin.py              ← Vista del administrador (7 pestañas)
│   ├── matrix.py             ← Plan de acción y matriz Top Page (solo lectura)
│   ├── common.py             ← Piezas compartidas
│   └── theme.py              ← Estilo LANDCROS
├── seed/                     ← Datos de origen
│   ├── Countermeasures Progress Tracker V2-19-Oct-26.xlsx
│   ├── HCM-Countermeasure Action & Roll out Plan.pdf
│   ├── build_seed.py         ← Convierte el Excel y el plan de acción en los CSV de abajo
│   ├── countermeasures_seed.csv  ← 20 contramedidas: responsable, fecha meta, duración, acción, pasos
│   └── records_seed.csv      ← Estado inicial por camión × contramedida (1052 registros)
├── assets/                   ← Logo LANDCROS e imagen del EH5000
├── scripts/users.py          ← Gestión de usuarios (solo el dueño, desde la terminal)
└── tests/                    ← Pruebas automáticas (pytest)
```

### Rama `data` (la escribe la app, no se edita a mano)

```text
plan/countermeasures.csv      ← Catálogo de contramedidas (se copia una vez desde seed/)
plan/baseline.csv             ← Estado inicial desde el Excel (se copia una vez desde seed/)
plan/settings.json            ← Configuración inicial
users/users.json              ← Usuarios con contraseña cifrada
log/record/AAAA-MM/…json      ← Avance de un camión en una contramedida (un archivo por fila guardada)
log/meta/…                    ← Cambios del plan de acción (responsable, fecha meta, duración, acción)
log/scope/…                   ← Contramedidas y camiones agregados o quitados
log/settings/…                ← Cambios de configuración
reports/                      ← Reportes publicados desde la app (Excel y PDF)
```

Cada acción crea un archivo nuevo, que nunca se modifica después. Así, dos personas pueden guardar al mismo tiempo sin conflictos y queda el historial completo de quién hizo qué y cuándo. El estado actual se calcula leyendo esos archivos en orden.

---

## Ejecutar en tu Mac (modo local, sin token)

```bash
cd "~/Desktop/20261009　FQM対策チーム向け図面/Project managment HCM /App Management HCMZ/App-Project managment 2027 Countermeasure"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app.py
```

Sin archivo de secretos, la app guarda todo en `local_data/` (está en `.gitignore`). Para entrar en modo local, define el usuario maestro en `.streamlit/secrets.toml` (sección `[master]`, ver `secrets.toml.example`) y pulsa **Load the plan from the tracker** la primera vez.

Pruebas: `pytest -q`

Para empezar de cero en modo local, borra la carpeta `local_data/`.

Si cambia el Excel de seguimiento, reemplázalo en `seed/` y ejecuta `python seed/build_seed.py` **antes** de inicializar. Después de inicializar, los cambios se registran en la app.

---

## Conectar con GitHub (producción)

1. Crea el repositorio (p. ej. `App-Project-managment-2027-Countermeasure`) y sube esta carpeta a la rama `main`.
2. El dueño crea un **token fine-grained**: _Settings → Developer settings → Personal access tokens → Fine-grained tokens_.
   - **Repository access:** _Only select repositories_ → este repositorio.
   - **Permissions → Repository → Contents:** _Read and write_.
3. Copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y pega el token.
4. En Streamlit Community Cloud, pega el mismo contenido en _App settings → Secrets_.

El token **nunca** se sube al repositorio: `.streamlit/secrets.toml` está en `.gitignore`.

---

## Usuarios

- La app abre en la vista pública **View**: cualquiera con el link ve el plan de acción, la matriz Top Page y puede descargar el PDF, en modo solo lectura. El inicio de sesión está a la derecha.
- **Roles:** cada rol ve solo su vista.
  - **Admin:** resumen, Top Page, avance, contramedidas, camiones, reportes y configuración.
  - **Supervisor:** registro de avance e historial.
  - **Maestro** (dueño de la app): alterna entre ambas vistas. Se define en los secretos (sección `[master]`).
- Los usuarios los crea **solo el dueño** con `scripts/users.py`:

```bash
python scripts/users.py add                       # crear usuario
python scripts/users.py list                      # ver usuarios
python scripts/users.py password <usuario>        # restablecer contraseña
python scripts/users.py role <usuario> admin      # cambiar rol
python scripts/users.py deactivate <usuario>      # quitar acceso (conserva el historial)
python scripts/users.py master-hash               # generar la sección [master] de los secretos
```
