# 🚀 Guía Rápida: Prepárate para el Taller de IA

¡Bienvenido! Sigue estos pasos para tener tu entorno listo en menos de 10 minutos.

---

## 🛠️ 1. Instalación de Software

Descarga e instala estas tres herramientas básicas:

*   **Python (3.9+)**: [Descargar aquí](https://www.python.org/downloads/) (Asegúrate de marcar "Add Python to PATH" durante la instalación).
*   **VS Code**: [Descargar aquí](https://code.visualstudio.com/) (El editor que usaremos).
*   **Git**: [Descargar aquí](https://git-scm.com/downloads) (Para bajar el código).

---

## 🔑 2. Obtén tus API Keys (Nivel Gratuito)

Necesitaremos "llaves" para hablar con la IA. Sigue estos enlaces y guarda las llaves que generes:

1.  **Google Gemini (Recomendado)**: [Google AI Studio](https://aistudio.google.com/app/apikey)
    *   *Ventaja*: Nivel gratuito muy amplio para experimentar.
2.  **Tavily (Búsqueda Web)**: [Tavily AI](https://tavily.com/)
    *   *Ventaja*: Permite que tu IA busque en Google/Internet gratis.
3.  **LangSmith (Monitoreo)**: [LangSmith](https://smith.langchain.com/)
    *   *Ventaja*: Para ver qué está pensando tu IA por detrás.

---

## 💻 3. Configuración del Proyecto

Abre una terminal (PowerShell o CMD) y pega estos comandos:

```bash
# 1. Clona el repositorio
git clone <url-del-repositorio>
cd "Taller de IA"

# 2. Crea y activa tu entorno virtual
python -m venv venv
# En Windows:
venv\Scripts\activate

# 3. Instala las librerías necesarias
pip install -r requirements.txt

# 4. Crea tu archivo de configuración
copy .env.example .env
```

> [!TIP]
> Ahora abre el archivo `.env` recién creado en VS Code y pega tus llaves donde dice `your_api_key_here`.

---

## ✅ 4. Validación Final

Para saber si todo está bien, corre esto en tu terminal:

```bash
python --version
pip list | findstr langchain
```

**¡Listo! Estás preparado para empezar a construir. 🦸‍♂️**
