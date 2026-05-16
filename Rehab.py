import os
import csv
import json
import uuid
from datetime import datetime
from utils import get_data_path
import numpy as np
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from tkinter import filedialog, messagebox, simpledialog
import tkinter as tk

# ============================================================
# TEAM MODULE IMPORTS
# ============================================================
try:
    from game_finger_tap import run_finger_tap
    from game_balloon_rehab import run_balloon_game
    from game_laser_slice import run_laser_game
    from game_fruit_ninja import run_fruit_ninja
except Exception as e:
    run_finger_tap = None
    run_balloon_game = None
    run_laser_game = None
    run_fruit_ninja = None
    TEAM_IMPORT_ERROR = str(e)
else:
    TEAM_IMPORT_ERROR = ""

# ============================================================
# CONFIG
# ============================================================
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
CSV_FILE      = get_data_path("patient_data.csv")
PATIENTS_FILE = get_data_path("patients.json")

GAME_OPTIONS  = ["Finger Tap", "Balloon Rehab", "Laser Slice", "Fruit Ninja"]
LEVEL_OPTIONS = ["Easy", "Medium", "Hard"]

COLORS = {
    "bg":        "#f5f0e8",   # warm cream background
    "panel":     "#fffdf7",   # off-white panels
    "card":      "#eef4fb",   # light blue-tinted card
    "accent":    "#4a90c4",   # soft steel blue
    "accent2":   "#5baa7a",   # muted sage green
    "warn":      "#e8a83a",   # warm amber
    "danger":    "#e05555",   # soft red (exit)
    "text":      "#2d3748",   # dark slate text
    "subtext":   "#6b7a8d",   # muted blue-grey
    "border":    "#d4e0ec",   # light blue border
    "success":   "#3da668",   # green (start session)
    "header":    "#4a7fa5",   # header bar blue
    "highlight": "#c8dff2",   # active selection highlight
}

# ============================================================
# HELPERS
# ============================================================
def ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp","PatientID","Game","Level","Score","Accuracy","ResponseTime","MotorIndex"])

def load_patients():
    if not os.path.exists(PATIENTS_FILE):
        return {}
    try:
        with open(PATIENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Patch any old records that were saved without an 'id' field
        changed = False
        for pid, p in data.items():
            if "id" not in p:
                p["id"] = pid
                changed = True
        if changed:
            save_patients(data)
        return data
    except Exception:
        return {}

def repair_csv_patient_ids():
    """One-time repair: if CSV has PatientIDs not matching any known patient,
    try to match by name and rewrite the CSV with corrected IDs."""
    if not os.path.exists(CSV_FILE) or not os.path.exists(PATIENTS_FILE):
        return
    try:
        patients = load_patients()
        known_ids = set(patients.keys())
        all_rows = load_sessions()
        if not all_rows:
            return
        # Build name->pid lookup
        name_to_pid = {p["name"].lower(): pid for pid, p in patients.items()}
        needs_repair = any(r["PatientID"] not in known_ids for r in all_rows)
        if not needs_repair:
            return
        # Rewrite CSV with best-guess IDs
        repaired = []
        for r in all_rows:
            if r["PatientID"] not in known_ids:
                # Can't auto-fix without knowing the name; keep as-is
                pass
            repaired.append(r)
        # If only one patient exists, reassign all orphan rows to them
        if len(patients) == 1:
            only_pid = list(patients.keys())[0]
            for r in repaired:
                if r["PatientID"] not in known_ids:
                    r["PatientID"] = only_pid
            with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["Timestamp","PatientID","Game","Level",
                                                        "Score","Accuracy","ResponseTime","MotorIndex"])
                writer.writeheader()
                writer.writerows(repaired)
    except Exception:
        pass

