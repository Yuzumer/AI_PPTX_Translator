import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import threading
import queue
import os
import asyncio
from workflow import run_translation_workflow


class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PowerPoint Translator")
        self.root.geometry("600x750")

        self.input_path = ""
        self.output_folder = ""
        self.is_running = False

        self.input_label = tk.Label(root, text="No PowerPoint file selected", wraplength=580)
        self.input_button = tk.Button(root, text="Select PowerPoint File", command=self.select_input_file)
        self.lang_label = tk.Label(root, text="Select Target Language:")
        self.language_options = ["Japanese", "Vietnamese", "Korean", "English", "Simplified Chinese", "French",
                                 "German", "Spanish"]
        self.language_var = tk.StringVar(value=self.language_options[0])
        self.lang_dropdown = ttk.Combobox(root, textvariable=self.language_var, values=self.language_options,
                                          state='readonly')
        self.instructions_label = tk.Label(root,
                                           text="Enter Additional Instructions (e.g., brand names not to translate):")
        self.instructions_text = scrolledtext.ScrolledText(root, height=8, width=70)
        self.output_label = tk.Label(root, text="No output folder selected", wraplength=580)
        self.output_button = tk.Button(root, text="Select Output Location", command=self.select_output_folder)
        self.translate_button = tk.Button(root, text="Translate!", command=self.start_translation,
                                          font=("Arial", 12, "bold"))
        self.progress_bar = ttk.Progressbar(root, orient='horizontal', length=100, mode='determinate')
        self.status_label = tk.Label(root, text="Status Log:")
        self.status_log = scrolledtext.ScrolledText(root, height=15, width=70, state=tk.DISABLED)

        self.input_button.pack(pady=(10, 0))
        self.input_label.pack(pady=5)
        self.lang_label.pack(pady=(15, 5))
        self.lang_dropdown.pack(pady=5)
        self.instructions_label.pack(pady=(15, 5))
        self.instructions_text.pack(pady=5)
        self.output_button.pack(pady=10)
        self.output_label.pack(pady=5)
        self.translate_button.pack(pady=20)
        self.progress_bar.pack(pady=5, fill=tk.X, padx=10)
        self.status_label.pack(pady=5)
        self.status_log.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

    def select_input_file(self):
        if self.is_running: return
        path = filedialog.askopenfilename(title="Select PowerPoint File", filetypes=(("PowerPoint files", "*.pptx"),))
        if path:
            self.input_path = path
            self.input_label.config(text=self.input_path)

    def select_output_folder(self):
        if self.is_running: return
        path = filedialog.askdirectory(title="Select Folder to Save Translated File")
        if path:
            self.output_folder = path
            self.output_label.config(text=self.output_folder)

    def log_status(self, message):
        self.status_log.config(state=tk.NORMAL)
        self.status_log.insert(tk.END, message + "\n")
        self.status_log.see(tk.END)
        self.status_log.config(state=tk.DISABLED)

    def check_queue(self):
        try:
            while True:
                message_type, payload = self.status_queue.get_nowait()
                if message_type == 'log':
                    self.log_status(payload)
                elif message_type == 'progress':
                    self.progress_bar['value'] = payload
                elif message_type == 'finished':
                    self.is_running = False
                    self.translate_button.config(state=tk.NORMAL)
                    return  # Stop checking the queue
        except queue.Empty:
            pass
        finally:
            if self.is_running:
                self.root.after(100, self.check_queue)

    def start_translation(self):
        if not self.input_path or not self.output_folder:
            self.log_status("ERROR: Please select an input file and an output folder.")
            return

        self.is_running = True
        self.translate_button.config(state=tk.DISABLED)
        self.log_status("=" * 40)
        self.log_status("Starting ASYNC translation process...")
        self.progress_bar['value'] = 0

        user_instructions = self.instructions_text.get("1.0", tk.END).strip()
        selected_language = self.language_var.get()
        self.status_queue = queue.Queue()

        # This wrapper function is what our thread will actually run.
        # Its job is to set up and run the asyncio event loop.
        def thread_starter():
            asyncio.run(run_translation_workflow(
                self.input_path,
                self.output_folder,
                user_instructions,
                self.status_queue,
                selected_language
            ))

        self.thread = threading.Thread(target=thread_starter)
        self.thread.start()
        self.root.after(100, self.check_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = TranslatorApp(root)
    root.mainloop()