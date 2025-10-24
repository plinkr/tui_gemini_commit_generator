#!/usr/bin/env python3
# uv venv --python 3.13
# source .venv/bin/activate
# uv pip install prompt_toolkit pyperclip requests 
# export GEMINI_API_KEY=AIzaYOURGEMINIAPIKEYHERE
import json
import os
import subprocess
import threading

import pyperclip
import requests
from prompt_toolkit.application import Application
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.widgets import (
    Box, Button, Label, RadioList, TextArea, Frame, Dialog
)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_URLS = {
    "flash": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    "pro": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
}

DEFAULT_PROMPT = """Eres un modelo de inteligencia artificial altamente capacitado en las mejores prácticas de desarrollo de software, específicamente para generar mensajes de commit siguiendo la especificación de Conventional Commits.
            Dado el Git diff que se proporciona a continuación, por favor genera un título y cuerpo de commit adecuado de acuerdo a las directrices de Conventional Commits:
            - Choose a type from the type-to-description below that best describes the git diff:
                        "docs": "Documentation only changes",
                        "style": "Changes that do not affect the meaning of the code",
                        "refactor": "A code change that neither fixes a bug nor adds a feature",
                        "perf": "A code change that improves performance",
                        "test": "Adding missing tests or correcting existing tests",
                        "build": "Changes that affect the build system or external dependencies",
                        "ci": "Changes to our CI configuration files and scripts",
                        "chore": "Other changes that don't modify src or test files",
                        "revert": "Reverts a previous commit",
                        "feat": "A new feature",
                        "fix": "A bug fix"
            - Proporciona un título conciso para el commit (no más de 72 caracteres).
            - Opcionalmente, incluye un cuerpo detallado del commit que explique el propósito de los cambios, la justificación y cualquier contexto relevante. Nunca uses comillas simples '' ni comillas dobles "" en el cuerpo detallado, en su caso usa backticks `` solamente.
"""

# --- Estado de la ayuda ---
show_help = False

# --- Widgets ---
lang_selector = RadioList([("es", "Español"), ("en", "English")])
model_selector = RadioList([("pro", "pro"), ("flash", "flash")])
temp_field = TextArea(text="0.2", height=1)
context_area = TextArea(text="", height=5)
prompt_area = TextArea(text=DEFAULT_PROMPT, height=15, scrollbar=True, multiline=True)
output_area = TextArea(text="", height=20, scrollbar=True, wrap_lines=True)
status_label = Label(text="F1 -> Help")

# --- Contenido de ayuda ---
HELP_CONTENT = """
CONTROLES DE TECLADO:

Navegación:
  Tab              - Siguiente campo
  Shift + Tab      - Campo anterior
  Ctrl + p         - Enfocar Prompt Base
  Ctrl + t         - Enfocar Contexto
  Ctrl + o         - Enfocar Salida

Acciones:
  F1               - Mostrar/ocultar esta ayuda
  Ctrl + j         - Generar commit
  Ctrl + y         - Copiar salida al portapapeles
  Ctrl + l         - Limpiar campo de contexto y enfocarlo
  Ctrl + q / Esc   - Cerrar ayuda o salir de la aplicación
  Ctrl + a         - Seleccionar todo el texto en el campo actual
  Ctrl + c         - Copiar texto seleccionado al portapapeles

CAMPOS:

• Lenguaje        - Idioma del mensaje de commit (Español/English)
• Modelo          - Modelo Gemini a utilizar (pro/flash)
• Temperatura     - Creatividad del modelo (0.1-1.0)
• Contexto        - Información adicional para el modelo
• Prompt Base     - Instrucciones base para el modelo (editable)
• Salida          - Resultado generado por el modelo

USO:
1. Configura lenguaje, modelo y temperatura según necesites
2. Opcionalmente agrega contexto en el campo correspondiente
3. Presiona Ctrl+j para generar el mensaje de commit
4. Usa Ctrl+y para copiar el resultado al portapapeles
5. El mensaje se genera basado en los cambios stageados (git diff --cached)
"""


# --- Helpers ---
def get_git_diff():
    try:
        return subprocess.check_output(["git", "diff", "--cached"], universal_newlines=True)
    except Exception:
        return ""


def build_prompt(lang, context):
    text = prompt_area.text
    if context.strip():
        text += f"\n\nUse the following context to understand intent:\n{context}"
    if lang == "es":
        text += "\n\nAhora, genera el mensaje de commit correcto basado en esta información. En español, ten en cuenta una buena ortografía y usa acentos donde sea necesario.\nAquí está el Git diff:\n"
    else:
        text += "\n\nNow, generate the correct commit message based on this information. In English language.\nHere is the Git diff:\n"
    text += get_git_diff()
    return text


def ensure_key():
    if not API_KEY:
        raise RuntimeError("Falta GEMINI_API_KEY en entorno.")
    return API_KEY


def call_gemini(prompt, temp, model):
    url = f"{MODEL_URLS[model]}?key={ensure_key()}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": float(temp)},
    }
    r = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    j = r.json()
    try:
        return (
            j.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        ) or json.dumps(j, indent=2)
    except Exception:
        return json.dumps(j, indent=2)


# --- Función para copiar texto seleccionado ---
def copy_selected_text():
    if show_help:
        return

    focused_widget = app.layout.current_control

    # Verificar si es un TextArea y tiene texto seleccionado
    if (hasattr(focused_widget, 'buffer') and
            hasattr(focused_widget.buffer, 'selection_state') and
            focused_widget.buffer.selection_state):

        # Obtener el texto seleccionado
        selected_text = focused_widget.buffer.copy_selection()
        if selected_text:
            pyperclip.copy(selected_text.text)
            status_label.text = "Texto seleccionado copiado"
            app.invalidate()
            return

    status_label.text = "No hay texto seleccionado"
    app.invalidate()


