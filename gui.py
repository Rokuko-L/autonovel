import os
import sys
import json
import queue
import shlex
import threading
import subprocess
from pathlib import Path
import customtkinter as ctk

# ---------------------------------------------------------------------------
# Design System & Theme Configuration
# ---------------------------------------------------------------------------
THEME = {
    "bg_main": "#0F172A",          # Slate 900
    "bg_card": "#1E293B",          # Slate 800
    "bg_input": "#0F172A",         # Slate 900 for fields
    "border_color": "#334155",      # Slate 700
    "accent": "#6366F1",           # Indigo 500
    "accent_hover": "#4F46E5",     # Indigo 600
    "text_primary": "#F8FAFC",     # Slate 50
    "text_secondary": "#94A3B8",   # Slate 400
    "error": "#EF4444",            # Red 500
    "success": "#10B981",          # Emerald 500
    "corner_radius": 8
}

# Cross-platform font families
UI_FONT_FAMILY = "Helvetica Neue" if sys.platform == "darwin" else ("Segoe UI" if sys.platform == "win32" else "DejaVu Sans")
MONO_FONT_FAMILY = "Menlo" if sys.platform == "darwin" else ("Consolas" if sys.platform == "win32" else "DejaVu Sans Mono")

CONFIG_PATH = "./gui_config.json"

DEFAULT_SETTINGS = {
    "project": "mynovel",
    "genre": "Cyberpunk Noir",
    "chapters": "24",
    "words_per_chapter": 3200,
    "notes": "A detective in a neon-drenched city receives a message from a rogue AI claiming to be his dead partner.",
    "from_scratch": False,
    "revision_cycles": 6,
    "skip_adversarial_editing": False,
    "skip_mechanical_cuts": False,
    "skip_reader_panel": False,
    "skip_targeted_revisions": False,
    "skip_full_novel_eval": False,
    "skip_opus_review": False
}

class AutonovelApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Autonovel Orchestrator Client")
        self.geometry("950x780")
        self.minsize(850, 650)
        self.configure(fg_color=THEME["bg_main"])
        
        # Tkinter window styling theme
        ctk.set_appearance_mode("dark")

        # Process management variables
        self.process = None
        self.log_queue = queue.Queue()
        self.is_running = False

        # Load settings
        self.settings = self.load_settings()

        # Build UI layout
        self.create_widgets()

        # Start log polling queue
        self.after(100, self.poll_queue)

        # Trigger initial project path check
        self.check_project_exists()

    # ---------------------------------------------------------------------------
    # Settings Persistence
    # ---------------------------------------------------------------------------
    def load_settings(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge with default settings to cover missing fields
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"[WARN] Failed to load config: {e}. Resetting to defaults.", file=sys.stderr)
        return DEFAULT_SETTINGS.copy()

    def save_settings(self):
        try:
            # Sync variables from UI elements to settings dictionary
            self.settings["project"] = self.entry_project.get().strip()
            self.settings["genre"] = self.entry_genre.get().strip()
            self.settings["chapters"] = self.entry_chapters.get().strip()
            
            try:
                self.settings["words_per_chapter"] = int(self.entry_words.get().strip())
            except ValueError:
                self.settings["words_per_chapter"] = 3200

            self.settings["notes"] = self.txt_notes.get("1.0", "end-1c").strip()
            self.settings["from_scratch"] = bool(self.cb_scratch.get())

            try:
                self.settings["revision_cycles"] = int(self.entry_cycles.get().strip())
            except ValueError:
                self.settings["revision_cycles"] = 6

            self.settings["skip_adversarial_editing"] = bool(self.cb_skip_adv.get())
            self.settings["skip_mechanical_cuts"] = bool(self.cb_skip_cuts.get())
            self.settings["skip_reader_panel"] = bool(self.cb_skip_panel.get())
            self.settings["skip_targeted_revisions"] = bool(self.cb_skip_targeted.get())
            self.settings["skip_full_novel_eval"] = bool(self.cb_skip_eval.get())
            self.settings["skip_opus_review"] = bool(self.cb_skip_opus.get())

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.write_log(f"[WARN] Failed to save settings: {e}\n")

    # ---------------------------------------------------------------------------
    # GUI Layout Generation
    # ---------------------------------------------------------------------------
    def create_widgets(self):
        # Configure fonts
        self.font_title = (UI_FONT_FAMILY, 18, "bold")
        self.font_section = (UI_FONT_FAMILY, 14, "bold")
        self.font_label = (UI_FONT_FAMILY, 12, "bold")
        self.font_body = (UI_FONT_FAMILY, 12)
        self.font_mono = (MONO_FONT_FAMILY, 11)

        # Tabview container
        self.tabview = ctk.CTkTabview(
            self,
            segmented_button_fg_color=THEME["bg_card"],
            segmented_button_selected_color=THEME["accent"],
            segmented_button_selected_hover_color=THEME["accent_hover"],
            segmented_button_unselected_color=THEME["bg_card"],
            text_color=THEME["text_primary"],
            fg_color=THEME["bg_main"],
            corner_radius=THEME["corner_radius"],
            command=self.on_tab_changed
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=16)

        # Add tabs
        self.tab_run = self.tabview.add("Run")
        self.tab_tools = self.tabview.add("Tools")
        self.tab_cycle = self.tabview.add("Cycle Config")

        # Build tabs
        self.build_tab_run()
        self.build_tab_tools()
        self.build_tab_cycle()

    # --- Tab 1: Run ---
    def build_tab_run(self):
        # Configure grid for Tab 1
        self.tab_run.grid_columnconfigure(0, weight=0, minsize=400)
        self.tab_run.grid_columnconfigure(1, weight=1)
        self.tab_run.grid_rowconfigure(0, weight=1)

        # Form Pane (Left)
        scroll_form = ctk.CTkScrollableFrame(
            self.tab_run,
            fg_color=THEME["bg_card"],
            border_color=THEME["border_color"],
            border_width=1,
            corner_radius=THEME["corner_radius"]
        )
        scroll_form.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        
        # Grid inside Form
        scroll_form.grid_columnconfigure(0, weight=1)

        # Section Header
        lbl_head = ctk.CTkLabel(scroll_form, text="Pipeline Parameters", font=self.font_section, text_color=THEME["text_primary"])
        lbl_head.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 12))

        # Project Name Field
        lbl_proj = ctk.CTkLabel(scroll_form, text="Project Name *", font=self.font_label, text_color=THEME["text_primary"])
        lbl_proj.grid(row=1, column=0, sticky="w", padx=16, pady=(10, 2))
        
        self.entry_project = ctk.CTkEntry(
            scroll_form, 
            fg_color=THEME["bg_input"],
            text_color=THEME["text_primary"],
            border_color=THEME["border_color"],
            corner_radius=THEME["corner_radius"],
            font=self.font_body
        )
        self.entry_project.grid(row=2, column=0, sticky="ew", padx=16, pady=2)
        self.entry_project.insert(0, self.settings["project"])
        self.entry_project.bind("<KeyRelease>", self.check_project_exists)

        # Validation Message
        self.lbl_project_warn = ctk.CTkLabel(scroll_form, text="", font=(UI_FONT_FAMILY, 11), text_color=THEME["text_secondary"], wraplength=350, justify="left")
        self.lbl_project_warn.grid(row=3, column=0, sticky="w", padx=16, pady=(2, 10))

        # Genre Field
        lbl_genre = ctk.CTkLabel(scroll_form, text="Genre", font=self.font_label, text_color=THEME["text_primary"])
        lbl_genre.grid(row=4, column=0, sticky="w", padx=16, pady=(10, 2))
        
        self.entry_genre = ctk.CTkEntry(
            scroll_form, 
            fg_color=THEME["bg_input"],
            text_color=THEME["text_primary"],
            border_color=THEME["border_color"],
            corner_radius=THEME["corner_radius"],
            font=self.font_body
        )
        self.entry_genre.grid(row=5, column=0, sticky="ew", padx=16, pady=2)
        self.entry_genre.insert(0, self.settings["genre"])

        # Chapters Field
        lbl_ch = ctk.CTkLabel(scroll_form, text="Chapters", font=self.font_label, text_color=THEME["text_primary"])
        lbl_ch.grid(row=6, column=0, sticky="w", padx=16, pady=(10, 2))
        
        self.entry_chapters = ctk.CTkEntry(
            scroll_form, 
            fg_color=THEME["bg_input"],
            text_color=THEME["text_primary"],
            border_color=THEME["border_color"],
            corner_radius=THEME["corner_radius"],
            font=self.font_body
        )
        self.entry_chapters.grid(row=7, column=0, sticky="ew", padx=16, pady=2)
        self.entry_chapters.insert(0, self.settings["chapters"])

        # Words per Chapter Field
        lbl_words = ctk.CTkLabel(scroll_form, text="Words per Chapter", font=self.font_label, text_color=THEME["text_primary"])
        lbl_words.grid(row=8, column=0, sticky="w", padx=16, pady=(10, 2))
        
        self.entry_words = ctk.CTkEntry(
            scroll_form, 
            fg_color=THEME["bg_input"],
            text_color=THEME["text_primary"],
            border_color=THEME["border_color"],
            corner_radius=THEME["corner_radius"],
            font=self.font_body
        )
        self.entry_words.grid(row=9, column=0, sticky="ew", padx=16, pady=2)
        self.entry_words.insert(0, str(self.settings["words_per_chapter"]))

        # Notes Field
        lbl_notes = ctk.CTkLabel(scroll_form, text="Premise & Notes", font=self.font_label, text_color=THEME["text_primary"])
        lbl_notes.grid(row=10, column=0, sticky="w", padx=16, pady=(10, 2))
        
        self.txt_notes = ctk.CTkTextbox(
            scroll_form,
            fg_color=THEME["bg_input"],
            text_color=THEME["text_primary"],
            border_color=THEME["border_color"],
            border_width=1,
            corner_radius=THEME["corner_radius"],
            font=self.font_body,
            height=120
        )
        self.txt_notes.grid(row=11, column=0, sticky="ew", padx=16, pady=2)
        self.txt_notes.insert("1.0", self.settings["notes"])

        # Checkbox --from-scratch
        self.cb_scratch = ctk.CTkCheckBox(
            scroll_form,
            text="Reset and start from scratch (--from-scratch)",
            font=self.font_body,
            text_color=THEME["text_primary"],
            hover_color=THEME["accent_hover"],
            fg_color=THEME["accent"],
            corner_radius=4,
            command=self.check_project_exists
        )
        self.cb_scratch.grid(row=12, column=0, sticky="w", padx=16, pady=(16, 20))
        if self.settings["from_scratch"]:
            self.cb_scratch.select()

        # Command Action Buttons
        btn_frame = ctk.CTkFrame(scroll_form, fg_color="transparent")
        btn_frame.grid(row=13, column=0, sticky="ew", padx=16, pady=(0, 16))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        self.btn_run = ctk.CTkButton(
            btn_frame,
            text="Run Pipeline",
            font=self.font_label,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            corner_radius=THEME["corner_radius"],
            command=self.run_pipeline,
            height=40
        )
        self.btn_run.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=0)

        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="Stop Execution",
            font=self.font_label,
            fg_color="#334155",
            hover_color=THEME["error"],
            text_color=THEME["text_primary"],
            corner_radius=THEME["corner_radius"],
            command=self.stop_process,
            state="disabled",
            height=40
        )
        self.btn_stop.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=0)


        # Log & Status Pane (Right)
        pane_right = ctk.CTkFrame(self.tab_run, fg_color="transparent")
        pane_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        pane_right.grid_columnconfigure(0, weight=1)
        pane_right.grid_rowconfigure(1, weight=1)

        # Status Bar / Frame
        status_bar = ctk.CTkFrame(pane_right, fg_color=THEME["bg_card"], height=48, border_color=THEME["border_color"], border_width=1, corner_radius=THEME["corner_radius"])
        status_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        status_bar.grid_propagate(False)
        status_bar.grid_columnconfigure(1, weight=1)

        # Status Indicator Canvas
        self.status_canvas = ctk.CTkCanvas(status_bar, width=16, height=16, bg=THEME["bg_card"], highlightthickness=0)
        self.status_canvas.grid(row=0, column=0, padx=(16, 8), pady=16)
        self.status_dot = self.status_canvas.create_oval(2, 2, 14, 14, fill=THEME["text_secondary"], outline="")

        # Status Label
        self.lbl_status = ctk.CTkLabel(status_bar, text="Status: Idle", font=self.font_label, text_color=THEME["text_secondary"])
        self.lbl_status.grid(row=0, column=1, sticky="w", padx=0, pady=10)

        # Monospace Live-Streaming Log Textbox
        self.log_textbox = ctk.CTkTextbox(
            pane_right,
            fg_color=THEME["bg_card"],
            text_color=THEME["text_primary"],
            border_color=THEME["border_color"],
            border_width=1,
            corner_radius=THEME["corner_radius"],
            font=self.font_mono
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.log_textbox.configure(state="disabled")

        # Configure textbox logging highlighting tags
        self.log_textbox.tag_config("error", foreground=THEME["error"])
        self.log_textbox.tag_config("success", foreground=THEME["success"])
        self.log_textbox.tag_config("warning", foreground="#F59E0B")

    # --- Tab 2: Tools ---
    def build_tab_tools(self):
        # Configure columns inside Tools Tab
        self.tab_tools.grid_columnconfigure(0, weight=1)
        self.tab_tools.grid_rowconfigure(0, weight=1)

        scroll_tools = ctk.CTkScrollableFrame(
            self.tab_tools,
            fg_color=THEME["bg_card"],
            border_color=THEME["border_color"],
            border_width=1,
            corner_radius=THEME["corner_radius"]
        )
        scroll_tools.grid(row=0, column=0, sticky="nsew")
        scroll_tools.grid_columnconfigure(0, weight=1)

        # Title
        lbl_title = ctk.CTkLabel(scroll_tools, text="One-off Utility Scripts", font=self.font_title, text_color=THEME["text_primary"])
        lbl_title.grid(row=0, column=0, sticky="w", padx=24, pady=(24, 16))

        # Shared running status indicator notice
        self.lbl_tools_notice = ctk.CTkLabel(
            scroll_tools, 
            text="Tools can only be run when the main pipeline is idle.",
            font=(UI_FONT_FAMILY, 11),
            text_color=THEME["text_secondary"]
        )
        self.lbl_tools_notice.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 16))

        row_idx = 2

        # -------------------------------------------------------------
        # Tool 1: Single-chapter evaluate
        # -------------------------------------------------------------
        fr_tool1 = ctk.CTkFrame(scroll_tools, fg_color=THEME["bg_main"], border_color=THEME["border_color"], border_width=1, corner_radius=THEME["corner_radius"])
        fr_tool1.grid(row=row_idx, column=0, sticky="ew", padx=24, pady=10)
        fr_tool1.grid_columnconfigure(1, weight=1)

        lbl_t1_title = ctk.CTkLabel(fr_tool1, text="Single-Chapter Evaluate", font=self.font_section, text_color=THEME["text_primary"])
        lbl_t1_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 4))
        lbl_t1_desc = ctk.CTkLabel(fr_tool1, text="Runs evaluate.py --chapter=N to generate quality metrics for a single chapter draft.", font=(UI_FONT_FAMILY, 11), text_color=THEME["text_secondary"])
        lbl_t1_desc.grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 12))

        # Project select
        lbl_t1_proj = ctk.CTkLabel(fr_tool1, text="Project:", font=self.font_label, text_color=THEME["text_primary"])
        lbl_t1_proj.grid(row=2, column=0, sticky="w", padx=16, pady=8)
        self.eval_project_dropdown = ctk.CTkOptionMenu(fr_tool1, values=self.get_existing_projects(), fg_color=THEME["bg_card"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_primary"])
        self.eval_project_dropdown.grid(row=2, column=1, sticky="w", padx=8, pady=8)

        # Chapter field
        lbl_t1_ch = ctk.CTkLabel(fr_tool1, text="Chapter Number:", font=self.font_label, text_color=THEME["text_primary"])
        lbl_t1_ch.grid(row=2, column=2, sticky="w", padx=16, pady=8)
        self.entry_eval_chapter = ctk.CTkEntry(fr_tool1, fg_color=THEME["bg_card"], text_color=THEME["text_primary"], border_color=THEME["border_color"], corner_radius=THEME["corner_radius"], width=100)
        self.entry_eval_chapter.grid(row=2, column=3, sticky="w", padx=8, pady=8)
        self.entry_eval_chapter.insert(0, "1")

        # Run Button
        self.btn_run_eval = ctk.CTkButton(
            fr_tool1, 
            text="Evaluate Chapter", 
            font=self.font_label, 
            fg_color=THEME["accent"], 
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"], 
            corner_radius=THEME["corner_radius"],
            command=self.run_eval_tool
        )
        self.btn_run_eval.grid(row=2, column=4, sticky="e", padx=16, pady=8)

        row_idx += 1

        # -------------------------------------------------------------
        # Tool 2: Word-count audit
        # -------------------------------------------------------------
        fr_tool2 = ctk.CTkFrame(scroll_tools, fg_color=THEME["bg_main"], border_color=THEME["border_color"], border_width=1, corner_radius=THEME["corner_radius"])
        fr_tool2.grid(row=row_idx, column=0, sticky="ew", padx=24, pady=10)
        fr_tool2.grid_columnconfigure(1, weight=1)

        lbl_t2_title = ctk.CTkLabel(fr_tool2, text="Word-Count History Audit", font=self.font_section, text_color=THEME["text_primary"])
        lbl_t2_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 4))
        lbl_t2_desc = ctk.CTkLabel(fr_tool2, text="Runs audit_word_counts.py to print the word count chronological changes across all chapters.", font=(UI_FONT_FAMILY, 11), text_color=THEME["text_secondary"])
        lbl_t2_desc.grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 12))

        # Project select
        lbl_t2_proj = ctk.CTkLabel(fr_tool2, text="Project:", font=self.font_label, text_color=THEME["text_primary"])
        lbl_t2_proj.grid(row=2, column=0, sticky="w", padx=16, pady=8)
        self.audit_project_dropdown = ctk.CTkOptionMenu(fr_tool2, values=self.get_existing_projects(), fg_color=THEME["bg_card"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_primary"])
        self.audit_project_dropdown.grid(row=2, column=1, sticky="w", padx=8, pady=8)

        # Spacer/Placeholder label for column alignment
        lbl_t2_spacer = ctk.CTkLabel(fr_tool2, text="")
        lbl_t2_spacer.grid(row=2, column=2, columnspan=2, sticky="ew", padx=8, pady=8)

        # Run Button
        self.btn_run_audit = ctk.CTkButton(
            fr_tool2, 
            text="Audit Word Counts", 
            font=self.font_label, 
            fg_color=THEME["accent"], 
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"], 
            corner_radius=THEME["corner_radius"],
            command=self.run_audit_tool
        )
        self.btn_run_audit.grid(row=2, column=4, sticky="e", padx=16, pady=8)

        row_idx += 1

        # -------------------------------------------------------------
        # Tool 3: Single adversarial edit
        # -------------------------------------------------------------
        fr_tool3 = ctk.CTkFrame(scroll_tools, fg_color=THEME["bg_main"], border_color=THEME["border_color"], border_width=1, corner_radius=THEME["corner_radius"])
        fr_tool3.grid(row=row_idx, column=0, sticky="ew", padx=24, pady=10)
        fr_tool3.grid_columnconfigure(1, weight=1)

        lbl_t3_title = ctk.CTkLabel(fr_tool3, text="Single Adversarial Edit Run", font=self.font_section, text_color=THEME["text_primary"])
        lbl_t3_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 4))
        lbl_t3_desc = ctk.CTkLabel(fr_tool3, text="Runs adversarial_edit.py to cut bloated sentences and produce a detailed revision plan for a chapter.", font=(UI_FONT_FAMILY, 11), text_color=THEME["text_secondary"])
        lbl_t3_desc.grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 12))

        # Project select
        lbl_t3_proj = ctk.CTkLabel(fr_tool3, text="Project:", font=self.font_label, text_color=THEME["text_primary"])
        lbl_t3_proj.grid(row=2, column=0, sticky="w", padx=16, pady=8)
        self.edit_project_dropdown = ctk.CTkOptionMenu(fr_tool3, values=self.get_existing_projects(), fg_color=THEME["bg_card"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_primary"])
        self.edit_project_dropdown.grid(row=2, column=1, sticky="w", padx=8, pady=8)

        # Chapter field
        lbl_t3_ch = ctk.CTkLabel(fr_tool3, text="Chapter Number:", font=self.font_label, text_color=THEME["text_primary"])
        lbl_t3_ch.grid(row=2, column=2, sticky="w", padx=16, pady=8)
        self.entry_edit_chapter = ctk.CTkEntry(fr_tool3, fg_color=THEME["bg_card"], text_color=THEME["text_primary"], border_color=THEME["border_color"], corner_radius=THEME["corner_radius"], width=100)
        self.entry_edit_chapter.grid(row=2, column=3, sticky="w", padx=8, pady=8)
        self.entry_edit_chapter.insert(0, "1")

        # Run Button
        self.btn_run_edit = ctk.CTkButton(
            fr_tool3, 
            text="Adversarial Edit", 
            font=self.font_label, 
            fg_color=THEME["accent"], 
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"], 
            corner_radius=THEME["corner_radius"],
            command=self.run_edit_tool
        )
        self.btn_run_edit.grid(row=2, column=4, sticky="e", padx=16, pady=8)

    # --- Tab 3: Cycle Config ---
    def build_tab_cycle(self):
        # Configure Grid inside Cycle Tab
        self.tab_cycle.grid_columnconfigure(0, weight=1)
        self.tab_cycle.grid_rowconfigure(0, weight=1)

        scroll_cycle = ctk.CTkScrollableFrame(
            self.tab_cycle,
            fg_color=THEME["bg_card"],
            border_color=THEME["border_color"],
            border_width=1,
            corner_radius=THEME["corner_radius"]
        )
        scroll_cycle.grid(row=0, column=0, sticky="nsew")
        scroll_cycle.grid_columnconfigure(0, weight=1)

        # Header Title
        lbl_title = ctk.CTkLabel(scroll_cycle, text="Revision Cycle Parameter Configuration", font=self.font_title, text_color=THEME["text_primary"])
        lbl_title.grid(row=0, column=0, sticky="w", padx=24, pady=(24, 16))

        # Revision Cycles Integer Selector (Spinner)
        lbl_cycles_label = ctk.CTkLabel(scroll_cycle, text="Number of Revision Cycles (--revision-cycles):", font=self.font_label, text_color=THEME["text_primary"])
        lbl_cycles_label.grid(row=1, column=0, sticky="w", padx=24, pady=(16, 2))

        spin_frame = ctk.CTkFrame(scroll_cycle, fg_color="transparent")
        spin_frame.grid(row=2, column=0, sticky="w", padx=24, pady=(2, 16))

        btn_minus = ctk.CTkButton(spin_frame, text="-", font=(UI_FONT_FAMILY, 14, "bold"), fg_color=THEME["bg_main"], hover_color=THEME["accent_hover"], text_color=THEME["text_primary"], width=32, height=32, corner_radius=4, command=lambda: self.change_cycles(-1))
        btn_minus.grid(row=0, column=0, padx=2)

        self.entry_cycles = ctk.CTkEntry(spin_frame, font=self.font_body, fg_color=THEME["bg_main"], text_color=THEME["text_primary"], border_color=THEME["border_color"], width=60, height=32, justify="center")
        self.entry_cycles.grid(row=0, column=1, padx=2)
        self.entry_cycles.insert(0, str(self.settings["revision_cycles"]))

        btn_plus = ctk.CTkButton(spin_frame, text="+", font=(UI_FONT_FAMILY, 14, "bold"), fg_color=THEME["bg_main"], hover_color=THEME["accent_hover"], text_color=THEME["text_primary"], width=32, height=32, corner_radius=4, command=lambda: self.change_cycles(1))
        btn_plus.grid(row=0, column=2, padx=2)

        # Skip Flags Header
        lbl_skip_head = ctk.CTkLabel(scroll_cycle, text="Sub-Phase Skipping Options:", font=self.font_section, text_color=THEME["text_primary"])
        lbl_skip_head.grid(row=3, column=0, sticky="w", padx=24, pady=(20, 4))
        lbl_skip_desc = ctk.CTkLabel(scroll_cycle, text="Select individual sub-phases to skip during faster, cheaper, or test execution runs.", font=(UI_FONT_FAMILY, 11), text_color=THEME["text_secondary"])
        lbl_skip_desc.grid(row=4, column=0, sticky="w", padx=24, pady=(0, 16))

        # Checkboxes Container
        fr_check = ctk.CTkFrame(scroll_cycle, fg_color=THEME["bg_main"], border_color=THEME["border_color"], border_width=1, corner_radius=THEME["corner_radius"])
        fr_check.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 24))
        fr_check.grid_columnconfigure(0, weight=1)

        # Builder helper for skip checkboxes
        self.cb_skip_adv = self.add_skip_checkbox(fr_check, 0, "Skip Adversarial Editing (--skip-adversarial-editing)", "Disables the parallel LLM editor pass that targets word reduction.", self.settings["skip_adversarial_editing"])
        self.cb_skip_cuts = self.add_skip_checkbox(fr_check, 1, "Skip Mechanical Cuts (--skip-mechanical-cuts)", "Bypasses applying apply_cuts.py templates for OVER-EXPLAIN and REDUNDANT segments.", self.settings["skip_mechanical_cuts"])
        self.cb_skip_panel = self.add_skip_checkbox(fr_check, 2, "Skip Reader Panel (--skip-reader-panel)", "Skips running reader_panel.py and the arc summary generation.", self.settings["skip_reader_panel"])
        self.cb_skip_targeted = self.add_skip_checkbox(fr_check, 3, "Skip Targeted Revisions (--skip-targeted-revisions)", "Prevents applying automated chapter revisions from reader panel consensus.", self.settings["skip_targeted_revisions"])
        self.cb_skip_eval = self.add_skip_checkbox(fr_check, 4, "Skip Full Novel Evaluation (--skip-full-novel-eval)", "Skips generating full novel quality metrics and skips plateau validation.", self.settings["skip_full_novel_eval"])
        self.cb_skip_opus = self.add_skip_checkbox(fr_check, 5, "Skip Opus Review Loop (--skip-opus-review)", "Skips the deep prose-level Opus evaluation rounds (Phase 3b) completely.", self.settings["skip_opus_review"])

    def add_skip_checkbox(self, parent, row, title, desc, default_val):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.grid(row=row, column=0, sticky="ew", padx=16, pady=8)
        
        cb = ctk.CTkCheckBox(fr, text=title, font=self.font_label, text_color=THEME["text_primary"], hover_color=THEME["accent_hover"], fg_color=THEME["accent"], corner_radius=4)
        cb.pack(anchor="w", padx=0, pady=2)
        if default_val:
            cb.select()

        lbl_desc = ctk.CTkLabel(fr, text="      " + desc, font=(UI_FONT_FAMILY, 11), text_color=THEME["text_secondary"])
        lbl_desc.pack(anchor="w", padx=0, pady=0)

        # Thin separator between items (except last one)
        if row < 5:
            sep = ctk.CTkFrame(parent, fg_color=THEME["border_color"], height=1)
            sep.grid(row=row, column=0, sticky="ew", padx=16, pady=4)
            
        return cb

    # Helper to change integer entries
    def change_cycles(self, delta):
        try:
            val = int(self.entry_cycles.get())
        except ValueError:
            val = 6
        new_val = max(1, val + delta)
        self.entry_cycles.delete(0, "end")
        self.entry_cycles.insert(0, str(new_val))

    # ---------------------------------------------------------------------------
    # GUI State & Project Directory Helpers
    # ---------------------------------------------------------------------------
    def on_tab_changed(self):
        current_tab = self.tabview.get()
        if current_tab == "Tools":
            projects = self.get_existing_projects()
            self.eval_project_dropdown.configure(values=projects)
            self.audit_project_dropdown.configure(values=projects)
            self.edit_project_dropdown.configure(values=projects)
            
            # Select the first project in dropdown if nothing selected
            if projects:
                self.eval_project_dropdown.set(projects[0])
                self.audit_project_dropdown.set(projects[0])
                self.edit_project_dropdown.set(projects[0])

    def get_existing_projects(self):
        projects_dir = Path("projects")
        if not projects_dir.exists():
            return ["default"]
        # Read subdirectories, excluding git repo tracking directories or registries
        subdirs = [p.name for p in projects_dir.iterdir() if p.is_dir() and p.name != ".git"]
        return sorted(subdirs) if subdirs else ["default"]

    def check_project_exists(self, *args):
        name = self.entry_project.get().strip()
        if not name:
            self.lbl_project_warn.configure(text="Project name is required", text_color=THEME["error"])
            return False
        
        # Verify relative directory naming safety
        try:
            projects_root = Path("projects").resolve()
            proposed = (projects_root / name).resolve()
            if not (proposed == projects_root or projects_root in proposed.parents):
                self.lbl_project_warn.configure(text="Invalid project folder name!", text_color=THEME["error"])
                return False
        except Exception:
            self.lbl_project_warn.configure(text="Invalid project folder name!", text_color=THEME["error"])
            return False

        project_dir = Path("projects") / name
        if project_dir.exists():
            if self.cb_scratch.get():
                self.lbl_project_warn.configure(
                    text="Warning: Project folder already exists. Running --from-scratch will reset it!",
                    text_color="#F59E0B"
                )
            else:
                self.lbl_project_warn.configure(
                    text="Notice: Project exists. Resuming from current state.",
                    text_color=THEME["success"]
                )
        else:
            self.lbl_project_warn.configure(
                text="New project folder will be created.",
                text_color=THEME["text_secondary"]
            )
        return True

    def set_status(self, status_text, color):
        # Update dot indicator canvas
        self.status_canvas.itemconfig(self.status_dot, fill=color)
        # Update label
        self.lbl_status.configure(text=f"Status: {status_text}", text_color=color if status_text not in ("Idle", "Stopping...") else THEME["text_secondary"])

    def disable_all_buttons(self):
        self.btn_run.configure(state="disabled")
        self.btn_run_eval.configure(state="disabled")
        self.btn_run_audit.configure(state="disabled")
        self.btn_run_edit.configure(state="disabled")
        self.lbl_tools_notice.configure(text="Pipeline/Tool execution is currently running...", text_color=THEME["error"])

    def enable_all_buttons(self):
        self.btn_run.configure(state="normal")
        self.btn_run_eval.configure(state="normal")
        self.btn_run_audit.configure(state="normal")
        self.btn_run_edit.configure(state="normal")
        self.lbl_tools_notice.configure(text="Tools can only be run when the main pipeline is idle.", text_color=THEME["text_secondary"])

    # ---------------------------------------------------------------------------
    # Threaded Process Runner Implementation
    # ---------------------------------------------------------------------------
    def execute_subprocess(self, cmd_args, project_name, execution_header=""):
        if self.is_running:
            return
        
        # Save settings on run
        self.save_settings()
        
        self.is_running = True
        self.set_status("Running", THEME["accent"])
        self.disable_all_buttons()
        self.btn_stop.configure(state="normal")

        # Clear log text pane and format header
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        
        if execution_header:
            self.log_textbox.insert("end", f"=== {execution_header} ===\n")
            
        self.log_textbox.insert("end", f"Project:     {project_name}\n")
        self.log_textbox.insert("end", f"Command:     {shlex.join(cmd_args)}\n")
        self.log_textbox.insert("end", "="*80 + "\n\n")
        self.log_textbox.configure(state="disabled")

        # Spawn reader thread
        self.thread = threading.Thread(
            target=self.process_executor_thread,
            args=(cmd_args, project_name),
            daemon=True
        )
        self.thread.start()

    def process_executor_thread(self, cmd_args, project_name):
        # Configure process environment variables
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Real-time stdout buffering

        try:
            self.process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )

            # Stream stdout/stderr outputs to UI queue
            for line in iter(self.process.stdout.readline, ''):
                self.log_queue.put(line)
            
            self.process.wait()
            ret_code = self.process.returncode
            self.log_queue.put(("SENTINEL", ret_code))
        except Exception as e:
            self.log_queue.put(("ERROR", str(e)))

    def stop_process(self):
        if not self.process:
            return
        
        self.write_log("\n[SYSTEM] Stopping process...\n")
        self.set_status("Stopping...", "#F59E0B")

        import platform
        if platform.system() == "Windows":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                self.write_log("[SYSTEM] Process tree terminated using taskkill.\n")
            except Exception as e:
                self.write_log(f"[SYSTEM] Failed to run taskkill: {e}. Falling back to terminate().\n")
                self.process.terminate()
        else:
            self.process.terminate()

            # Background thread to monitor process and send SIGKILL if still active after 3s
            def poll_and_kill():
                for _ in range(30):  # 3 seconds max polling
                    if self.process is None or self.process.poll() is not None:
                        return
                    threading.Event().wait(0.1)
                
                if self.process and self.process.poll() is None:
                    self.write_log("\n[SYSTEM] Process still alive after 3s. Force killing (SIGKILL)...\n")
                    self.process.kill()

            threading.Thread(target=poll_and_kill, daemon=True).start()

    def poll_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                
                # Check for sentinel / completion
                if isinstance(item, tuple) and item[0] == "SENTINEL":
                    ret_code = item[1]
                    self.is_running = False
                    self.process = None
                    self.enable_all_buttons()
                    self.btn_stop.configure(state="disabled")

                    if ret_code == 0:
                        self.set_status("Success", THEME["success"])
                        self.write_log(f"\n[SUCCESS] Run finished successfully.\n")
                    elif ret_code in (-15, -9, 15, 9):  # Terminated by signals
                        self.set_status("Stopped", THEME["text_secondary"])
                        self.write_log(f"\n[STOPPED] Stopped by user.\n")
                    else:
                        self.set_status("Error", THEME["error"])
                        self.write_log(f"\n[ERROR] Finished with non-zero exit code {ret_code}.\n")
                
                # Check for launch errors
                elif isinstance(item, tuple) and item[0] == "ERROR":
                    err_msg = item[1]
                    self.is_running = False
                    self.process = None
                    self.enable_all_buttons()
                    self.btn_stop.configure(state="disabled")
                    self.set_status("Error", THEME["error"])
                    self.write_log(f"\n[LAUNCH ERROR] Failed to spawn process:\n{err_msg}\n")
                
                # Write log line
                else:
                    self.write_log(item)
        except queue.Empty:
            pass

        # Schedule next queue check (100ms)
        self.after(100, self.poll_queue)

    def write_log(self, text):
        self.log_textbox.configure(state="normal")
        start_index = self.log_textbox.index("end-1c")
        self.log_textbox.insert("end", text)
        end_index = self.log_textbox.index("end-1c")

        # Color logging output lines selectively
        inserted = text.lower()
        if any(term in inserted for term in ("[error]", "fail", "exception", "traceback")):
            self.log_textbox.tag_add("error", start_index, end_index)
        elif any(term in inserted for term in ("[success]", "pipeline complete")):
            self.log_textbox.tag_add("success", start_index, end_index)
        elif any(term in inserted for term in ("[warn]", "warning")):
            self.log_textbox.tag_add("warning", start_index, end_index)

        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    # ---------------------------------------------------------------------------
    # Action Handlers: Tab 1 Pipeline Run
    # ---------------------------------------------------------------------------
    def run_pipeline(self):
        if self.is_running:
            return

        project = self.entry_project.get().strip()
        genre = self.entry_genre.get().strip()
        chapters = self.entry_chapters.get().strip()
        words = self.entry_words.get().strip()

        # Validate inputs
        if not project:
            self.write_log("[VALIDATION ERROR] Project name is required.\n")
            self.set_status("Error", THEME["error"])
            return

        # Prepare command line arguments
        cmd = ["uv", "run", "python", "run_pipeline.py", "--project", project]

        if self.cb_scratch.get():
            cmd.append("--from-scratch")

        if genre:
            cmd += ["--genre", genre]
        if chapters:
            cmd += ["--chapters", chapters]

        notes = self.txt_notes.get("1.0", "end-1c").strip()
        if notes:
            cmd += ["--notes", notes]
        
        if words:
            try:
                # verify integer
                int(words)
                cmd += ["--words-per-chapter", words]
            except ValueError:
                self.write_log(f"[VALIDATION WARNING] Invalid Words value '{words}', falling back to default.\n")

        # Thread through Cycle Configuration Tab options
        try:
            cycles = int(self.entry_cycles.get().strip())
            cmd += ["--revision-cycles", str(cycles)]
        except ValueError:
            pass

        if self.cb_skip_adv.get():
            cmd.append("--skip-adversarial-editing")
        if self.cb_skip_cuts.get():
            cmd.append("--skip-mechanical-cuts")
        if self.cb_skip_panel.get():
            cmd.append("--skip-reader-panel")
        if self.cb_skip_targeted.get():
            cmd.append("--skip-targeted-revisions")
        if self.cb_skip_eval.get():
            cmd.append("--skip-full-novel-eval")
        if self.cb_skip_opus.get():
            cmd.append("--skip-opus-review")

        # Execute
        self.execute_subprocess(cmd, project, "PIPELINE RUN")

    # ---------------------------------------------------------------------------
    # Action Handlers: Tab 2 Tool Runs
    # ---------------------------------------------------------------------------
    def run_eval_tool(self):
        project = self.eval_project_dropdown.get()
        chapter = self.entry_eval_chapter.get().strip()

        if not chapter:
            self.write_log("[VALIDATION ERROR] Chapter number is required for evaluation.\n")
            return
        try:
            int(chapter)
        except ValueError:
            self.write_log(f"[VALIDATION ERROR] Chapter '{chapter}' is not a valid integer.\n")
            return

        cmd = ["uv", "run", "python", "evaluate.py", "--chapter", chapter, "--project", project]
        
        # Switch tab view to 'Run' to read logging stream output
        self.tabview.set("Run")
        self.execute_subprocess(cmd, project, f"TOOL RUN: evaluate.py --chapter {chapter}")

    def run_audit_tool(self):
        project = self.audit_project_dropdown.get()
        
        cmd = ["uv", "run", "python", "scratch/audit_word_counts.py", "--project", project]

        self.tabview.set("Run")
        self.execute_subprocess(cmd, project, "TOOL RUN: audit_word_counts.py")

    def run_edit_tool(self):
        project = self.edit_project_dropdown.get()
        chapter = self.entry_edit_chapter.get().strip()

        if not chapter:
            self.write_log("[VALIDATION ERROR] Chapter selection is required for adversarial editing.\n")
            return
        try:
            int(chapter)
        except ValueError:
            self.write_log(f"[VALIDATION ERROR] Chapter '{chapter}' is not a valid integer.\n")
            return
        
        cmd = ["uv", "run", "python", "adversarial_edit.py", chapter, "--project", project]

        self.tabview.set("Run")
        self.execute_subprocess(cmd, project, f"TOOL RUN: adversarial_edit.py {chapter}")


if __name__ == "__main__":
    app = AutonovelApp()
    app.mainloop()
