import obsws_python as obs
import schedule
import time
import json
import os
import logging
from datetime import datetime

# Setup basic logging
logging.basicConfig(
    filename='obs_scheduler.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class OBSSchedulerCore:
        def __init__(self, config_file="obs_scheduler_config.json"):
            self.config_file = config_file
            self.presets_file = "presets.json"
            self.obs_client = None
            self.is_connected = False
            self.last_mtime = 0
            self.config = self.load_config()
    
        def log(self, message):
            print(message)
            logging.info(message)
    
        def load_config(self):
            if os.path.exists(self.config_file):
                try:
                    # Update mtime
                    self.last_mtime = os.path.getmtime(self.config_file)
                    with open(self.config_file, "r") as f:
                        return json.load(f)
                except Exception as e:
                    self.log(f"Error loading config: {e}")
                    return {}
            return {}
        
        def load_presets_file(self):
            if os.path.exists(self.presets_file):
                try:
                    with open(self.presets_file, "r") as f:
                        return json.load(f)
                except Exception as e:
                    self.log(f"Error loading presets: {e}")
                    return {}
            return {}
    
        def save_presets_file(self, data):
            try:
                with open(self.presets_file, "w") as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                self.log(f"Error saving presets: {e}")
    
        # ... (Connection and Execution methods remain unchanged) ...
    
        def connect_obs(self):
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 4455)
            password = self.config.get("password", "")
    
            try:
                # Ensure port is int
                port = int(port)
                self.obs_client = obs.ReqClient(host=host, port=port, password=password, timeout=3)
                self.is_connected = True
                self.log("Connected to OBS WebSocket.")
                return True, "Connected successfully."
            except ConnectionRefusedError:
                msg = "Connection Refused. Is OBS running and WebSocket enabled?"
                self.is_connected = False
                self.log(msg)
                return False, msg
            except Exception as e:
                self.is_connected = False
                self.log(f"Connection Error: {e}")
                return False, str(e)
    
        def disconnect_obs(self):
            self.obs_client = None
            self.is_connected = False
            self.log("Disconnected from OBS.")
    
        def execute_action(self, action):
            self.log(f"Executing task: {action}...")
            
            # Attempt reconnect if needed
            if not self.is_connected or not self.obs_client:
                self.log("Not connected. Attempting to reconnect...")
                if not self.connect_obs()[0]: # Check tuple first element
                    self.log("Reconnect failed. Skipping task.")
                    return
    
            try:
                if action == "Start Streaming":
                    self.obs_client.start_stream()
                elif action == "Stop Streaming":
                    self.obs_client.stop_stream()
                elif action == "Start Recording":
                    self.obs_client.start_record()
                elif action == "Stop Recording":
                    self.obs_client.stop_record()
                self.log(f"Successfully executed: {action}")
            except Exception as e:
                self.log(f"Failed to execute {action}: {e}")
                # If execution fails, it might be a connection drop
                self.is_connected = False
    
        def run_if_date_matches(self, target_date, action):
            today_str = datetime.now().strftime("%Y-%m-%d")
            if today_str == target_date:
                self.log(f"Date matched ({target_date}). Executing one-time task.")
                self.execute_action(action)
                return schedule.CancelJob
            elif today_str > target_date:
                self.log(f"Task date {target_date} has passed. Removing job.")
                return schedule.CancelJob
            # If future, do nothing and wait for next check
    
        def schedule_jobs_from_config(self):
            schedule.clear()
            self.config = self.load_config() # Reload config to get latest
            tasks = self.config.get("tasks", [])
            
            if not tasks:
                self.log("No tasks found in config.")
            
            for task in tasks:
                t_time = task.get("time")
                t_action = task.get("action")
                # Default to 'daily' for backward compatibility
                t_type = task.get("type", "daily") 
                
                if not t_time or not t_action:
                    continue
    
                try:
                    if t_type == "daily":
                        self.log(f"Scheduling Daily: {t_action} at {t_time}")
                        schedule.every().day.at(t_time).do(self.execute_action, action=t_action)
                    
                    elif t_type == "weekly":
                        days = task.get("days", [])
                        self.log(f"Scheduling Weekly ({','.join(days)}): {t_action} at {t_time}")
                        
                        day_map = {
                            "mon": "monday", "tue": "tuesday", "wed": "wednesday",
                            "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"
                        }
                        
                        for day_name in days:
                            full_name = day_map.get(day_name.lower())
                            if full_name:
                                job_creator = getattr(schedule.every(), full_name, None)
                                if job_creator:
                                    job_creator.at(t_time).do(self.execute_action, action=t_action)
                            else:
                                self.log(f"Warning: Invalid day name '{day_name}' skipped.")
                    
                    elif t_type == "onetime":
                        t_date = task.get("date")
                        if t_date:
                            self.log(f"Scheduling One-time ({t_date}): {t_action} at {t_time}")
                            # Check every day at this time if the date matches
                            schedule.every().day.at(t_time).do(
                                self.run_if_date_matches, target_date=t_date, action=t_action
                            )
                except Exception as e:
                    self.log(f"Failed to schedule task {task}: {e}")
            
            job_count = len(schedule.get_jobs())
            self.log(f"Total scheduled jobs: {job_count}")
            for job in schedule.get_jobs():
                self.log(f" - Job: {job}")
    
        def run_forever(self):
            self.log("Starting Scheduler Service...")
            if self.config.get("auto_connect", False):
                self.connect_obs()
                
            self.schedule_jobs_from_config()
            
            while True:
                # Check for config file changes
                try:
                    if os.path.exists(self.config_file):
                        current_mtime = os.path.getmtime(self.config_file)
                        if current_mtime > self.last_mtime:
                            self.log("Config file changed. Reloading schedule...")
                            # Debounce slightly to ensure write is complete
                            time.sleep(0.5)
                            self.schedule_jobs_from_config()
                except Exception as e:
                    self.log(f"Error checking config file: {e}")
    
                schedule.run_pending()
                time.sleep(1)
    
        # --- Preset Management ---
    
        def save_config_file(self):
            try:
                with open(self.config_file, "w") as f:
                    json.dump(self.config, f, indent=4)
                self.last_mtime = os.path.getmtime(self.config_file) # Update mtime to avoid reload loop
            except Exception as e:
                self.log(f"Error saving config: {e}")
    
        def get_preset_names(self):
            presets = self.load_presets_file()
            return list(presets.keys())
    
        def save_preset(self, name, tasks):
            presets = self.load_presets_file()
            presets[name] = tasks
            self.save_presets_file(presets)
            self.log(f"Preset '{name}' saved to {self.presets_file}.")
    
        def load_preset(self, name):
            presets = self.load_presets_file()
            if name in presets:
                self.config["tasks"] = presets[name]
                self.save_config_file()
                self.schedule_jobs_from_config()
                self.log(f"Preset '{name}' loaded.")
                return True
            return False
    
        def delete_preset(self, name):
            presets = self.load_presets_file()
            if name in presets:
                del presets[name]
                self.save_presets_file(presets)
                self.log(f"Preset '{name}' deleted.")
                return True
            return False
    
