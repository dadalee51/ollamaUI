import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import configparser
import os
import aiohttp
import asyncio

CONFIG_FILE = 'config.ini'


class PromptAndResponseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Prompt and Response")
        self.root.config(bg="#000000")

        self.server_ip = tk.StringVar()
        self.instructions = tk.StringVar()

        self.load_history()
        self.load_configuration()
        self.create_widgets()

        self.history_index = -1
        self.current_prompt = ""

        # Initialize the asyncio event loop
        self.loop = asyncio.get_event_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(100, self.run_asyncio_loop)

    def create_widgets(self):
        # Container frame
        self.container = tk.Frame(self.root, bg="#1a1a1a", bd=2, relief="groove", padx=20, pady=20)
        self.container.grid(row=0, column=0, padx=50, pady=50)

        self.container.grid_rowconfigure(1, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Title
        self.title = tk.Label(self.container, text="Prompt and Response", font=("Courier New", 20), fg="#00FF00", bg="#1a1a1a")
        self.title.grid(row=0, column=0, sticky="w")

        # Server IP Address Input
        self.ip_label = tk.Label(self.container, text="Server IP Address:", font=("Courier New", 12), fg="#00FF00", bg="#1a1a1a")
        self.ip_label.grid(row=1, column=0, sticky="w")
        self.ip_entry = tk.Entry(self.container, textvariable=self.server_ip, font=("Courier New", 12), fg="#00FF00", bg="#0a0a0a", width=70, insertbackground="#00FF00")
        self.ip_entry.grid(row=2, column=0, pady=10, sticky="ew")

        # Instructions area
        self.instructions_label = tk.Label(self.container, text="Instructions:", font=("Courier New", 12), fg="#00FF00", bg="#1a1a1a")
        self.instructions_label.grid(row=3, column=0, sticky="w")
        self.instructions_entry = tk.Entry(self.container, textvariable=self.instructions, font=("Courier New", 12), fg="#00FF00", bg="#0a0a0a", width=70, insertbackground="#00FF00")
        self.instructions_entry.grid(row=4, column=0, pady=10, sticky="ew")
        self.instructions.trace("w", lambda *args: self.save_configuration())

        # Prompt text area
        self.prompt = scrolledtext.ScrolledText(self.container, wrap=tk.WORD, width=70, height=4, font=("Courier New", 12), fg="#00FF00", bg="#0a0a0a", borderwidth=1, relief="solid")
        self.prompt.grid(row=5, column=0, pady=10, sticky="ew")
        self.prompt.bind('<Up>', self.show_previous_prompt)
        self.prompt.bind('<Down>', self.show_next_prompt)
        self.prompt.config(insertbackground="white")  # Show cursor in the prompt area
        
        # Execute button
        self.execute_button = tk.Button(self.container, text="Get Response (Ctrl+Enter)", command=self.fetch_response, fg="#000000", bg="#00FF00", activebackground="#33FF33", font=("Courier New", 12))
        self.execute_button.grid(row=8, column=0, pady=10, sticky="ew")
        
        # Response area with scrollbar
        self.response_label = tk.Label(self.container, text="Current Response:", font=("Courier New", 12), fg="#00FF00", bg="#1a1a1a")
        self.response_label.grid(row=6, column=0, sticky="w")
        self.current_response = scrolledtext.ScrolledText(self.container, wrap=tk.WORD, width=70, height=6, font=("Courier New", 12), fg="#00FF00", bg="#0a0a0a", borderwidth=1, relief="solid")
        self.current_response.grid(row=7, column=0, pady=10, sticky="ew")
        self.current_response.config(state=tk.DISABLED)
        self.current_response.config(insertbackground="white")  # Show cursor in the response area

       

        self.root.bind('<Control-Return>', lambda event: self.fetch_response())

        # History area
        self.history_label = tk.Label(self.container, text="History", font=("Courier New", 16), fg="#00FF00", bg="#1a1a1a")
        self.history_label.grid(row=9, column=0, sticky="w")
        self.history = scrolledtext.ScrolledText(self.container, wrap=tk.WORD, width=70, height=10, font=("Courier New", 12), fg="#00FF00", bg="#0a0a0a", borderwidth=1, relief="solid")
        self.history.grid(row=10, column=0, pady=10, sticky="ew")
        self.history.config(insertbackground="white")  # Show cursor in the history area

        self.load_history()

    def fetch_response(self):
        prompt_text = self.prompt.get("1.0", tk.END).strip()
        server_ip = self.server_ip.get().strip()
        instructions_text = self.instructions.get().strip()

        if not server_ip:
            messagebox.showwarning("Warning", "Server IP Address cannot be empty!")
            return

        if not prompt_text:
            messagebox.showwarning("Warning", "Prompt cannot be empty!")
            return

        # Save current prompt to history
        self.add_to_history(prompt_text)

        # Save the current prompt in the logs
        self.current_response.config(state=tk.NORMAL)
        self.current_response.delete("1.0", tk.END)
        self.current_response.insert(tk.END, "Fetching response...")
        self.current_response.config(state=tk.DISABLED)

        asyncio.run_coroutine_threadsafe(self.get_response_from_model(prompt_text, instructions_text, server_ip), self.loop)

    async def get_response_from_model(self, prompt, instructions, server_ip):
        try:
            # Replace with your server's actual URL
            url = f"http://{server_ip}:11434/api/generate"
            headers = {'Content-Type': 'application/json'}
            data = {
                "model": "llama3:8b",
                "prompt": prompt,
                "instructions": instructions,
                "options": {"num_ctx": 4096}
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    response.raise_for_status()  # Raise an HTTPError for bad responses (4xx, 5xx)
                    response_content = ""

                    async for line in response.content:
                        decoded_line = line.decode('utf-8')
                        try:
                            data = json.loads(decoded_line)
                            if 'response' in data:
                                response_content += data['response']
                                self.root.after(0, self.update_text_widget, self.current_response, response_content)
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")

                    # Update history
                    self.root.after(0, self.history.insert, tk.END, f"Prompt: {prompt}\nResponse: {response_content}\n\n")

                    # Clear the prompt
                    self.root.after(0, self.prompt.delete, "1.0", tk.END)

                    # Save the configuration with the latest server IP
                    self.save_configuration()

        except aiohttp.ClientError as e:
            self.root.after(0, self.update_text_widget, self.current_response, f"Error fetching response: {e}")

    def update_text_widget(self, widget, text):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)

    def show_previous_prompt(self, event):
        if self.history_index > 0:
            if self.history_index == len(self.logs):  # Just entered history mode; save current prompt
                self.current_prompt = self.prompt.get("1.0", tk.END).strip()

            self.history_index -= 1
            previous_prompt = self.logs[self.history_index]['prompt']
            self.prompt.delete("1.0", tk.END)
            self.prompt.insert(tk.END, previous_prompt)

        return "break"

    def show_next_prompt(self, event):
        if self.history_index < len(self.logs) - 1:
            self.history_index += 1
            next_prompt = self.logs[self.history_index]['prompt']
            self.prompt.delete("1.0", tk.END)
            self.prompt.insert(tk.END, next_prompt)
        elif self.history_index == len(self.logs) - 1:
            self.history_index += 1
            self.prompt.delete("1.0", tk.END)
            self.prompt.insert(tk.END, self.current_prompt)

        return "break"

    def add_to_history(self, prompt):
        self.logs.append({"prompt": prompt, "response": ""})
        self.history_index = len(self.logs)
        self.save_history()

    def load_history(self):
        self.logs = []
        if os.path.exists(CONFIG_FILE):
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            if 'History' in config:
                for key in config['History']:
                    self.logs.append(json.loads(config['History'][key]))

    def save_history(self):
        config = configparser.ConfigParser()
        config['History'] = {}
        for index, log in enumerate(self.logs):
            config['History'][f"log_{index}"] = json.dumps(log)

        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

    def load_configuration(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            if 'Settings' in config:
                self.server_ip.set(config['Settings'].get('server_ip', ''))
                self.instructions.set(config['Settings'].get('instructions', ''))

    def save_configuration(self):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'server_ip': self.server_ip.get(),
            'instructions': self.instructions.get()
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

    def run_asyncio_loop(self):
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()
        self.root.after(100, self.run_asyncio_loop)

    def on_closing(self):
        self.loop.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PromptAndResponseApp(root)
    root.mainloop()