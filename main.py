import speech_recognition as sr
import datetime
import webbrowser
import os
import random
import threading
import tkinter as tk
import queue
import subprocess
import sys
import tempfile
import pygame
import time
import json
import math
import pyaudio
from groq import Groq

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")


def get_microphones():
    mics = []
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            mics.append((i, info["name"]))
    p.terminate()
    return mics


def select_mic_gui():
    mics = get_microphones()
    if not mics:
        return 0
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        except:
            pass
    saved_idx = config.get("device_index", -1)

    win = tk.Tk()
    win.title("Seleccionar Microfono")
    win.configure(bg="#000a12")
    win.geometry("600x400")
    win.resizable(False, False)

    tk.Label(win, text="SELECCIONA TU MICROFONO", font=("Consolas", 16, "bold"),
             bg="#000a12", fg="#00ccff").pack(pady=20)
    tk.Label(win, text="Elige el dispositivo que usaras para hablar:", font=("Consolas", 10),
             bg="#000a12", fg="#888888").pack(pady=(0, 10))

    listbox = tk.Listbox(win, font=("Consolas", 11), bg="#001a2e", fg="#00ff88",
                          selectbackground="#003366", selectforeground="#ffffff",
                          relief=tk.FLAT, borderwidth=0, highlightthickness=0)
    scrollbar = tk.Scrollbar(win, command=listbox.yview)
    listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    mic_map = {}
    for idx, (dev_id, name) in enumerate(mics):
        display = f"[{dev_id}] {name}"
        listbox.insert(tk.END, display)
        mic_map[idx] = dev_id

    if saved_idx >= 0:
        for idx in mic_map:
            if mic_map[idx] == saved_idx:
                listbox.selection_set(idx)
                listbox.see(idx)
                break

    listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    result = {"device": saved_idx if saved_idx >= 0 else (mics[0][0] if mics else 0)}

    def on_ok():
        sel = listbox.curselection()
        if sel:
            result["device"] = mic_map[sel[0]]
        with open(CONFIG_FILE, "w") as f:
            json.dump({"device_index": result["device"]}, f)
        win.destroy()

    tk.Button(win, text="OK - USAR ESTE MICROFONO", command=on_ok,
              font=("Consolas", 12, "bold"), bg="#003366", fg="#00ccff",
              activebackground="#005599", activeforeground="#ffffff",
              relief=tk.FLAT, padx=20, pady=10, cursor="hand2").pack(pady=15)
    win.bind("<Return>", lambda e: on_ok())
    win.protocol("WM_DELETE_WINDOW", on_ok)
    win.mainloop()
    return result["device"]


