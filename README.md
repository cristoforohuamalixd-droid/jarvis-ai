# J.A.R.V.I.S. - Asistente de IA con Reconocimiento de Voz

Asistente virtual tipo Jarvis con inteligencia artificial (Groq), reconocimiento de voz y respuesta por voz en español.

## Versión Web (recomendada)

Usa Jarvis directamente en tu navegador:

👉 **https://cristoforohuamalixd-droid.github.io/jarvis-ai**

Funciona en Chrome y Edge. No requiere instalación.

### Cómo usar la web
1. Abre el enlace
2. Presiona **INICIAR** y concede permiso para el micrófono
3. Habla y Jarvis te responderá

## Versión Python (escritorio)

Para ejecutar localmente en Windows:

### Requisitos
- Python 3.8+
- Micrófono funcional

### Instalación
```bash
pip install -r requirements.txt
python main.py
```

### Comandos de voz
- "Hola" - Inicia conversación
- "¿Qué hora es?" - Escuchar la hora actual
- "¿Qué día es?" - Escuchar la fecha actual
- "Abre Chrome" - Abre calculadora, notepad, explorador o Chrome
- "Busca [tema]" - Busca en Google
- "Adiós" - Cierra la aplicación

## Tecnologías
- **IA**: Groq (Llama 3.3 70B)
- **Voz**: edge-tts (Python) / Web Speech API (web)
- **Reconocimiento**: Google Speech Recognition (Python) / Web Speech API (web)
- **Interfaz**: Tkinter (Python) / HTML5 Canvas (web)
