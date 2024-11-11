import tkinter as tk
from tkinter import ttk, messagebox
import serial
import threading
import time
from datetime import datetime
import json
import os

class FingerprintSystem:
    def _init_(self, root):
        self.root = root
        self.root.title("Fingerprint Authentication System")
        self.root.geometry("1024x600")
        
        # Custom theme colors and fonts
        self.colors = {
            'primary': '#0D47A1',
            'secondary': '#1976D2',
            'success': '#388E3C',
            'danger': '#D32F2F',
            'warning': '#F57C00',
            'background': '#ECEFF1',
            'text': '#212121'
        }
        
        self.fonts = {
            'title': ('Helvetica', 16, 'bold'),
            'label': ('Helvetica', 12),
            'button': ('Helvetica', 10, 'bold')
        }
        
        self.root.configure(bg=self.colors['background'])
        
        # Initialize serial connection
        try:
            self.serial = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
            time.sleep(2)
        except:
            messagebox.showerror("Error", "Could not connect to Arduino!")
            self.root.destroy()
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_serial)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        self.setup_gui()
        self.load_logs()
        
    def setup_gui(self):
        style = ttk.Style()
        style.configure('TFrame', background=self.colors['background'])
        style.configure('TLabel', background=self.colors['background'], font=self.fonts['label'])
        style.configure('TButton', background=self.colors['primary'], foreground='white', font=self.fonts['button'])
        
        # Main container with padding
        self.main_container = ttk.Frame(self.root, padding=10, style='TFrame')
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Status section
        self.status_frame = ttk.LabelFrame(self.main_container, text="System Status", padding=10, style='TFrame')
        self.status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.status_label = ttk.Label(self.status_frame, text="System Ready", font=self.fonts['title'])
        self.status_label.pack(pady=10)
        
        self.bac_label = ttk.Label(self.status_frame, text="BAC Level: 0.0 mg/L", font=self.fonts['label'], foreground=self.colors['warning'])
        self.bac_label.pack(pady=5)
        
        # Control section
        self.control_frame = ttk.LabelFrame(self.main_container, text="Controls", padding=10, style='TFrame')
        self.control_frame.pack(fill=tk.X, pady=(0, 20))
        
        btn_frame = ttk.Frame(self.control_frame, style='TFrame')
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Scan Fingerprint", command=self.scan_fingerprint, style='TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Enroll New", command=self.show_enroll_dialog, style='TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete ID", command=self.show_delete_dialog, style='TButton').pack(side=tk.LEFT, padx=5)
        
        # Log section
        self.log_frame = ttk.LabelFrame(self.main_container, text="Activity Log", padding=10, style='TFrame')
        self.log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_tree = ttk.Treeview(self.log_frame, columns=('Time', 'Event', 'Details'), show='headings')
        self.log_tree.heading('Time', text='Time')
        self.log_tree.heading('Event', text='Event')
        self.log_tree.heading('Details', text='Details')
        
        scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def monitor_serial(self):
        while self.running:
            if self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8').strip()
                self.process_serial_data(line)
            time.sleep(0.1)
    
    def process_serial_data(self, line):
        if line.startswith('BAC:'):
            bac_value = float(line.split(':')[1])
            self.root.after(0, lambda: self.bac_label.configure(text=f"BAC Level: {bac_value:.2f} mg/L"))
        elif line.startswith('STATUS:'):
            status = line.split(':')[1]
            if status == 'DRUNK':
                self.add_log_entry('Warning', 'High BAC Level Detected')
                messagebox.showwarning('Warning', 'Driver is not allowed to drive!')
        elif line.startswith('MATCH:'):
            id_num = line.split(':')[1]
            self.add_log_entry('Access', f'Fingerprint match found (ID: {id_num})')
        elif line == 'NO_MATCH':
            self.add_log_entry('Access Denied', 'No fingerprint match found')
    
    def scan_fingerprint(self):
        self.serial.write(b'SCAN\n')
        self.add_log_entry('System', 'Initiating fingerprint scan')
    
    def show_enroll_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Enroll New Fingerprint")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="Enter ID number (0-25):").pack(pady=10)
        
        id_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=id_var)
        entry.pack(pady=10)
        
        def enroll():
            try:
                id_num = int(id_var.get())
                if 0 <= id_num <= 25:
                    self.serial.write(f'ENROLL:{id_num}\n'.encode())
                    self.add_log_entry('System', f'Starting enrollment for ID {id_num}')
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "ID must be between 0 and 25")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        ttk.Button(dialog, text="Enroll", command=enroll, style='TButton').pack(pady=10)
    
    def show_delete_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Delete Fingerprint")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="Enter ID to delete (0-25):").pack(pady=10)
        
        id_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=id_var)
        entry.pack(pady=10)
        
        def delete():
            try:
                id_num = int(id_var.get())
                if 0 <= id_num <= 25:
                    self.serial.write(f'DELETE:{id_num}\n'.encode())
                    self.add_log_entry('System', f'Deleting fingerprint ID {id_num}')
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "ID must be between 0 and 25")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        ttk.Button(dialog, text="Delete", command=delete, style='TButton').pack(pady=10)
    
    def add_log_entry(self, event_type, details):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_tree.insert('', 0, values=(timestamp, event_type, details))
        self.save_logs()
    
    def load_logs(self):
        try:
            if os.path.exists('system_logs.json'):
                with open('system_logs.json', 'r') as f:
                    logs = json.load(f)
                    for log in logs:
                        self.log_tree.insert('', 'end', values=(log['time'], log['event'], log['details']))
        except:
            pass
    
    def save_logs(self):
        logs = []
        for item in self.log_tree.get_children():
            values = self.log_tree.item(item)['values']
            logs.append({
                'time': values[0],
                'event': values[1],
                'details': values[2]
            })
        
        with open('system_logs.json', 'w') as f:
            json.dump(logs, f)
    
    def _del_(self):
        self.running = False
        if hasattr(self, 'serial'):
            self.serial.close()

if _name_ == "_main_":
    root = tk.Tk()
    app = FingerprintSystem(root)
    root.mainloop()