# --- Función para seleccionar todo el texto ---
def select_all_text():
    if show_help:
        return

    focused_widget = app.layout.current_control

    # Verificar si es un TextArea y tiene buffer
    if hasattr(focused_widget, 'buffer'):
        # Seleccionar todo el texto
        focused_widget.buffer.cursor_position = 0
        focused_widget.buffer.start_selection()
        focused_widget.buffer.cursor_position = len(focused_widget.buffer.text)
        status_label.text = "Todo el texto seleccionado"
        app.invalidate()
    else:
        status_label.text = "No se puede seleccionar texto en este campo"
        app.invalidate()


# --- Acciones ---
def generate_commit():
    if show_help:
        return
    status_label.text = "Generando..."
    app.invalidate()

    def task():
        try:
            prompt = build_prompt(lang_selector.current_value, context_area.text)
            text = call_gemini(prompt, temp_field.text.strip() or "0.2", model_selector.current_value)
            output_area.text = text
            status_label.text = "Hecho"
        except Exception as e:
            output_area.text = f"Error: {e}"
            status_label.text = "Error"
        app.invalidate()

    threading.Thread(target=task, daemon=True).start()


def copy_output():
    if show_help:
        return
    pyperclip.copy(output_area.text)
    status_label.text = "Copiado al portapapeles"
    app.invalidate()


def quit_app():
    app.exit()


def focus_context():
    if not show_help:
        app.layout.focus(context_area)


def focus_prompt():
    if not show_help:
        app.layout.focus(prompt_area)


def focus_output():
    if not show_help:
        app.layout.focus(output_area)


def toggle_help():
    global show_help
    show_help = not show_help
    app.layout = create_layout()
    app.invalidate()


# --- Botones ---
generate_btn = Button(text="Generar", handler=generate_commit)
copy_btn = Button(text="Copiar", handler=copy_output)
quit_btn = Button(text="Salir", handler=quit_app)

# --- Diálogo de ayuda ---
help_text_area = TextArea(
    text=HELP_CONTENT,
    read_only=True,
    scrollbar=True,
    multiline=True,
    height=35,
    width=80
)

help_dialog = Dialog(
    title="Ayuda - Controles de la Aplicación",
    body=HSplit([
        help_text_area
    ]),
    buttons=[
        Button(text="Cerrar (Esc)", handler=toggle_help)
    ],
    with_background=True
)

# --- Panel superior (controles + contexto + prompt) ---
top_panel = VSplit([
    # Panel izquierdo, controles
    Box(
        Frame(
            HSplit([
                Label(text="Lenguaje"),
                lang_selector,
                Label(text="Modelo"),
                model_selector,
                Label(text="Temperatura"),
                temp_field,
                Label(text="Contexto"),
                context_area,
                VSplit([generate_btn, copy_btn, quit_btn], padding=2, width=D(weight=1)),
            ]),
            title="Controles",
        ),
        padding=0,
        width=D(weight=45),  # 45%
    ),
    # Panel derecho
    Box(
        Frame(
            HSplit([
                prompt_area,
            ]),
            title="Prompt Base",
        ),
        padding=0,
        width=D(weight=55),  # 55%
    ),
],
    padding=1,
)

# --- Panel intermedio (status) ---
status_panel = Frame(
    HSplit([
        status_label,
    ]),
    title="Estado",
    height=3
)

# --- Panel inferior (salida del modelo) ---
bottom_panel = Frame(
    HSplit([
        output_area,
    ]),
    title="Salida del modelo"
)

# --- Layout principal ---
root_content = HSplit([
    top_panel,
    status_panel,
    bottom_panel
], padding=0)


def create_layout():
    if show_help:
        return Layout(
            HSplit([
                Window(height=1),
                help_dialog
            ])
        )
    else:
        return Layout(Box(root_content, padding=0))


# --- Atajos de teclado ---
kb = KeyBindings()


@kb.add("tab")
def _(event):
    if not show_help:
        event.app.layout.focus_next()


@kb.add("s-tab")
def _(event):
    if not show_help:
        event.app.layout.focus_previous()


@kb.add("c-q")
@kb.add("escape")
def _(event):
    if show_help:
        toggle_help()
    else:
        event.app.exit()


@kb.add("c-y")
def _(event):
    copy_output()


@kb.add("c-j")
def _(event):
    generate_commit()


@kb.add("c-p")
def _(event):
    focus_prompt()


@kb.add("c-t")
def _(event):
    focus_context()


@kb.add("c-l")
def _(event):
    if not show_help:
        context_area.text = ""
        app.layout.focus(context_area)
        status_label.text = "Contexto limpiado"
        app.invalidate()


@kb.add("c-o")
def _(event):
    focus_output()


@kb.add("f1")
def _(event):
    toggle_help()


@kb.add("c-c")
def _(event):
    copy_selected_text()


@kb.add("c-a")
def _(event):
    select_all_text()


# --- App ---
app = Application(
    layout=create_layout(),
    key_bindings=kb,
    full_screen=True,
    mouse_support=True,
    clipboard=PyperclipClipboard()
)

if __name__ == "__main__":
    lang_selector.current_value = "es"
    model_selector.current_value = "pro"
    app.run()
