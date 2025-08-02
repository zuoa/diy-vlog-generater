# -*- coding: utf-8 -*-
"""
Flask Web应用 - 视频处理工具
从video_process.py拆分出来的Web界面部分
"""

import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file, abort

from database import TaskStatus, create_tables
from utils import success
# 导入视频处理相关的类
from video_process import VideoProcessor
from video_processor import VideoProcessor as VP

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

APP_HOST = os.getenv("APP_HOST", "http://127.0.0.1:5003")

# 配置目录
STATIC_DIR = Path(__file__).parent / "static"
OUTPUT_DIR = Path(__file__).parent / "output"
STATIC_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 线程池执行器用于后台任务
executor = ThreadPoolExecutor(max_workers=4)


def process_videos_background(task_id: str, video1_path: str, video2_path: str, beat_times: list = None):
    """后台处理两个视频的函数"""
    try:
        # 更新任务状态为处理中
        TaskStatus.update_task_status(task_id, status="processing", message="正在处理视频...", progress=20)

        processor = VP()

        output_filename = f"processed_video_{task_id}.mp4"
        output_filepath = f"output/processed_video_{task_id}.mp4"
        # 生成视频访问URL
        video_url = f"/output/{output_filename}"

        TaskStatus.update_task_status(task_id, progress=40, message="正在分析视频...")
        if beat_times is None:
            beat_times = [1, 2, 3, 4, 5, 6]
        processor.create_beat_video(
            video1_path=video1_path,
            video2_path=video2_path,
            beat_times=beat_times,
            output_path=output_filepath,
            speed_factor=5,  # 第二个视频1.5倍速播放
            font_size=120,  # 时间显示字体大小
            background_music_path="jiggy boogy.mp3"  # 使用默认背景音乐 jiggy boogy.mp3，或指定其他音乐文件路径
        )

        TaskStatus.update_task_status(task_id, progress=80, message="正在生成最终文件...")

        # 更新任务状态为完成
        TaskStatus.update_task_status(task_id,
                                      status="completed",
                                      message="视频处理完成",
                                      progress=100,
                                      video_filename=output_filename,
                                      video_url=video_url,
                                      completed_at=datetime.now())

        # 清理临时文件
        os.remove(video1_path)
        os.remove(video2_path)
        del processor

    except Exception as e:
        TaskStatus.update_task_status(task_id, status="error", message=f"处理失败: {str(e)}", progress=0)
        # 清理临时文件
        if os.path.exists(video1_path):
            os.remove(video1_path)
        if os.path.exists(video2_path):
            os.remove(video2_path)


def process_maozibi_background(task_id: str, video0_path: str, video1_path: str):
    """后台处理maozibi视频的函数"""
    try:
        # 更新任务状态为处理中
        TaskStatus.update_task_status(task_id, status="processing", message="正在处理maozibi视频...", progress=20)

        processor = VideoProcessor()

        # 检查ffmpeg
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if not loop.run_until_complete(processor.check_ffmpeg()):
            TaskStatus.update_task_status(task_id, status="error", message="FFmpeg未安装或不可用")
            return

        TaskStatus.update_task_status(task_id, progress=40, message="正在分析视频...")

        # 读取视频数据
        with open(video0_path, 'rb') as f:
            video0_data = f.read()
        with open(video1_path, 'rb') as f:
            video1_data = f.read()

        # 处理视频
        output_path, output_filename = loop.run_until_complete(
            processor.process_maozibi_videos(video0_data, video1_data)
        )

        TaskStatus.update_task_status(task_id, progress=80, message="正在生成最终文件...")

        # 生成视频访问URL
        video_url = f"http://8.215.28.241:721/output/{output_filename}"

        # 更新任务状态为完成
        TaskStatus.update_task_status(task_id,
                                      status="completed",
                                      message="maozibi视频处理完成",
                                      progress=100,
                                      video_filename=output_filename,
                                      video_url=video_url,
                                      completed_at=datetime.now())

        # 清理临时文件
        os.remove(video0_path)
        os.remove(video1_path)
        del processor
        loop.close()

    except Exception as e:
        TaskStatus.update_task_status(task_id, status="error", message=f"处理失败: {str(e)}", progress=0)
        # 清理临时文件
        if os.path.exists(video0_path):
            os.remove(video0_path)
        if os.path.exists(video1_path):
            os.remove(video1_path)


