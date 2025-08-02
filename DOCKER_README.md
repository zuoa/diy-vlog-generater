# Docker部署说明

## 快速启动

在 `src/video_process/` 目录下运行：

```bash
docker-compose up -d
```

## 访问服务

- Web界面: http://localhost:8000
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 停止服务

```bash
docker-compose down
```

## 查看日志

```bash
docker-compose logs -f
```

## 配置说明

- **基础镜像**: python:3.10.15
- **端口映射**: 8000:8000
- **数据卷映射**: /data/wch/VideoProcess → /data
- **自动重启**: 容器异常退出时自动重启
- **FFmpeg**: 自动安装在容器中

## 注意事项

1. 确保宿主机的 `/data/wch/VideoProcess` 目录存在
2. 容器会自动安装FFmpeg和Python依赖
3. 生成的视频和二维码文件存储在容器内的 `/app/static` 和 `/app/output` 目录