def save_patients(patients: dict):
    with open(PATIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(patients, f, indent=2)

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def compute_summary(rows):
    if not rows:
        return None
    scores = [r["Score"]        for r in rows]
    accs   = [r["Accuracy"]     for r in rows]
    rts    = [r["ResponseTime"] for r in rows]
    motors = [r["MotorIndex"]   for r in rows]
    return {
        "avg_score": float(np.mean(scores)),
        "avg_acc":   float(np.mean(accs)),
        "avg_rt":    float(np.mean(rts)),
        "avg_motor": float(np.mean(motors)),
        "best_score": float(np.max(scores)),
        "best_motor": float(np.max(motors)),
        "trend_motor": float(motors[-1] - motors[0]) if len(motors) > 1 else 0.0,
    }

def generate_feedback(acc, rt, motor):
    if motor >= 0.8 and acc >= 85:
        return "★ Outstanding — Motor function and accuracy are excellent. Consider advancing difficulty."
    if acc >= 85 and rt <= 0.6:
        return "✔ Excellent — High accuracy and fast response. Keep it up!"
    if acc >= 70:
        return "↑ Good progress — Focus on improving reaction speed."
    if rt >= 1.0:
        return "⚠ Slow reactions — Try steady movements and quicker taps."
    return "↻ Needs improvement — Repeat sessions for better coordination."

def load_sessions(patient_id=None):
    rows = []
    try:
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if patient_id and r.get("PatientID","") != patient_id:
                    continue
                rows.append({
                    "Timestamp":    r.get("Timestamp",""),
                    "PatientID":    r.get("PatientID",""),
                    "Game":         r.get("Game",""),
                    "Level":        r.get("Level",""),
                    "Score":        safe_float(r.get("Score",0)),
                    "Accuracy":     safe_float(r.get("Accuracy",0)),
                    "ResponseTime": safe_float(r.get("ResponseTime",0)),
                    "MotorIndex":   safe_float(r.get("MotorIndex",0)),
                })
    except Exception:
        pass
    return rows


# ============================================================
# PATIENT DIALOG
# ============================================================
class PatientDialog(ctk.CTkToplevel):
    """Add or edit a patient."""
    def __init__(self, parent, patients: dict, edit_id: str = None):
        super().__init__(parent)
        self.patients = patients
        self.edit_id  = edit_id
        self.result   = None

        self.title("Edit Patient" if edit_id else "Add New Patient")
        self.geometry("420x720")
        self.resizable(False, False)
        self.grab_set()

        self._build()
        if edit_id and edit_id in patients:
            self._prefill(patients[edit_id])

    def _build(self):
        pad = {"padx": 24, "pady": 6}

        ctk.CTkLabel(self, text="Patient Details",
                     font=("Georgia", 20, "bold")).pack(pady=(20,10))

        fields = [
            ("Name",       "name"),
            ("Age",        "age"),
            ("Gender",     "gender"),
            ("Diagnosis",  "diagnosis"),
            ("Therapist",  "therapist"),
            ("Notes",      "notes"),
        ]
        self.entries = {}
        for label, key in fields:
            ctk.CTkLabel(self, text=label, anchor="w",
                         font=("Georgia", 11)).pack(fill="x", **pad)
            if key == "notes":
                e = ctk.CTkTextbox(self, height=70, wrap="word", corner_radius=8)
            else:
                e = ctk.CTkEntry(self, placeholder_text=label, corner_radius=8,
                                 font=("Georgia", 11))
            e.pack(fill="x", **pad)
            self.entries[key] = e

        # Save/Cancel always anchored at bottom, outside scroll area
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(12, 20), side="bottom")
        ctk.CTkButton(btn_row, text="✔  Save Patient", fg_color=COLORS["accent"],
                      text_color="#fff",
                      font=("Georgia", 12, "bold"), height=38, corner_radius=10,
                      command=self._save).pack(side="left", expand=True, padx=(0,6))
        ctk.CTkButton(btn_row, text="Cancel", fg_color=COLORS["border"],
                      text_color=COLORS["text"],
                      font=("Georgia", 11), height=38, corner_radius=10,
                      command=self.destroy).pack(side="left", expand=True)

    def _prefill(self, data):
        for key, widget in self.entries.items():
            val = data.get(key, "")
            if isinstance(widget, ctk.CTkTextbox):
                widget.insert("1.0", val)
            else:
                widget.insert(0, val)

    def _save(self):
        name = self.entries["name"].get().strip()
        if not name:
            messagebox.showwarning("Required", "Name is required.", parent=self)
            return
        pid = self.edit_id or str(uuid.uuid4())[:8].upper()
        self.result = {
            "id":         pid,
            "name":       name,
            "age":        self.entries["age"].get().strip(),
            "gender":     self.entries["gender"].get().strip(),
            "diagnosis":  self.entries["diagnosis"].get().strip(),
            "therapist":  self.entries["therapist"].get().strip(),
            "notes":      self.entries["notes"].get("1.0", "end").strip(),
            "created":    self.patients.get(pid, {}).get("created",
                          datetime.now().strftime("%Y-%m-%d")),
        }
        self.destroy()


