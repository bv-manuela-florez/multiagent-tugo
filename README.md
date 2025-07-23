# 🤖 BV Multi-Agent Tugo

Este proyecto es una plataforma de orquestación de agentes inteligentes, con interfaz web (FastAPI) y almacenamiento de interacciones en Azure CosmosDB.

---

## 📁 Estructura del Proyecto

```
bv_ind_multiagent_tugo/
│
├── agents/                         # Agentes inteligentes (RAG, Interpreter, Selector)
│   ├── rag_agent/
│   │   └── agent_ai_search.py
│   ├── interpreter_agent/
│   │   └── agent_interpreter.py
│   └── selector_agent/
│       └── agent_selector.py
│
├── app/
│   └── routes.py                   # Rutas principales de la aplicación FastAPI
│
├── utils/
│   └── cosmos_utils.py             # Utilidades para CosmosDB
│
├── static/                         # Archivos estáticos (imágenes, generados, etc.)
│   ├── Tugo3.jpg
│   └── generated/
│
├── templates/                      # Templates Jinja2 para FastAPI
│   ├── chat.html
│   └── login.html
│
├── notebook/                       # Notebooks para pruebas y prototipos
│   └── results_500.csv
│
├── main.py                         # Punto de entrada FastAPI
├── requirements.txt                # Dependencias Python
└── README.md                       # Este archivo
```

---

## 🚀 ¿Qué hace este proyecto?

- Permite a usuarios autenticarse y chatear con agentes inteligentes.
- Orquesta agentes para responder preguntas o ejecutar tareas.
- Guarda todas las interacciones en Azure CosmosDB.
- Interfaz web usando FastAPI y Jinja2.

---

## ⚙️ Instalación y Ejecución

1. **Clona el repositorio y entra al directorio:**
    ```bash
    git clone <repo-url>
    cd bv_ind_multiagent_tugo
    ```

2. **Crea y configura tu entorno virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # o venv\Scripts\activate en Windows
    pip install -r requirements.txt
    ```

3. **Configura tus variables de entorno (.env):**
    - CosmosDB URL, KEY, DATABASE, CONTAINER
    - Credenciales de Azure para los agentes

4. **Ejecuta la aplicación:**
    ```bash
    uvicorn main:app --reload
    ```

5. **Accede a la interfaz web:**
    - Navega a [http://localhost:8000](http://localhost:8000)

---

## 🧠 Agentes

Los agentes están organizados en la carpeta `agents/`:

- **rag_agent/agent_ai_search.py**: Recuperación y generación de información.
- **interpreter_agent/agent_interpreter.py**: Interpreta y ejecuta instrucciones.
- **selector_agent/agent_selector.py**: Selecciona el agente adecuado según la consulta.

Puedes agregar nuevos agentes siguiendo la misma estructura.

---

## ☁️ Azure CosmosDB

Las interacciones de usuario se almacenan automáticamente en Azure CosmosDB usando el helper en `utils/cosmos_utils.py`.

---

## 🗂️ Organización recomendada

- **app/routes.py**: Todas las rutas de FastAPI.
- **utils/cosmos_utils.py**: Funciones para CosmosDB.
- **agents/**: Lógica de cada agente.
- **templates/**: HTML para la interfaz web.
- **static/**: Archivos estáticos.

---

## 🧑‍💻 Autor

**Manuela Florez**
BigView SAS

---

## 📜 Licencia

Licenciado por **BigView SAS**.
Uso no autorizado prohibido. Contacto: `legal@bigview.ai`

