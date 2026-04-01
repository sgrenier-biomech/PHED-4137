#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 16:47:54 2026

@author: sgrenier
"""
print("--- GUI IS INITIALIZING ---")
import sys
import kineticstoolkit.lab as ktk
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QComboBox, QRadioButton, QHBoxLayout, 
                             QFileDialog, QGroupBox, QMainWindow, QStyle, QMessageBox)
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
        self.video_win = None # Persistent reference to the video window
        self.video_path_pre = None
        self.video_path_post = None
        
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

        self.btn_plot_com = QPushButton("Plot CoM Trajectory (2D)")
        self.btn_plot_com.clicked.connect(self.plot_com_2d)
        self.btn_plot_com.setStyleSheet("height: 35px; background-color: #fce4ec; font-weight: bold;")
        layout.addWidget(self.btn_plot_com)

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

    def plot_joint(self):
        if not self.file_pre or not self.file_post: return
        side = "L" if self.rb_left.isChecked() else "R"
        joint, metric = self.combo_joint.currentText(), self.combo_metric.currentText()
        var = f"{side}{joint}Angles" if metric == "Angle" else f"{side}{joint}{metric}"
        fig, axs = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
        planes = ["Sagittal (X)", "Frontal (Y)", "Transverse (Z)"]
        for f, label, color in [(self.file_pre, "Pre", '#1f77b4'), (self.file_post, "Post", '#ff7f0e')]:
            try:
                data = ktk.read_c3d(f)
                points = data["Points"]
                t0 = [e.time for e in points.events if "STRIKE" in e.name.upper()][0] if points.events else 0
                if var in points.data:
                    for i in range(3):
                        axs[i].plot(points.time - t0, points.data[var][:, i], color=color, label=label if i==0 else None)
                        axs[i].set_ylabel(planes[i]); axs[i].grid(True, alpha=0.3)
                    self.draw_events(axs, points, t0, color)
            except: pass
        axs[0].legend(); plt.suptitle(f"{joint} {metric} Comparison"); plt.show()

    def plot_grf_comparison(self):
        if not self.file_pre and not self.file_post: return
        fig, axs = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
        labels = ["Medio-Lateral (X)", "Antero-Posterior (Y)", "Vertical (Z)"]
        
        for f, group_label, color in [(self.file_pre, "Pre", '#1f77b4'), (self.file_post, "Post", '#ff7f0e')]:
            if not f: continue
            try:
                data = ktk.read_c3d(f)
                points = data["Points"]
                fp_group = data["ForcePlatforms"]
                t0 = [e.time for e in points.events if "STRIKE" in e.name.upper()][0] if points.events else 0
                
                for p in [0, 1]:
                    chan = f"FP{p}_Force"
                    ls = "-" if p == 0 else "--"
                    if chan in fp_group.data:
                        for i in range(3):
                            axs[i].plot(fp_group.time - t0, fp_group.data[chan][:, i]/9.81, 
                                         color=color, linestyle=ls, 
                                         label=f"{group_label} FP{p}" if i==0 else None)
                self.draw_events(axs, points, t0, color)
            except Exception as e:
                print(f"GRF Error: {e}")

        for i in range(3): 
            axs[i].set_ylabel(f"{labels[i]} [BW]")
            axs[i].grid(True, alpha=0.3)
        axs[0].legend(fontsize='x-small', ncol=2)
        plt.suptitle("Bilateral GRF Comparison (ForcePlatforms)\nSolid: Platform 0 | Dashed: Platform 1"); plt.show()

    def plot_com_2d(self):
        if not self.file_pre and not self.file_post: return
        fig, axs = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
        planes = ["Medio-Lateral (X)", "Antero-Posterior (Y)", "Vertical (Z)"]
        for f, label, color in [(self.file_pre, "Pre", '#1f77b4'), (self.file_post, "Post", '#ff7f0e')]:
            if not f: continue
            try:
                data = ktk.read_c3d(f)
                points = data["Points"]
                t0 = [e.time for e in points.events if "STRIKE" in e.name.upper()][0] if points.events else 0
                com = points.data['CentreOfMass']
                for i in range(3):
                    axs[i].plot(points.time - t0, com[:, i], color=color, label=label if i==0 else None)
                    axs[i].set_ylabel(planes[i]); axs[i].grid(True, alpha=0.3)
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
        
        # FIX: Assign to self.video_win so it persists in memory
        self.video_win = VideoPlayer(path, grp)
        self.video_win.show()

if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    gui = GaitDashboard(); gui.show(); sys.exit(app.exec_())
