import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import cv2
import csv
import torch
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import time
from collections import defaultdict
import sqlite3
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def setup_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Modify detections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    object_type TEXT,
                    confidence REAL,
                    x_min INTEGER,
                    y_min INTEGER,
                    x_max INTEGER,
                    y_max INTEGER,
                    frame_number INTEGER
                )
            ''')
            
            # Modify anomalies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    anomaly_type TEXT,
                    description TEXT,
                    x_min INTEGER,
                    y_min INTEGER,
                    x_max INTEGER,
                    y_max INTEGER,
                    frame_number INTEGER,
                    severity INTEGER
                )
            ''')
            
            # Add missing columns to detections table if they don't exist
            cursor.execute('PRAGMA table_info(detections)')
            columns = {column[1] for column in cursor.fetchall()}
            missing_columns = {'frame_number'} - columns
            for column in missing_columns:
                cursor.execute(f'ALTER TABLE detections ADD COLUMN {column} INTEGER')

            # Add missing columns to anomalies table if they don't exist
            cursor.execute('PRAGMA table_info(anomalies)')
            columns = {column[1] for column in cursor.fetchall()}
            missing_columns = {'frame_number', 'severity'} - columns
            for column in missing_columns:
                cursor.execute(f'ALTER TABLE anomalies ADD COLUMN {column} INTEGER')

            conn.commit()

    def log_detection(self, detection, frame_number):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO detections (timestamp, object_type, confidence, x_min, y_min, x_max, y_max, frame_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                detection['name'],
                detection['confidence'],
                detection['xmin'],
                detection['ymin'],
                detection['xmax'],
                detection['ymax'],
                frame_number
            ))
            conn.commit()

    def log_anomaly(self, anomaly_type, description, detection, frame_number, severity):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO anomalies (timestamp, anomaly_type, description, x_min, y_min, x_max, y_max, frame_number, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                anomaly_type,
                description,
                detection['xmin'],
                detection['ymin'],
                detection['xmax'],
                detection['ymax'],
                frame_number,
                severity
            ))
            conn.commit()

    def get_recent_detections(self, limit=5):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, object_type, confidence
                FROM detections
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

    def get_recent_anomalies(self, limit=5):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, anomaly_type, description
                FROM anomalies
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

    def get_detection_stats(self, time_range=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if time_range:
                start_time = (datetime.now() - time_range).isoformat()
                query = '''
                    SELECT object_type, COUNT(*) as count
                    FROM detections
                    WHERE timestamp > ?
                    GROUP BY object_type
                '''
                cursor.execute(query, (start_time,))
            else:
                query = '''
                    SELECT object_type, COUNT(*) as count
                    FROM detections
                    GROUP BY object_type
                '''
                cursor.execute(query)
            
            return cursor.fetchall()


            cursor = conn.cursor()
            
            if time_range:
                start_time = (datetime.now() - time_range).isoformat()
                query = '''
                    SELECT anomaly_type, COUNT(*) as count
                    FROM anomalies
                    WHERE timestamp > ?
                    GROUP BY anomaly_type
                '''
                cursor.execute(query, (start_time,))
            else:
                query = '''
                    SELECT anomaly_type, COUNT(*) as count
                    FROM anomalies
                    GROUP BY anomaly_type
                '''
                cursor.execute(query)
            
            return cursor.fetchall()

    def get_anomaly_stats(self, time_range=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if time_range:
                start_time = (datetime.now() - time_range).isoformat()
                query = '''
                    SELECT anomaly_type, COUNT(*) as count
                    FROM anomalies
                    WHERE timestamp > ?
                    GROUP BY anomaly_type
                '''
                cursor.execute(query, (start_time,))
            else:
                query = '''
                    SELECT anomaly_type, COUNT(*) as count
                    FROM anomalies
                    GROUP BY anomaly_type
                '''
                cursor.execute(query)
            
            return cursor.fetchall()

    def cleanup_old_records(self, days_to_keep):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            cursor.execute('DELETE FROM detections WHERE timestamp < ?', (cutoff_date,))
            cursor.execute('DELETE FROM anomalies WHERE timestamp < ?', (cutoff_date,))
            
            conn.commit()

    def export_to_csv(self, table_name, output_file):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            
            with open(output_file, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow([description[0] for description in cursor.description])  # Write headers
                csv_writer.writerows(cursor)

class SmartSecurityCameraSystem(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Set appearance mode and theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Set window title and size
        self.title("Smart Security Camera System")
        self.geometry("1280x720")  # Default window size

        self.options_window = None  # Add this line to track the options window
        
        # Initialize variables for video processing
        self.cap = None
        self.is_webcam = False
        self.video_path = None
        self.is_playing = False

        # Initialize variables for restricted area selection
        self.restricted_area = None
        self.start_x = None
        self.start_y = None
        self.rectangle_id = None

        # Initialize variables for object detection
        self.model = None
        self.load_yolo_model()
        self.detection_classes = ["person", "car", "animal"]  # Default classes to detect
        self.confidence_threshold = 0.5  # Default confidence threshold
        self.other_filter = tk.BooleanVar(value=True)

        # Initialize recording variables
        self.automatic_recording_enabled = tk.BooleanVar(value=False)
        self.is_recording = False
        self.out = None
        self.recording_start_time = None
        self.recordings_folder = "recordings"
        self.recording_duration = 30  # Duration in seconds for each automatic recording
        
    
        # Create recordings folder if it doesn't exist
        if not os.path.exists(self.recordings_folder):
            os.makedirs(self.recordings_folder)

        # Initialize object detection variables
        self.object_tracker = defaultdict(lambda: {
            "first_detected": None, 
            "last_detected": None,
            "in_restricted_area": False,
            "positions": [],
            "loitering_start": None
        })

        # Initialize anomaly detection variables
        self.anomaly_threshold_time = 5  # Time in seconds before an object in the restricted area is considered an anomaly
        self.rapid_movement_threshold = 50  # Pixel distance to consider as rapid movement
        self.sudden_appearance_threshold = 3  # Frames to consider an object as suddenly appeared
        self.interaction_distance_threshold = 50  # Pixel distance to consider objects as interacting
        self.loitering_threshold = 30  # Time in seconds to consider as loitering
        self.previous_detections = None
        self.frame_count = 0
        
        # Add this line to periodically refresh the detection tab
        self.after(5000, self.periodic_refresh)

        # Initialize UI variables
        self.anomaly_detection_enabled = tk.BooleanVar(value=False)

        # Performance mode variables
        self.performance_mode = False
        self.frame_skip = 0

        # Database setup
        self.db_path = 'security_camera.db'
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.setup_database()

        # Email and notification settings
        self.email_settings = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'sender_email': '',
            'sender_password': '',
            'recipient_email': ''
        }
        
        self.notification_settings = {
            'notify_on_anomaly': True,
            'notify_on_detection_threshold': 10
        }

        # Configure the grid layout
        self.grid_rowconfigure(0, weight=1)  # Main content row
        self.grid_rowconfigure(1, weight=0)  # Bottom bar row
        self.grid_columnconfigure(0, weight=3)  # Main video area
        self.grid_columnconfigure(1, weight=1)  # Side panel


        self.create_ui_elements()


        # Start with a blank black image in the video canvas
        self.display_blank_image()

        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Update the preset_selector configuration
        self.preset_selector = ctk.CTkComboBox(self.right_frame, values=self.get_preset_list(), command=self.load_preset)
        self.preset_selector.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="ew")

    def load_yolo_model(self):
        try:
            self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load YOLOv5 model: {str(e)}")

    def create_ui_elements(self):
        # Create the video display area with a canvas
        self.video_frame = ctk.CTkFrame(self, width=800, height=600)
        self.video_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.video_canvas = tk.Canvas(self.video_frame, bg="black", width=800, height=600)
        self.video_canvas.pack(fill="both", expand=True)

        # Add this near the beginning of the __init__ method
        self.presets_folder = "presets"
        if not os.path.exists(self.presets_folder):
            os.makedirs(self.presets_folder)
        

        # Bind mouse events for restricted area selection
        self.video_canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.video_canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.video_canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        # Create a resizable side panel for logs/detections and right section controls
        self.side_panel = ctk.CTkFrame(self)
        self.side_panel.grid(row=0, rowspan=2, column=1, padx=10, pady=10, sticky="nsew")

        # Configure side panel layout
        self.side_panel.grid_rowconfigure(0, weight=3)  # Notebook area
        self.side_panel.grid_rowconfigure(1, weight=1)  # Right section controls

        self.notebook = ctk.CTkTabview(self.side_panel)
        self.notebook.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Add tabs for logs and recorded videos
        self.detection_tab = self.notebook.add("Detections")
        self.anomaly_tab = self.notebook.add("Anomalies")
        self.recorded_videos_tab = self.notebook.add("Recorded Videos")

        # Detections tab
        self.create_detections_tab()

        # Anomalies tab
        self.anomaly_log = ctk.CTkTextbox(self.anomaly_tab, wrap="word")
        self.anomaly_log.pack(fill="both", expand=True)

        # Recorded Videos tab
        self.recorded_videos_listbox = tk.Listbox(self.recorded_videos_tab, height=10, bg="#2E2E2E", fg="#FFFFFF", selectbackground="#1F1F1F", selectforeground="#FFFFFF")
        self.recorded_videos_listbox.pack(fill="both", expand=True)
        self.update_recorded_videos_list()

        # Add open button for recorded videos
        self.open_button = ctk.CTkButton(self.recorded_videos_tab, text="Open Selected", command=self.open_video)
        self.open_button.pack(pady=10)

        # Create the right section (formerly in button frame) in the side panel
        self.create_right_section()

        # Create button frame at the bottom (scalable)
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Configure columns to make buttons and elements scale
        self.button_frame.grid_columnconfigure(0, weight=1)  # Left section
        self.button_frame.grid_columnconfigure(1, weight=3)  # Middle section (wider)

        self.create_control_buttons()


    def create_right_section(self):
        # Right section: Preset controls, Options, and Performance Mode
        self.right_frame = ctk.CTkFrame(self.side_panel)
        self.right_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Configure right frame rows and columns
        for i in range(4):  # Increased to 4 rows for better spacing
            self.right_frame.grid_rowconfigure(i, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        preset_label = ctk.CTkLabel(self.right_frame, text="Select Preset:", anchor="w")
        preset_label.grid(row=0, column=0, padx=5, pady=(10, 0), sticky="ew")
        
        #self.preset_selector = ctk.CTkComboBox(self.right_frame, values=self.get_preset_list(), command=self.load_preset)
        #self.preset_selector.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="ew")

        self.save_preset_button = ctk.CTkButton(self.right_frame, text="Save Preset", command=self.save_preset)
        self.save_preset_button.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        button_frame = ctk.CTkFrame(self.right_frame)
        button_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.options_button = ctk.CTkButton(button_frame, text="Options", command=self.open_options)
        self.options_button.grid(row=0, column=0, padx=(0, 2), pady=0, sticky="ew")

        self.performance_mode_button = ctk.CTkButton(
            button_frame,
            text="Enable Performance Mode",
            command=self.toggle_performance_mode,
            fg_color=("gray70", "gray30"),
            state="normal"
        )
        self.performance_mode_button.grid(row=0, column=1, padx=(2, 0), pady=0, sticky="ew")
    
    def create_detections_tab(self):
        # Create a main frame for the detection tab
        main_frame = ctk.CTkFrame(self.detection_tab)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Recent Detections
        ctk.CTkLabel(main_frame, text="Recent Detections", font=("Helvetica", 12, "bold")).pack(pady=(5, 0))
        self.recent_detections_listbox = tk.Listbox(main_frame, height=5, bg="#2a2a2a", fg="white",
                                                    selectbackground="#1F538D", selectforeground="white",
                                                    font=("Helvetica", 9))
        self.recent_detections_listbox.pack(fill="x", padx=5, pady=(0, 5))

        # Recent Anomalies
        ctk.CTkLabel(main_frame, text="Recent Anomalies", font=("Helvetica", 12, "bold")).pack(pady=(5, 0))
        self.recent_anomalies_listbox = tk.Listbox(main_frame, height=5, bg="#2a2a2a", fg="white",
                                                selectbackground="#1F538D", selectforeground="white",
                                                font=("Helvetica", 9))
        self.recent_anomalies_listbox.pack(fill="x", padx=5, pady=(0, 5))

        # Detection Statistics
        ctk.CTkLabel(main_frame, text="Detection Statistics", font=("Helvetica", 12, "bold")).pack(pady=(5, 0))
        self.detection_stats_listbox = tk.Listbox(main_frame, height=3, bg="#2a2a2a", fg="white",
                                                selectbackground="#1F538D", selectforeground="white",
                                                font=("Helvetica", 9))
        self.detection_stats_listbox.pack(fill="x", padx=5, pady=(0, 5))

        # Anomaly Statistics
        ctk.CTkLabel(main_frame, text="Anomaly Statistics", font=("Helvetica", 12, "bold")).pack(pady=(5, 0))
        self.anomaly_stats_listbox = tk.Listbox(main_frame, height=4, bg="#2a2a2a", fg="white",
                                                selectbackground="#1F538D", selectforeground="white",
                                                font=("Helvetica", 9))
        self.anomaly_stats_listbox.pack(fill="x", padx=5, pady=(0, 5))

        # Refresh button
        self.refresh_button = ctk.CTkButton(main_frame, text="Refresh", command=self.refresh_detection_tab)
        self.refresh_button.pack(pady=10)

    def create_control_buttons(self):
        # Left section: Control buttons
        self.left_frame = ctk.CTkFrame(self.button_frame)
        self.left_frame.grid(row=0, column=0, padx=2, pady=2, sticky="nsew")

        # Configure left frame rows and columns
        for i in range(3):
            self.left_frame.grid_rowconfigure(i, weight=1)
        for i in range(2):
            self.left_frame.grid_columnconfigure(i, weight=1)

        button_params = {"width": 80, "height": 25, "font": ("Helvetica", 10)}

        self.pause_button = ctk.CTkButton(self.left_frame, text="Pause", command=self.pause_video, **button_params)
        self.pause_button.grid(row=0, column=0, padx=1, pady=1, sticky="nsew")

        self.restart_button = ctk.CTkButton(self.left_frame, text="Restart", command=self.restart_video, **button_params)
        self.restart_button.grid(row=0, column=1, padx=1, pady=1, sticky="nsew")

        self.select_video_button = ctk.CTkButton(self.left_frame, text="Select Video", command=self.select_video_file, **button_params)
        self.select_video_button.grid(row=1, column=0, padx=1, pady=1, sticky="nsew")

        self.switch_webcam_button = ctk.CTkButton(self.left_frame, text="Switch to Webcam", command=self.switch_to_webcam, **button_params)
        self.switch_webcam_button.grid(row=1, column=1, padx=1, pady=1, sticky="nsew")

        self.select_tracker_button = ctk.CTkButton(self.left_frame, text="Select Tracker", command=self.select_tracker, **button_params)
        self.select_tracker_button.grid(row=2, column=0, columnspan=2, padx=1, pady=1, sticky="nsew")

        # Middle section: Confidence threshold, loitering threshold, filters, and toggles
        self.middle_frame = ctk.CTkFrame(self.button_frame)
        self.middle_frame.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        # Configure middle frame columns
        for i in range(2):
            self.middle_frame.grid_columnconfigure(i, weight=1)

        # Row 1: Confidence Threshold and Loitering Threshold
        self.create_slider(self.middle_frame, "Confidence:", 0, 1, 100, self.confidence_threshold, self.update_confidence_threshold, 0, 0, 
                        "Adjust the confidence threshold for object detection. Higher values increase precision but may miss some objects.")

        self.create_slider(self.middle_frame, "Loitering (s):", 10, 120, 110, self.loitering_threshold, self.update_loitering_threshold, 0, 1,
                        "Set the time threshold (in seconds) for detecting loitering behavior.")

        # Row 2: Anomaly Threshold Time and Rapid Movement Threshold
        self.create_slider(self.middle_frame, "Anomaly Time (s):", 1, 20, 19, self.anomaly_threshold_time, self.update_anomaly_threshold_time, 1, 0,
                        "Set the time threshold (in seconds) for classifying an event as an anomaly.")

        self.create_slider(self.middle_frame, "Rapid Movement:", 10, 100, 90, self.rapid_movement_threshold, self.update_rapid_movement_threshold, 1, 1,
                        "Set the threshold for detecting rapid movements. Higher values require faster movement to trigger.")

        # Row 3: Sudden Appearance Threshold and Interaction Distance Threshold
        self.create_slider(self.middle_frame, "Sudden Appear:", 1, 10, 9, self.sudden_appearance_threshold, self.update_sudden_appearance_threshold, 2, 0,
                        "Set the threshold for detecting sudden appearances. Lower values are more sensitive.")

        self.create_slider(self.middle_frame, "Interaction Dist:", 10, 100, 90, self.interaction_distance_threshold, self.update_interaction_distance_threshold, 2, 1,
                        "Set the distance threshold for detecting interactions between objects.")

        # Row 4: Detection Filters
        self.detection_filters_label = ctk.CTkLabel(self.middle_frame, text=" ", font=("Helvetica", 10))
        self.detection_filters_label.grid(row=3, column=0, columnspan=2, padx=2, pady=(5,2), sticky="w")

        filter_frame = ctk.CTkFrame(self.middle_frame)
        filter_frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        for i in range(4):
            filter_frame.grid_columnconfigure(i, weight=1)

        checkbox_params = {"width": 20, "height": 20, "font": ("Helvetica", 10)}

        self.filter_person = ctk.CTkCheckBox(filter_frame, text="Person", command=self.update_filters, **checkbox_params)
        self.filter_person.grid(row=0, column=0, padx=2, pady=2)
        self.filter_person.select()

        self.filter_vehicle = ctk.CTkCheckBox(filter_frame, text="Vehicle", command=self.update_filters, **checkbox_params)
        self.filter_vehicle.grid(row=0, column=1, padx=2, pady=2)
        self.filter_vehicle.select()

        self.filter_animal = ctk.CTkCheckBox(filter_frame, text="Animal", command=self.update_filters, **checkbox_params)
        self.filter_animal.grid(row=0, column=2, padx=2, pady=2)
        self.filter_animal.select()

        self.filter_other = ctk.CTkCheckBox(filter_frame, text="Other", command=self.update_filters, variable=self.other_filter, **checkbox_params)
        self.filter_other.grid(row=0, column=3, padx=2, pady=2)

        # Row 5: Toggles
        toggle_frame = ctk.CTkFrame(self.middle_frame)
        toggle_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(5,0))
        for i in range(3):
            toggle_frame.grid_columnconfigure(i, weight=1)

        switch_params = {"width": 40, "height": 20, "font": ("Helvetica", 10)}

        self.restricted_area_toggle = ctk.CTkSwitch(toggle_frame, text="Restricted Area", command=self.toggle_restricted_area, **switch_params)
        self.restricted_area_toggle.grid(row=0, column=0, padx=2, pady=2)

        self.anomaly_detection_toggle = ctk.CTkSwitch(toggle_frame, text="Anomaly Detection", 
                                                    variable=self.anomaly_detection_enabled,
                                                    command=self.toggle_anomaly_detection, **switch_params)
        self.anomaly_detection_toggle.grid(row=0, column=1, padx=2, pady=2)

        self.recording_toggle = ctk.CTkSwitch(toggle_frame, text="Auto Recording", variable=self.automatic_recording_enabled,
                                            command=self.toggle_recording, **switch_params)
        self.recording_toggle.grid(row=0, column=2, padx=2, pady=2)

    def create_slider(self, parent, label, from_, to, steps, initial_value, command, row, column, tooltip_text):
        ctk.CTkLabel(parent, text=label, font=("Helvetica", 10)).grid(row=row*2, column=column, padx=2, pady=(2,0), sticky="w")
        slider = ctk.CTkSlider(parent, from_=from_, to=to, number_of_steps=steps, command=command, height=15, width=150)
        slider.set(initial_value)
        slider.grid(row=row*2+1, column=column, padx=2, pady=(0,2), sticky="ew")
        self.add_tooltip(slider, tooltip_text)
        return slider

    def add_tooltip(self, widget, text):
        def create_tooltip(widget):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)  # Remove window decorations
            tooltip.wm_geometry("+0+0")  # Place tooltip at top-left corner initially
            label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()
            return tooltip

        def enter(event):
            tooltip = create_tooltip(widget)
            x = y = 0
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            tooltip.wm_geometry(f"+{x}+{y}")
            tooltip.deiconify()
            widget.tooltip = tooltip

        def leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

    def update_anomaly_threshold_time(self, value):
        self.anomaly_threshold_time = int(value)
        print(f"Anomaly threshold time updated to: {self.anomaly_threshold_time}")

    def update_rapid_movement_threshold(self, value):
        self.rapid_movement_threshold = int(value)
        print(f"Rapid movement threshold updated to: {self.rapid_movement_threshold}")

    def update_sudden_appearance_threshold(self, value):
        self.sudden_appearance_threshold = int(value)
        print(f"Sudden appearance threshold updated to: {self.sudden_appearance_threshold}")

    def update_interaction_distance_threshold(self, value):
        self.interaction_distance_threshold = int(value)
        print(f"Interaction distance threshold updated to: {self.interaction_distance_threshold}")

    def update_filters(self):
        self.detection_classes = []
        if self.filter_person.get():
            self.detection_classes.append("person")
        if self.filter_vehicle.get():
            self.detection_classes.append("car")
        if self.filter_animal.get():
            self.detection_classes.append("animal")
        if self.other_filter.get():
            self.detection_classes.append("other")
        print(f"Detection classes updated to: {self.detection_classes}")
        
    def display_blank_image(self):
        blank_image = Image.new('RGB', (800, 600), color='black')
        self.photo = ImageTk.PhotoImage(blank_image)
        self.video_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

    def start_video_capture(self):
        if self.is_webcam:
            self.cap = cv2.VideoCapture(0)
        elif self.video_path:
            self.cap = cv2.VideoCapture(self.video_path)
        else:
            messagebox.showerror("Error", "No video source selected.")
            return

        if not self.cap.isOpened():
            messagebox.showerror("Error", "Unable to open video source.")
            return

        self.is_playing = True
        self.update_frame()

    def update_frame(self):
        if self.is_playing and self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                self.frame_count += 1
                
                # Skip frames in performance mode
                if self.performance_mode and (self.frame_count % (self.frame_skip + 1) != 0):
                    self.after(10, self.update_frame)
                    return

                 # Write frame if recording
                if self.is_recording and self.out is not None:
                    self.out.write(frame)

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (800, 600))

                # Perform object detection
                results = self.detect_objects(frame)

                # Check for anomalies
                if self.anomaly_detection_enabled.get():
                    self.detect_anomalies(frame, results)

                # Draw bounding boxes and labels
                frame_with_boxes = self.draw_boxes(frame, results)

                self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame_with_boxes))
                self.video_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                self.after(10, self.update_frame)
            else:
                self.stop_video()

    def detect_objects(self, frame):
        if self.model is None:
            return []

        results = self.model(frame)
        detections = results.pandas().xyxy[0]
        filtered_detections = detections[
            (detections['confidence'] >= self.confidence_threshold) &
            (detections['name'].isin(self.detection_classes))
        ]
        
        # Log each detection to the database
        for _, detection in filtered_detections.iterrows():
            self.db_manager.log_detection(detection, self.frame_count)
        
        # Check and send notifications
        self.check_and_send_notifications(filtered_detections, [])  # Pass an empty list for anomalies for now
        
        return filtered_detections

    def detect_anomalies(self, frame, detections):
        anomaly_detected = False
        current_time = time.time()
        current_objects = set()
        anomalies = []
        
        for _, detection in detections.iterrows():
            object_id = f"{detection['name']}_{detection['xmin']}_{detection['ymin']}"
            current_objects.add(object_id)
            
            # Update object tracker
            if self.object_tracker[object_id]["first_detected"] is None:
                self.object_tracker[object_id]["first_detected"] = self.frame_count
            self.object_tracker[object_id]["last_detected"] = self.frame_count
            
            self.object_tracker[object_id]["positions"].append((detection['xmin'], detection['ymin'], detection['xmax'], detection['ymax']))
            
            # Check for sudden appearance
            if self.frame_count - self.object_tracker[object_id]["first_detected"] <= self.sudden_appearance_threshold:
                anomaly = self.log_anomaly(detection, "Sudden appearance")
                self.draw_anomaly(frame, detection, "SUDDEN APPEARANCE")
                self.db_manager.log_anomaly("Sudden appearance", "Object suddenly appeared", detection, self.frame_count, 1)
                anomaly_detected = True
                anomalies.append(anomaly)
            
            # Other existing anomaly checks
            if self.check_restricted_area_anomaly(frame, detection, object_id, current_time) or \
            self.check_rapid_movement_anomaly(frame, detection) or \
            self.check_unusual_size_anomaly(frame, detection) or \
            self.check_loitering_anomaly(frame, detection, object_id, current_time):
                anomaly_detected = True

        # Check for sudden disappearances
        for obj_id in list(self.object_tracker.keys()):
            if obj_id not in current_objects and self.frame_count - self.object_tracker[obj_id]["last_detected"] <= self.sudden_appearance_threshold:
                anomaly = self.log_anomaly({"name": obj_id.split("_")[0]}, "Sudden disappearance")
                anomalies.append(anomaly)
                anomaly_detected = True

        # Check for object interactions
        self.check_object_interactions(frame, detections)

        # Update previous detections for next frame
        self.previous_detections = detections

        # Clean up old objects from tracker
        self.clean_object_tracker()

        # Start recording if an anomaly is detected and automatic recording is enabled
        if anomaly_detected and self.automatic_recording_enabled.get() and not self.is_recording:
            self.start_recording()

        # Stop recording if no anomaly is detected for the past recording_duration seconds
        if self.is_recording and time.time() - self.recording_start_time > self.recording_duration:
            self.stop_recording()

        # Check and send notifications for anomalies
        self.check_and_send_notifications(detections, anomalies)

    def check_restricted_area_anomaly(self, frame, detection, object_id, current_time):
        if self.is_in_restricted_area(detection):
            if not self.object_tracker[object_id]["in_restricted_area"]:
                self.object_tracker[object_id]["first_detected"] = current_time
            self.object_tracker[object_id]["in_restricted_area"] = True
            time_in_area = current_time - self.object_tracker[object_id]["first_detected"]
            if time_in_area > self.anomaly_threshold_time:
                anomaly = self.log_anomaly(detection, "Long presence in restricted area")
                self.draw_anomaly(frame, detection, "TEMPORAL ANOMALY")
                self.db_manager.log_anomaly("Restricted Area", f"Object in restricted area for {time_in_area:.2f} seconds", detection, self.frame_count, 2)
                return True
        else:
            self.object_tracker[object_id]["in_restricted_area"] = False
            self.object_tracker[object_id]["first_detected"] = None
        return False

    def check_rapid_movement_anomaly(self, frame, detection):
        if self.previous_detections is not None:
            prev_detection = self.previous_detections[self.previous_detections['name'] == detection['name']]
            if not prev_detection.empty:
                prev_detection = prev_detection.iloc[0]
                movement = self.calculate_movement(prev_detection, detection)
                if movement > self.rapid_movement_threshold:
                    anomaly = self.log_anomaly(detection, "Rapid movement detected")
                    self.draw_anomaly(frame, detection, "RAPID MOVEMENT")
                    self.db_manager.log_anomaly("Rapid Movement", f"Object moved {movement:.2f} pixels", detection, self.frame_count, 2)
                    return True
        return False

    def check_unusual_size_anomaly(self, frame, detection):
        object_area = (detection['xmax'] - detection['xmin']) * (detection['ymax'] - detection['ymin'])
        frame_area = frame.shape[0] * frame.shape[1]
        if object_area > frame_area / 4:
            anomaly = self.log_anomaly(detection, "Unusually large object detected")
            self.draw_anomaly(frame, detection, "LARGE OBJECT")
            self.db_manager.log_anomaly("Unusual Size", "Unusually large object detected", detection, self.frame_count, 1)
            return True
        return False

    def check_loitering_anomaly(self, frame, detection, object_id, current_time):
        if detection['name'] == 'person':
            if self.object_tracker[object_id]["loitering_start"] is None:
                self.object_tracker[object_id]["loitering_start"] = current_time
            else:
                loitering_duration = current_time - self.object_tracker[object_id]["loitering_start"]
                if loitering_duration > self.loitering_threshold:
                    anomaly = self.log_anomaly(detection, f"Loitering detected for {loitering_duration:.2f} seconds")
                    self.draw_anomaly(frame, detection, "LOITERING")
                    self.db_manager.log_anomaly("Loitering", f"Person loitering for {loitering_duration:.2f} seconds", detection, self.frame_count, 2)
                    return True
        else:
            self.object_tracker[object_id]["loitering_start"] = None
        return False

    def check_object_interactions(self, frame, detections):
        for i, detection1 in detections.iterrows():
            for j, detection2 in detections.iterrows():
                if i < j:  # Avoid checking the same pair twice
                    distance = self.calculate_distance(detection1, detection2)
                    if distance < self.interaction_distance_threshold:
                        interaction_type = self.classify_interaction(detection1, detection2)
                        if interaction_type == "Person-Object" and detection2['name'] in ['bag', 'suitcase', 'backpack']:
                            anomaly = self.log_anomaly(detection1, f"Suspicious interaction: Person with {detection2['name']}")
                            self.draw_interaction(frame, detection1, detection2, "SUSPICIOUS")
                            self.db_manager.log_anomaly("Suspicious Interaction", f"Person interacting with {detection2['name']}", detection1, self.frame_count, 3)
                        else:
                            anomaly = self.log_anomaly(detection1, f"Interaction detected: {interaction_type} with {detection2['name']}")
                            self.draw_interaction(frame, detection1, detection2, interaction_type)
                            self.db_manager.log_anomaly("Object Interaction", f"{interaction_type} interaction detected", detection1, self.frame_count, 1)

    def classify_interaction(self, detection1, detection2):
        if detection1['name'] == 'person' and detection2['name'] == 'person':
            return "Person-Person"
        elif 'person' in [detection1['name'], detection2['name']]:
            return "Person-Object"
        else:
            return "Object-Object"

    def draw_interaction(self, frame, detection1, detection2, interaction_type):
        x1, y1 = int((detection1['xmin'] + detection1['xmax']) / 2), int((detection1['ymin'] + detection1['ymax']) / 2)
        x2, y2 = int((detection2['xmin'] + detection2['xmax']) / 2), int((detection2['ymin'] + detection2['ymax']) / 2)
        cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(frame, interaction_type, (min(x1, x2), min(y1, y2) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

    def calculate_distance(self, detection1, detection2):
        x1, y1 = (detection1['xmin'] + detection1['xmax']) / 2, (detection1['ymin'] + detection1['ymax']) / 2
        x2, y2 = (detection2['xmin'] + detection2['xmax']) / 2, (detection2['ymin'] + detection2['ymax']) / 2
        return ((x1 - x2)**2 + (y1 - y2)**2)**0.5

    def clean_object_tracker(self):
        current_frame = self.frame_count
        for obj_id in list(self.object_tracker.keys()):
            if current_frame - self.object_tracker[obj_id]["last_detected"] > 2 * self.sudden_appearance_threshold:
                del self.object_tracker[obj_id]

    def calculate_movement(self, prev_detection, current_detection):
        prev_center = ((prev_detection['xmin'] + prev_detection['xmax']) / 2, 
                       (prev_detection['ymin'] + prev_detection['ymax']) / 2)
        current_center = ((current_detection['xmin'] + current_detection['xmax']) / 2, 
                          (current_detection['ymin'] + current_detection['ymax']) / 2)
        return ((prev_center[0] - current_center[0])**2 + (prev_center[1] - current_center[1])**2)**0.5

    def log_anomaly(self, detection, anomaly_type):
        anomaly_msg = f"Anomaly detected: {detection['name']} - {anomaly_type} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.anomaly_log.insert(tk.END, anomaly_msg + "\n")
        self.anomaly_log.see(tk.END)
        print(anomaly_msg)  # For console logging
        return anomaly_msg

    def draw_anomaly(self, frame, detection, anomaly_type):
        xmin, ymin, xmax, ymax = map(int, [detection['xmin'], detection['ymin'], detection['xmax'], detection['ymax']])
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 2)  # Red box for anomalies
        cv2.putText(frame, anomaly_type, (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    def draw_boxes(self, frame, detections):
        img = Image.fromarray(frame)
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Load a larger font
        try:
            font = ImageFont.truetype("arial.ttf", 20)  # Adjust size as needed
        except IOError:
            font = ImageFont.load_default()
        
        for _, detection in detections.iterrows():
            label = f"{detection['name']} {detection['confidence']:.2f}"
            box = [detection['xmin'], detection['ymin'], detection['xmax'], detection['ymax']]
            
            # Define colors
            highlight_color = (255, 0, 0, 64) if self.is_in_restricted_area(detection) else (200, 200, 200, 64)  # Light grey for normal detections
            text_color = (255, 255, 255, 255)  # White color for text
            
            # Draw semi-transparent rectangle
            draw.rectangle(box, fill=highlight_color)
            
            # Calculate text position and size
            left, top, right, bottom = draw.textbbox((box[0], box[1]), label, font=font)
            text_width = right - left
            text_height = bottom - top
            text_position = (box[0], box[1] - text_height - 5)
            
            # Draw text background
            draw.rectangle([text_position[0], text_position[1], 
                            text_position[0] + text_width, text_position[1] + text_height], 
                        fill=(0, 0, 0, 128))  # Semi-transparent black background
            
            # Draw text
            draw.text(text_position, label, font=font, fill=text_color)
        
        return np.array(img)

    def is_in_restricted_area(self, detection):
        if not self.restricted_area:
            return False
        x1, y1, x2, y2 = self.restricted_area
        xmin, ymin, xmax, ymax = detection['xmin'], detection['ymin'], detection['xmax'], detection['ymax']
        return (xmin > x1 and ymin > y1 and xmax < x2 and ymax < y2)

    def stop_video(self):
        self.is_playing = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.display_blank_image()

    def pause_video(self):
        if self.is_playing:
            self.is_playing = False
            self.pause_button.configure(text="Resume")
        else:
            self.is_playing = True
            self.pause_button.configure(text="Pause")
            self.update_frame()

    def restart_video(self):
        self.stop_video()
        self.start_video_capture()

    def select_video_file(self):
        self.video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
        if self.video_path:
            self.is_webcam = False
            self.stop_video()
            self.start_video_capture()

    def switch_to_webcam(self):
        self.is_webcam = True
        self.video_path = None
        self.stop_video()
        self.start_video_capture()

    def select_tracker(self):
        messagebox.showinfo("Select Tracker", "Tracker selection not implemented yet.")

    def update_confidence_threshold(self, value):
        self.confidence_threshold = float(value)
        print(f"Confidence threshold updated to: {self.confidence_threshold}")

    def update_filters(self):
        self.detection_classes = []
        if self.filter_person.get():
            self.detection_classes.append("person")
        if self.filter_vehicle.get():
            self.detection_classes.append("car")
        if self.filter_animal.get():
            self.detection_classes.append("animal")
        if self.other_filter.get():
            self.detection_classes.append("other")
        print(f"Detection classes updated to: {self.detection_classes}")

    def toggle_restricted_area(self):
        if self.restricted_area_toggle.get():
            messagebox.showinfo("Restricted Area", "Click and drag on the video to set the restricted area.")
        else:
            self.restricted_area = None
            if self.rectangle_id:
                self.video_canvas.delete(self.rectangle_id)
                self.rectangle_id = None

    def toggle_anomaly_detection(self):
        status = "enabled" if self.anomaly_detection_enabled.get() else "disabled"
        print(f"Anomaly detection {status}")

    def start_recording(self):
        if self.cap is None:
            print("Error: No video source selected.")
            return

        self.is_recording = True
        self.recording_start_time = time.time()
        filename = f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(self.recordings_folder, filename)
        
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
        
        print(f"Started automatic recording: {filename}")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.out is not None:
                self.out.release()
                self.out = None
            
            duration = time.time() - self.recording_start_time
            print(f"Stopped automatic recording. Duration: {duration:.2f} seconds")
            
            # Update the recorded videos list
            self.update_recorded_videos_list()

    def toggle_recording(self):
            if self.automatic_recording_enabled.get():
                print("Automatic recording enabled")
            else:
                print("Automatic recording disabled")

    def update_loitering_threshold(self, value):
        self.loitering_threshold = int(value)
        print(f"Loitering threshold updated to {self.loitering_threshold} seconds")

    def toggle_performance_mode(self):
            self.performance_mode = not self.performance_mode
            if self.performance_mode:
                self.frame_skip = 2  # Process every 3rd frame
                self.performance_mode_button.configure(
                    text="Disable Performance Mode",
                    fg_color=("green", "darkgreen")  # Active color
                )
            else:
                self.frame_skip = 0
                self.performance_mode_button.configure(
                    text="Enable Performance Mode",
                    fg_color=("gray70", "gray30")  # Inactive color
                )

    def save_preset(self):
        preset_name = simpledialog.askstring("Save Preset", "Enter a name for this preset:")
        if preset_name:
            settings = self.get_current_settings()
            try:
                with open(os.path.join(self.presets_folder, f'{preset_name}.json'), 'w') as f:
                    json.dump(settings, f)
                messagebox.showinfo("Save Preset", f"Preset '{preset_name}' saved successfully.")
                self.update_preset_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save preset: {str(e)}")

    def load_preset(self, preset_name):
        try:
            with open(os.path.join(self.presets_folder, f'{preset_name}.json'), 'r') as f:
                settings = json.load(f)
            
            # Update settings with error handling
            if 'confidence_threshold' in settings:
                self.confidence_threshold = settings['confidence_threshold']
                if hasattr(self, 'confidence_slider'):
                    self.confidence_slider.set(self.confidence_threshold)
            
            if 'loitering_threshold' in settings:
                self.loitering_threshold = settings['loitering_threshold']
                if hasattr(self, 'loitering_slider'):
                    self.loitering_slider.set(self.loitering_threshold)
            
            if 'detection_classes' in settings:
                self.detection_classes = settings['detection_classes']
                if hasattr(self, 'filter_person'):
                    self.filter_person.select() if 'person' in self.detection_classes else self.filter_person.deselect()
                if hasattr(self, 'filter_vehicle'):
                    self.filter_vehicle.select() if 'car' in self.detection_classes else self.filter_vehicle.deselect()
                if hasattr(self, 'filter_animal'):
                    self.filter_animal.select() if 'animal' in self.detection_classes else self.filter_animal.deselect()
                if hasattr(self, 'other_filter'):
                    self.other_filter.set('other' in self.detection_classes)
            
            for attr in ['anomaly_threshold_time', 'rapid_movement_threshold', 
                        'sudden_appearance_threshold', 'interaction_distance_threshold']:
                if attr in settings:
                    setattr(self, attr, settings[attr])
            
            if 'anomaly_detection_enabled' in settings and hasattr(self, 'anomaly_detection_enabled'):
                self.anomaly_detection_enabled.set(settings['anomaly_detection_enabled'])
            
            if 'automatic_recording_enabled' in settings and hasattr(self, 'automatic_recording_enabled'):
                self.automatic_recording_enabled.set(settings['automatic_recording_enabled'])
            
            messagebox.showinfo("Load Preset", f"Preset '{preset_name}' loaded successfully.")
        except FileNotFoundError:
            messagebox.showerror("Error", f"Preset file '{preset_name}.json' not found.")
        except json.JSONDecodeError:
            messagebox.showerror("Error", f"Invalid JSON in preset file '{preset_name}.json'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preset: {str(e)}")

    def update_preset_list(self):
        presets = [f[:-5] for f in os.listdir(self.presets_folder) if f.endswith('.json')]
        self.preset_selector.configure(values=presets)

    def get_preset_list(self):
        return [f[:-5] for f in os.listdir(self.presets_folder) if f.endswith('.json')]

    def open_options(self):
        if self.options_window is not None and self.options_window.winfo_exists():
            # If the window exists, close it and reset the reference
            self.options_window.destroy()
            self.options_window = None
        else:
            # Create a new options window
            self.options_window = ctk.CTkToplevel(self)
            self.options_window.title("Options")
            self.options_window.geometry("400x500")
            self.options_window.attributes('-topmost', True)  # Keep the window on top
            self.options_window.after(10, lambda: self.options_window.focus_force())  # Force focus after a short delay
            
            # Add a protocol to handle window close event
            self.options_window.protocol("WM_DELETE_WINDOW", self.on_options_window_close)
            
            # Email Settings
            email_frame = ctk.CTkFrame(self.options_window)
            email_frame.pack(padx=10, pady=10, fill="x")
            
            ctk.CTkLabel(email_frame, text="Email Settings").pack()
            
            ctk.CTkLabel(email_frame, text="SMTP Server:").pack()
            smtp_server_entry = ctk.CTkEntry(email_frame)
            smtp_server_entry.insert(0, self.email_settings['smtp_server'])
            smtp_server_entry.pack()
            
            ctk.CTkLabel(email_frame, text="SMTP Port:").pack()
            smtp_port_entry = ctk.CTkEntry(email_frame)
            smtp_port_entry.insert(0, str(self.email_settings['smtp_port']))
            smtp_port_entry.pack()
            
            ctk.CTkLabel(email_frame, text="Sender Email:").pack()
            sender_email_entry = ctk.CTkEntry(email_frame)
            sender_email_entry.insert(0, self.email_settings['sender_email'])
            sender_email_entry.pack()
            
            ctk.CTkLabel(email_frame, text="Sender Password:").pack()
            sender_password_entry = ctk.CTkEntry(email_frame, show="*")
            sender_password_entry.insert(0, self.email_settings['sender_password'])
            sender_password_entry.pack()
            
            ctk.CTkLabel(email_frame, text="Recipient Email:").pack()
            recipient_email_entry = ctk.CTkEntry(email_frame)
            recipient_email_entry.insert(0, self.email_settings['recipient_email'])
            recipient_email_entry.pack()
            
            # Notification Settings
            notification_frame = ctk.CTkFrame(self.options_window)
            notification_frame.pack(padx=10, pady=10, fill="x")
            
            ctk.CTkLabel(notification_frame, text="Notification Settings").pack()
            
            notify_on_anomaly_var = tk.BooleanVar(value=self.notification_settings['notify_on_anomaly'])
            notify_on_anomaly_check = ctk.CTkCheckBox(notification_frame, text="Notify on Anomaly", variable=notify_on_anomaly_var)
            notify_on_anomaly_check.pack()
            
            ctk.CTkLabel(notification_frame, text="Notify on Detection Threshold:").pack()
            detection_threshold_entry = ctk.CTkEntry(notification_frame)
            detection_threshold_entry.insert(0, str(self.notification_settings['notify_on_detection_threshold']))
            detection_threshold_entry.pack()
            
            # Save Button
            save_button = ctk.CTkButton(self.options_window, text="Save Settings", command=lambda: self.save_options(
                smtp_server_entry.get(),
                int(smtp_port_entry.get()),
                sender_email_entry.get(),
                sender_password_entry.get(),
                recipient_email_entry.get(),
                notify_on_anomaly_var.get(),
                int(detection_threshold_entry.get())
            ))
            save_button.pack(pady=10)

    def on_options_window_close(self):
        # This method is called when the options window is closed
        self.options_window.destroy()
        self.options_window = None

    def save_options(self, smtp_server, smtp_port, sender_email, sender_password, recipient_email, notify_on_anomaly, detection_threshold):
        self.email_settings.update({
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'sender_email': sender_email,
            'sender_password': sender_password,
            'recipient_email': recipient_email
        })
        
        self.notification_settings.update({
            'notify_on_anomaly': notify_on_anomaly,
            'notify_on_detection_threshold': detection_threshold
        })
        
        messagebox.showinfo("Settings Saved", "Your settings have been saved successfully.")

    def send_email_notification(self, subject, body):
        if not self.email_settings['sender_email'] or not self.email_settings['sender_password']:
            print("Email settings not configured. Skipping notification.")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_settings['sender_email']
            msg['To'] = self.email_settings['recipient_email']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_settings['smtp_server'], self.email_settings['smtp_port'])
            server.starttls()
            server.login(self.email_settings['sender_email'], self.email_settings['sender_password'])
            text = msg.as_string()
            server.sendmail(self.email_settings['sender_email'], self.email_settings['recipient_email'], text)
            server.quit()
            print("Email notification sent successfully")
        except Exception as e:
            print(f"Failed to send email notification: {str(e)}")
            print(f"Failed to send email notification: {str(e)}")

    def check_and_send_notifications(self, detections, anomalies):
        if self.notification_settings['notify_on_anomaly'] and anomalies:
            subject = "Security Alert: Anomaly Detected"
            body = f"An anomaly has been detected:\n\n{anomalies[-1]}"
            self.send_email_notification(subject, body)
        
        if len(detections) >= self.notification_settings['notify_on_detection_threshold']:
            subject = "Security Alert: Detection Threshold Reached"
            body = f"The number of detections has reached the threshold of {self.notification_settings['notify_on_detection_threshold']}."
            self.send_email_notification(subject, body)

    def on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rectangle_id:
            self.video_canvas.delete(self.rectangle_id)
        self.rectangle_id = self.video_canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")

    def on_mouse_drag(self, event):
        if self.rectangle_id:
            self.video_canvas.coords(self.rectangle_id, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        if self.rectangle_id:
            self.restricted_area = self.video_canvas.coords(self.rectangle_id)
            print(f"Restricted Area Selected: {self.restricted_area}")
            # Convert to integers
            self.restricted_area = tuple(map(int, self.restricted_area))

    def update_recorded_videos_list(self):
        self.recorded_videos_list = [f for f in os.listdir(self.recordings_folder) if f.endswith('.mp4')]
        self.recorded_videos_listbox.delete(0, "end")
        for video in self.recorded_videos_list:
            self.recorded_videos_listbox.insert("end", video)

    def open_video(self):
        selected_index = self.recorded_videos_listbox.curselection()
        if selected_index:
            video = self.recorded_videos_listbox.get(selected_index)
            video_path = os.path.join(self.recordings_folder, video)
            self.video_path = video_path
            self.is_webcam = False
            self.stop_video()
            self.start_video_capture()

    def refresh_detection_tab(self):
        # Clear existing items
        for listbox in [self.recent_detections_listbox, self.recent_anomalies_listbox, 
                        self.detection_stats_listbox, self.anomaly_stats_listbox]:
            listbox.delete(0, tk.END)
        
        # Fetch and display recent detections
        recent_detections = self.db_manager.get_recent_detections(5)
        for detection in recent_detections:
            formatted_time = detection[0].split('T')[1][:8]  # Extract time part and truncate to HH:MM:SS
            self.recent_detections_listbox.insert(tk.END, f"{formatted_time} - {detection[1]} ({detection[2]:.2f})")
        
        # Fetch and display recent anomalies
        recent_anomalies = self.db_manager.get_recent_anomalies(5)
        for anomaly in recent_anomalies:
            formatted_time = anomaly[0].split('T')[1][:8]  # Extract time part and truncate to HH:MM:SS
            self.recent_anomalies_listbox.insert(tk.END, f"{formatted_time} - {anomaly[1]}")
        
        # Fetch and display detection statistics
        detection_stats = self.db_manager.get_detection_stats(timedelta(days=7))  # Last 7 days
        for stat in detection_stats:
            self.detection_stats_listbox.insert(tk.END, f"{stat[0]}: {stat[1]}")
        
        # Fetch and display anomaly statistics
        anomaly_stats = self.db_manager.get_anomaly_stats(timedelta(days=7))  # Last 7 days
        for stat in anomaly_stats:
            self.anomaly_stats_listbox.insert(tk.END, f"{stat[0]}: {stat[1]}")

        print(f"Detection tab refreshed. Detections: {len(recent_detections)}, Anomalies: {len(recent_anomalies)}")
        
    def periodic_refresh(self):
        self.refresh_detection_tab()
        self.after(5000, self.periodic_refresh)  # Schedule next refresh in 5 seconds

    def get_current_settings(self):
        return {
            'confidence_threshold': self.confidence_threshold,
            'loitering_threshold': self.loitering_threshold,
            'detection_classes': self.detection_classes,
            'anomaly_threshold_time': self.anomaly_threshold_time,
            'rapid_movement_threshold': self.rapid_movement_threshold,
            'sudden_appearance_threshold': self.sudden_appearance_threshold,
            'interaction_distance_threshold': self.interaction_distance_threshold,
            'anomaly_detection_enabled': self.anomaly_detection_enabled.get(),
            'automatic_recording_enabled': self.automatic_recording_enabled.get(),
            'other_filter': self.other_filter.get(),
        }
        
    def on_closing(self):
        self.stop_recording()
        self.stop_video()
        self.destroy()

if __name__ == "__main__":
    app = SmartSecurityCameraSystem()
    app.mainloop()
        
    