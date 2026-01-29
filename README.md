# TransVideo 视频智能分割工具

基于 TransNetV2 AI 模型的视频场景智能分割桌面应用，支持批量处理和图形化操作。

## ✨ 功能特点

- **批量处理**: 一键处理整个文件夹的视频
- **智能场景检测**: 使用 TransNetV2 深度学习模型精准识别场景边界
- **关键帧提取**: 自动提取每个场景的第一帧作为缩略图
- **内置视频预览**: 直接在应用内播放源视频和分割片段
- **断点续传**: 支持中断后继续处理，自动跳过已完成的视频
- **合并导出**: 将所有分割片段合并到一个文件夹，顺序重命名 (001.mp4, 002.mp4...)
- **现代 UI**: Element Plus 风格的清爽界面

## 📋 环境要求

- Python 3.9+
- FFmpeg (系统级安装)
- NVIDIA GPU (可选，用于加速 TensorFlow)

## 🚀 安装步骤

### 1. 创建 Conda 环境

```bash
# 创建新的 conda 环境
conda create -n transvideo python=3.10 -y

# 激活环境
conda activate transvideo
```

### 2. 安装 FFmpeg

**Windows (使用 Chocolatey):**
```bash
choco install ffmpeg
```

**Windows (手动安装):**
1. 从 https://ffmpeg.org/download.html 下载
2. 解压到如 `C:\ffmpeg`
3. 添加 `C:\ffmpeg\bin` 到系统 PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 3. 安装 Python 依赖

```bash
# 进入项目目录
cd TransVideo

# 安装依赖
pip install -r requirements.txt
```

### 4. 下载模型权重

模型权重文件已上传至百度网盘：

> **百度网盘下载链接**: [请在此处填写链接]
> 
> **提取码**: [请在此处填写]

下载后，将压缩包解压到项目根目录，确保文件结构如下：

```
TransVideo/
├── transnetv2-weights/          ← 解压后的模型文件夹
│   ├── saved_model.pb
│   ├── variables/
│   └── ...
├── main_gui.py
├── main_window.py
└── ...
```

## 📖 使用方法

### 启动应用

```bash
# 确保已激活 conda 环境
conda activate transvideo

# 运行 GUI
python main_gui.py
```

### 操作流程

1. **选择文件夹**: 点击"浏览文件夹"，选择包含视频的目录
2. **勾选视频**: 在左侧列表中勾选要处理的视频（支持全选/反选）
3. **开始处理**: 点击"▶ 智能分割"按钮
4. **查看结果**: 
   - 点击左侧列表项可预览源视频和已处理的场景
   - 点击预览卡片可播放对应的分割片段
5. **合并导出**: 点击"📦 合并导出"将所有片段复制到统一文件夹
6. **查看合并**: 点击"👁 查看合并"浏览合并后的文件

## 📁 输出结构

```
视频源文件夹/
└── output/
    ├── 视频1/
    │   ├── 视频1_scene_001.mp4
    │   ├── 视频1_scene_002.mp4
    │   └── keyframes/
    │       ├── 视频1_scene_001.jpg
    │       └── 视频1_scene_002.jpg
    ├── 视频2/
    │   └── ...
    └── merged/                    # 合并导出后生成
        ├── 001.mp4
        ├── 002.mp4
        ├── 003.mp4
        └── thumbnails/
            ├── 001.jpg
            ├── 002.jpg
            └── 003.jpg
```

## ⚠️ 常见问题

### DLL load failed 错误
如果遇到 DLL 加载错误，请重新创建干净的 conda 环境：
```bash
conda deactivate
conda remove -n transvideo --all
conda create -n transvideo python=3.10 -y
conda activate transvideo
pip install -r requirements.txt
```

### 视频预览黑屏
确保已正确安装 PySide6 的多媒体组件。如果仍有问题，将使用系统播放器作为回退。

### 处理速度慢
- 确保安装了 GPU 版本的 TensorFlow
- 使用 `pip install tensorflow[and-cuda]` 安装 GPU 支持

## 📝 技术栈

- **AI 模型**: TransNetV2 (TensorFlow)
- **视频处理**: MoviePy 2.x + FFmpeg
- **GUI 框架**: PySide6 (Qt6)
- **图像处理**: Pillow, NumPy

## 📄 许可证

MIT License
