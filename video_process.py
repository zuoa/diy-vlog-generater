# -*- coding: utf-8 -*-
"""
视频处理核心模块
包含视频处理和二维码生成的核心业务逻辑
"""

import os
import uuid
import tempfile
import shutil
from pathlib import Path
import asyncio
import subprocess

import ffmpeg
import qrcode


class VideoProcessor:
    """视频处理类"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def __del__(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def check_ffmpeg(self) -> bool:
        """检查ffmpeg是否可用"""
        try:
            ffmpeg_paths = ['ffmpeg', '/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']
            
            for ffmpeg_path in ffmpeg_paths:
                try:
                    result = subprocess.run([ffmpeg_path, '-version'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"FFmpeg found at: {ffmpeg_path}")
                        return True
                except FileNotFoundError:
                    continue
            
            print("FFmpeg paths checked:", ffmpeg_paths)
            return False
            
        except subprocess.TimeoutExpired:
            print("FFmpeg check timed out")
            return False
        except Exception as e:
            print(f"FFmpeg check error: {e}")
            return False
    
    async def get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            raise Exception(f"无法获取视频时长: {str(e)}")
    
    async def extract_video_segment(self, input_path: str, output_path: str, 
                                  start_time: float, duration: float) -> bool:
        """提取视频片段"""
        try:
            (
                ffmpeg
                .input(input_path, ss=start_time, t=duration, accurate_seek=None)
                .output(output_path, 
                       vcodec='libx264', 
                       acodec='aac',
                       **{
                           'avoid_negative_ts': 'make_zero',
                           'fflags': '+genpts',
                           'preset': 'medium',
                           'crf': '18',
                           'pix_fmt': 'yuv420p',
                           'movflags': '+faststart'
                       })
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except Exception as e:
            raise Exception(f"视频片段提取失败: {str(e)}")
    
    async def concatenate_videos(self, video1_path: str, video2_path: str, 
                               output_path: str) -> bool:
        """拼接两个视频"""
        try:
            concat_file = os.path.join(self.temp_dir, "concat_list.txt")
            with open(concat_file, 'w', encoding='utf-8') as f:
                f.write(f"file '{video1_path}'\n")
                f.write(f"file '{video2_path}'\n")
            
            (
                ffmpeg
                .input(concat_file, format='concat', safe=0)
                .output(output_path, 
                       vcodec='libx264', 
                       acodec='aac',
                       **{
                           'avoid_negative_ts': 'make_zero',
                           'fflags': '+genpts',
                           'preset': 'medium',
                           'crf': '18',
                           'pix_fmt': 'yuv420p',
                           'movflags': '+faststart'
                       })
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except Exception as e:
            raise Exception(f"视频拼接失败: {str(e)}")
    
    async def add_background_music(self, input_path: str, output_path: str) -> bool:
        """为视频添加背景音乐"""
        try:
            music_path = str(Path(__file__).parent / "jiggy boogy.mp3")
            video = ffmpeg.input(input_path)
            audio = ffmpeg.input(music_path, stream_loop='-1')
            (
                ffmpeg
                .output(video.video, audio.audio, output_path, **{'c:v': 'copy', 'c:a': 'aac', 'shortest': None})
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except Exception as e:
            raise Exception(f"添加背景音乐失败: {str(e)}")
    
    async def add_background_music_maozibi(self, input_path: str, output_path: str) -> bool:
        """为maozibi视频添加背景音乐，使用jiggy boogy2.mp3"""
        try:
            music_path = str(Path(__file__).parent / "jiggy boogy2.mp3")
            if not os.path.exists(music_path):
                raise Exception("背景音乐文件jiggy boogy2.mp3不存在")
            
            video = ffmpeg.input(input_path)
            audio = ffmpeg.input(music_path, stream_loop='-1')
            (
                ffmpeg
                .output(video.video, audio.audio, output_path, **{'c:v': 'copy', 'c:a': 'aac', 'shortest': None})
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except Exception as e:
            raise Exception(f"添加背景音乐失败: {str(e)}")
    
    async def create_picture_in_picture(self, main_video_path: str, overlay_video_path: str, 
                                        output_path: str) -> bool:
        """创建画中画效果"""
        try:
            probe = ffmpeg.probe(main_video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if not video_stream:
                raise Exception("无法获取主视频信息")
            
            main_width = int(video_stream['width'])
            main_height = int(video_stream['height'])
            
            overlay_width = main_width // 4
            overlay_height = main_height // 4
            overlay_x = main_width - overlay_width - 10
            overlay_y = 10
            
            main_input = ffmpeg.input(main_video_path)
            overlay_input = ffmpeg.input(overlay_video_path)
            overlay_scaled = ffmpeg.filter(overlay_input, 'scale', overlay_width, overlay_height)
            output = ffmpeg.filter([main_input, overlay_scaled], 'overlay', overlay_x, overlay_y)
            
            (
                ffmpeg
                .output(output, output_path,
                       vcodec='libx264',
                       acodec='aac',
                       **{
                           'preset': 'medium',
                           'crf': '18',
                           'pix_fmt': 'yuv420p',
                           'movflags': '+faststart'
                       })
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except Exception as e:
            raise Exception(f"画中画创建失败: {str(e)}")

    async def create_picture_in_picture_with_score(self, main_video_path: str, overlay_video_path: str, 
                                                   output_path: str, score: str) -> bool:
        """创建带分数显示的画中画效果"""
        try:
            probe = ffmpeg.probe(main_video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if not video_stream:
                raise Exception("无法获取主视频信息")
            
            main_width = int(video_stream['width'])
            main_height = int(video_stream['height'])
            
            overlay_width = main_width // 4
            overlay_height = main_height // 4
            overlay_x = main_width - overlay_width - 10
            overlay_y = 10
            
            main_input = ffmpeg.input(main_video_path)
            overlay_input = ffmpeg.input(overlay_video_path)
            overlay_scaled = ffmpeg.filter(overlay_input, 'scale', overlay_width, overlay_height)
            pip_output = ffmpeg.filter([main_input, overlay_scaled], 'overlay', overlay_x, overlay_y)
            
            font_size = max(24, main_width // 40)
            text_output = ffmpeg.filter(pip_output, 'drawtext',
                                       text=score,
                                       fontsize=font_size,
                                       fontcolor='white',
                                       x=20,
                                       y=20,
                                       box=1,
                                       boxcolor='black@0.5',
                                       boxborderw=5)
            
            (
                ffmpeg
                .output(text_output, output_path,
                       vcodec='libx264',
                       acodec='aac',
                       **{
                           'preset': 'medium',
                           'crf': '18',
                           'pix_fmt': 'yuv420p',
                           'movflags': '+faststart'
                       })
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except Exception as e:
            raise Exception(f"带分数的画中画创建失败: {str(e)}")

    async def process_videos(self, video1_data: bytes, video2_data: bytes) -> tuple[str, str]:
        """处理两个视频文件"""
        unique_id = str(uuid.uuid4())
        
        if not video1_data or len(video1_data) == 0:
            raise Exception("第一个视频文件数据为空")
        if not video2_data or len(video2_data) == 0:
            raise Exception("第二个视频文件数据为空")
        
        OUTPUT_DIR = Path(__file__).parent / "output"
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        video1_path = os.path.join(self.temp_dir, f"video1_{unique_id}.mp4")
        video2_path = os.path.join(self.temp_dir, f"video2_{unique_id}.mp4")
        
        try:
            with open(video1_path, 'wb') as f:
                f.write(video1_data)
            with open(video2_path, 'wb') as f:
                f.write(video2_data)
            
            duration1 = await self.get_video_duration(video1_path)
            duration2 = await self.get_video_duration(video2_path)
            
            segment1_path = os.path.join(self.temp_dir, f"segment1_{unique_id}.mp4")
            segment2_path = os.path.join(self.temp_dir, f"segment2_{unique_id}.mp4")
            
            segment_duration1 = min(10, duration1)
            await self.extract_video_segment(video1_path, segment1_path, 0, segment_duration1)
            
            segment_duration2 = min(10, duration2)
            start_time2 = max(0, duration2 - segment_duration2)
            await self.extract_video_segment(video2_path, segment2_path, start_time2, segment_duration2)
            
            output_filename = f"merged_{unique_id}.mp4"
            output_path = OUTPUT_DIR / output_filename
            
            await self.concatenate_videos(segment1_path, segment2_path, str(output_path))
            
            final_output = os.path.join(self.temp_dir, f"final_{unique_id}.mp4")
            await self.add_background_music(str(output_path), final_output)
            shutil.move(final_output, output_path)
            
            for temp_file in [video1_path, video2_path, segment1_path, segment2_path]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            return str(output_path), output_filename
        except Exception as e:
            for path in [video1_path, video2_path]:
                if os.path.exists(path):
                    os.remove(path)
            raise

    async def process_maozibi_videos(self, video0_data: bytes, video1_data: bytes) -> tuple[str, str]:
        """处理两个视频文件，创建画中画效果"""
        unique_id = str(uuid.uuid4())
        
        if not video0_data or len(video0_data) == 0:
            raise Exception("video0文件数据为空")
        if not video1_data or len(video1_data) == 0:
            raise Exception("video1文件数据为空")
        
        OUTPUT_DIR = Path(__file__).parent / "output"
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        video0_path = os.path.join(self.temp_dir, f"video0_{unique_id}.mp4")
        video1_path = os.path.join(self.temp_dir, f"video1_{unique_id}.mp4")
        
        try:
            with open(video0_path, 'wb') as f:
                f.write(video0_data)
            with open(video1_path, 'wb') as f:
                f.write(video1_data)
            
            duration0 = await self.get_video_duration(video0_path)
            duration1 = await self.get_video_duration(video1_path)
            
            final_duration = min(duration0, duration1)
            
            trimmed_video0_path = video0_path
            trimmed_video1_path = video1_path
            
            if duration0 > final_duration:
                trimmed_video0_path = os.path.join(self.temp_dir, f"trimmed_video0_{unique_id}.mp4")
                await self.extract_video_segment(video0_path, trimmed_video0_path, 0, final_duration)
            
            if duration1 > final_duration:
                trimmed_video1_path = os.path.join(self.temp_dir, f"trimmed_video1_{unique_id}.mp4")
                await self.extract_video_segment(video1_path, trimmed_video1_path, 0, final_duration)
            
            pip_path = os.path.join(self.temp_dir, f"pip_maozibi_{unique_id}.mp4")
            await self.create_picture_in_picture(trimmed_video0_path, trimmed_video1_path, pip_path)
            
            output_filename = f"maozibi_{unique_id}.mp4"
            output_path = OUTPUT_DIR / output_filename
            
            await self.add_background_music_maozibi(pip_path, str(output_path))
            
            temp_files = [video0_path, video1_path, pip_path]
            if trimmed_video0_path != video0_path:
                temp_files.append(trimmed_video0_path)
            if trimmed_video1_path != video1_path:
                temp_files.append(trimmed_video1_path)
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            return str(output_path), output_filename
        except Exception as e:
            for path in [video0_path, video1_path]:
                if os.path.exists(path):
                    os.remove(path)
            raise

    async def process_maozibi_score_videos(self, video0_data: bytes, video1_data: bytes, score: str) -> tuple[str, str]:
        """处理两个视频文件，创建带分数显示的画中画效果"""
        unique_id = str(uuid.uuid4())
        
        if not video0_data or len(video0_data) == 0:
            raise Exception("video0文件数据为空")
        if not video1_data or len(video1_data) == 0:
            raise Exception("video1文件数据为空")
        if not score or score.strip() == "":
            raise Exception("score参数不能为空")
        
        OUTPUT_DIR = Path(__file__).parent / "output"
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        video0_path = os.path.join(self.temp_dir, f"video0_{unique_id}.mp4")
        video1_path = os.path.join(self.temp_dir, f"video1_{unique_id}.mp4")
        
        try:
            with open(video0_path, 'wb') as f:
                f.write(video0_data)
            with open(video1_path, 'wb') as f:
                f.write(video1_data)
            
            duration0 = await self.get_video_duration(video0_path)
            duration1 = await self.get_video_duration(video1_path)
            
            final_duration = min(duration0, duration1)
            
            trimmed_video0_path = video0_path
            trimmed_video1_path = video1_path
            
            if duration0 > final_duration:
                trimmed_video0_path = os.path.join(self.temp_dir, f"trimmed_video0_{unique_id}.mp4")
                await self.extract_video_segment(video0_path, trimmed_video0_path, 0, final_duration)
            
            if duration1 > final_duration:
                trimmed_video1_path = os.path.join(self.temp_dir, f"trimmed_video1_{unique_id}.mp4")
                await self.extract_video_segment(video1_path, trimmed_video1_path, 0, final_duration)
            
            pip_path = os.path.join(self.temp_dir, f"pip_maozibi_score_{unique_id}.mp4")
            await self.create_picture_in_picture_with_score(trimmed_video0_path, trimmed_video1_path, pip_path, score)
            
            output_filename = f"maozibi_score_{unique_id}.mp4"
            output_path = OUTPUT_DIR / output_filename
            
            await self.add_background_music_maozibi(pip_path, str(output_path))
            
            temp_files = [video0_path, video1_path, pip_path]
            if trimmed_video0_path != video0_path:
                temp_files.append(trimmed_video0_path)
            if trimmed_video1_path != video1_path:
                temp_files.append(trimmed_video1_path)
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            return str(output_path), output_filename
        except Exception as e:
            for path in [video0_path, video1_path]:
                if os.path.exists(path):
                    os.remove(path)
            raise


class QRCodeGenerator:
    """二维码生成器"""
    
    @staticmethod
    def generate_qr_code(data: str, output_path: str, size: int = 10, border: int = 4) -> bool:
        """生成二维码"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size,
                border=border,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(output_path)
            return True
        except Exception as e:
            print(f"二维码生成失败: {str(e)}")
            return False
    
    @staticmethod
    async def generate_qr_code_async(data: str, output_path: str, size: int = 10, border: int = 4) -> bool:
        """异步生成二维码"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, QRCodeGenerator.generate_qr_code, data, output_path, size, border)


if __name__ == "__main__":
    async def test_video_processing():
        """测试视频处理功能"""
        processor = VideoProcessor()
        
        if await processor.check_ffmpeg():
            print("FFmpeg可用，可以进行视频处理")
        else:
            print("FFmpeg不可用，请安装FFmpeg")
        
        qr_generator = QRCodeGenerator()
        test_qr_path = "test_qr.png"
        if qr_generator.generate_qr_code("https://example.com", test_qr_path):
            print(f"二维码生成成功: {test_qr_path}")
        else:
            print("二维码生成失败")
        
        del processor
    
    asyncio.run(test_video_processing())