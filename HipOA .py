#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  8 10:33:31 2026

@author: sgrenier
"""

print("--- GUI IS INITIALIZING ---")
import sys
import kineticstoolkit.lab as ktk
import matplotlib
# MUST be called before importing pyplot to fix Mac buttons and Windows animation
matplotlib.use('Qt5Agg')  
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QComboBox, QRadioButton, QHBoxLayout, 
                             QFileDialog, QGroupBox, QMainWindow, QStyle, 
                             QMessageBox, QLineEdit) 
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt

class VideoPlayer(QMainWindow):
    def __init__(self, video_path, group_label):
        super().__init__()
        self.setWindowTitle(f"{group_label} Video: {Path(video_path).name}")
        self.resize(700, 500)
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        videoWidget = QVideoWidget()
        self.playBtn = QPushButton()
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playBtn.clicked.connect(self.toggle_video)
        layout = QVBoxLayout(); layout.addWidget(videoWidget)
        controls = QHBoxLayout(); controls.addWidget(self.playBtn); layout.addLayout(controls)
        container = QWidget(); container.setLayout(layout); self.setCentralWidget(container)
        self.mediaPlayer.setVideoOutput(videoWidget)
        self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        self.mediaPlayer.play()

    def toggle_video(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            self.mediaPlayer.play()
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

class GaitDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.file_pre = None
        self.file_post = None
        self.video_win = None 
        self.video_path_pre = None
        self.video_path_post = None
        
        # Biomechanics Settings
        self.body_mass_kg = 70.0  # Default mass for normalization (adjust as needed)
        
        self.interconnections = {
            "Pelvis": {"Color": (1, 0.5, 1), "Links": [["LASI", "RASI", "RPSI", "LPSI", "LASI"]]},
            "Left Leg": {"Color": (1, 0.5, 0), "Links": [["LASI", "LKNE"], ["LKNE", "LANK"], ["LANK", "LHEE", "LTOE", "LANK"]]},
            "Right Leg": {"Color": (0, 0.5, 1), "Links": [["RASI", "RKNE"], ["RKNE", "RANK"], ["RANK", "RHEE", "RTOE", "RANK"]]},
            "Torso": {"Color": (0.5, 1, 0.5), "Links": [["C7", "T10", "STRN", "CLAV", "C7"], ["LSHO", "RSHO", "STRN", "LSHO"]]},
            "Left Arm": {"Color": (1, 1, 0), "Links": [["LSHO", "LELB"], ["LELB", "LWRA", "LELB"], ["LWRA", "LFIN"]]},
            "Right Arm": {"Color": (0, 1, 1), "Links": [["RSHO", "RELB"], ["RELB", "RWRA", "RELB"], ["RWRA", "RFIN"]]}
        }
        self.init_ui()
        self.raise_(); self.activateWindow()

    def init_ui(self):
        self.setWindowTitle("Hip OA Clinical Analysis")
        self.setGeometry(100, 100, 550, 850)
        layout = QVBoxLayout()

        file_layout = QHBoxLayout()
        for mode, title, color in [('pre', 'Group A (PRE)', '#1f77b4'), ('post', 'Group B (POST)', '#ff7f0e')]:
            group = QGroupBox(title)
            group.setStyleSheet(f"QGroupBox {{ border: 2px solid {color}; font-weight: bold; }}")
            v = QVBoxLayout()
            lbl = QLabel("<i>No file loaded</i>"); lbl.setWordWrap(True)
            if mode == 'pre': self.lbl_pre = lbl
            else: self.lbl_post = lbl
            btn = QPushButton("Select C3D File")
            btn.clicked.connect(lambda checked, m=mode: self.load_file(m))
            v.addWidget(lbl); v.addWidget(btn); group.setLayout(v); file_layout.addWidget(group)
        layout.addLayout(file_layout)

        settings_group = QGroupBox("Plot Settings")
        s_layout = QVBoxLayout()
        side_h = QHBoxLayout()
        self.rb_left = QRadioButton("Left"); self.rb_left.setChecked(True)
        self.rb_right = QRadioButton("Right")
        side_h.addWidget(self.rb_left); side_h.addWidget(self.rb_right)
        self.combo_joint = QComboBox(); self.combo_joint.addItems(["Hip", "Knee", "Ankle"])
        self.combo_metric = QComboBox(); self.combo_metric.addItems(["Angle", "Moment", "Force", "Power"])
        s_layout.addLayout(side_h); s_layout.addWidget(self.combo_joint); s_layout.addWidget(self.combo_metric)
        settings_group.setLayout(s_layout); layout.addWidget(settings_group)

        self.btn_plot_joint = QPushButton("Plot Joint Comparison")
        self.btn_plot_joint.clicked.connect(self.plot_joint)
        self.btn_plot_joint.setStyleSheet("font-weight: bold; height: 35px; background-color: #e3f2fd;")
        layout.addWidget(self.btn_plot_joint)

        self.btn_plot_grf = QPushButton("Plot GRF (ForcePlatforms)")
        self.btn_plot_grf.clicked.connect(self.plot_grf_comparison)
        self.btn_plot_grf.setStyleSheet("height: 35px; background-color: #f1f8e9;")
        layout.addWidget(self.btn_plot_grf)
        
        self.btn_plot_cop = QPushButton("Plot COP Trajectory (X vs. Y)")
        self.btn_plot_cop.clicked.connect(self.plot_cop_2d_path)
        self.btn_plot_cop.setStyleSheet("height: 35px; background-color: #fff9c4; font-weight: bold;")
        layout.addWidget(self.btn_plot_cop)
        
        self.btn_plot_com = QPushButton("Plot CoM Trajectory (2D)")
        self.btn_plot_com.clicked.connect(self.plot_com_2d)
        self.btn_plot_com.setStyleSheet("height: 35px; background-color: #fce4ec; font-weight: bold;")
        layout.addWidget(self.btn_plot_com)
        
        # # Add a Mass Input row
        # mass_layout = QHBoxLayout()
        # mass_label = QLabel("Subject Mass (kg):")
        # self.edit_mass = QLineEdit("70.0")  # Default value as a string
        # self.edit_mass.setFixedWidth(60)
        # mass_layout.addWidget(mass_label)
        # mass_layout.addWidget(self.edit_mass)
        # mass_layout.addStretch()
        
        # # Add it to your existing settings layout
        # s_layout.addLayout(mass_layout)

        for g in ["Pre", "Post"]:
            h = QHBoxLayout()
            btn_a = QPushButton(f"Animate {g}"); btn_a.clicked.connect(lambda checked, gr=g: self.animate_file(gr))
            btn_v = QPushButton(f"Video {g}"); btn_v.clicked.connect(lambda checked, gr=g: self.play_video(gr))
            h.addWidget(btn_a); h.addWidget(btn_v); layout.addLayout(h)

        self.btn_close = QPushButton("Close Plots"); self.btn_close.clicked.connect(lambda: plt.close('all'))
        layout.addWidget(self.btn_close); self.setLayout(layout)

    def load_file(self, mode):
        combined_filter = "All Files (*.c3d *.avi *.mp4);;C3D Files (*.c3d);;Videos (*.avi *.mp4)"
        fname, _ = QFileDialog.getOpenFileName(self, "Select File", "", combined_filter)
        if fname:
            ext = Path(fname).suffix.lower()
            if ext == '.c3d':
                if mode == 'pre': self.file_pre = fname; self.lbl_pre.setText(f"Data: {Path(fname).name}")
                else: self.file_post = fname; self.lbl_post.setText(f"Data: {Path(fname).name}")
            else:
                if mode == 'pre': self.video_path_pre = fname
                else: self.video_path_post = fname
                QMessageBox.information(self, "Linked", f"Video linked to {mode}")

    def draw_events(self, axs, points, t0, color):
        s, o = 0, 0
        sorted_ev = sorted(points.events, key=lambda x: x.time)
        for ev in sorted_ev:
            t_ev = ev.time - t0
            if "STRIKE" in ev.name.upper():
                s += 1; lbl, ls = f" Strike {s}", "-"
            elif "OFF" in ev.name.upper():
                o += 1; lbl, ls = f" Off {o}", "--"
            else: continue
            for i in range(len(axs)):
                axs[i].axvline(x=t_ev, color=color, alpha=0.3, linestyle=ls)
                if i == 0:
                    axs[i].text(t_ev, 0.95, lbl, color=color, rotation=90, 
                                verticalalignment='top', fontsize=8, fontweight='bold',
                                transform=axs[i].get_xaxis_transform())
    def get_body_mass(self):
        try:
            return float(self.edit_mass.text())
        except ValueError:
            # Fallback to 70kg and warn the user
            QMessageBox.warning(self, "Invalid Mass", "Please enter a numeric value for mass. Defaulting to 70kg.")
            self.edit_mass.setText("70.0")
            return 70.0
        
    def plot_joint(self):
        if not self.file_pre or not self.file_post: 
            QMessageBox.warning(self, "Missing Files", "Please load both Pre and Post files.")
            return
            
        side = "L" if self.rb_left.isChecked() else "R"
        joint, metric = self.combo_joint.currentText(), self.combo_metric.currentText()
        var = f"{side}{joint}Angles" if metric == "Angle" else f"{side}{joint}{metric}"
        
        fig, axs = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
        planes = ["Sagittal (X)", "Frontal (Y)", "Transverse (Z)"]
        
        for f, label, color in [(self.file_pre, "Pre", '#1f77b4'), (self.file_post, "Post", '#ff7f0e')]:
            try:
                # convert_point_unit=False prevents clinical degrees from being divided by 1000
                data = ktk.read_c3d(f, convert_point_unit=False)
                points = data["Points"]
                
                # Time normalization to first strike
                strikes = [e.time for e in points.events if "STRIKE" in e.name.upper()]
                t0 = strikes[0] if strikes else points.time[0]
                
                if var in points.data:
                    for i in range(3):
                        # Ensure 1D array for math
                        plot_data = points.data[var][:, i].flatten()
                        
                        
                        #Fix Flipping/Gimbal Lock (Only for Angles)
                        if metric == "Angle":
                            # Use unwrap to remove 360-degree jumps
                            plot_data = np.unwrap(plot_data * np.pi / 180) * 180 / np.pi
                            
                            # Shift mean toward zero to align Pre and Post
                            # (Prevents one being at 0 and the other at 360)
                            if (np.nanmax(plot_data) - np.nanmin(plot_data)) > 150:
                                offset = round(np.nanmean(plot_data) / 180) * 180
                                plot_data = plot_data - offset
                                
                        # 2. FIX: Scaling for Moments
                        # If the values are > 100, they are likely in N*mm. 
                        # Clinical standard is N*m (or N*m/kg). 
                        elif metric == "Moment":
                            if np.nanmax(np.abs(plot_data)) > 50:
                                plot_data = plot_data / 1000.0  # Convert mm to m
                
                        # 3. FIX: Horizontal "Tiers" (Vertical Offsets)
                        # If there are massive jumps in Moments, it's a C3D metadata error.
                        # This zero-centers the moment around the first few frames.
                        if metric == "Moment" or metric == "Force":
                            plot_data = plot_data - np.nanmedian(plot_data[:10])                                

                        # 3. Plotting (Now correctly inside the 'i' loop)
                        axs[i].plot(points.time - t0, plot_data, color=color, label=label if i==0 else None)
                        
                        # Set the units based on what we are plotting
                        if metric == "Angle":
                            unit_label = " [deg]"
                        elif metric == "Moment":
                            unit_label = " [N·m/kg]"  # Standard clinical unit
                        elif metric == "Power":
                            unit_label = " [W/kg]"
                        elif metric == "Force":
                            unit_label = " [N/kg]"
                        else:
                            unit_label = ""                       
                        axs[i].set_ylabel(f"{planes[i]}{unit_label}")
                        axs[i].grid(True, alpha=0.3)
                    
                    self.draw_events(axs, points, t0, color)
            except Exception as e: 
                print(f"Error processing {label}: {e}")

        # Add legend only if data was plotted
        handles, labels = axs[0].get_legend_handles_labels()
        if handles:
            axs[0].legend(handles, labels)
            
        plt.suptitle(f"{joint} {metric} Comparison")
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()
        
    def plot_grf_comparison(self):
        if not self.file_pre and not self.file_post: 
            QMessageBox.warning(self, "Missing Files", "Please load both Pre and Post files.")
            return
        
        # 3 Rows (Planes), 2 Columns (Pre, Post)
        fig, axs = plt.subplots(3, 2, sharex=True, sharey=True, figsize=(12, 10))
        planes = ["Medio-Lateral (X)", "Antero-Posterior (Y)", "Vertical (Z)"]
        col_map = {"Pre": 0, "Post": 1}

        for f, group_label, color in [(self.file_pre, "Pre", '#1f77b4'), (self.file_post, "Post", '#ff7f0e')]:
            if not f: continue
            col = col_map[group_label]
            
            try:
                data = ktk.read_c3d(f, convert_point_unit=True)
                points = data["Points"]
                fp_group = data["ForcePlatforms"]
                
                # Align to first strike
                strikes = [e.time for e in points.events if "STRIKE" in e.name.upper()]
                t0 = strikes[0] if strikes else fp_group.time[0]
                
                for p in [0, 1]:
                    chan = f"FP{p}_Force"
                    ls = "-" if p == 0 else "--"
                    
                    if chan in fp_group.data:
                        for row in range(3):
                            plot_data = fp_group.data[chan][:, row].flatten()
                            # Normalizing to BW (70kg default)
                            plot_data = plot_data / (70.0 * 9.81)
                            
                            ax = axs[row, col]
                            ax.plot(fp_group.time - t0, plot_data, 
                                    color=color, linestyle=ls, 
                                    label=f"Plate {p}" if row == 0 else None)
                            
                            if col == 0: ax.set_ylabel(f"{planes[row]} [BW]")
                            if row == 0: ax.set_title(f"Group: {group_label}")
                            ax.grid(True, alpha=0.3)
                
                # IMPROVED: Call the label drawer specifically for this column
                self.draw_labels_on_grid(axs, points, t0, color, col)

            except Exception as e:
                print(f"GRF Error for {group_label}: {e}")

        axs[0, 0].legend(fontsize='x-small')
        axs[0, 1].legend(fontsize='x-small')
        plt.suptitle("Ground Reaction Force (GRF) Comparison\nNormalized to Body Weight (BW)")
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()

    def draw_labels_on_grid(self, axs, points, t0, color, col):
        """Draws vertical lines and 'Strike/Off' text labels on a specific column"""
        for e in points.events:
            e_name = e.name.upper()
            if "STRIKE" in e_name or "OFF" in e_name:
                t_rel = e.time - t0
                ls = '-' if "STRIKE" in e_name else '--'
                
                for row in range(3):
                    ax = axs[row, col]
                    # Draw the vertical line
                    ax.axvline(t_rel, color=color, linestyle=ls, alpha=0.3)
                    
                    # Only put the TEXT label on the TOP row to avoid clutter
                    if row == 0:
                        ax.text(t_rel, ax.get_ylim()[1], e.name, 
                                color=color, rotation=90, va='bottom', ha='right', fontsize=8)

    def draw_events_on_cols(self, axs, points, t0, color, col):
        """Helper to draw event lines only on the active column"""
        for e in points.events:
            if "STRIKE" in e.name.upper() or "OFF" in e.name.upper():
                ls = '-' if "STRIKE" in e.name.upper() else '--'
                for row in range(3):
                    axs[row, col].axvline(e.time - t0, color=color, linestyle=ls, alpha=0.3)
                    
    def plot_cop_2d_path(self):
        if not self.file_pre and not self.file_post: 
            QMessageBox.warning(self, "Missing Files", "Please load both Pre and Post files.")
            return
        
        # Threshold (N/kg) to isolate stance phase (approx 5% BW)
        threshold_nkg = 0.5 

        # Create 1 row, 2 columns for side-by-side comparison
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 8), sharey=True, sharex=True)
        axes = {'Pre': ax1, 'Post': ax2}
        
        for f, label, color in [(self.file_pre, "Pre", '#1f77b4'), (self.file_post, "Post", '#ff7f0e')]:
            if not f: continue
            ax = axes[label]
            try:
                data = ktk.read_c3d(f, convert_point_unit=True)
                fp_group = data["ForcePlatforms"]
                
                all_handles = []
                all_labels = []

                for p in [0, 1]:
                    force_chan = f"FP{p}_Force"
                    cop_chan = f"FP{p}_COP"
                    ls = "-" if p == 0 else "--" 
                    
                    if force_chan in fp_group.data and cop_chan in fp_group.data:
                        fz = fp_group.data[force_chan][:, 2].flatten() 
                        copx = fp_group.data[cop_chan][:, 0].flatten()
                        copy = fp_group.data[cop_chan][:, 1].flatten()
                        
                        # Thresholding using the 70kg default or mass logic
                        is_stance = np.abs(fz / 70.0) > threshold_nkg
                        
                        copx_s = np.where(is_stance, copx, np.nan)
                        copy_s = np.where(is_stance, copy, np.nan)
                        
                        if np.any(is_stance):
                            # Zero-center relative to the platform's own data
                            copx_s = copx_s - np.nanmedian(copx_s)
                            copy_s = copy_s - np.nanmedian(copy_s)

                            line, = ax.plot(copx_s, copy_s, color=color, linestyle=ls, alpha=0.8)
                            all_handles.append(line)
                            all_labels.append(f"Plate {p}")

                # Format individual subplot
                ax.set_title(f"Group: {label}")
                ax.set_xlabel("ML COP (X) [m]")
                if label == "Pre": ax.set_ylabel("AP COP (Y) [m]")
                ax.grid(True, alpha=0.3)
                ax.axhline(0, color='black', lw=1, alpha=0.2)
                ax.axvline(0, color='black', lw=1, alpha=0.2)
                ax.legend(all_handles, all_labels, fontsize='x-small')

            except Exception as e:
                print(f"COP Error for {label}: {e}")

        plt.suptitle("Center of Pressure Trajectory Comparison (X vs. Y)\n(Stance Phase Only)")
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()
        
        
    def plot_com_2d(self):
        if not self.file_pre and not self.file_post: return
        fig, axs = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
        planes = ["Medio-Lateral (X)", "Antero-Posterior (Y)", "Vertical (Z)"]
        for f, label, color in [(self.file_pre, "Pre", '#1f77b4'), (self.file_post, "Post", '#ff7f0e')]:
            if not f: continue
            try:
                data = ktk.read_c3d(f, convert_point_unit=True)
                points = data["Points"]
                t0 = [e.time for e in points.events if "STRIKE" in e.name.upper()][0] if points.events else 0
                com = points.data['CentreOfMass']
                for i in range(3):
                    axs[i].plot(points.time - t0, com[:, i], color=color, label=label if i==0 else None)
                    axs[i].set_ylabel(f"{planes[i]} [m]"); axs[i].grid(True, alpha=0.3)
                self.draw_events(axs, points, t0, color)
            except: pass
        plt.suptitle("CoM Comparison"); plt.show()

    def animate_file(self, grp):
        f = self.file_pre if grp == "Pre" else self.file_post
        if f:
            data = ktk.read_c3d(f, convert_point_unit=True)
            points = data["Points"]
            used_markers = set()
            for segment in self.interconnections.values():
                for link in segment["Links"]:
                    for marker in link: used_markers.add(marker)
            filtered_points = ktk.TimeSeries(time=points.time)
            for marker in used_markers:
                if marker in points.data: filtered_points.data[marker] = points.data[marker]
            
            # The Player will now be interactive on both OSs thanks to Qt5Agg
            p = ktk.Player(filtered_points, up="z", anterior="y", target_distance=5.0)
            p.set_interconnections(self.interconnections)

    def play_video(self, grp):
        path = self.video_path_pre if grp == "Pre" else self.video_path_post
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, f"Select Video for {grp}", "", "Videos (*.avi *.mp4);;All Files (*)")
            if path:
                if grp == "Pre": self.video_path_pre = path
                else: self.video_path_post = path
            else: return
        
        self.video_win = VideoPlayer(path, grp)
        self.video_win.show()

if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    gui = GaitDashboard(); gui.show(); sys.exit(app.exec_())
