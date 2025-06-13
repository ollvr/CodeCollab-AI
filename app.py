import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox , simpledialog
import threading
import webbrowser
from langchain_ollama import OllamaLLM

CONVERSATION_DIR = "conversations"
if not os.path.exists(CONVERSATION_DIR):
    os.makedirs(CONVERSATION_DIR)   

MODEL_CONTEXT_WINDOWS = {
    "qwen3:4b": 40000,
    "qwen2.5-coder:latest":32000,
    "gemma3:4b": 128000,
}

def estimate_tokens(text):
    return len(text) // 4

def get_available_models():
    return ["qwen2.5-coder:latest", "qwen3:4b", "gemma3:4b"]

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

class RoundedButton(ttk.Button):
    def __init__(self, master=None, **kw):
        self.radius      = kw.pop('radius', 10)
        self.color       = kw.pop('color', "#ffffff")
        self.hover_color = kw.pop('hover_color', "#28282c")
        self.text_color  = kw.pop('text_color', 'white')
        super().__init__(master, **kw)

        style = ttk.Style()
        style.configure('Rounded.TButton',
                        font=('Helvetica', 10, 'bold'),
                        borderwidth=1,
                        padding=8,
                        background=self.color,
                        foreground=self.text_color,
                        borderradius=self.radius)

        # **Match padding & border in hover style**
        style.configure('RoundedHover.TButton',
                        font=('Helvetica', 10, 'bold'),
                        borderwidth=1,
                        padding=8,
                        background=self.hover_color,
                        foreground=self.text_color,
                        borderradius=self.radius)

        # **Prevent relief/padding changes when pressed**
        style.map('Rounded.TButton',
                  background=[('active', self.hover_color)],
                  foreground=[('active', self.text_color)],
                  relief=[('pressed', 'flat'), ('!pressed', 'flat')],
                  padding=[('pressed', 8), ('!pressed', 8)])

        self.configure(style='Rounded.TButton')
        #self.bind("<Enter>", self.on_enter)
        #self.bind("<Leave>", self.on_leave)

    """def on_enter(self, event):
        self.configure(style='RoundedHover.TButton')

    def on_leave(self, event):
        self.configure(style='Rounded.TButton')"""


class CodingAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeCollab AI")
        self.root.minsize(1000, 700)
        self.root.configure(bg="#f5f7fa")

        self.configure_styles()

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

        self.main_frame = tk.Frame(root, bg="#f5f7fa")
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self.left_sidebar = tk.Frame(self.main_frame, bg="#ffffff", width=250)
        self.left_sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.left_sidebar.pack_propagate(False)

        title_frame = tk.Frame(self.left_sidebar, bg="#ffffff", height=60)
        title_frame.pack(fill="x", pady=(0, 10))
        title_label = tk.Label(title_frame, text="CodeCollab", bg="#ffffff", fg="#2d3436",
                              font=('Helvetica', 16, 'bold'))
        title_label.pack(expand=True)

        models_frame = tk.LabelFrame(self.left_sidebar, text="AI Models", bg="#ffffff", fg="#2d3436",
                                    font=('Helvetica', 10, 'bold'), bd=0)
        models_frame.pack(fill="x", padx=10, pady=(0, 10))

        models = get_available_models()

        main_model_frame = tk.Frame(models_frame, bg="#ffffff")
        main_model_frame.pack(fill="x", pady=5)
        ttk.Label(main_model_frame, text="Main Developer", style="SidebarHeader.TLabel").pack(anchor="w", padx=5)
        self.main_model_var = tk.StringVar(value=models[0])
        self.main_model_menu = ttk.Combobox(main_model_frame, textvariable=self.main_model_var,
                                          values=models, style="TCombobox")
        self.main_model_menu.pack(fill="x", padx=5, pady=2)

        helper1_frame = tk.Frame(models_frame, bg="#ffffff")
        helper1_frame.pack(fill="x", pady=5)
        ttk.Label(helper1_frame, text="Helper 1", style="SidebarHeader.TLabel").pack(anchor="w", padx=5)
        self.helper1_model_var = tk.StringVar(value=models[1] if len(models) > 1 else models[0])
        self.helper1_model_menu = ttk.Combobox(helper1_frame, textvariable=self.helper1_model_var,
                                             values=models, style="TCombobox")
        self.helper1_model_menu.pack(fill="x", padx=5, pady=2)

        helper2_frame = tk.Frame(models_frame, bg="#ffffff")
        helper2_frame.pack(fill="x", pady=5)
        ttk.Label(helper2_frame, text="Helper 2", style="SidebarHeader.TLabel").pack(anchor="w", padx=5)
        self.helper2_model_var = tk.StringVar(value=models[2] if len(models) > 2 else models[0])
        self.helper2_model_menu = ttk.Combobox(helper2_frame, textvariable=self.helper2_model_var,
                                             values=models, style="TCombobox")
        self.helper2_model_menu.pack(fill="x", padx=5, pady=2)

        conv_frame = tk.LabelFrame(self.left_sidebar, text="Conversations", bg="#ffffff", fg="#2d3436",
                                  font=('Helvetica', 10, 'bold'), bd=0)
        conv_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        buttons_frame = tk.Frame(conv_frame, bg="#ffffff")
        buttons_frame.pack(fill="x", pady=(0, 5))

        self.new_chat_btn = RoundedButton(buttons_frame, text="➕ New Chat", command=self.new_conversation,
                                        radius=5, color="#6c5ce7", hover_color="#5649c0")
        self.new_chat_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.delete_chat_btn = RoundedButton(buttons_frame, text="🗑️ Delete", command=self.delete_conversation,
                                           radius=5, color="#fd79a8", hover_color="#d63031")
        self.delete_chat_btn.pack(side="right", fill="x", expand=True, padx=(2, 0))

        list_frame = tk.Frame(conv_frame, bg="#ffffff")
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.conversation_listbox = tk.Listbox(list_frame, bg="#ffffff", fg="#2d3436", font=("Helvetica", 10),
                                             borderwidth=0, highlightthickness=0, selectbackground="#6c5ce7",
                                             selectforeground="white", activestyle='none')
        self.conversation_listbox.pack(fill="both", expand=True)
        self.conversation_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.conversation_listbox.yview)

        self.conversation_listbox.bind("<<ListboxSelect>>", self.load_conversation)
        self.update_conversation_list()

        self.chat_frame = tk.Frame(self.main_frame, bg="#f5f7fa", bd=0)
        self.chat_frame.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        chat_display_frame = tk.Frame(self.chat_frame, bg="#f5f7fa")
        chat_display_frame.pack(fill="both", expand=True, padx=15, pady=(15, 5))

        chat_header = tk.Label(chat_display_frame, text="Conversation", bg="#f5f7fa", fg="#2d3436",
                              font=('Helvetica', 12, 'bold'), anchor="w")
        chat_header.pack(fill="x", pady=(0, 5))

        chat_container = tk.Frame(chat_display_frame, bg="#ffffff", bd=0)
        chat_container.pack(fill="both", expand=True)

        chat_scrollbar = ttk.Scrollbar(chat_container)
        chat_scrollbar.pack(side="right", fill="y")

        self.chat_display = tk.Text(chat_container, wrap="word", state="disabled", bg="#ffffff", fg="#2d3436",
                                  font=("Menlo", 11), borderwidth=0, highlightthickness=0,
                                  padx=15, pady=15, spacing3=5, selectbackground="#a29bfe")
        self.chat_display.pack(side="left", fill="both", expand=True)
        self.chat_display.config(yscrollcommand=chat_scrollbar.set)
        chat_scrollbar.config(command=self.chat_display.yview)

        self.chat_display.tag_configure("user", foreground="#0984e3", font=("Helvetica", 10, "bold"))
        self.chat_display.tag_configure("system", foreground="#d63031", font=("Helvetica", 10, "bold"))
        self.chat_display.tag_configure("main_dev", foreground="#6c5ce7", font=("Helvetica", 10, "bold"))
        self.chat_display.tag_configure("helper1", foreground="#00b894", font=("Helvetica", 10, "bold"))
        self.chat_display.tag_configure("helper2", foreground="#fd79a8", font=("Helvetica", 10, "bold"))
        self.chat_display.tag_configure("code", font=("Menlo", 10), background="#f1f2f6", foreground="#2d3436")

        input_frame = tk.Frame(self.chat_frame, bg="#f5f7fa")
        input_frame.pack(fill="x", padx=15, pady=(5, 15))

        self.input_entry = tk.Text(input_frame, height=3, bg="#ffffff", fg="#2d3436",
                                 font=("Helvetica", 10), borderwidth=1, highlightthickness=1,
                                 padx=10, pady=10, wrap="word", highlightbackground="#dfe6e9", highlightcolor="#6c5ce7")
        self.input_entry.pack(side="left", fill="both", expand=True)
        self.input_entry.bind("<Return>", lambda e: "break")

        self.input_entry.insert("1.0", "Type your message here...")
        self.input_entry.bind("<FocusIn>", self.clear_placeholder)
        self.input_entry.bind("<FocusOut>", self.restore_placeholder)

        input_scrollbar = ttk.Scrollbar(input_frame, command=self.input_entry.yview)
        input_scrollbar.pack(side="right", fill="y")
        self.input_entry.config(yscrollcommand=input_scrollbar.set)

        send_btn_frame = tk.Frame(input_frame, bg="#f5f7fa")
        send_btn_frame.pack(side="right", padx=(5, 0))

        self.send_button = RoundedButton(send_btn_frame, text="Send", command=self.send_prompt_from_text,
                                       radius=5, color="#6c5ce7", hover_color="#5649c0")
        self.send_button.pack(pady=(0, 5))

        self.right_sidebar = tk.Frame(self.main_frame, bg="#ffffff", width=200)
        self.right_sidebar.pack(side="right", fill="y", padx=0, pady=0)
        self.right_sidebar.pack_propagate(False)

        guide_frame = tk.Frame(self.right_sidebar, bg="#ffffff")
        guide_frame.pack(fill="x", pady=(20, 0), padx=10)

        guide_title = tk.Label(guide_frame, text="App Guide", bg="#ffffff", fg="#2d3436",
                             font=('Helvetica', 12, 'bold'))
        guide_title.pack(anchor="w")

        guide_desc = tk.Label(guide_frame, text="Need help using CodeCollab?", bg="#ffffff", fg="#636e72",
                            font=('Helvetica', 9), anchor="w")
        guide_desc.pack(anchor="w", pady=(0, 5))

        guide_link = tk.Label(guide_frame, text="Read the App Guide →", fg="#6c5ce7", bg="#ffffff",
                            cursor="hand2", font=('Helvetica', 10, 'bold'))
        guide_link.pack(anchor="w")
        guide_link.bind("<Button-1>", lambda e: webbrowser.open("https://code-collab-ai-guide.vercel.app/"))

        sep = ttk.Separator(self.right_sidebar, orient="horizontal")
        sep.pack(fill="x", pady=(15, 10), padx=10)

        quick_actions = tk.LabelFrame(self.right_sidebar, text="Quick Actions", bg="#ffffff", fg="#2d3436",
                                    font=('Helvetica', 10, 'bold'), bd=0)
        quick_actions.pack(fill="x", padx=10, pady=(0, 10))

        clear_chat_btn = RoundedButton(quick_actions, text="Clear Conversation", command=self.clear_conversation,
                                     radius=5, color="#b2bec3", hover_color="#7f8c8d")
        clear_chat_btn.pack(fill="x", pady=5)

        export_btn = RoundedButton(quick_actions, text="Export Chat", command=self.export_conversation,
                                 radius=5, color="#b2bec3", hover_color="#7f8c8d")
        export_btn.pack(fill="x", pady=5)

        tips_frame = tk.LabelFrame(self.right_sidebar, text="Tips", bg="#ffffff", fg="#2d3436",
                                  font=('Helvetica', 10, 'bold'), bd=0)
        tips_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tips_text = tk.Text(tips_frame, wrap="word", bg="#ffffff", fg="#636e72", font=("Helvetica", 9),
                          borderwidth=0, highlightthickness=0, padx=5, pady=5, height=10)
        tips_text.pack(fill="both", expand=True)
        tips_text.insert("1.0", """• Use clear and specific questions for best results
• You can ask for code examples, explanations, or debugging help
• The AI remembers conversation context
• If you don't have enough hardware resources, try using smaller models
• For code blocks, use triple backticks (```)""")
        tips_text.config(state="disabled")

        tk.Label(self.right_sidebar, bg="#ffffff").pack(fill='both', expand=True)

    def configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')

        style.configure("TLabel", font=("Helvetica", 10), background="#ffffff", foreground="#2d3436")
        style.configure("SidebarHeader.TLabel", font=("Helvetica", 10, "bold"), foreground="#2d3436", background="#ffffff")
        style.configure("TCombobox", font=("Helvetica", 10), selectbackground="#f5f7fa", selectforeground="#2d3436",
                       fieldbackground="#f5f7fa", background="#ffffff", foreground="#2d3436", padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", "#f5f7fa")], background=[("readonly", "#ffffff")])

        style.layout("Vertical.TScrollbar",
                    [('Vertical.Scrollbar.trough',
                      {'children': [('Vertical.Scrollbar.thumb',
                                     {'expand': '1', 'sticky': 'nswe'})],
                       'sticky': 'ns'})])
        style.configure("Vertical.TScrollbar", troughcolor="#f5f7fa", bordercolor="#f5f7fa",
                       arrowcolor="#2d3436", background="#dfe6e9", thickness=8)
        style.map("Vertical.TScrollbar",
                 background=[('active', '#6c5ce7'), ('disabled', '#f5f7fa')],
                 arrowcolor=[('active', '#2d3436'), ('disabled', '#b2bec3')])

    def clear_placeholder(self, event):
        if self.input_entry.get("1.0", "end-1c") == "Type your message here...":
            self.input_entry.delete("1.0", "end")
            self.input_entry.config(fg="#2d3436")

    def restore_placeholder(self, event):
        if not self.input_entry.get("1.0", "end-1c").strip():
            self.input_entry.delete("1.0", "end")
            self.input_entry.insert("1.0", "Type your message here...")
            self.input_entry.config(fg="#7f8c8d")

    def send_prompt_from_text(self):
        content = self.input_entry.get("1.0", "end-1c")
        if content.strip() and content != "Type your message here...":
            self.send_prompt(text_content=content)

    def send_prompt(self, event=None, text_content=None):
        if text_content is None:
            user_input = self.input_entry.get().strip().lower()
        else:
            user_input = text_content.strip().lower()

        self.input_entry.delete("1.0", "end")
        self.restore_placeholder(None)

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
                    self.chat_history.append({"role": "System", "content": "Please describe what went wrong or what you expected."})
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

    def update_chat_display(self):
        self.chat_display.config(state="normal")
        self.chat_display.delete("1.0", tk.END)

        for entry in self.chat_history:
            tag = ""
            if entry["role"] == "Programmer":
                tag = "user"
                role_text = "You"
            elif entry["role"] == "Main Developer":
                tag = "main_dev"
                role_text = "Main Developer"
            elif entry["role"] == "Helper 1":
                tag = "helper1"
                role_text = "Helper 1"
            elif entry["role"] == "Helper 2":
                tag = "helper2"
                role_text = "Helper 2"
            elif entry["role"] == "System":
                tag = "system"
                role_text = "System"
            else:
                tag = ""
                role_text = entry["role"]

            self.chat_display.insert(tk.END, f"{role_text}\n", tag)
            self.chat_display.insert(tk.END, f"{entry['content']}\n\n")

        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)

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

    def clear_conversation(self):
        if self.current_conversation and messagebox.askyesno("Confirm", "Clear current conversation?", parent=self.root):
            self.chat_history = []
            self.state = "initial"
            self.update_chat_display()
            if self.current_conversation:
                save_conversation(self.current_conversation, self.chat_history)

    def export_conversation(self):
        if not self.chat_history:
            messagebox.showinfo("Info", "No conversation to export", parent=self.root)
            return

        # Debug information
        print(f"Exporting conversation with {len(self.chat_history)} messages")
        if len(self.chat_history) > 0:
            first_msg = self.chat_history[0]
            last_msg = self.chat_history[-1]
            print(f"First message role: {first_msg.get('role')}, length: {len(str(first_msg.get('content', '')))}")
            print(f"Last message role: {last_msg.get('role')}, length: {len(str(last_msg.get('content', '')))}")

        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Conversation"
        )

        if not file_path:  # User cancelled the dialog
            return

        try:
            # Create a timestamp for the export
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Build the content with proper formatting
            content_lines = []
            content_lines.append("CodeCollab AI Conversation Export")
            content_lines.append("=" * 40)
            content_lines.append(f"Date: {timestamp}")
            content_lines.append(f"Total messages: {len(self.chat_history)}")
            content_lines.append("=" * 40)
            content_lines.append("")  # Add blank line

            # Process each message
            for i, entry in enumerate(self.chat_history, 1):
                try:
                    role = entry.get('role', 'Unknown')
                    content = entry.get('content', '')

                    # Handle content that might have encoding issues
                    if isinstance(content, str):
                        # Replace problematic characters
                        content = content.replace("\r\n", "\n").replace("\r", "\n")
                    else:
                        content = str(content)

                    # Add message to content
                    content_lines.append(f"Message #{i}")
                    content_lines.append(f"From: {role}")
                    content_lines.append("Content:")
                    content_lines.append(content)
                    content_lines.append("-" * 20)  # Separator
                    content_lines.append("")  # Blank line
                except Exception as e:
                    error_msg = f"Error processing message {i}: {str(e)}"
                    print(error_msg)
                    content_lines.append(error_msg)
                    content_lines.append("-" * 20)
                    content_lines.append("")

            # Join all lines with newlines
            full_content = "\n".join(content_lines)

            # Write to file with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            # Verify the file was written correctly
            with open(file_path, 'r', encoding='utf-8') as f:
                exported_content = f.read()
                print(f"Exported file contains {len(exported_content)} characters")

            messagebox.showinfo(
                "Success",
                f"Conversation exported successfully!\n\n"
                f"File: {os.path.basename(file_path)}\n"
                f"Location: {os.path.dirname(file_path)}\n"
                f"Total messages: {len(self.chat_history)}",
                parent=self.root
            )
        except Exception as e:
            error_details = f"Failed to export conversation:\n\n{str(e)}"
            print(error_details)
            # Get traceback for more detailed error information
            import traceback
            full_error = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            print(full_error)

            messagebox.showerror(
                "Error",
                f"Failed to export conversation:\n\n{str(e)}\n\n"
                "See console for more details.",
                parent=self.root
            )


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
                try:
                    os.remove(os.path.join(CONVERSATION_DIR, filename))
                    self.update_conversation_list()
                    if self.current_conversation == filename:
                        self.chat_history = []
                        self.current_conversation = None
                        self.state = "initial"
                        self.update_chat_display()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete conversation: {e}", parent=self.root)

    def save_conversation(self):
        if self.current_conversation:
            save_conversation(self.current_conversation, self.chat_history)

    def generate_initial_response(self):
        if not self.main_llm:
            self.main_llm = OllamaLLM(model=self.main_model_var.get())
            self.helper1_llm = OllamaLLM(model=self.helper1_model_var.get())
            self.helper2_llm = OllamaLLM(model=self.helper2_model_var.get())
        prompt = create_initial_prompt(self.latest_request, self.chat_history)
        self.latest_main_response = self.main_llm.invoke(prompt)
        self.chat_history.append({"role": "Main Developer", "content": self.latest_main_response})
        self.chat_history.append({"role": "System", "content": "Was this response helpful? (yes/no)"})
        self.update_chat_display()
        self.save_conversation()

    def consult_helpers(self):
        helper_prompt = create_helper_prompt(self.latest_request, self.latest_main_response,
                                          self.chat_history, self.feedback_description)

        self.helper1_response = self.helper1_llm.invoke(helper_prompt)
        self.chat_history.append({"role": "Helper 1", "content": self.helper1_response})
        self.update_chat_display()
        self.save_conversation()

        self.helper2_response = self.helper2_llm.invoke(helper_prompt)
        self.chat_history.append({"role": "Helper 2", "content": self.helper2_response})
        self.update_chat_display()
        self.save_conversation()

        improved_prompt = create_improved_prompt(self.latest_request, self.chat_history,
                                               self.latest_main_response,
                                               self.helper1_response, self.helper2_response,
                                               self.feedback_description)

        total_tokens = estimate_tokens(improved_prompt)
        main_model = self.main_model_var.get()
        if main_model in MODEL_CONTEXT_WINDOWS:
            context_window = MODEL_CONTEXT_WINDOWS[main_model]
            if total_tokens > 0.8 * context_window:
                summary_prompt = "Your previous response was too long. Please provide a concise summary in 2-3 sentences."
                helper1_summary = self.helper1_llm.invoke(summary_prompt)
                helper2_summary = self.helper2_llm.invoke(summary_prompt)

                improved_prompt = create_improved_prompt(self.latest_request, self.chat_history,
                                                       self.latest_main_response,
                                                       helper1_summary, helper2_summary,
                                                       self.feedback_description)

        self.latest_main_response = self.main_llm.invoke(improved_prompt)
        self.chat_history.append({"role": "Main Developer", "content": self.latest_main_response})
        self.chat_history.append({"role": "System", "content": "Was this response helpful? (yes/no)"})
        self.update_chat_display()
        self.save_conversation()

if __name__ == "__main__":
    root = tk.Tk()
    app = CodingAssistantApp(root)
    root.mainloop()
