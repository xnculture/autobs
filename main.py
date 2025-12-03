import tkinter as tk
from tkinter import ttk, messagebox
import obs_core
import threading
import time
import json
import os
from datetime import datetime

class OBSSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OBS Auto Scheduler")
        self.root.geometry("900x700")
        self.root.resizable(False, False)

        # Initialize Core Logic
        self.core = obs_core.OBSSchedulerCore()

        # --- UI Layout ---
        self.create_widgets()
        
        # --- Start Scheduler Thread (GUI Mode) ---
        # The GUI runs its own scheduler loop to provide feedback
        self.running = True
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()

        # --- Initial Connection Attempt ---
        if self.core.config.get("auto_connect", False):
            self.connect_obs()

    def create_widgets(self):
        # 1. Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text="OBS WebSocket Connection")
        conn_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_host = ttk.Entry(conn_frame, width=15)
        self.entry_host.insert(0, self.core.config.get("host", "localhost"))
        self.entry_host.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_port = ttk.Entry(conn_frame, width=10)
        self.entry_port.insert(0, self.core.config.get("port", 4455))
        self.entry_port.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(conn_frame, text="Password:").grid(row=0, column=4, padx=5, pady=5)
        self.entry_pwd = ttk.Entry(conn_frame, show="*", width=15)
        self.entry_pwd.insert(0, self.core.config.get("password", ""))
        self.entry_pwd.grid(row=0, column=5, padx=5, pady=5)

        self.btn_connect = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection, takefocus=0)
        self.btn_connect.grid(row=0, column=6, padx=10, pady=5)

        self.lbl_status = ttk.Label(conn_frame, text="Status: Disconnected", foreground="red")
        self.lbl_status.grid(row=1, column=0, columnspan=7, pady=5)

        # 2. Scheduling Frame
        sched_frame = ttk.LabelFrame(self.root, text="Schedule Task")
        sched_frame.pack(padx=10, pady=5, fill="x")

        # --- Row 0: Freq -> Time -> Action ---
        
        # 1. Frequency
        ttk.Label(sched_frame, text="Freq:").grid(row=0, column=0, padx=5, pady=5)
        self.combo_freq = ttk.Combobox(sched_frame, values=["Daily", "Weekly", "Specific Date"], state="readonly", width=12)
        self.combo_freq.current(0)
        self.combo_freq.grid(row=0, column=1, padx=5, pady=5)
        self.combo_freq.bind("<<ComboboxSelected>>", self.update_dynamic_options)

        # 2. Time (Hour : Minute : AM/PM)
        ttk.Label(sched_frame, text="Time:").grid(row=0, column=2, padx=5, pady=5)
        
        time_frame = ttk.Frame(sched_frame)
        time_frame.grid(row=0, column=3, padx=0, pady=5)

        self.spin_hour = ttk.Spinbox(time_frame, from_=1, to=12, width=3, wrap=True)
        self.spin_hour.set(12)
        self.spin_hour.pack(side="left")

        ttk.Label(time_frame, text=":").pack(side="left")

        self.spin_min = ttk.Spinbox(time_frame, from_=0, to=59, width=3, wrap=True, format="%02.0f")
        self.spin_min.set("00")
        self.spin_min.pack(side="left")

        ttk.Label(time_frame, text=":").pack(side="left")

        self.spin_sec = ttk.Spinbox(time_frame, from_=0, to=59, width=3, wrap=True, format="%02.0f")
        self.spin_sec.set("00")
        self.spin_sec.pack(side="left")

        self.combo_ampm = ttk.Combobox(time_frame, values=["AM", "PM"], state="readonly", width=4)
        self.combo_ampm.current(0) # Default AM
        self.combo_ampm.pack(side="left", padx=5)

        # 3. Action
        ttk.Label(sched_frame, text="Action:").grid(row=0, column=4, padx=5, pady=5)
        self.combo_action = ttk.Combobox(sched_frame, values=[
            "Start Streaming", "Stop Streaming", 
            "Start Recording", "Stop Recording"
        ], state="readonly", width=15)
        self.combo_action.current(0)
        self.combo_action.grid(row=0, column=5, padx=5, pady=5)

        self.btn_add = ttk.Button(sched_frame, text="Add Task", command=self.add_task, takefocus=0)
        self.btn_add.grid(row=0, column=6, padx=10, pady=5)

        # Row 1: Dynamic Options (Date or Days)
        self.dynamic_frame = ttk.Frame(sched_frame)
        self.dynamic_frame.grid(row=1, column=0, columnspan=7, pady=5, sticky="w")
        
        # Components for Dynamic Frame
        # 1. Date Input
        self.lbl_date = ttk.Label(self.dynamic_frame, text="Date (YYYY-MM-DD):")
        self.entry_date = ttk.Entry(self.dynamic_frame, width=15)
        
        # 2. Weekday Checkboxes
        self.days_vars = {}
        self.days_frame = ttk.Frame(self.dynamic_frame)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.days_frame, text=day, variable=var)
            chk.pack(side="left", padx=2)
            self.days_vars[day] = var

        # Initial state
        self.update_dynamic_options()

        # 3. Task List
        list_frame = ttk.LabelFrame(self.root, text="Scheduled Tasks")
        list_frame.pack(padx=10, pady=5, fill="both", expand=True)

        # Columns: Freq, Details, Time, Action (Reordered)
        self.tree = ttk.Treeview(list_frame, columns=("Freq", "Details", "Time", "Action"), show="headings")
        self.tree.heading("Freq", text="Freq")
        self.tree.heading("Details", text="Details")
        self.tree.heading("Time", text="Time")
        self.tree.heading("Action", text="Action")
        
        self.tree.column("Freq", width=80)
        self.tree.column("Details", width=200)
        self.tree.column("Time", width=100)
        self.tree.column("Action", width=120)
        
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Configure tags for enabled/disabled
        self.tree.tag_configure("disabled", foreground="gray")
        self.tree.tag_configure("enabled", foreground="black")


        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side="bottom", fill="x", pady=5)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_task, takefocus=0).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Toggle Enable/Disable", command=self.toggle_task_status, takefocus=0).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Edit Selected", command=self.load_task_for_edit, takefocus=0).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all_tasks).pack(side="right", padx=5)


        # 4. Preset Management Frame
        preset_frame = ttk.LabelFrame(self.root, text="Presets")
        preset_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(preset_frame, text="Preset Name:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_preset = ttk.Entry(preset_frame, width=15)
        self.entry_preset.grid(row=0, column=1, padx=5, pady=5)

        self.btn_save_preset = ttk.Button(preset_frame, text="Save Preset", command=self.save_preset, takefocus=0)
        self.btn_save_preset.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(preset_frame, text="Load/Delete:").grid(row=0, column=3, padx=5, pady=5)
        self.combo_presets = ttk.Combobox(preset_frame, state="readonly", width=15)
        self.combo_presets.grid(row=0, column=4, padx=5, pady=5)
        self.refresh_preset_list()

        self.btn_load_preset = ttk.Button(preset_frame, text="Load", command=self.load_preset, takefocus=0)
        self.btn_load_preset.grid(row=0, column=5, padx=5, pady=5)
        
        self.btn_del_preset = ttk.Button(preset_frame, text="Delete", command=self.delete_preset, takefocus=0)
        self.btn_del_preset.grid(row=0, column=6, padx=5, pady=5)

        # Initialize internal task list
        self.current_tasks = []
        self.editing_index = None

        
        # Restore tasks from config
        for task in self.core.config.get("tasks", []):
            self.add_task_to_ui(task)
        
        # Initialize schedule in core
        self.core.schedule_jobs_from_config()

        # 5. Log Area
        log_frame = ttk.LabelFrame(self.root, text="Logs")
        log_frame.pack(padx=10, pady=5, fill="x")
        self.log_text = tk.Text(log_frame, height=5, state="disabled")
        self.log_text.pack(fill="x", padx=5, pady=5)

    # --- Logic Methods ---

    def update_dynamic_options(self, event=None):
        # Clear dynamic frame
        for widget in self.dynamic_frame.winfo_children():
            widget.pack_forget()
            widget.grid_forget()

        freq = self.combo_freq.get()
        
        if freq == "Weekly":
            self.days_frame.pack(side="left", padx=5)
        elif freq == "Specific Date":
            self.lbl_date.pack(side="left", padx=5)
            self.entry_date.pack(side="left", padx=5)
            # Set default to today if empty
            if not self.entry_date.get():
                self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        else: # Daily
            pass # Nothing extra needed

    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {message}\n"
        self.log_text.config(state="normal")
        self.log_text.insert("end", full_msg)
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        try:
            print(full_msg.strip())
        except:
            pass

    def save_config_ui(self):
        # Updates core config from UI state and saves it
        config_data = self.core.config
        config_data["host"] = self.entry_host.get()
        config_data["port"] = self.entry_port.get()
        config_data["password"] = self.entry_pwd.get()
        config_data["auto_connect"] = self.core.is_connected
        
        # Use the internal list self.current_tasks which is kept in sync
        config_data["tasks"] = self.current_tasks

        self.core.config = config_data
        self.core.save_config_file()
        
        # Refresh core schedule
        self.core.schedule_jobs_from_config()

    def refresh_preset_list(self):
        presets = self.core.get_preset_names()
        self.combo_presets['values'] = presets
        if presets:
            self.combo_presets.current(0)
        else:
            self.combo_presets.set('')

    def save_preset(self):
        name = self.entry_preset.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter a preset name.")
            return
        
        if not self.current_tasks:
            if not messagebox.askyesno("Confirm", "Current task list is empty. Save empty preset?"):
                return

        self.core.save_preset(name, self.current_tasks)
        self.refresh_preset_list()
        self.log(f"Preset '{name}' saved.")
        messagebox.showinfo("Success", f"Preset '{name}' saved successfully.")
        self.entry_preset.delete(0, "end")

    def load_preset(self):
        name = self.combo_presets.get()
        if not name:
            return
        
        if self.core.load_preset(name):
            # Clear current UI list and internal list
            self.tree.delete(*self.tree.get_children())
            self.current_tasks = []
            
            # Populate UI from loaded config
            for task in self.core.config.get("tasks", []):
                self.add_task_to_ui(task)
            
            self.log(f"Preset '{name}' loaded.")
        else:
            messagebox.showerror("Error", "Failed to load preset.")

    def delete_preset(self):
        name = self.combo_presets.get()
        if not name:
            return
        
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete preset '{name}'?"):
            if self.core.delete_preset(name):
                self.refresh_preset_list()
                self.log(f"Preset '{name}' deleted.")
            else:
                messagebox.showerror("Error", "Failed to delete preset.")

    def toggle_connection(self):
        if self.core.is_connected:
            self.disconnect_obs()
        else:
            self.connect_obs()

    def connect_obs(self):
        # Update config in core before connecting
        self.core.config["host"] = self.entry_host.get()
        self.core.config["port"] = self.entry_port.get()
        self.core.config["password"] = self.entry_pwd.get()
        
        success, msg = self.core.connect_obs()
        if success:
            self.lbl_status.config(text="Status: Connected", foreground="green")
            self.btn_connect.config(text="Disconnect")
            self.log("Connected to OBS WebSocket.")
            self.save_config_ui()
        else:
            self.lbl_status.config(text="Status: Connection Failed", foreground="red")
            self.log(f"Connection Error: {msg}")
            messagebox.showerror("Connection Failed", f"Could not connect to OBS.\n\nDetails: {msg}")

    def disconnect_obs(self):
        self.core.disconnect_obs()
        self.lbl_status.config(text="Status: Disconnected", foreground="red")
        self.btn_connect.config(text="Connect")
        self.log("Disconnected from OBS.")

    def add_task(self):
        # 1. Get Time Components
        try:
            hour = int(self.spin_hour.get())
            minute = int(self.spin_min.get())
            second = int(self.spin_sec.get())
            ampm = self.combo_ampm.get()
        except ValueError:
            messagebox.showerror("Invalid Time", "Please enter valid time numbers.")
            return

        # 2. Convert to 24-hour format for storage
        if ampm == "PM" and hour != 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0
        
        t_time = f"{hour:02d}:{minute:02d}:{second:02d}"
        t_action = self.combo_action.get()
        t_freq = self.combo_freq.get()
        
        # Build Task Object
        new_task = {
            "time": t_time,
            "action": t_action
        }

        if t_freq == "Daily":
            new_task["type"] = "daily"
        
        elif t_freq == "Weekly":
            new_task["type"] = "weekly"
            selected_days = [day for day, var in self.days_vars.items() if var.get()]
            if not selected_days:
                messagebox.showerror("Missing Info", "Please select at least one day for Weekly schedule.")
                return
            new_task["days"] = selected_days

        elif t_freq == "Specific Date":
            new_task["type"] = "onetime"
            t_date = self.entry_date.get().strip()
            try:
                datetime.strptime(t_date, "%Y-%m-%d")
                new_task["date"] = t_date
            except ValueError:
                messagebox.showerror("Invalid Date", "Date must be in YYYY-MM-DD format.")
                return

        if self.editing_index is not None:
            # Update existing task
            old_task = self.current_tasks[self.editing_index]
            new_task["enabled"] = old_task.get("enabled", True) # Preserve enabled status
            
            self.current_tasks[self.editing_index] = new_task
            self.refresh_task_list_ui()
            
            self.editing_index = None
            self.btn_add.config(text="Add Task")
            self.log(f"Task updated: {t_action} at {t_time}")
        else:
            # Add new task
            new_task["enabled"] = True
            self.add_task_to_ui(new_task)
            self.log(f"Scheduled: {t_action} at {t_time} ({t_freq})")

        self.save_config_ui()


    def add_task_to_ui(self, task):
        # Updates internal list and treeview
        self.current_tasks.append(task)
        
        t_time = task.get("time")
        t_action = task.get("action")
        t_type = task.get("type", "daily") # Default to daily
        
        # Convert 24h string to 12h AM/PM for display
        try:
            if len(t_time.split(":")) == 2:
                display_time = datetime.strptime(t_time, "%H:%M").strftime("%I:%M %p")
            else:
                display_time = datetime.strptime(t_time, "%H:%M:%S").strftime("%I:%M:%S %p")
        except ValueError:
            display_time = t_time # Fallback

        details = ""
        freq_display = "Daily"
        
        if t_type == "weekly":
            freq_display = "Weekly"
            details = ",".join(task.get("days", []))
        elif t_type == "onetime":
            freq_display = "One-time"
            details = task.get("date", "")
        elif t_type == "daily":
            details = "Every day"

        # Insert with new column order: Freq, Details, Time, Action
        # Apply tag based on enabled status
        is_enabled = task.get("enabled", True)
        tag = "enabled" if is_enabled else "disabled"
        
        self.tree.insert("", "end", values=(freq_display, details, display_time, t_action), tags=(tag,))

    def refresh_task_list_ui(self):
        # Clear tree
        self.tree.delete(*self.tree.get_children())
        # Re-populate from current_tasks
        # We temporarily clear current_tasks to avoid duplication in add_task_to_ui, 
        # or we just copy the logic of inserting to tree.
        # To avoid refactoring add_task_to_ui too much, let's just manually insert here or use a helper.
        # Actually, add_task_to_ui appends to current_tasks. We shouldn't use it here.
        
        for task in self.current_tasks:
            t_time = task.get("time")
            t_action = task.get("action")
            t_type = task.get("type", "daily")
            t_enabled = task.get("enabled", True)
            
            try:
                if len(t_time.split(":")) == 2:
                    display_time = datetime.strptime(t_time, "%H:%M").strftime("%I:%M %p")
                else:
                    display_time = datetime.strptime(t_time, "%H:%M:%S").strftime("%I:%M:%S %p")
            except ValueError:
                display_time = t_time

            details = ""
            freq_display = "Daily"
            
            if t_type == "weekly":
                freq_display = "Weekly"
                details = ",".join(task.get("days", []))
            elif t_type == "onetime":
                freq_display = "One-time"
                details = task.get("date", "")
            elif t_type == "daily":
                details = "Every day"

            tag = "enabled" if t_enabled else "disabled"
            self.tree.insert("", "end", values=(freq_display, details, display_time, t_action), tags=(tag,))

    def load_task_for_edit(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        index = self.tree.index(selected_item)
        if not (0 <= index < len(self.current_tasks)):
            return

        task = self.current_tasks[index]
        self.editing_index = index
        self.btn_add.config(text="Update Task")
        
        # Populate fields
        # 1. Action
        self.combo_action.set(task.get("action"))
        
        # 2. Time
        t_time = task.get("time")
        try:
            # Parse time
            parts = t_time.split(":")
            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            
            # Convert to 12h for UI
            ampm = "AM"
            if h >= 12:
                ampm = "PM"
                if h > 12:
                    h -= 12
            if h == 0:
                h = 12
                
            self.spin_hour.set(h)
            self.spin_min.set(f"{m:02d}")
            self.spin_sec.set(f"{s:02d}")
            self.combo_ampm.set(ampm)
        except:
            pass
            
        # 3. Frequency & Details
        t_type = task.get("type", "daily")
        if t_type == "daily":
            self.combo_freq.current(0)
        elif t_type == "weekly":
            self.combo_freq.current(1)
            # Set days
            days = task.get("days", [])
            for day, var in self.days_vars.items():
                var.set(day in days)
        elif t_type == "onetime":
            self.combo_freq.current(2)
            self.entry_date.delete(0, "end")
            self.entry_date.insert(0, task.get("date", ""))
            
        self.update_dynamic_options()
        self.log(f"Editing task #{index + 1}")

    def toggle_task_status(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        index = self.tree.index(selected_item)
        if 0 <= index < len(self.current_tasks):
            task = self.current_tasks[index]
            new_status = not task.get("enabled", True)
            task["enabled"] = new_status
            self.current_tasks[index] = task
            
            self.refresh_task_list_ui()
            self.save_config_ui()
            
            status_str = "Enabled" if new_status else "Disabled"
            self.log(f"Task #{index + 1} {status_str}")


    def remove_task(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        # Get index of selected item
        index = self.tree.index(selected_item)
        
        # Remove from internal list
        if 0 <= index < len(self.current_tasks):
            del self.current_tasks[index]

        # Remove from UI
        self.tree.delete(selected_item)
        
        self.save_config_ui()
        self.log("Task removed.")
        
        # Reset edit mode if we removed the task being edited
        if self.editing_index == index:
            self.editing_index = None
            self.btn_add.config(text="Add Task")


    def clear_all_tasks(self):
        if not self.current_tasks:
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to delete ALL tasks?"):
            self.current_tasks = []
            self.tree.delete(*self.tree.get_children())
            self.save_config_ui()
            self.log("All tasks cleared.")

    def run_scheduler(self):
        # Wrapper to run schedule.run_pending()
        while self.running:
            # Accessing global schedule via core's import of it (or import it here too)
            # It's safer to import schedule here too or rely on core
            obs_core.schedule.run_pending()
            time.sleep(1)

    def on_closing(self):
        self.running = False
        self.save_config_ui()
        self.root.destroy()


if __name__ == "__main__":
    print("Starting application...")
    try:
        root = tk.Tk()
        print("Tkinter root created.")
        app = OBSSchedulerApp(root)
        print("App initialized.")
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        print("Entering main loop...")
        root.mainloop()
        print("Main loop exited.")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
