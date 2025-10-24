# TUI Gemini Commit Generator

Aplicación básica en **Python** que genera mensajes de commit siguiendo la especificación **Conventional Commits**, usando la **API de Gemini** de Google.

---

## Requisitos

- **Python 3.13** (o superior)
- **[uv](https://github.com/astral-sh/uv)** para manejar entornos virtuales y dependencias  
  Instálalo si no lo tienes:
  ```bash
  pip install uv
  ```
  *Puedes usar `pip` en vez de `uv` también*

---

## Instalación

Clona el repositorio y entra en la carpeta:

```bash
git clone https://github.com/plinkr/tui_gemini_commit_generator
cd tui_gemini_commit_generator
```

Crea el entorno virtual e instala dependencias usando `uv`:

```bash
uv venv --python 3.13
```

Activa el Entorno Virtual:
```bash
source .venv/bin/activate
```

Si estás en Windows, el comando puede ser:
```powershell
.venv\Scripts\activate
```

### Opción 1: Instalar dependencias básicas

```bash
uv pip install prompt_toolkit pyperclip requests
```

### Opción 2: Instalar desde `requirements.txt`

```bash
uv pip install -r requirements.txt
```

---

## Configurar la clave de API de Gemini

Antes de ejecutar la app, exporta tu clave de API de Gemini:

```bash
export GEMINI_API_KEY="AIzaYOURGEMINIAPIKEYHERE"
```

---

## Ejecución

Ejecuta la aplicación:

```bash
python tui_gemini_commit_generator.py
```

---

## Uso general

* Navega con `tab` / `Shift + tab`
* Genera un commit con `Ctrl + j`
* Copia la salida con `Ctrl + y`
* Muestra ayuda con `F1`
* Limpia el contexto con `Ctrl + l`
* Sal de la aplicación con `Esc` o `Ctrl + q`

---

## Dependencias

* [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/)
* [pyperclip](https://pypi.org/project/pyperclip/)
* [requests](https://pypi.org/project/requests/)


