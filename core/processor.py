
import os
import sys
import logging
import threading
import time
import shutil
import math
import numpy as np
from PySide6.QtCore import QObject, Signal, QThread
from moviepy import VideoFileClip
import moviepy.video.fx as vfx

# Import TransNetV2 from root
# Assuming main_gui.py adds root to sys.path or is run from root
try:
    from transnetv2 import TransNetV2
except ImportError:
    # Fallback if run directly or paths issue
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from transnetv2 import TransNetV2

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    finished = Signal()
    error = Signal(str)
    result = Signal(object)
    progress_total = Signal(int, int) # current, total
    progress_video = Signal(int) # 0-100 percentage
    log = Signal(str)

class TransNetWorker(QObject):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.signals = WorkerSignals()
        self.is_interrupted = False
        self.model = None

    def stop(self):
        self.is_interrupted = True

    def run(self):
        try:
            files = self.config.get('files', [])
            output_root = self.config.get('output_dir')
            extract_keyframes = self.config.get('extract_keyframes', True)

            total_files = len(files)
            
            # Pre-filter files to see what actually needs processing
            # This avoids loading the model if everything is already done
            to_process = []
            
            for idx, video_path in enumerate(files):
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                video_output_dir = os.path.join(output_root, video_name)
                keyframes_dir = os.path.join(video_output_dir, "keyframes")
                
                # Check if this video seems "done"
                # Heuristic: Keyframes directory exists and is not empty (if check_keyframes is on)
                # Or just video dir exists and has mp4 files
                is_done = False
                if os.path.exists(video_output_dir):
                    scene_files = [f for f in os.listdir(video_output_dir) if f.endswith('.mp4')]
                    if len(scene_files) > 0:
                        is_done = True
                
                if is_done:
                    self.signals.log.emit(f"检测到已处理: {video_name}，跳过AI分析")
                    self.signals.progress_total.emit(idx + 1, total_files)
                    
                    # Emit results for existing files so they show up in UI
                    if extract_keyframes and os.path.exists(keyframes_dir):
                        kf_files = sorted([f for f in os.listdir(keyframes_dir) if f.endswith('.jpg')])
                        for kf in kf_files:
                            scene_idx = kf.split('_')[-1].split('.')[0] # 1_scene_001.jpg -> 001
                            try:
                                scene_num = int(scene_idx)
                                video_file = kf.replace('.jpg', '.mp4')
                                self.signals.result.emit({
                                    "type": "keyframe",
                                    "video": video_name,
                                    "scene_index": scene_num,
                                    "image_path": os.path.join(keyframes_dir, kf),
                                    "video_path": os.path.join(video_output_dir, video_file)
                                })
                            except: pass
                    
                    # Also notify list item to turn green
                    self.signals.log.emit(f"FINISH_SIGNAL:{video_name}") 
                    continue

                to_process.append((idx, video_path))

            if not to_process:
                self.signals.log.emit("所有文件均已存在结果，无需重复处理。")
                self.signals.finished.emit()
                return

            self.signals.log.emit("正在加载AI模型 (TransNetV2)...")
            # Only load model if we have work
            if self.model is None:
                self.model = TransNetV2()
            
            for idx, video_path in to_process:
                if self.is_interrupted:
                    self.signals.log.emit("任务已中断")
                    break
                
                self.process_single_video(video_path, output_root, extract_keyframes)
                # Emit progress AFTER completion, not before
                self.signals.progress_total.emit(idx + 1, total_files)
            
            self.signals.log.emit("所有任务完成")
            self.signals.finished.emit()
            
        except Exception as e:
            import traceback
            err_msg = f"发生未捕获异常: {str(e)}\n{traceback.format_exc()}"
            self.signals.error.emit(err_msg)
            
        except Exception as e:
            import traceback
            err_msg = f"发生未捕获异常: {str(e)}\n{traceback.format_exc()}"
            self.signals.error.emit(err_msg)

    def process_single_video(self, video_path, output_root, extract_keyframes):
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        self.signals.log.emit(f"开始处理: {video_name}")
        
        # Create output structure
        # Output/VideoName/
        video_output_dir = os.path.join(output_root, video_name)
        keyframes_dir = os.path.join(video_output_dir, "keyframes")
        
        os.makedirs(video_output_dir, exist_ok=True)
        if extract_keyframes:
            os.makedirs(keyframes_dir, exist_ok=True)

        try:
            # 1. Predict scenes
            self.signals.log.emit(f"正在分析场景: {video_name} ...")
            # Predict takes time, we can't easily get specialized progress from it without patching TransNetV2 more
            # but we can assume it takes 50% of work
            self.signals.progress_video.emit(10)
            
            video_frames, single_frame_predictions, all_frame_predictions = self.model.predict_video_2(video_path)
            scenes = self.model.predictions_to_scenes(single_frame_predictions)
            
            self.signals.progress_video.emit(50)
            self.signals.log.emit(f"场景分析完成，共识别出 {len(scenes)} 个场景")

            # 2. Split and Save
            clip = VideoFileClip(video_path)
            # Fix: Ensure logic uses original clip or handles resize? 
            # predict_video_2 in transnetv2.py uses a resized clip for PREDICTION.
            # But the 'scenes' start/end are frame indices of the RESIZED clip (fps might be same?).
            # TransNetV2 predict_video_2 implementation:
            # It loads clip, resizes it.
            # fps = clip.fps
            # frames loop...
            # The 'scenes' returned are frame indices.
            # Since we want to cut the ORIGINAL video, we use the original clip here.
            # We assume frame indices map 1:1 if FPS is same.
            
            total_scenes = len(scenes)
            
            for i, (start_frame, end_frame) in enumerate(scenes):
                if self.is_interrupted:
                    break
                
                # Convert frames to time
                # Note: predict_video_2 uses clip.fps of the resized clip which should preserve original FPS usually
                # But let's be safe. TransNetV2 code: `fps = clip.fps`.
                
                fps = clip.fps
                start_time = start_frame / fps
                end_time = end_frame / fps
                
                scene_idx = i + 1
                scene_name = f"{video_name}_scene_{scene_idx:03d}"
                scene_filename = f"{scene_name}.mp4"
                scene_path = os.path.join(video_output_dir, scene_filename)
                
                # Check if exists (Resume capability)
                if os.path.exists(scene_path):
                    self.signals.log.emit(f"跳过已存在: {scene_filename}")
                else:
                    self.signals.log.emit(f"导出片段 {scene_idx}/{total_scenes}: {scene_filename}")
                    # subclip -> subclipped (v2)
                    sub = clip.subclipped(start_time, end_time)
                    sub.write_videofile(
                        scene_path, 
                        codec='libx264', 
                        audio_codec='aac', 
                        logger=None, # Disable internal logger to avoid spam
                        fps=fps
                        # threads=4 # Optional optimization
                    )
                
                # Keyframe extraction
                if extract_keyframes:
                    kf_filename = f"{scene_name}.jpg"
                    kf_path = os.path.join(keyframes_dir, kf_filename)
                    if not os.path.exists(kf_path):
                        # Extract first frame instead of middle
                        try:
                            clip.save_frame(kf_path, t=start_time)
                            # Emit result for preview
                            self.signals.result.emit({
                                "type": "keyframe",
                                "video": video_name,
                                "scene_index": scene_idx,
                                "image_path": kf_path,
                                "video_path": scene_path
                            })
                        except Exception as e:
                            self.signals.log.emit(f"关键帧提取失败 {scene_name}: {e}")

                # Update progress
                # 50% to 100% mapping
                current_progress = 50 + int((i + 1) / total_scenes * 50)
                self.signals.progress_video.emit(current_progress)

            clip.close()
            self.signals.progress_video.emit(100)
            
        except Exception as e:
            self.signals.log.emit(f"处理视频 {video_name} 失败: {str(e)}")
            raise e
