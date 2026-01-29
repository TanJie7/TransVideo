
import os
from moviepy.video.io.VideoFileClip import VideoFileClip
from transnetv2 import TransNetV2
import logging
import shutil

def get_next_available_name(base_name, output_folder):
    """
    在指定的输出文件夹中生成下一个可用的文件名，格式为 base_name-x-y-z.mp4
    """
    i = 1
    while True:
        # 构造新的文件名
        new_name = f"{base_name}-{i}-0-0.mp4"
        new_path = os.path.join(output_folder, new_name)
        # 检查文件是否存在
        if not os.path.exists(new_path):
            return new_name
        i += 1

def process_video(video_path, output_folder, type_name="video"):
    """
    处理视频并按类型保存
    """
    logger = logging.getLogger(__name__)
    
    # 使用绝对路径
    video_path = os.path.abspath(video_path)
    logger.info(f'开始处理视频: {video_path}')
    
    if not os.path.isfile(video_path):
        logger.error(f'无效的视频文件路径: {video_path}')
        return

    try:
        model = TransNetV2()
        # 在这里添加视频文件检查
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
        logger.info(f'开始处理视频文件: {video_path}')
        video_frames, single_frame_predictions, all_frame_predictions = model.predict_video_2(video_path)
        scenes = model.predictions_to_scenes(single_frame_predictions)
    except Exception as e:
        logger.error(f'视频处理或模型预测出错: {str(e)}')
        return

    try:
        video_clip = VideoFileClip(video_path)
        for i, (start, end) in enumerate(scenes):  # 处理所有分割片段
            start_time = start / video_clip.fps
            end_time = end / video_clip.fps
            segment_clip = video_clip.subclipped(start_time, end_time)
            # 用指定的类型名替换原有的视频名称，而不是用 video_name_without_ext
            base_name = f"{type_name}"
            new_name = get_next_available_name(base_name, output_folder)
            output_path = os.path.join(output_folder, new_name)
            segment_clip.write_videofile(output_path, codec='libx264', fps=video_clip.fps)
            logger.info(f'保存视频片段: {output_path}')
        video_clip.close()
    except Exception as e:
        logger.error(f'视频分割或保存出错: {e}')
        return

def copy_to_used_folder(video_path, used_folder):
    """
    将处理完的视频文件复制到 used 文件夹
    """
    logger = logging.getLogger(__name__)
    
    # 确保源文件存在
    if not os.path.isfile(video_path):
        logger.error(f'源文件不存在: {video_path}')
        return
        
    # 确保目标目录存在
    os.makedirs(used_folder, exist_ok=True)

    video_name = os.path.basename(video_path)
    used_path = os.path.join(used_folder, video_name)
    
    try:
        # 如果目标文件已存在，先删除
        if os.path.exists(used_path):
            os.remove(used_path)
            
        shutil.copy2(video_path, used_path)  # 使用copy2保留文件元数据
        logger.info(f'成功复制视频文件到: {used_path}')
    except Exception as e:
        logger.error(f'复制文件时出错: {str(e)}')

def main(directory, type_name='video'):
    logger = logging.getLogger(__name__)
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)
    
    # 使用绝对路径
    directory = os.path.abspath(directory)
    logger.info(f'处理目录: {directory}')
    
    if not os.path.isdir(directory):
        logger.error(f'无效的文件夹路径: {directory}')
        return

    # 检查目录中的视频文件
    video_files = []
    for file in os.listdir(directory):
        if file.endswith('.mp4'):
            full_path = os.path.join(directory, file)
            if os.path.isfile(full_path):
                video_files.append(file)
    
    logger.info(f'找到的视频文件: {video_files}')
    
    if not video_files:
        logger.warning(f'目录中没有找到.mp4文件: {directory}')
        return

    output_folder = os.path.join(directory, 'output')
    used_folder = os.path.join(directory, 'used')
    
    # 确保输出目录存在
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(used_folder, exist_ok=True)

    for file in video_files:
        video_path = os.path.join(directory, file)
        # 在处理之前验证文件是否存在
        if os.path.isfile(video_path):
            logger.info(f'开始处理文件: {video_path}')
            process_video(video_path, output_folder, type_name)
            copy_to_used_folder(video_path, used_folder)
        else:
            logger.error(f'文件不存在: {video_path}')

    input('\n任务已完成，按回车键退出……')


def main2(directory, type_name='video'):
    # 读取主文件夹，循环处理子文件夹
    for sub_dir in os.listdir(directory):
        sub_dir_path = os.path.join(directory, sub_dir)
        if os.path.isdir(sub_dir_path):
            main(sub_dir_path, type_name)

if __name__ == '__main__':
    # 使用原始的反斜杠路径
    directory = os.path.abspath("Data/作品")
    type_name = '测试'
    main(directory, type_name)