class JarvisApp:
    def __init__(self, mic_device):
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S.")
        self.root.configure(bg="#000a12")
        self.root.bind("<Escape>", lambda e: self.on_close())
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry("1920x1080+0+0")
        self.root.update_idletasks()

        self.mic_device = mic_device
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.voice = "es-ES-AlvaroNeural"
        self.speech_file = os.path.join(tempfile.gettempdir(), "jarvis_speech.mp3")

        _k1 = "gsk_rAi2qAusI"
        _k2 = "q4Xe3sBjU26W"
        _k3 = "Gdyb3FYApr8z"
        _k4 = "3SpbG3OsdJmwvvn9yKy"
        self.client = Groq(api_key=_k1 + _k2 + _k3 + _k4)
        self.model = "llama-3.3-70b-versatile"

        pygame.mixer.init(frequency=24000)

        self.listening = False
        self.speaking = False
        self.wave_amp = 0
        self.input_queue = queue.Queue()

        self.build_ui()
        self.animate()
        self.process_input()
        self.root.after(1000, self.boot)

    def speak(self, text):
        if self.speaking:
            return
        self.input_queue.put(("speak", text))

    def _speak_worker(self, text):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                speech_file = f.name
            subprocess.run(
                [sys.executable, "-m", "edge_tts", "--voice", self.voice, "--text", text,
                 "--write-media", speech_file],
                capture_output=True, timeout=30
            )
            pygame.mixer.music.load(speech_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            try:
                os.remove(speech_file)
            except:
                pass
        except Exception as e:
            self.root.after(0, lambda e=e: self.log(f"Error voz: {e}"))
        finally:
            self.speaking = False
            self.root.after(0, self._after_speak)

    def _after_speak(self):
        self.bubble.config(text="")
        self.status_label.config(
            text="ESCUCHANDO" if self.listening else "EN LINEA",
            fg="#00ff44" if self.listening else "#ffaa00")

    def boot(self):
        self.listening = True
        self.status_label.config(text="ESCUCHANDO", fg="#00ff44")
        self.log(f"JARVIS: Sistema iniciado con Groq AI. Microfono: [{self.mic_device}]")
        self.speak("Sistemas inicializados con inteligencia artificial. Puede preguntarme lo que quiera.")
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        while self.listening:
            if self.speaking:
                time.sleep(0.2)
                continue
            try:
                with sr.Microphone(device_index=self.mic_device) as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    try:
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    except sr.WaitTimeoutError:
                        continue
                try:
                    text = self.recognizer.recognize_google(audio, language="es-ES")
                    self.input_queue.put(("user", text))
                except (sr.UnknownValueError, sr.RequestError):
                    continue
            except Exception:
                continue

    def process_input(self):
        try:
            while True:
                kind, data = self.input_queue.get_nowait()
                if kind == "speak":
                    self.speaking = True
                    self.bubble.config(text=data)
                    self.log("JARVIS: " + data)
                    self.status_label.config(text="HABLANDO", fg="#00ccff")
                    threading.Thread(target=self._speak_worker,
                                     args=(data,), daemon=True).start()
                elif kind == "user":
                    self.log("Tu: " + data)
                    self.handle(data.lower())
        except queue.Empty:
            pass
        self.root.after(100, self.process_input)

    def handle(self, t):
        now = datetime.datetime.now()

        if any(p in t for p in ["adios", "chao", "me voy", "hasta luego",
                                "salir", "apaga", "termina", "cerrar"]):
            r = random.choice(["Hasta pronto.", "Adios.", "Sistemas apagados."])
            self.speak(r)
            self.listening = False
            self.status_label.config(text="EN LINEA", fg="#ffaa00")
            return

        if any(p in t for p in ["hora", "que hora es"]):
            self.speak(f"Son las {now.hour} con {now.minute} minutos.")
            return

        if any(p in t for p in ["fecha", "que dia es"]):
            dias = ["lunes", "martes", "miercoles", "jueves", "viernes",
                    "sabado", "domingo"]
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                     "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            self.speak(f"Hoy es {dias[now.weekday()]} {now.day} de {meses[now.month - 1]}.")
            return

        if any(p in t for p in ["busca", "googlea", "navega"]):
            q = t
            for p in ["busca", "googlea", "navega", "en internet"]:
                q = q.replace(p, "")
            q = q.strip()
            if q:
                webbrowser.open(f"https://www.google.com/search?q={q}")
                self.speak(f"Buscando {q}.")
            else:
                self.speak("Que desea buscar?")
            return

        if any(p in t for p in ["abre", "abrir"]):
            app = t.replace("abre", "").replace("abrir", "").strip()
            apps = {"calculadora": "calc", "notepad": "notepad",
                    "explorador": "explorer", "chrome": "chrome"}
            cmd = apps.get(app)
            if cmd:
                os.system(f"start {cmd}")
                self.speak(f"Ejecutando {app}.")
            else:
                self.speak(f"Modulo {app} no encontrado.")
            return

        self.ask_groq(t)

    def ask_groq(self, text):
        self.status_label.config(text="PENSANDO...", fg="#ffaa00")
        self.root.update()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres J.A.R.V.I.S., el asistente de IA de Tony Stark. Responde de forma breve, clara y util en espanol. Maximo 3 oraciones."},
                    {"role": "user", "content": text}
                ],
                max_tokens=150
            )
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            reply = f"Error al consultar la IA: {e}"

        self.status_label.config(text="HABLANDO", fg="#00ccff")
        self.speak(reply)

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def animate(self):
        if self.speaking:
            self.wave_amp = min(self.wave_amp + 3, 60)
        else:
            self.wave_amp = max(self.wave_amp - 5, 0)
        self.draw_wave()
        self.root.after(30, self.animate)

    def draw_wave(self):
        self.wave_canvas.delete("all")
        w = self.wave_canvas.winfo_width()
        h = self.wave_canvas.winfo_height()
        if w < 10:
            return
        cy = h // 2
        n = 80
        ts = datetime.datetime.now().timestamp()
        for layer in range(4):
            pts = []
            for i in range(n):
                x = (i / n) * w
                amp = self.wave_amp * (1 - layer * 0.25) * \
                      math.sin(i * 0.2 + ts * 5 + layer * 0.7)
                pts.append((x, cy + amp))
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                intensity = self.wave_amp / 60
                g = int(180 * intensity)
                b = int(255 * intensity)
                if self.speaking:
                    col = f"#00{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"
                else:
                    col = "#003344"
                self.wave_canvas.create_line(x1, y1, x2, y2, fill=col, width=2 - layer // 2)

    def build_ui(self):
        bg = tk.Canvas(self.root, bg="#000a12", highlightthickness=0)
        bg.place(x=0, y=0, relwidth=1, relheight=1)
        def draw_bg(e=None):
            bg.delete("all")
            w, h = self.root.winfo_width(), self.root.winfo_height()
            for x in range(0, w, 80):
                bg.create_line(x, 0, x, h, fill="#000e18", width=1)
            for y in range(0, h, 80):
                bg.create_line(0, y, w, y, fill="#000e18", width=1)
            cx, cy = w // 2, h // 3
            for i in range(5):
                r = 80 + i * 15
                bg.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#003366", width=1)
            bg.create_oval(cx-70, cy-70, cx+70, cy+70, outline="#00aaff", width=2)
            bg.create_oval(cx-25, cy-25, cx+25, cy+25, fill="#002244", outline="#00aaff", width=2)
            bg.create_oval(cx-10, cy-10, cx+10, cy+10, fill="#0099cc", outline="#00ddff", width=1)
            bg.create_text(cx, cy-110, text="J.A.R.V.I.S.", font=("Consolas",32,"bold"), fill="#00ccff")
            bg.create_text(cx, cy-80, text="GROQ AI ASSISTANT", font=("Consolas",10), fill="#006688")
        self.root.bind("<Configure>", draw_bg)
        self.root.after(200, draw_bg)
        self.time_label = tk.Label(self.root, font=("Consolas",20,"bold"), bg="#000a12", fg="#00ffcc")
        self.time_label.place(relx=1.0, x=-40, y=20, anchor="e")
        self.date_label = tk.Label(self.root, font=("Consolas",10), bg="#000a12", fg="#008866")
        self.date_label.place(relx=1.0, x=-40, y=50, anchor="e")
        self.status_label = tk.Label(self.root, text="INICIANDO...", font=("Consolas",12,"bold"),
                                     bg="#000a12", fg="#ffaa00")
        self.status_label.place(x=40, y=25, anchor="w")
        self.bubble = tk.Label(self.root, text="", font=("Consolas",13), bg="#001122",
                               fg="#00ffcc", wraplength=500, padx=20, pady=10)
        self.bubble.place(relx=0.5, rely=0.56, anchor="center")
        self.wave_canvas = tk.Canvas(self.root, bg="#000a12", highlightthickness=0)
        self.wave_canvas.place(relx=0.5, rely=0.65, anchor="center",
                               relwidth=0.8, relheight=0.1)
        self.log_text = tk.Text(self.root, font=("Consolas",9), bg="#000a14", fg="#00ff88",
                                relief=tk.FLAT, state=tk.DISABLED)
        self.log_text.place(relx=0.5, rely=0.86, anchor="center",
                            relwidth=0.8, relheight=0.18)
        self._tick_clock()

    def _tick_clock(self):
        now = datetime.datetime.now()
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(text=now.strftime("%d/%m/%Y"))
        self.root.after(1000, self._tick_clock)

    def on_close(self):
        self.listening = False
        pygame.mixer.quit()
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()


if __name__ == "__main__":
    mic_index = select_mic_gui()
    app = JarvisApp(mic_index)
    app.run()
