import os
import sys
import shutil
import logging
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QComboBox, 
                               QFileDialog, QProgressBar, QPlainTextEdit, 
                               QCheckBox, QGroupBox, QScrollArea, QGridLayout, 
                               QFrame, QMessageBox, QGraphicsDropShadowEffect,
                               QListWidget, QListWidgetItem, QAbstractItemView, 
                               QSplitter, QToolButton)
from PySide6.QtCore import Qt, QThread, Slot, QSize, QUrl, QTimer
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices, QColor, QFont

# Multimedia
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False
    class QVideoWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setStyleSheet("background-color: black;")
            layout = QVBoxLayout(self)
            label = QLabel("组件缺失: PySide6.QtMultimedia")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: white;")
            layout.addWidget(label)

from core.processor import TransNetWorker
from core.config import ConfigManager

class FileListItem(QWidget):
    """自定义文件列表项组件"""
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)
        
        # Explicit Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.checkbox)
        
        # Icon
        self.icon_lbl = QLabel("MP4")
        self.icon_lbl.setFixedSize(40, 40)
        self.icon_lbl.setStyleSheet("background-color: #F0F2F5; border-radius: 8px; color: #909399; font-weight: bold; font-size: 11px;")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        self.name_lbl = QLabel(os.path.basename(path))
        self.name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #303133;")
        
        self.status_lbl = QLabel("等待处理")
        self.status_lbl.setStyleSheet("font-size: 12px; color: #909399;")
        
        text_layout.addWidget(self.name_lbl)
        text_layout.addWidget(self.status_lbl)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Status Icon (Right side)
        self.state_icon = QLabel()
        self.state_icon.setFixedSize(10, 10)
        self.state_icon.setStyleSheet("border-radius: 5px; background-color: #E4E7ED;")
        layout.addWidget(self.state_icon)

    def set_status(self, status, color_hex="#909399"):
        self.status_lbl.setText(status)
        self.status_lbl.setStyleSheet(f"font-size: 12px; color: {color_hex};")
        
    def set_processing(self):
        self.state_icon.setStyleSheet("border-radius: 5px; background-color: #409EFF;")
        self.status_lbl.setText("正在处理...")
        self.status_lbl.setStyleSheet("font-size: 12px; color: #409EFF;")
        
    def set_active(self, active):
        if active:
            self.setStyleSheet("background-color: #ECF5FF; border-radius: 8px;")
            self.icon_lbl.setStyleSheet("background-color: #D9ECFF; border-radius: 8px; color: #409EFF; font-weight: bold; font-size: 11px;")
        else:
            self.setStyleSheet("background-color: transparent;")
            self.icon_lbl.setStyleSheet("background-color: #F0F2F5; border-radius: 8px; color: #909399; font-weight: bold; font-size: 11px;")

    def set_checked(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        self.checkbox.setCheckState(state)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TransVideo 视频智能分割工具")
        self.resize(1180, 820)
        
        self.config = ConfigManager()
        self.worker = None
        self.thread = None
        self.files_map = {} 
        self.current_preview_path = None
        self.result_idx = 0
        
        # Player config
        self.player = None
        self.audio_output = None

        self.setup_styles()
        self.setup_ui()
        self.setup_player()
        
        # Init
        last_folder = self.config.get("last_folder")
        if last_folder and os.path.isdir(last_folder):
            self.load_folder(last_folder)
            
        self.check_keyframes.setChecked(self.config.get("extract_keyframes"))

    def setup_styles(self):
        # Force Light Theme - Element Plus Style with ID Selectors
        self.setStyleSheet("""
            /* Global Application Style */
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 14px;
                color: #303133; 
            }
            
            QMainWindow, QWidget#CentralWidget {
                background-color: #F2F3F5; 
            }
            
            QFrame#Card {
                background-color: #FFFFFF;
                border: 1px solid #E4E7ED;
                border-radius: 8px;
            }
            
            /* ---- Buttons (ID Selectors for Priority) ---- */
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #DCDFE6;
                border-radius: 6px;
                padding: 8px 16px;
                color: #606266;
            }
            
            /* PRIMARY BUTTON (Start) */
            QPushButton#StartBtn {
                background-color: #409EFF;
                color: #FFFFFF;
                border: 1px solid #409EFF;
                font-weight: bold;
            }
            QPushButton#StartBtn:hover {
                background-color: #66B1FF;
                border-color: #66B1FF;
            }
            QPushButton#StartBtn:pressed {
                background-color: #3a8ee6;
                border-color: #3a8ee6;
            }
            
            /* DANGER BUTTON (Stop) */
            QPushButton#StopBtn {
                background-color: #F56C6C;
                color: #FFFFFF;
                border: 1px solid #F56C6C;
                font-weight: bold;
            }
            QPushButton#StopBtn:hover {
                background-color: #F78989;
                border-color: #F78989;
            }
            QPushButton#StopBtn:disabled {
                background-color: #FAB6B6;
                border-color: #FAB6B6;
                color: #FFFFFF;
            }

            /* Tool Buttons */
            QPushButton#ToolBtn {
                background-color: #FFFFFF;
                border: 1px solid #DCDFE6;
                padding: 5px 10px;
                color: #606266;
            }
            QPushButton#ToolBtn:hover {
                color: #409EFF;
                border-color: #409EFF;
            }

            /* Inputs */
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #DCDFE6;
                border-radius: 4px;
                padding: 0 12px;
                height: 38px;
                color: #303133;
            }
            QLineEdit:focus {
                border-color: #409EFF;
            }

            /* List Widget */
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #E4E7ED;
                border-radius: 6px;
                outline: none;
                padding: 4px;
            }
            QListWidget::item {
                border-bottom: 1px solid #F2F6FC;
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 2px;
                color: #303133;
            }
            QListWidget::item:hover {
                background-color: #F5F7FA;
            }
            QListWidget::item:selected {
                background-color: #ECF5FF;
                color: #409EFF;
                border: 1px solid #D9ECFF;
            }

            /* Checkbox */
            QCheckBox { spacing: 8px; color: #606266; font-size: 14px; }
            QCheckBox::indicator {
                width: 18px; height: 18px;
                border: 1px solid #DCDFE6; border-radius: 4px; background-color: #FFFFFF;
            }
            QCheckBox::indicator:unchecked:hover { border-color: #409EFF; }
            QCheckBox::indicator:checked {
                background-color: #409EFF; border-color: #409EFF;
                image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png);
            }

            /* Progress Bar - Blue theme */
            QProgressBar {
                border: 1px solid #E4E7ED;
                border-radius: 4px;
                background-color: #F5F7FA;
                text-align: center;
                height: 16px;
                font-size: 11px;
                color: #303133;
            }
            QProgressBar::chunk {
                background-color: #409EFF;
                border-radius: 3px;
            }

            /* Message Box styling */
            QMessageBox {
                background-color: #FFFFFF;
            }
            QMessageBox QLabel {
                color: #303133;
            }
        """)

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # --- Top Bar ---
        top_bar = QHBoxLayout()
        path_group = QFrame()
        path_group.setObjectName("Card")
        path_group.setFrameShape(QFrame.NoFrame)
        path_layout = QHBoxLayout(path_group)
        path_layout.setContentsMargins(15, 10, 15, 10)
        
        self.path_label_icon = QLabel("📂 视频源目录：")
        self.path_label_icon.setStyleSheet("font-weight: 600; color: #303133;")
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("请点击右侧按钮选择包含视频的文件夹...")
        self.path_edit.setReadOnly(True)
        self.path_edit.setStyleSheet("border: none; background: transparent; font-size: 14px; color: #606266;")
        self.browse_btn = QPushButton("浏览文件夹")
        self.browse_btn.setMinimumHeight(36)
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(self.path_label_icon)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        top_bar.addWidget(path_group)
        main_layout.addLayout(top_bar)

        # --- Content Area ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # --- Left Panel ---
        left_container = QFrame()
        left_container.setObjectName("Card")
        left_container.setFixedWidth(320)  # Narrower left panel
        self.apply_shadow(left_container)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)
        
        # List Header
        list_header = QHBoxLayout()
        list_label = QLabel("待处理视频列表")
        list_label.setStyleSheet("font-weight: 700; font-size: 16px; color: #303133;")
        list_header.addWidget(list_label)
        list_header.addStretch()
        
        self.btn_check_all = QPushButton("全选")
        self.btn_check_all.setObjectName("ToolBtn")
        self.btn_check_all.setCursor(Qt.PointingHandCursor)
        self.btn_check_all.clicked.connect(lambda: self.set_list_checked(True))
        
        self.btn_check_none = QPushButton("反选")
        self.btn_check_none.setObjectName("ToolBtn")
        self.btn_check_none.setCursor(Qt.PointingHandCursor)
        self.btn_check_none.clicked.connect(self.invert_list_checked)
        
        list_header.addWidget(self.btn_check_all)
        list_header.addWidget(self.btn_check_none)
        left_layout.addLayout(list_header)
        
        # Merge Export Row
        merge_row = QHBoxLayout()
        merge_row.setSpacing(8)
        
        self.btn_merge_export = QPushButton("📦 合并导出")
        self.btn_merge_export.setObjectName("ToolBtn")
        self.btn_merge_export.setCursor(Qt.PointingHandCursor)
        self.btn_merge_export.setToolTip("将所有分割视频复制到一个文件夹并顺序重命名")
        self.btn_merge_export.clicked.connect(self.merge_export_videos)
        merge_row.addWidget(self.btn_merge_export)
        
        self.btn_view_merged = QPushButton("👁 查看合并")
        self.btn_view_merged.setObjectName("ToolBtn")
        self.btn_view_merged.setCursor(Qt.PointingHandCursor)
        self.btn_view_merged.setToolTip("在预览区浏览合并文件夹内容")
        self.btn_view_merged.clicked.connect(self.view_merged_folder)
        merge_row.addWidget(self.btn_view_merged)
        
        merge_row.addStretch()
        left_layout.addLayout(merge_row)
        
        # File List
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_item_clicked)
        left_layout.addWidget(self.file_list)
        
        # Action Area
        action_area = QFrame()
        action_area.setStyleSheet("background-color: #F5F7FA; border-radius: 8px; padding: 15px;")
        action_layout = QVBoxLayout(action_area)
        
        self.check_keyframes = QCheckBox("智能提取中间帧 (缩略图)")
        self.check_keyframes.setStyleSheet("font-weight: 500; font-size: 14px;")
        self.check_keyframes.stateChanged.connect(lambda s: self.config.set("extract_keyframes", bool(s)))
        action_layout.addWidget(self.check_keyframes)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        
        # Primary button with INLINE style for guaranteed visibility
        self.start_btn = QPushButton("▶ 智能分割")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet("background-color: #409EFF; color: white; border: none; border-radius: 6px; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_processing)
        
        self.stop_btn = QPushButton("⏹ 停止任务")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setStyleSheet("background-color: #F56C6C; color: white; border: none; border-radius: 6px; font-weight: bold;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)
        
        btn_box.addWidget(self.start_btn)
        btn_box.addWidget(self.stop_btn)
        action_layout.addLayout(btn_box)
        left_layout.addWidget(action_area)
        content_layout.addWidget(left_container)
        
        # --- Right Panel ---
        right_container = QFrame()
        right_container.setObjectName("Card")
        self.apply_shadow(right_container)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(0)
        
        # Video Player - Make it prominent
        player_container = QFrame()
        player_container.setStyleSheet("background-color: #000000; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        player_layout = QVBoxLayout(player_container)
        player_layout.setContentsMargins(0,0,0,0)
        player_layout.setSpacing(0)
        
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(350)  # Ensure minimum video display area
        player_layout.addWidget(self.video_widget, 1)  # Stretch factor 1
        
        # Player Control Bar - Enhanced visibility
        self.player_control = QFrame()
        self.player_control.setFixedHeight(50)
        self.player_control.setStyleSheet("background-color: #1A1A1A;")
        ctrl_layout = QHBoxLayout(self.player_control)
        ctrl_layout.setContentsMargins(15, 8, 15, 8)
        ctrl_layout.setSpacing(15)
        
        # Play/Pause button - LARGE and VISIBLE
        self.play_pause_btn = QPushButton("▶ 播放")
        self.play_pause_btn.setFixedSize(80, 34)
        self.play_pause_btn.setCursor(Qt.PointingHandCursor)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66B1FF;
            }
        """)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        ctrl_layout.addWidget(self.play_pause_btn)
        
        self.player_status_lbl = QLabel("准备就绪")
        self.player_status_lbl.setStyleSheet("color: #CCC; font-size: 13px;")
        ctrl_layout.addWidget(self.player_status_lbl)
        ctrl_layout.addStretch()
        
        player_layout.addWidget(self.player_control)
        right_layout.addWidget(player_container, 2)  # Stretch factor 2 - prioritize player
        
        # Results area
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(20, 15, 20, 20)
        
        # Header with Open Folder Button
        res_header = QHBoxLayout()
        res_label = QLabel("处理进度与结果")
        res_label.setStyleSheet("font-weight: 700; font-size: 15px; color: #303133;")
        res_header.addWidget(res_label)
        res_header.addStretch()
        
        self.open_folder_btn = QPushButton("📂 打开输出文件夹")
        self.open_folder_btn.setObjectName("ToolBtn")
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.setVisible(False) # Show only when processing starts/done
        res_header.addWidget(self.open_folder_btn)
        detail_layout.addLayout(res_header)
        
        # Progress - Compact
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(18)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        detail_layout.addWidget(self.progress_bar)
        
        # Result Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(290)  # 2 full rows: 130px card + 12px spacing x 2
        self.scroll_area.setStyleSheet("border: 1px solid #E4E7ED; border-radius: 6px; background-color: #FAFAFA;")
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        
        self.preview_grid = QGridLayout(self.scroll_content)
        self.preview_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.preview_grid.setSpacing(12)
        self.scroll_area.setWidget(self.scroll_content)
        detail_layout.addWidget(self.scroll_area, 2)  # Higher stretch priority
        
        # Log - Smaller
        self.log_text = QPlainTextEdit()
        self.log_text.setMaximumHeight(60)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("任务日志将在这里显示...")
        self.log_text.setStyleSheet("border: 1px solid #E4E7ED; background-color: #FDFDFD; color: #909399; font-size: 12px;")
        detail_layout.addWidget(self.log_text)
        
        right_layout.addWidget(detail_widget, 1)  # Stretch factor 1 - less priority than player
        content_layout.addWidget(right_container)
        main_layout.addLayout(content_layout)

    def setup_player(self):
        if HAS_MULTIMEDIA:
            self.audio_output = QAudioOutput()
            self.player = QMediaPlayer()
            self.player.setAudioOutput(self.audio_output)
            self.player.setVideoOutput(self.video_widget)
            # Handle playback end - seek to start to show first frame
            self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        else:
            if hasattr(self, 'video_widget'):
                 layout = self.video_widget.parentWidget().layout()
                 layout.removeWidget(self.video_widget)
                 self.video_widget.deleteLater()
            
            self.fallback_widget = QFrame()
            self.fallback_widget.setStyleSheet("background-color: #000000; border-top-left-radius: 8px; border-top-right-radius: 8px;")
            fb_layout = QVBoxLayout(self.fallback_widget)
            fb_layout.setAlignment(Qt.AlignCenter)
            
            icon = QLabel("⚠️")
            icon.setStyleSheet("font-size: 40px; background: transparent;")
            fb_layout.addWidget(icon)
            
            lbl = QLabel("预览组件缺失 (QtMultimedia)")
            lbl.setStyleSheet("color: white; font-weight: bold; font-size: 16px; background: transparent;")
            fb_layout.addWidget(lbl)
            
            sub = QLabel("您仍然可以处理视频，点击下方按钮调用系统播放器预览。")
            sub.setStyleSheet("color: #909399; margin-bottom: 20px; background: transparent;")
            fb_layout.addWidget(sub)
            
            btn = QPushButton("使用系统播放器播放")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("background-color: #409EFF; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
            btn.clicked.connect(self.play_external_preview)
            fb_layout.addWidget(btn)
            layout.addWidget(self.fallback_widget)
            
    def play_external_preview(self):
        if self.current_preview_path and os.path.exists(self.current_preview_path):
             QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_preview_path))
        else:
             QMessageBox.information(self, "提示", "请先选择一个视频文件")

    def apply_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 4)
        widget.setGraphicsEffect(shadow)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", self.config.get("last_folder"))
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder):
        self.path_edit.setText(folder)
        self.config.set("last_folder", folder)
        self.file_list.clear()
        self.files_map.clear()
        
        files = []
        try:
            for f in os.listdir(folder):
                if f.lower().endswith('.mp4'):
                    files.append(os.path.join(folder, f))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取目录: {e}")
            return
            
        for path in files:
            item = QListWidgetItem(self.file_list)
            item.setSizeHint(QSize(0, 70))
            widget = FileListItem(path)
            self.file_list.setItemWidget(item, widget)
            self.files_map[path] = widget
            
            # Check if this file is ALREADY processed and update status immediately
            vname = os.path.splitext(os.path.basename(path))[0]
            output_path = os.path.join(folder, "output", vname)
            if os.path.exists(output_path) and len(os.listdir(output_path)) > 0:
                 widget.set_status("✅ 已完成", "#67C23A") 
                 widget.state_icon.setStyleSheet("border-radius: 5px; background-color: #67C23A;")

    def set_list_checked(self, checked):
        for w in self.files_map.values():
            w.set_checked(checked)

    def invert_list_checked(self):
        for w in self.files_map.values():
            w.set_checked(not w.checkbox.isChecked())

    def on_item_clicked(self, item):
        widget = self.file_list.itemWidget(item)
        if widget:
            self.current_preview_path = widget.path
            # Update list visual state
            for i in range(self.file_list.count()):
                it = self.file_list.item(i)
                w = self.file_list.itemWidget(it)
                if it == item: w.set_active(True)
                else: w.set_active(False)
            
            # Play source video
            self.play_video(widget.path, "源视频")
            
            # ALWAYS clear results first, then load new ones
            self.clear_results()
            self.open_folder_btn.setVisible(False)
            
            # Calculate output folder for this specific video
            folder = os.path.dirname(widget.path)
            vname = os.path.splitext(os.path.basename(widget.path))[0]
            self.current_output_folder = os.path.join(folder, "output", vname)
            kf_dir = os.path.join(self.current_output_folder, "keyframes")
            
            # Load existing results if available
            if os.path.exists(kf_dir):
                kf_files = sorted([f for f in os.listdir(kf_dir) if f.endswith('.jpg')])
                if kf_files:
                    for kf in kf_files:
                        try:
                            scene_idx = kf.split('_')[-1].split('.')[0]
                            scene_num = int(scene_idx)
                            video_file = kf.replace('.jpg', '.mp4')
                            data = {
                                "type": "keyframe",
                                "scene_index": scene_num,
                                "image_path": os.path.join(kf_dir, kf),
                                "video_path": os.path.join(self.current_output_folder, video_file)
                            }
                            self.add_result_item(data)
                        except: pass
                    self.open_folder_btn.setVisible(True)

    def start_processing(self):
        tasks = []
        for w in self.files_map.values():
            if w.checkbox.isChecked():
                tasks.append(w.path)
                    
        if not tasks:
            QMessageBox.warning(self, "提示", "请先在列表中勾选需要处理的视频。")
            return
            
        output_dir = os.path.join(self.path_edit.text(), "output")
        
        self.toggle_ui(processing=True)
        self.clear_results()
        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.open_folder_btn.setVisible(True)
        
        for path in tasks:
            self.files_map[path].set_status("等待处理...")
            self.files_map[path].state_icon.setStyleSheet("border-radius: 4px; background-color: #E4E7ED;")
        
        # Pass extract_keyframes config
        config = {
            'files': tasks,
            'output_dir': output_dir,
            'extract_keyframes': self.check_keyframes.isChecked()
        }
        
        self.thread = QThread()
        self.worker = TransNetWorker(config)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.signals.finished.connect(self.on_finished)
        self.worker.signals.error.connect(self.on_error)
        self.worker.signals.log.connect(self.append_log)
        self.worker.signals.progress_total.connect(self.update_total_progress)
        self.worker.signals.result.connect(self.add_result_item)
        
        # Cleanup
        self.worker.signals.finished.connect(self.thread.quit)
        self.worker.signals.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.append_log("初始化处理引擎...")

    def stop_processing(self):
        if self.worker:
            self.worker.stop()
            self.append_log("正在停止...")
            self.stop_btn.setEnabled(False)

    def toggle_ui(self, processing):
        self.start_btn.setEnabled(not processing)
        self.browse_btn.setEnabled(not processing)
        self.stop_btn.setEnabled(processing)
        self.path_edit.setEnabled(not processing)

    def update_total_progress(self, current_idx, total):
        pct = int(current_idx / total * 100)
        self.progress_bar.setValue(pct)

    def append_log(self, text):
        if text.startswith("FINISH_SIGNAL:"):
             fname = text.split(":")[1]
             for w in self.files_map.values():
                 if os.path.basename(os.path.splitext(w.path)[0]) == fname:
                     w.set_status("✅ 已完成 (秒开)", "#67C23A")
                     w.state_icon.setStyleSheet("background-color: #67C23A;")
             return

        self.log_text.appendPlainText(text)
        if text.startswith("开始处理:"):
            try:
                fname = text.split(": ")[1].strip()
                for w in self.files_map.values():
                    if os.path.basename(os.path.splitext(w.path)[0]) == fname:
                        w.set_status("正在处理...", "#409EFF")
                        w.set_processing()
            except: pass

    def on_finished(self):
        self.toggle_ui(processing=False)
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "完成", "处理任务全部完成。")
        self.open_folder_btn.setVisible(True)

    def on_error(self, msg):
        self.toggle_ui(processing=False)
        QMessageBox.critical(self, "错误", msg)

    def clear_results(self):
         while self.preview_grid.count():
            item = self.preview_grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
         self.result_idx = 0

    def add_result_item(self, data):
         if data['type'] == 'keyframe':
            card = QFrame()
            card.setFixedSize(160, 130)
            card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 6px;
                    border: 1px solid #EBEEF5;
                }
                QFrame:hover {
                    border: 1px solid #409EFF;
                    background-color: #F2F6FC;
                }
            """)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(5,5,5,5)
            layout.setSpacing(5)
            
            img = QLabel()
            pix = None
            
            # First try pre-generated thumbnail
            if data.get('image_path') and os.path.exists(data['image_path']):
                pix = QPixmap(data['image_path'])
            
            # Fallback: extract first frame from video (slower)
            if (pix is None or pix.isNull()) and data.get('video_path') and os.path.exists(data['video_path']):
                try:
                    from moviepy import VideoFileClip
                    from PySide6.QtGui import QImage
                    clip = VideoFileClip(data['video_path'])
                    frame = clip.get_frame(0)
                    clip.close()
                    h, w, ch = frame.shape
                    bytes_per_line = ch * w
                    q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pix = QPixmap.fromImage(q_img)
                except:
                    pass
            
            if pix and not pix.isNull():
                img.setPixmap(pix.scaled(150, 85, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img.setText("无预览")
            img.setAlignment(Qt.AlignCenter)
            img.setStyleSheet("background: #F0F2F5; border-radius: 4px;")
            layout.addWidget(img)
            
            lbl = QLabel(f"场景 {data['scene_index']}")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("border:none; color: #606266; font-size: 12px;")
            layout.addWidget(lbl)
            
            btn = QPushButton(card)
            btn.setGeometry(0,0,160,130)
            btn.setStyleSheet("background: transparent; border: none;")
            btn.setCursor(Qt.PointingHandCursor)
            video_path = data['video_path']
            scene_idx = data['scene_index']
            btn.clicked.connect(lambda checked, p=video_path, s=scene_idx: self.play_video(p, f"场景 {s}"))
            
            # Dynamic column calculation based on scroll area width
            cols = max(1, (self.scroll_area.viewport().width() - 30) // 172)  # 160 card + 12 spacing
            row = self.result_idx // cols
            col = self.result_idx % cols
            self.preview_grid.addWidget(card, row, col)
            self.result_idx += 1

    def open_output_folder(self):
        # Open specific video output folder if available
        target = getattr(self, 'current_output_folder', None)
        if target and os.path.exists(target):
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))
        else:
            # Fallback to root output
            path = os.path.join(self.path_edit.text(), "output")
            if os.path.exists(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            else:
                QMessageBox.information(self, "提示", "输出目录不存在")

    def play_video(self, path, label=""):
        """Play video in internal player"""
        if HAS_MULTIMEDIA and self.player:
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
            if hasattr(self, 'player_status_lbl'):
                self.player_status_lbl.setText(f"正在播放: {label if label else os.path.basename(path)}")


    def toggle_play_pause(self):
        """Toggle play/pause state"""
        if HAS_MULTIMEDIA and self.player:
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.pause()
                self.play_pause_btn.setText("▶ 播放")
            else:
                self.player.play()
                self.play_pause_btn.setText("⏸ 暂停")

    def on_media_status_changed(self, status):
        """Handle media status changes - show first frame when video ends"""
        if HAS_MULTIMEDIA:
            if status == QMediaPlayer.EndOfMedia:
                # Video finished - seek to start to show first frame instead of black
                self.player.setPosition(0)
                self.player.pause()
                self.play_pause_btn.setText("▶ 播放")
                if hasattr(self, 'player_status_lbl'):
                    current_text = self.player_status_lbl.text()
                    if "正在播放" in current_text:
                        self.player_status_lbl.setText(current_text.replace("正在播放", "已播放完"))

    def merge_export_videos(self):
        """Copy all split videos to a single folder with sequential naming"""
        base_folder = self.path_edit.text()
        if not base_folder or not os.path.isdir(base_folder):
            QMessageBox.warning(self, "提示", "请先选择包含视频的文件夹")
            return
        
        output_root = os.path.join(base_folder, "output")
        if not os.path.exists(output_root):
            QMessageBox.warning(self, "提示", "未找到 output 文件夹，请先处理视频")
            return
        
        # Create merged folder
        merged_dir = os.path.join(output_root, "merged")
        os.makedirs(merged_dir, exist_ok=True)
        
        # Collect all scene mp4 files with their keyframe paths
        all_items = []  # (video_path, keyframe_path)
        for video_folder in sorted(os.listdir(output_root)):
            folder_path = os.path.join(output_root, video_folder)
            if os.path.isdir(folder_path) and video_folder != "merged":
                keyframes_folder = os.path.join(folder_path, "keyframes")
                scene_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.mp4')])
                for sf in scene_files:
                    video_path = os.path.join(folder_path, sf)
                    # Keyframe has same name but .jpg extension
                    kf_name = sf.replace('.mp4', '.jpg')
                    kf_path = os.path.join(keyframes_folder, kf_name) if os.path.exists(keyframes_folder) else ""
                    all_items.append((video_path, kf_path))
        
        if not all_items:
            QMessageBox.information(self, "提示", "未找到任何分割视频")
            return
        
        # Copy videos and existing keyframes (no re-extraction needed!)
        copied = 0
        thumb_dir = os.path.join(merged_dir, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)
        
        for idx, (src_video, src_keyframe) in enumerate(all_items, start=1):
            new_name = f"{idx:03d}.mp4"
            thumb_name = f"{idx:03d}.jpg"
            dst_path = os.path.join(merged_dir, new_name)
            thumb_path = os.path.join(thumb_dir, thumb_name)
            try:
                # Copy video
                shutil.copy2(src_video, dst_path)
                
                # Copy existing keyframe (fast!) instead of extracting
                if src_keyframe and os.path.exists(src_keyframe):
                    shutil.copy2(src_keyframe, thumb_path)
                
                copied += 1
            except Exception as e:
                self.append_log(f"复制失败: {src_video} -> {e}")
        
        QMessageBox.information(self, "合并完成", f"已将 {copied} 个视频和缩略图复制到:\n{merged_dir}")
        self.append_log(f"合并导出完成: {copied} 个文件 -> {merged_dir}")

    def view_merged_folder(self):
        """Show merged folder contents in preview grid"""
        base_folder = self.path_edit.text()
        if not base_folder:
            QMessageBox.warning(self, "提示", "请先选择文件夹")
            return
        
        merged_dir = os.path.join(base_folder, "output", "merged")
        if not os.path.exists(merged_dir):
            QMessageBox.information(self, "提示", "合并文件夹不存在，请先执行'合并导出'")
            return
        
        # Clear and load merged videos
        self.clear_results()
        self.current_output_folder = merged_dir
        self.open_folder_btn.setVisible(True)
        
        video_files = sorted([f for f in os.listdir(merged_dir) if f.endswith('.mp4')])
        if not video_files:
            QMessageBox.information(self, "提示", "合并文件夹为空")
            return
        
        # Update player status
        if hasattr(self, 'player_status_lbl'):
            self.player_status_lbl.setText("查看: 合并文件夹")
        
        thumb_dir = os.path.join(merged_dir, "thumbnails")
        
        # Add items with pre-generated thumbnails
        for vf in video_files:
            video_path = os.path.join(merged_dir, vf)
            idx_str = vf.replace('.mp4', '')
            thumb_path = os.path.join(thumb_dir, f"{idx_str}.jpg")
            try:
                idx_num = int(idx_str)
            except:
                idx_num = 0
            
            data = {
                "type": "keyframe",
                "scene_index": idx_num,
                "image_path": thumb_path if os.path.exists(thumb_path) else "",
                "video_path": video_path
            }
            self.add_result_item(data)
        
        self.append_log(f"正在浏览合并文件夹: {len(video_files)} 个视频")