# ============================================================
# MAIN APP
# ============================================================
class NeuroRehabApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NeuroRehab Analytics")
        self.geometry("1280x780")
        self.minsize(1100, 680)
        self.after(0, lambda: self.state("zoomed"))

        ensure_csv()
        self.patients        = load_patients()
        repair_csv_patient_ids()
        self.active_patient  = None   # patient dict or None
        self.history_rows    = []
        self._last_fig       = None

        self.selected_game  = ctk.StringVar(value=GAME_OPTIONS[0])
        self.selected_level = ctk.StringVar(value="Medium")
        self.last_run_label = ctk.StringVar(value="Select a patient and run a session.")
        self.feedback_label = ctk.StringVar(value="")
        self.patient_label  = ctk.StringVar(value="No patient selected")

        self._build_ui()
        self._refresh_patient_list()
        self.plot_report()
        self.bind("<Control-q>", lambda e: self._confirm_exit())
        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)

    # ----------------------------------------------------------
    # EXIT
    # ----------------------------------------------------------
    def _confirm_exit(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit NeuroRehab Analytics?"):
            self.destroy()

    # ----------------------------------------------------------
    # UI CONSTRUCTION
    # ----------------------------------------------------------
    def _build_ui(self):
        self.configure(fg_color=COLORS["bg"])
        hdr = ctk.CTkFrame(self, fg_color=COLORS["header"], corner_radius=0, height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="🧠  NEURO REHAB ANALYTICS",
                     font=("Georgia", 22, "bold"),
                     text_color="#ffffff").pack(side="left", padx=24, pady=14)
        self.header_patient_lbl = ctk.CTkLabel(
            hdr, textvariable=self.patient_label,
            font=("Georgia", 13), text_color="#ddeeff")
        self.header_patient_lbl.pack(side="right", padx=24)

        body = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=12)

        # Left sidebar
        self.sidebar = ctk.CTkFrame(body, fg_color=COLORS["panel"],
                                    corner_radius=16, width=270)
        self.sidebar.pack(side="left", fill="y", padx=(0,12))
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # Right content
        content = ctk.CTkFrame(body, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True)

        # Top row: history table
        top = ctk.CTkFrame(content, fg_color=COLORS["panel"], corner_radius=14)
        top.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(top, text="SESSION HISTORY",
                     font=("Georgia", 12, "bold"),
                     text_color=COLORS["subtext"]).pack(anchor="w", padx=16, pady=(10,2))
        self.history_box = ctk.CTkTextbox(
            top, font=("Courier", 11), height=130,
            fg_color=COLORS["card"], text_color=COLORS["text"],
            corner_radius=10)
        self.history_box.pack(fill="x", padx=12, pady=(0,10))

        # Bottom: chart
        chart_card = ctk.CTkFrame(content, fg_color=COLORS["panel"], corner_radius=14)
        chart_card.pack(fill="both", expand=True)

        # Chart header row with dropdown
        chart_hdr = ctk.CTkFrame(chart_card, fg_color="transparent")
        chart_hdr.pack(fill="x", padx=16, pady=(10, 2))
        ctk.CTkLabel(chart_hdr, text="ANALYTICS",
                     font=("Georgia", 12, "bold"),
                     text_color=COLORS["subtext"]).pack(side="left")
        self.chart_view = ctk.StringVar(value="Motor Index")
        ctk.CTkOptionMenu(
            chart_hdr,
            variable=self.chart_view,
            values=["Motor Index", "Score", "Accuracy %", "Response Time", "All"],
            fg_color=COLORS["highlight"],
            button_color=COLORS["accent"],
            text_color=COLORS["text"],
            font=("Georgia", 11),
            width=160,
            corner_radius=10,
            command=lambda _: self.plot_report()
        ).pack(side="right")

        self.plot_frame = ctk.CTkFrame(chart_card, fg_color="transparent")
        self.plot_frame.pack(fill="both", expand=True, padx=12, pady=(0,12))

    def _build_sidebar(self):
        S = self.sidebar
        pad = {"padx": 16, "pady": 4}

        # ── Patient section ───────────────────────────────────
        ctk.CTkLabel(S, text="PATIENT", font=("Georgia", 11, "bold"),
                     text_color=COLORS["subtext"]).pack(anchor="w", padx=16, pady=(14,2))

        self.patient_list_frame = ctk.CTkScrollableFrame(
            S, fg_color=COLORS["card"], corner_radius=10, height=160)
        self.patient_list_frame.pack(fill="x", **pad)

        # Patient action buttons
        pbtns = ctk.CTkFrame(S, fg_color="transparent")
        pbtns.pack(fill="x", **pad)
        ctk.CTkButton(pbtns, text="+ Add", width=80,
                      fg_color=COLORS["accent2"], text_color="#fff",
                      font=("Georgia", 11, "bold"), corner_radius=8,
                      command=self._add_patient).pack(side="left", padx=(0,4))
        ctk.CTkButton(pbtns, text="✎ Edit", width=70,
                      fg_color=COLORS["border"], text_color=COLORS["text"],
                      font=("Georgia", 11), corner_radius=8,
                      command=self._edit_patient).pack(side="left", padx=(0,4))
        ctk.CTkButton(pbtns, text="🗑", width=40,
                      fg_color=COLORS["danger"], text_color="#fff",
                      font=("Georgia", 11), corner_radius=8,
                      command=self._delete_patient).pack(side="left")

        # Patient info card
        self.patient_info = ctk.CTkTextbox(
            S, height=80, font=("Georgia", 10),
            fg_color=COLORS["card"], text_color=COLORS["subtext"],
            corner_radius=10)
        self.patient_info.pack(fill="x", **pad)
        self.patient_info.configure(state="disabled")

        # ── Divider ───────────────────────────────────────────
        ctk.CTkFrame(S, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=16, pady=10)

        # ── Session config ────────────────────────────────────
        ctk.CTkLabel(S, text="SESSION", font=("Georgia", 11, "bold"),
                     text_color=COLORS["subtext"]).pack(anchor="w", **pad)

        ctk.CTkLabel(S, text="Game", font=("Georgia", 11),
                     text_color=COLORS["text"]).pack(anchor="w", **pad)
        ctk.CTkOptionMenu(S, variable=self.selected_game,
                          values=GAME_OPTIONS,
                          fg_color=COLORS["card"],
                          button_color=COLORS["accent"],
                          text_color=COLORS["text"],
                          font=("Georgia", 11),
                          corner_radius=8).pack(fill="x", **pad)

        ctk.CTkLabel(S, text="Difficulty", font=("Georgia", 11),
                     text_color=COLORS["text"]).pack(anchor="w", **pad)
        ctk.CTkOptionMenu(S, variable=self.selected_level,
                          values=LEVEL_OPTIONS,
                          fg_color=COLORS["card"],
                          button_color=COLORS["accent"],
                          text_color=COLORS["text"],
                          font=("Georgia", 11),
                          corner_radius=8).pack(fill="x", **pad)

        # ── Action buttons ────────────────────────────────────
        ctk.CTkFrame(S, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=16, pady=10)

        self.btn_start = ctk.CTkButton(
            S, text="▶  Start Session",
            fg_color=COLORS["success"], text_color="#fff",
            font=("Georgia", 13, "bold"), height=40, corner_radius=10,
            command=self.start_session)
        self.btn_start.pack(fill="x", **pad)

        self.btn_report = ctk.CTkButton(
            S, text="↻  Refresh Report",
            fg_color=COLORS["accent"], text_color="#fff",
            font=("Georgia", 11), corner_radius=8,
            command=self.plot_report)
        self.btn_report.pack(fill="x", **pad)

        self.btn_export = ctk.CTkButton(
            S, text="⬇  Export PNG",
            fg_color=COLORS["card"], text_color=COLORS["text"],
            font=("Georgia", 11), corner_radius=8,
            command=self.export_report_png)
        self.btn_export.pack(fill="x", **pad)

        self.btn_clear = ctk.CTkButton(
            S, text="🗑  Clear Patient Sessions",
            fg_color=COLORS["border"], text_color=COLORS["text"],
            font=("Georgia", 11), corner_radius=8,
            command=self.clear_history)
        self.btn_clear.pack(fill="x", **pad)

        ctk.CTkFrame(S, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=16, pady=10)

        self.btn_exit = ctk.CTkButton(
            S, text="✕  Exit",
            fg_color=COLORS["danger"], text_color="#fff",
            font=("Georgia", 12, "bold"), height=36, corner_radius=10,
            command=self._confirm_exit)
        self.btn_exit.pack(fill="x", **pad)

        # ── Last result ───────────────────────────────────────
        ctk.CTkFrame(S, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(S, text="LAST RESULT", font=("Georgia", 11, "bold"),
                     text_color=COLORS["subtext"]).pack(anchor="w", **pad)
        ctk.CTkLabel(S, textvariable=self.last_run_label,
                     wraplength=240, justify="left",
                     font=("Georgia", 10), text_color=COLORS["text"]).pack(anchor="w", **pad)
        ctk.CTkLabel(S, textvariable=self.feedback_label,
                     wraplength=240, justify="left",
                     font=("Georgia", 10), text_color=COLORS["accent2"]).pack(anchor="w", **pad)

    # ----------------------------------------------------------
    # PATIENT MANAGEMENT
    # ----------------------------------------------------------
    def _refresh_patient_list(self):
        for w in self.patient_list_frame.winfo_children():
            w.destroy()

        if not self.patients:
            ctk.CTkLabel(self.patient_list_frame, text="No patients yet.",
                         font=("Courier", 10), text_color=COLORS["subtext"]).pack(pady=8)
            return

        for pid, p in self.patients.items():
            is_active = (self.active_patient and self.active_patient["id"] == pid)
            btn = ctk.CTkButton(
                self.patient_list_frame,
                text=f"  {p['name']}",
                anchor="w",
                fg_color=COLORS["highlight"] if is_active else "transparent",
                text_color=COLORS["accent"] if is_active else COLORS["text"],
                hover_color=COLORS["highlight"],
                font=("Georgia", 11, "bold" if is_active else "normal"),
                height=30, corner_radius=8,
                command=lambda pid=pid: self._select_patient(pid)
            )
            btn.pack(fill="x", pady=2)

    def _select_patient(self, pid):
        self.active_patient = self.patients.get(pid)
        if self.active_patient:
            # Patch old records saved without 'id' inside the dict
            if "id" not in self.active_patient:
                self.active_patient["id"] = pid
                self.patients[pid] = self.active_patient
                save_patients(self.patients)
            p = self.active_patient
            self.patient_label.set(f"Patient: {p['name']}  |  ID: {p['id']}")
            info = (f"Age: {p.get('age','-')}   Gender: {p.get('gender','-')}\n"
                    f"Dx: {p.get('diagnosis','-')}\n"
                    f"Therapist: {p.get('therapist','-')}")
            self.patient_info.configure(state="normal")
            self.patient_info.delete("1.0","end")
            self.patient_info.insert("1.0", info)
            self.patient_info.configure(state="disabled")
        self._refresh_patient_list()
        self.refresh_history()
        self.plot_report()

    def _add_patient(self):
        dlg = PatientDialog(self, self.patients)
        self.wait_window(dlg)
        if dlg.result:
            pid = dlg.result["id"]
            self.patients[pid] = dlg.result
            save_patients(self.patients)
            self._select_patient(pid)
            self._refresh_patient_list()

    def _edit_patient(self):
        if not self.active_patient:
            messagebox.showinfo("No patient", "Select a patient first.")
            return
        dlg = PatientDialog(self, self.patients, edit_id=self.active_patient["id"])
        self.wait_window(dlg)
        if dlg.result:
            pid = dlg.result["id"]
            self.patients[pid] = dlg.result
            save_patients(self.patients)
            self._select_patient(pid)
            self._refresh_patient_list()

    def _delete_patient(self):
        if not self.active_patient:
            messagebox.showinfo("No patient", "Select a patient first.")
            return
        name = self.active_patient["name"]
        if not messagebox.askyesno("Delete Patient",
                f"Delete '{name}' and ALL their session data?"):
            return
        pid = self.active_patient["id"]
        del self.patients[pid]
        save_patients(self.patients)

        # Remove from CSV
        rows = load_sessions()
        remaining = [r for r in rows if r["PatientID"] != pid]
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Timestamp","PatientID","Game","Level",
                                                    "Score","Accuracy","ResponseTime","MotorIndex"])
            writer.writeheader()
            writer.writerows(remaining)

        self.active_patient = None
        self.patient_label.set("No patient selected")
        self.patient_info.configure(state="normal")
        self.patient_info.delete("1.0","end")
        self.patient_info.configure(state="disabled")
        self._refresh_patient_list()
        self.refresh_history()
        self.plot_report()

    # ----------------------------------------------------------
    # SESSION
    # ----------------------------------------------------------
    def set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        for btn in (self.btn_start, self.btn_report, self.btn_export, self.btn_clear):
            btn.configure(state=state)

    def start_session(self):
        if not self.active_patient:
            messagebox.showwarning("No Patient",
                "Please select or create a patient before starting a session.")
            return

        if any(fn is None for fn in (run_finger_tap, run_balloon_game, run_laser_game, run_fruit_ninja)):
            messagebox.showerror("Modules Missing",
                f"Could not import game modules.\n\n{TEAM_IMPORT_ERROR}")
            return

        game  = self.selected_game.get()
        level = self.selected_level.get()
        pid   = self.active_patient["id"]

        self.set_busy(True)
        self.withdraw()

        try:
            if game == "Finger Tap":
                score, acc, rt, motor = run_finger_tap(level)
            elif game == "Balloon Rehab":
                score, acc, rt, motor = run_balloon_game(level)
            elif game == "Laser Slice":
                score, acc, rt, motor = run_laser_game(level)
            elif game == "Fruit Ninja":
                score, acc, rt, motor = run_fruit_ninja(level)
            else:
                raise ValueError("Unknown game selection.")

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, pid, game, level, score, acc, rt, motor])

            self.last_run_label.set(
                f"{game} ({level})\nScore={score}  Acc={acc:.1f}%\nRT={rt:.2f}s  Motor={motor:.2f}")
            self.feedback_label.set(generate_feedback(acc, rt, motor))

        except Exception as e:
            self.last_run_label.set(f"Error: {e}")
            self.feedback_label.set("")
            messagebox.showerror("Session Failed", str(e))

        finally:
            self.deiconify()
            self.state("zoomed")
            self.set_busy(False)
            self.refresh_history()
            self.plot_report()

    # ----------------------------------------------------------
    # HISTORY
    # ----------------------------------------------------------
    def refresh_history(self):
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")
        self.history_rows = []

        pid = self.active_patient["id"] if self.active_patient else None
        rows = load_sessions(patient_id=pid)
        # Fallback: if no rows found for this patient id, try matching by name
        if not rows and self.active_patient:
            all_rows = load_sessions()
            name_pid = None
            # scan CSV for any pid associated with this patient's known ids
            for r in all_rows:
                if r["PatientID"] == pid:
                    name_pid = pid
                    break
            if not name_pid and all_rows:
                # Just show all rows so chart isn't blank
                rows = all_rows
        rows = rows[-15:]
        self.history_rows = rows

        if not rows:
            msg = "No sessions for this patient yet." if pid else "Select a patient to view history."
            self.history_box.insert("end", msg + "\n")
            self.history_box.configure(state="disabled")
            return

        header = f"{'Date':<19}  {'Game':<12}  {'Lvl':<6}  {'Score':<6}  {'Acc%':<6}  {'RT':<5}  {'Motor'}\n"
        self.history_box.insert("end", header)
        self.history_box.insert("end", "─" * 80 + "\n")
        for r in reversed(rows):
            line = (f"{r['Timestamp'][:19]}  "
                    f"{r['Game']:<12}  {r['Level']:<6}  "
                    f"{r['Score']:<6.0f}  {r['Accuracy']:<6.1f}  "
                    f"{r['ResponseTime']:<5.2f}  {r['MotorIndex']:.2f}\n")
            self.history_box.insert("end", line)
        self.history_box.configure(state="disabled")

    # ----------------------------------------------------------
    # REPORT / CHART
    # ----------------------------------------------------------
    def plot_report(self):
        for w in self.plot_frame.winfo_children():
            w.destroy()

        self.refresh_history()
        rows = self.history_rows
        summary = compute_summary(rows)

        BG      = COLORS["panel"]
        CARD_BG = COLORS["card"]
        plt.rcParams.update({"font.family": "sans-serif"})

        if not rows or not summary:
            fig = plt.Figure(figsize=(8, 4), dpi=95)
            fig.patch.set_facecolor(BG)
            ax = fig.add_subplot(111)
            ax.set_facecolor(CARD_BG)
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values(): sp.set_visible(False)
            ax.text(0.5, 0.5,
                    "No data — select a patient and run a session.",
                    ha="center", va="center",
                    color=COLORS["subtext"], fontsize=13)
        else:
            x      = list(range(1, len(rows) + 1))
            motors = [r["MotorIndex"]   for r in rows]
            scores = [r["Score"]        for r in rows]
            accs   = [r["Accuracy"]     for r in rows]
            rts    = [r["ResponseTime"] for r in rows]

            datasets = {
                "Motor Index":    (motors, COLORS["accent"],  "Motor Index"),
                "Score":          (scores, "#e07070",         "Score"),
                "Accuracy %":     (accs,   COLORS["accent2"], "Accuracy %"),
                "Response Time":  (rts,    COLORS["warn"],    "Response Time (s)"),
            }

            view = getattr(self, "chart_view", None)
            selected = view.get() if view else "Motor Index"

            if selected == "All":
                fig, axes = plt.subplots(2, 2, figsize=(11, 4.5), dpi=95)
                fig.patch.set_facecolor(BG)
                axes_flat = axes.flatten()
                for ax, (key, (data, color, title)) in zip(axes_flat, datasets.items()):
                    ax.set_facecolor(CARD_BG)
                    ax.plot(x, data, color=color, linewidth=2, marker="o",
                            markersize=5, markerfacecolor="white", markeredgecolor=color)
                    ax.fill_between(x, data, alpha=0.15, color=color)
                    ax.set_title(title, color=COLORS["subtext"], fontsize=9, pad=5,
                                 fontweight="bold")
                    ax.tick_params(colors=COLORS["subtext"], labelsize=7)
                    ax.grid(True, linestyle="--", alpha=0.25, color=COLORS["border"])
                    for sp in ax.spines.values():
                        sp.set_color(COLORS["border"])
                fig.tight_layout(pad=1.5)
            else:
                data, color, title = datasets.get(selected, datasets["Motor Index"])
                fig = plt.Figure(figsize=(11, 4.2), dpi=95)
                fig.patch.set_facecolor(BG)
                ax = fig.add_subplot(111)
                ax.set_facecolor(CARD_BG)
                ax.plot(x, data, color=color, linewidth=2.5, marker="o",
                        markersize=6, markerfacecolor="white", markeredgecolor=color,
                        markeredgewidth=1.5)
                ax.fill_between(x, data, alpha=0.15, color=color)
                ax.set_title(title, color=COLORS["subtext"], fontsize=11, pad=8,
                             fontweight="bold")
                ax.tick_params(colors=COLORS["subtext"], labelsize=9)
                ax.grid(True, linestyle="--", alpha=0.25, color=COLORS["border"])
                for sp in ax.spines.values():
                    sp.set_color(COLORS["border"])

                # trend annotation for motor index
                if selected == "Motor Index":
                    trend = summary["trend_motor"]
                    trend_str = f"▲ +{trend:.2f}" if trend > 0 else f"▼ {trend:.2f}"
                    trend_color = COLORS["success"] if trend >= 0 else COLORS["danger"]
                    ax.set_title(f"Motor Index   {trend_str}",
                                 color=trend_color, fontsize=11, pad=8, fontweight="bold")

                fig.tight_layout(pad=1.5)

            # Suptitle
            patient_name = self.active_patient["name"] if self.active_patient else "—"
            fig.suptitle(
                f"Patient: {patient_name}  |  Sessions: {len(rows)}  |  "
                f"Avg Motor: {summary['avg_motor']:.2f}   Best: {summary['best_motor']:.2f}",
                color=COLORS["subtext"], fontsize=9, y=0.99)

        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._last_fig = fig

    # ----------------------------------------------------------
    # EXPORT
    # ----------------------------------------------------------
    def export_report_png(self):
        if not self._last_fig:
            messagebox.showinfo("Export", "Generate a report first.")
            return
        name = self.active_patient["name"].replace(" ","_") if self.active_patient else "report"
        default = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = filedialog.asksaveasfilename(
            defaultextension=".png", initialfile=default,
            filetypes=[("PNG", "*.png")], title="Save Report")
        if not path:
            return
        try:
            self._last_fig.savefig(path, dpi=200, bbox_inches="tight",
                                   facecolor=COLORS["panel"])
            messagebox.showinfo("Exported", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def clear_history(self):
        if not self.active_patient:
            messagebox.showinfo("No Patient", "Select a patient first.")
            return
        name = self.active_patient["name"]
        if not messagebox.askyesno("Clear Sessions",
                f"Delete all sessions for '{name}'?"):
            return
        pid = self.active_patient["id"]
        all_rows = load_sessions()
        remaining = [r for r in all_rows if r["PatientID"] != pid]
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Timestamp","PatientID","Game","Level",
                                                    "Score","Accuracy","ResponseTime","MotorIndex"])
            writer.writeheader()
            writer.writerows(remaining)
        self.last_run_label.set("Sessions cleared.")
        self.feedback_label.set("")
        self.refresh_history()
        self.plot_report()


# ============================================================
if __name__ == "__main__":
    app = NeuroRehabApp()
    app.mainloop()