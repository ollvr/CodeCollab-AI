import os
import json
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading
from langchain_ollama import OllamaLLM  # Updated import to use OllamaLLM

CONVERSATION_DIR = "conversations"
if not os.path.exists(CONVERSATION_DIR):
    os.makedirs(CONVERSATION_DIR)

MODEL_CONTEXT_WINDOWS = {
    "deepseek-coder": 128000,
    "qwen2.5-coder:latest": 128000,
    "deepseek-r1": 128000,
}

def estimate_tokens(text):
    return len(text) // 4

def get_available_models():
    return ["qwen2.5-coder:latest", "deepseek-coder", "deepseek-r1"]

def load_conversation(filename):
    try:
        with open(os.path.join(CONVERSATION_DIR, filename), "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading conversation {filename}: {e}")
        return []

def save_conversation(filename, chat_history):
    try:
        with open(os.path.join(CONVERSATION_DIR, filename), "w") as f:
            json.dump(chat_history, f)
    except Exception as e:
        print(f"Error saving conversation {filename}: {e}")

def create_initial_prompt(request, chat_history):
    history_text = "\n".join([f"{entry['role']}: {entry['content']}" for entry in chat_history])
    return f"""Here is the conversation history so far:

{history_text}

The programmer has made the following request:

{request}

Your task is to understand the programmer's goal and provide a helpful response. This could involve:
- Generating complete, working code if they ask for it, along with a clear explanation.
- Explaining a concept or code clearly and concisely if they seek understanding.
- Identifying and fixing issues if they provide code with errors or ask for improvements.
Please interpret their request and respond with a solution that meets their goal.
"""

def create_helper_prompt(request, main_response, chat_history, feedback_description=""):
    history_text = "\n".join([f"{entry['role']}: {entry['content']}" for entry in chat_history])
    print("HISTORY TEXT :",history_text)
    feedback_text = f"The programmer said: {feedback_description}" if feedback_description else "The programmer didn't provide specific feedback."
    return f"""We're in a group discussion to help a programmer. Here's the conversation so far:

{history_text}

The programmer asked: 

{request}

I responded with:

{main_response}

But it wasn't helpful. {feedback_text}
Can you suggest a better solution? Please:
- Provide complete code if applicable.
- Include a clear explanation.
- Focus on accurately addressing the programmer's goal.
"""

def create_improved_prompt(request, chat_history, latest_main_response, helper1_response, helper2_response, feedback_description=""):
    history_text = "\n".join([f"{entry['role']}: {entry['content']}" for entry in chat_history])
    feedback_text = f"The programmer said: {feedback_description}" if feedback_description else "The programmer didn't provide specific feedback."
    return f"""We're working together to solve the programmer's request. Here's the conversation history:

{history_text}

The programmer asked:

{request}

My latest response was:

{latest_main_response}

But it wasn't helpful. {feedback_text}
Here’s what the team suggested:

Helper 1 said:

{helper1_response}

Helper 2 said:

{helper2_response}

Now, it’s my turn again. Using the helpers’ suggestions and the history:
- Provide an improved response that accurately meets the programmer’s goal.
- Include complete code if applicable, with a clear explanation.
- Correct any mistakes from my previous attempt.
"""

class CodingAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeCollab AI")
        self.root.minsize(900, 600)
        self.root.configure(bg="#1e1e2f")

        self.chat_history = []
        self.current_conversation = None
        self.main_llm = None
        self.helper1_llm = None
        self.helper2_llm = None
        self.state = "initial"
        self.latest_request = None
        self.latest_main_response = None
        self.helper1_response = None
        self.helper2_response = None
        self.feedback_description = ""

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", font=("Roboto", 12), background="#1e1e2f", foreground="#ffffff")
        self.style.configure("Sidebar.TLabel", font=("Roboto", 12, "bold"), foreground="#ffffff")
        self.style.configure("TCombobox", font=("Roboto", 11), fieldbackground="#2a2a3b", background="#2a2a3b", foreground="#ffffff")
        self.style.configure("TButton", font=("Roboto", 11), padding=5)
        self.style.map("TButton", background=[('active', '#5e5e8d')], foreground=[('active', '#ffffff')])

        self.main_frame = tk.Frame(root, bg="#1e1e2f")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.left_sidebar = tk.Frame(self.main_frame, bg="#2a2a3b", width=250, relief="flat", borderwidth=0)
        self.left_sidebar.pack(side="left", fill="y", padx=(0, 5))

        models = get_available_models()
        ttk.Label(self.left_sidebar, text="Main Developer", style="Sidebar.TLabel").pack(pady=(10, 5), padx=10)
        self.main_model_var = tk.StringVar(value=models[0])
        self.main_model_menu = ttk.Combobox(self.left_sidebar, textvariable=self.main_model_var, values=models)
        self.main_model_menu.pack(pady=5, padx=10, fill="x")

        ttk.Label(self.left_sidebar, text="Helper 1", style="Sidebar.TLabel").pack(pady=(10, 5), padx=10)
        self.helper1_model_var = tk.StringVar(value=models[0])
        self.helper1_model_menu = ttk.Combobox(self.left_sidebar, textvariable=self.helper1_model_var, values=models)
        self.helper1_model_menu.pack(pady=5, padx=10, fill="x")

        ttk.Label(self.left_sidebar, text="Helper 2", style="Sidebar.TLabel").pack(pady=(10, 5), padx=10)
        self.helper2_model_var = tk.StringVar(value=models[0])
        self.helper2_model_menu = ttk.Combobox(self.left_sidebar, textvariable=self.helper2_model_var, values=models)
        self.helper2_model_menu.pack(pady=5, padx=10, fill="x")

        ttk.Label(self.left_sidebar, text="Conversations", style="Sidebar.TLabel").pack(pady=(10, 5), padx=10)
        self.conversation_listbox = tk.Listbox(self.left_sidebar, bg="#2a2a3b", fg="#ffffff", font=("Roboto", 11),
                                               borderwidth=0, highlightthickness=0, selectbackground="#5e5e8d")
        self.conversation_listbox.pack(fill="both", expand=True, padx=10, pady=5)
        self.conversation_listbox.bind("<<ListboxSelect>>", self.load_conversation)
        self.update_conversation_list()

        ttk.Button(self.left_sidebar, text="New Chat", command=self.new_conversation).pack(pady=5, padx=10, fill="x")
        ttk.Button(self.left_sidebar, text="Delete Chat", command=self.delete_conversation).pack(pady=5, padx=10, fill="x")

        self.chat_frame = tk.Frame(self.main_frame, bg="#ffffff", relief="flat", borderwidth=1)
        self.chat_frame.pack(side="left", fill="both", expand=True, padx=5)

        self.chat_display = tk.Text(self.chat_frame, wrap="word", state="disabled", bg="#ffffff", fg="#1e1e2f",
                                    font=("Fira Code", 11), borderwidth=0, highlightthickness=0)
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=10)
        self.chat_display.tag_configure("role", foreground="#5e5e8d", font=("Roboto", 11, "bold"))

        self.input_frame = tk.Frame(self.chat_frame, bg="#f0f0f5")
        self.input_frame.pack(fill="x", padx=10, pady=10)
        self.input_entry = ttk.Entry(self.input_frame, font=("Roboto", 11))
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self.send_prompt)
        self.send_button = ttk.Button(self.input_frame, text="Send", command=self.send_prompt, style="Accent.TButton")
        self.style.configure("Accent.TButton", background="#5e5e8d", foreground="#ffffff")
        self.send_button.pack(side="right")

        self.right_sidebar = tk.Frame(self.main_frame, bg="#2a2a3b", width=150, relief="flat", borderwidth=0)
        self.right_sidebar.pack(side="right", fill="y", padx=(5, 0))

        ttk.Label(self.right_sidebar, text="Quick Start Guide", style="Sidebar.TLabel").pack(pady=(10, 5), padx=10)
        notes_frame = tk.Frame(self.right_sidebar, bg="#2a2a3b")
        notes_frame.pack(fill="both", expand=True, padx=10, pady=5)
        notes_text = tk.Text(notes_frame, wrap="word", bg="#2a2a3b", fg="#d0d0e0", font=("Roboto", 11),
                             height=20, borderwidth=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(notes_frame, command=notes_text.yview, bg="#2a2a3b", troughcolor="#1e1e2f")
        notes_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        notes_text.pack(side="left", fill="both", expand=True)
        notes_text.insert("1.0", """
                          
• Download & install Ollama to enable app functionality.

• Select coding-optimized models from Ollama based on your hardware.

• Replace the default LLMs by editing the get_available_models() method with your preferred models.

• Pay attention to change also the model context window with the correct values .

• This app leverages 3 LLMs for collaboration choose wisely!

• Start by clicking "New Chat," naming it, and diving in.

• Response times vary with hardware; Ollama shines on GPUs.

• How it works :

    • The Main LLM delivers the first response to your query.
    
    • You’ll be asked, “Was it helpful?” (Type "yes" or "no").
    
    • If "yes," keep chatting or start a new query.
    
    • If "no," describe the issue (or press Enter to skip). The Main LLM will team up with helper LLMs to refine its answer.

• Love the app? Star us on GitHub!
""")
        notes_text.config(state="disabled")

    def update_conversation_list(self):
        self.conversation_listbox.delete(0, tk.END)
        for filename in os.listdir(CONVERSATION_DIR):
            if filename.endswith(".json"):
                self.conversation_listbox.insert(tk.END, filename[:-5])

    def new_conversation(self):
        name = simpledialog.askstring("New Chat", "Name your new conversation:", parent=self.root)
        if name:
            self.current_conversation = name + ".json"
            self.chat_history = []
            self.state = "initial"
            self.update_chat_display()
            self.save_conversation()
            self.update_conversation_list()

    def load_conversation(self, event):
        selection = self.conversation_listbox.curselection()
        if selection:
            filename = self.conversation_listbox.get(selection[0]) + ".json"
            self.current_conversation = filename
            self.chat_history = load_conversation(filename)
            if self.chat_history:
                last_entry = self.chat_history[-1]
                if last_entry["role"] == "System" and "Was this response helpful?" in last_entry["content"]:
                    self.state = "awaiting_feedback"
                elif last_entry["role"] == "System" and "Please describe what went wrong" in last_entry["content"]:
                    self.state = "awaiting_description"
                else:
                    self.state = "initial"
            else:
                self.state = "initial"
            self.update_chat_display()

    def delete_conversation(self):
        selection = self.conversation_listbox.curselection()
        if selection:
            filename = self.conversation_listbox.get(selection[0]) + ".json"
            if messagebox.askyesno("Confirm", "Delete this conversation?", parent=self.root):
                os.remove(os.path.join(CONVERSATION_DIR, filename))
                self.update_conversation_list()
                if self.current_conversation == filename:
                    self.chat_history = []
                    self.current_conversation = None
                    self.state = "initial"
                    self.update_chat_display()

    def save_conversation(self):
        if self.current_conversation:
            save_conversation(self.current_conversation, self.chat_history)

    def update_chat_display(self):
        self.chat_display.config(state="normal")
        self.chat_display.delete("1.0", tk.END)
        for entry in self.chat_history:
            self.chat_display.insert(tk.END, f"[{entry['role']}] ", "role")
            self.chat_display.insert(tk.END, f"{entry['content']}\n\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)

    def send_prompt(self, event=None):
        user_input = self.input_entry.get().strip().lower()
        self.input_entry.delete(0, tk.END)
        if self.state == "initial":
            self.latest_request = user_input
            self.chat_history.append({"role": "Programmer", "content": self.latest_request})
            self.update_chat_display()
            self.save_conversation()
            threading.Thread(target=self.generate_initial_response).start()
            self.state = "awaiting_feedback"
        elif self.state == "awaiting_feedback":
            if user_input in ["yes", "no"]:
                self.chat_history.append({"role": "Programmer", "content": f"Was this helpful? {user_input}"})
                self.update_chat_display()
                self.save_conversation()
                if user_input == "yes":
                    self.chat_history.append({"role": "Main Developer", "content": "Awesome! Glad we got it right."})
                    self.update_chat_display()
                    self.save_conversation()
                    self.state = "initial"
                else:
                    self.chat_history.append({"role": "System", "content": "Please describe what went wrong or what you expected. (Press Enter to skip)"})
                    self.update_chat_display()
                    self.save_conversation()
                    self.state = "awaiting_description"
            else:
                self.chat_history.append({"role": "System", "content": "Please respond with 'yes' or 'no'."})
                self.update_chat_display()
        elif self.state == "awaiting_description":
            self.feedback_description = user_input if user_input else ""
            if self.feedback_description:
                self.chat_history.append({"role": "Programmer", "content": f"Feedback: {self.feedback_description}"})
            else:
                self.chat_history.append({"role": "Programmer", "content": "No specific feedback provided."})
            self.update_chat_display()
            self.save_conversation()
            threading.Thread(target=self.consult_helpers).start()
            self.state = "awaiting_feedback"

    def generate_initial_response(self):
        if not self.main_llm:
            self.main_llm = OllamaLLM(model=self.main_model_var.get())  # Updated to use OllamaLLM
            self.helper1_llm = OllamaLLM(model=self.helper1_model_var.get())  # Updated to use OllamaLLM
            self.helper2_llm = OllamaLLM(model=self.helper2_model_var.get())  # Updated to use OllamaLLM
        prompt = create_initial_prompt(self.latest_request, self.chat_history)
        self.latest_main_response = self.main_llm.invoke(prompt)  # Updated to use invoke
        self.chat_history.append({"role": "Main Developer", "content": self.latest_main_response})
        self.chat_history.append({"role": "System", "content": "Was this response helpful? (yes/no)"})
        self.update_chat_display()
        self.save_conversation()

    def consult_helpers(self):
        # Create the prompt for the helpers based on the latest request and feedback
        helper_prompt = create_helper_prompt(self.latest_request, self.latest_main_response, self.chat_history, self.feedback_description)
        
        # Generate and display Helper 1's response immediately
        self.helper1_response = self.helper1_llm.invoke(helper_prompt)
        self.chat_history.append({"role": "Helper 1", "content": self.helper1_response})
        self.update_chat_display()
        self.save_conversation()
        
        # Generate and display Helper 2's response immediately
        self.helper2_response = self.helper2_llm.invoke(helper_prompt)
        self.chat_history.append({"role": "Helper 2", "content": self.helper2_response})
        self.update_chat_display()
        self.save_conversation()
        
        # Create the improved prompt for the Main LLM, using the chat history (now including helpers' responses)
        improved_prompt = create_improved_prompt(self.latest_request, self.chat_history, self.latest_main_response, 
                                                self.helper1_response, self.helper2_response, self.feedback_description)
        
        # Check token count to ensure the prompt fits within the Main LLM's context window
        total_tokens = estimate_tokens(improved_prompt)
        main_model = self.main_model_var.get()
        if main_model in MODEL_CONTEXT_WINDOWS:
            context_window = MODEL_CONTEXT_WINDOWS[main_model]
            if total_tokens > 0.8 * context_window:
                # If the prompt is too long, generate concise summaries from the helpers
                summary_prompt = "Your previous response was too long. Please provide a concise summary in 2-3 sentences."
                helper1_summary = self.helper1_llm.invoke(summary_prompt)
                helper2_summary = self.helper2_llm.invoke(summary_prompt)
                # Use summaries in the improved prompt, but keep full responses in chat_history
                improved_prompt = create_improved_prompt(self.latest_request, self.chat_history, self.latest_main_response, 
                                                        helper1_summary, helper2_summary, self.feedback_description)
        
        # Generate and display the Main LLM's response immediately
        self.latest_main_response = self.main_llm.invoke(improved_prompt)
        self.chat_history.append({"role": "Main Developer", "content": self.latest_main_response})
        self.chat_history.append({"role": "System", "content": "Was this response helpful? (yes/no)"})
        self.update_chat_display()
        self.save_conversation()

if __name__ == "__main__":
    root = tk.Tk()
    app = CodingAssistantApp(root)
    root.mainloop()