def process_maozibi_score_background(task_id: str, video0_path: str, video1_path: str, score: str):
    """后台处理maozibi_score视频的函数"""
    try:
        # 更新任务状态为处理中
        TaskStatus.update_task_status(task_id, status="processing", message="正在处理maozibi_score视频...", progress=20)

        processor = VideoProcessor()

        # 检查ffmpeg
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if not loop.run_until_complete(processor.check_ffmpeg()):
            TaskStatus.update_task_status(task_id, status="error", message="FFmpeg未安装或不可用")
            return

        TaskStatus.update_task_status(task_id, progress=40, message="正在分析视频...")

        # 读取视频数据
        with open(video0_path, 'rb') as f:
            video0_data = f.read()
        with open(video1_path, 'rb') as f:
            video1_data = f.read()

        # 处理视频
        output_path, output_filename = loop.run_until_complete(
            processor.process_maozibi_score_videos(video0_data, video1_data, score)
        )

        TaskStatus.update_task_status(task_id, progress=80, message="正在生成最终文件...")

        # 生成视频访问URL
        video_url = f"http://8.215.28.241:721/output/{output_filename}"

        # 更新任务状态为完成
        TaskStatus.update_task_status(task_id,
                                      status="completed",
                                      message="maozibi_score视频处理完成",
                                      progress=100,
                                      video_filename=output_filename,
                                      video_url=video_url,
                                      completed_at=datetime.now())

        # 清理临时文件
        os.remove(video0_path)
        os.remove(video1_path)
        del processor
        loop.close()

    except Exception as e:
        TaskStatus.update_task_status(task_id, status="error", message=f"处理失败: {str(e)}", progress=0)
        # 清理临时文件
        if os.path.exists(video0_path):
            os.remove(video0_path)
        if os.path.exists(video1_path):
            os.remove(video1_path)


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/process-videos-web', methods=['POST'])
def process_videos_web():
    """处理两个视频文件 - Web界面版本"""
    # 检查文件
    if 'video1' not in request.files or 'video2' not in request.files:
        abort(400, "缺少视频文件")

    beat_times = request.form.get('times')

    video1 = request.files['video1']
    video2 = request.files['video2']

    if video1.filename == '' or video2.filename == '':
        abort(400, "请选择视频文件")

    # 检查文件类型
    if not video1.content_type.startswith('video/'):
        abort(400, "第一个文件不是视频格式")
    if not video2.content_type.startswith('video/'):
        abort(400, "第二个文件不是视频格式")

    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 初始化任务状态
    TaskStatus.create_task_status(task_id,
                                  status="pending",
                                  message="任务已创建，准备处理...",
                                  progress=0)

    # 保存临时文件
    temp_dir = tempfile.mkdtemp()
    video1_path = os.path.join(temp_dir, f"video1_{task_id}.mp4")
    video2_path = os.path.join(temp_dir, f"video2_{task_id}.mp4")

    video1.save(video1_path)
    video2.save(video2_path)

    # 生成状态页面URL
    status_url = f"{APP_HOST}/status/{task_id}"

    # 启动后台任务
    executor.submit(process_videos_background, task_id, video1_path, video2_path, beat_times)

    task_data = TaskStatus.get_task_status(task_id)
    return success({
        "task_id": task_id,
        "status_url": status_url,
        "api_status_url": status_url,
        "created_at": task_data["created_at"]
    })


@app.route('/maozibi-web', methods=['POST'])
def maozibi_web():
    """处理两个视频文件，创建maozibi画中画效果 - Web界面版本"""
    # 检查文件
    if 'video0' not in request.files or 'video1' not in request.files:
        abort(400, "缺少视频文件")

    video0 = request.files['video0']
    video1 = request.files['video1']

    if video0.filename == '' or video1.filename == '':
        abort(400, "请选择视频文件")

    # 检查文件类型
    if not video0.content_type.startswith('video/'):
        abort(400, "video0必须是视频文件")
    if not video1.content_type.startswith('video/'):
        abort(400, "video1必须是视频文件")

    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 初始化任务状态
    TaskStatus.create_task_status(task_id,
                                  status="pending",
                                  message="任务已创建，等待处理...",
                                  progress=0)

    # 保存临时文件
    temp_dir = tempfile.mkdtemp()
    video0_path = os.path.join(temp_dir, f"video0_{task_id}.mp4")
    video1_path = os.path.join(temp_dir, f"video1_{task_id}.mp4")

    video0.save(video0_path)
    video1.save(video1_path)

    # 生成二维码URL（指向任务状态页面）
    status_url = f"http://8.215.28.241:721/status/{task_id}"

    # 更新任务状态，包含状态页面URL
    TaskStatus.update_task_status(task_id, status_url=status_url)

    # 启动后台任务
    executor.submit(process_maozibi_background, task_id, video0_path, video1_path)

    # 重定向到状态页面
    return redirect(url_for('get_task_status_page', task_id=task_id))


@app.route('/maobizi_score-web', methods=['POST'])
def maobizi_score_web():
    """处理两个视频文件和分数 - Web界面版本"""
    # 检查文件
    if 'video0' not in request.files or 'video1' not in request.files:
        abort(400, "缺少视频文件")

    video0 = request.files['video0']
    video1 = request.files['video1']
    score = request.form.get('score', '')

    if video0.filename == '' or video1.filename == '':
        abort(400, "请选择视频文件")

    if not score.strip():
        abort(400, "请输入分数")

    # 检查文件类型
    if not video0.content_type.startswith('video/'):
        abort(400, "video0必须是视频文件")
    if not video1.content_type.startswith('video/'):
        abort(400, "video1必须是视频文件")

    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 初始化任务状态
    TaskStatus.create_task_status(task_id,
                                  status="pending",
                                  message="任务已创建，等待处理...",
                                  progress=0)

    # 保存临时文件
    temp_dir = tempfile.mkdtemp()
    video0_path = os.path.join(temp_dir, f"video0_{task_id}.mp4")
    video1_path = os.path.join(temp_dir, f"video1_{task_id}.mp4")

    video0.save(video0_path)
    video1.save(video1_path)

    # 生成二维码URL（指向任务状态页面）  
    status_url = f"http://8.215.28.241:721/status/{task_id}"

    # 更新任务状态，包含状态页面URL
    TaskStatus.update_task_status(task_id, status_url=status_url)

    # 启动后台任务
    executor.submit(process_maozibi_score_background, task_id, video0_path, video1_path, score)

    # 重定向到状态页面
    return redirect(url_for('get_task_status_page', task_id=task_id))


