# 视频处理工具 - Flask版本

## 项目结构说明

项目已重构为分离的架构：

- `app.py` - Flask Web应用，包含所有Web界面和API接口
- `video_process.py` - 核心业务逻辑，包含视频处理和二维码生成功能
- `requirements.txt` - 项目依赖

## 功能特性

- 两个视频拼接处理
- Maozibi画中画效果
- Maobizi Score（带分数显示的画中画）
- 单个视频上传
- 图片上传
- 二维码生成
- 实时处理状态查看

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 确保FFmpeg已安装

确保系统中已安装FFmpeg：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS (使用Homebrew)
brew install ffmpeg

# Windows
# 下载FFmpeg并添加到PATH环境变量
```

### 3. 准备音乐文件

确保项目根目录下有以下音乐文件：
- `jiggy boogy.mp3` - 用于普通视频处理
- `jiggy boogy2.mp3` - 用于maozibi功能

### 4. 运行Flask应用

```bash
python app.py
```

应用将在以下地址启动：
- 本地访问：http://localhost:5000
- 网络访问：http://0.0.0.0:5000（Docker环境）

### 5. 访问应用

打开浏览器访问 http://localhost:5000 即可使用Web界面。

## API接口

应用提供以下主要接口：

- `GET /` - 主页面
- `POST /process-videos-web` - 两个视频处理
- `POST /maozibi-web` - Maozibi画中画
- `POST /maobizi_score-web` - Maobizi Score
- `POST /process-single-video-web` - 单个视频上传
- `POST /maozibi_img-web` - 图片上传
- `GET /status/<task_id>` - 查看处理状态
- `GET /api/status/<task_id>` - 获取状态JSON
- `GET /output/<filename>` - 下载文件
- `GET /health` - 系统健康检查

## 与原FastAPI版本的区别

1. **框架变更**：从FastAPI改为Flask
2. **异步处理**：使用线程池代替FastAPI的后台任务
3. **文件上传**：使用Flask的request.files代替FastAPI的UploadFile
4. **模板系统**：直接返回HTML字符串，未使用模板引擎
5. **端口变更**：默认端口从8000改为5000

## 开发和部署

### 开发模式

```bash
python app.py
```

### 生产模式

使用Gunicorn等WSGI服务器：

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker部署

可以继续使用现有的Docker配置，只需要修改启动命令为：

```dockerfile
CMD ["python", "app.py"]
```

## 注意事项

1. Flask应用默认是单线程的，大文件上传可能需要调整配置
2. 后台任务使用线程池，可以通过修改`ThreadPoolExecutor(max_workers=4)`来调整并发数
3. 文件上传大小限制为500MB，可通过`app.config['MAX_CONTENT_LENGTH']`调整
4. 确保有足够的磁盘空间用于临时文件存储
5. 生产环境建议使用反向代理（如Nginx）

## 故障排除

### FFmpeg相关问题

如果出现FFmpeg错误，请检查：
1. FFmpeg是否正确安装
2. FFmpeg是否在系统PATH中
3. 访问 `/health` 接口查看FFmpeg状态

### 文件上传问题

如果文件上传失败：
1. 检查文件大小是否超过限制
2. 检查磁盘空间是否充足
3. 确认文件格式是否支持

### 性能优化

对于高并发场景：
1. 增加线程池大小
2. 使用更强的服务器硬件
3. 考虑使用Redis等缓存系统存储任务状态