@app.route('/process-single-video-web', methods=['POST'])
def process_single_video_web():
    """处理单个视频上传 - Web界面版本"""
    # 检查文件
    if 'video' not in request.files:
        abort(400, "缺少视频文件")

    video = request.files['video']

    if video.filename == '':
        abort(400, "请选择视频文件")

    # 检查文件类型
    if not video.content_type.startswith('video/'):
        abort(400, "上传的文件必须是视频格式")

    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 获取文件扩展名
    file_extension = video.filename.split('.')[-1] if '.' in video.filename else 'mp4'
    video_filename = f"single_video_{task_id}.{file_extension}"
    video_path = OUTPUT_DIR / video_filename

    # 保存视频文件
    video.save(str(video_path))

    # 生成视频访问URL
    video_url = f"http://8.215.28.241:721/output/{video_filename}"

    # 构建结果对象，用于HTML模板
    result = {
        "task_id": task_id,
        "video_url": video_url
    }

    # 返回模板响应
    return render_template('single_video_result.html', result=result)


@app.route('/maozibi_img-web', methods=['POST'])
def maozibi_img_web():
    if 'image' not in request.files:
        abort(400, "缺少上传的图片文件")

    image = request.files['image']

    if not image.mimetype.startswith('image/'):
        abort(400, "上传的文件必须是图片格式")

    task_id = str(uuid.uuid4())

    file_extension = image.filename.rsplit('.', 1)[-1] if '.' in image.filename else 'jpg'
    image_filename = f"maozibi_img_{task_id}.{file_extension}"
    image_path = OUTPUT_DIR / image_filename

    try:
        image_data = image.read()

        if not image_data:
            abort(400, "图片文件数据为空")

        with open(image_path, 'wb') as f:
            f.write(image_data)

        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            abort(500, "图片文件保存失败")

        print(f"图片保存成功: {image_path}, 大小: {len(image_data)} bytes")

        image_url = f"{APP_HOST}/output/{image_filename}"

        TaskStatus.update_task_status(task_id, **{"status": "completed",
            "message": "图片上传并处理完成",
            "progress": 100,
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "image_filename": image_filename,})

        return success({
            "task_id": task_id,
            "message": "图片上传成功，二维码已生成",
            "status": "completed",
            "image_url": image_url,
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        })

    except Exception as e:
        if os.path.exists(image_path):
            os.remove(image_path)
        abort(500, f"处理失败: {str(e)}")


@app.route('/status/<task_id>', methods=['GET', 'POST'])
def get_task_status_page(task_id):
    """获取任务状态页面"""
    if not TaskStatus.task_exists(task_id):
        abort(404, "任务不存在")

    task = TaskStatus.get_task_status(task_id)
    if request.method == 'POST':
        return success(task)
    else:
        return render_template('status.html', task=task, task_id=task_id)


@app.route('/output/<filename>')
def get_output_file(filename):
    """获取输出文件（视频、二维码等）"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        abort(404, "文件不存在")
    return send_file(str(file_path))


@app.route('/health')
def health_check():
    """健康检查"""
    import asyncio
    import subprocess

    processor = VideoProcessor()

    # 检查FFmpeg
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ffmpeg_available = loop.run_until_complete(processor.check_ffmpeg())

    # 获取FFmpeg版本信息
    ffmpeg_version = "未知"
    if ffmpeg_available:
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # 提取版本信息的第一行
                ffmpeg_version = result.stdout.split('\n')[0]
        except:
            pass

    del processor
    loop.close()

    return jsonify({
        "status": "healthy",
        "ffmpeg_available": ffmpeg_available,
        "ffmpeg_version": ffmpeg_version,
        "output_dir": str(OUTPUT_DIR),
        "is_docker": os.path.exists('/.dockerenv'),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "active_tasks": TaskStatus.select().count()
    })


@app.route('/favicon.ico')
def favicon():
    """返回favicon，避免404错误"""
    return '', 204


if __name__ == '__main__':
    print("启动Flask视频处理Web应用...")
    print("访问 http://localhost:5000 查看Web界面")
    print("访问 http://localhost:5000/health 查看系统状态")
    create_tables()
    # 检查是否在Docker环境中运行
    is_docker = os.path.exists('/.dockerenv')

    if is_docker:
        app.run(host='0.0.0.0', port=5003, debug=False)
    else:
        app.run(host='127.0.0.1', port=5003, debug=True)
