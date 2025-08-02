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

import qrcode

from config import OUTPUT_DIR

# MoviePy v2 导入
try:
    from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, concatenate_audioclips
except ImportError as e:
    print(f"MoviePy 导入错误: {e}")
    print("请确保 MoviePy v2 已正确安装: pip install moviepy==2.2.1")


class VideoProcessor:
    """视频处理类 - 使用 MoviePy 优化"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        # 设置 MoviePy 的默认线程数以提高性能
        os.environ.setdefault('MOVIEPY_NUMTHREADS', '4')
    
    def __del__(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _cleanup_clips(self, *clips):
        """安全地清理视频剪辑以释放内存"""
        for clip in clips:
            if clip is not None:
                try:
                    clip.close()
                except Exception:
                    pass  # 忽略清理错误
    
    async def check_ffmpeg(self) -> bool:
        """检查moviepy/ffmpeg是否可用"""
        try:
            # 尝试创建一个简单的视频剪辑来测试moviepy是否正常工作
            test_clip = VideoFileClip("test.mp4", logger=None) if os.path.exists("test.mp4") else None
            if test_clip:
                test_clip.close()
            print("MoviePy is available and ready to use")
            return True
        except Exception:
            # 如果moviepy不可用，回退到检查ffmpeg
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
                
                print("MoviePy/FFmpeg not available")
                return False
                
            except Exception as e:
                print(f"Video processing check error: {e}")
                return False
    
    async def get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        try:
            with VideoFileClip(video_path) as clip:
                duration = clip.duration
            return duration
        except Exception as e:
            raise Exception(f"无法获取视频时长: {str(e)}")
    
    async def extract_video_segment(self, input_path: str, output_path: str, 
                                  start_time: float, duration: float) -> bool:
        """提取视频片段"""
        try:
            with VideoFileClip(input_path) as clip:
                # 提取指定时间段的视频片段
                end_time = start_time + duration
                segment = clip.subclipped(start_time, end_time)
                
                # 写入文件，使用优化的编码参数
                segment.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=f"{output_path}_temp_audio.m4a",
                    remove_temp=True,
                    preset='fast',  # 使用 fast preset 提高速度
                    ffmpeg_params=['-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'],  # 调整 CRF 平衡质量和速度
                    logger=None
                )
                self._cleanup_clips(segment)
            return True
        except Exception as e:
            raise Exception(f"视频片段提取失败: {str(e)}")
    
    async def concatenate_videos(self, video1_path: str, video2_path: str, 
                               output_path: str) -> bool:
        """拼接两个视频"""
        try:
            # 使用 moviepy 加载两个视频
            clip1 = VideoFileClip(video1_path)
            clip2 = VideoFileClip(video2_path)
            
            # 拼接视频
            final_clip = concatenate_videoclips([clip1, clip2])
            
            # 写入输出文件
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f"{output_path}_temp_audio.m4a",
                remove_temp=True,
                preset='fast',  # 使用 fast preset 提高速度
                ffmpeg_params=['-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'],  # 调整 CRF 平衡质量和速度

                logger=None,
                threads=4  # 使用多线程编码
            )
            
            # 清理资源
            self._cleanup_clips(clip1, clip2, final_clip)
            
            return True
        except Exception as e:
            raise Exception(f"视频拼接失败: {str(e)}")
    
    async def add_background_music(self, input_path: str, output_path: str) -> bool:
        """为视频添加背景音乐"""
        try:
            music_path = str(Path(__file__).parent / "jiggy boogy.mp3")
            
            # 加载视频和音频
            video_clip = VideoFileClip(input_path)
            audio_clip = AudioFileClip(music_path)
            
            # 如果音频比视频短，循环播放音频
            if audio_clip.duration < video_clip.duration:
                # 计算需要循环的次数
                loops = int(video_clip.duration / audio_clip.duration) + 1
                # 使用 concatenate_audioclips 创建循环效果，确保每个副本都是独立的
                looped_clips = []
                for i in range(loops):
                    # 创建音频的独立副本以避免维度不匹配
                    clip_copy = audio_clip.subclipped(0, audio_clip.duration)
                    looped_clips.append(clip_copy)
                
                try:
                    audio_clip = concatenate_audioclips(looped_clips)
                except Exception as concat_error:
                    # 如果拼接失败，使用简单的重复方法
                    print(f"音频拼接失败，使用备用方法: {concat_error}")
                    # 使用第一个音频片段，重复到所需长度
                    single_duration = audio_clip.duration
                    target_duration = video_clip.duration
                    audio_clip = audio_clip.subclipped(0, min(single_duration, target_duration))
                    if single_duration < target_duration:
                        # 使用音频自身的loop功能
                        audio_clip = audio_clip.loop(duration=target_duration)
                
                # 截取到确切的视频长度
                audio_clip = audio_clip.subclipped(0, video_clip.duration)
                
                # 清理临时片段
                for clip in looped_clips:
                    try:
                        clip.close()
                    except:
                        pass
            else:
                # 如果音频比视频长，截取音频
                audio_clip = audio_clip.subclipped(0, video_clip.duration)
            
            # 将背景音乐添加到视频中
            final_clip = video_clip.with_audio(audio_clip)
            
            # 写入输出文件
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f"{output_path}_temp_audio.m4a",
                remove_temp=True,
                preset='fast',  # 使用 fast preset 提高速度
                ffmpeg_params=['-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'],  # 调整 CRF 平衡质量和速度

                logger=None,
                threads=4  # 使用多线程编码
            )
            
            # 清理资源
            self._cleanup_clips(video_clip, audio_clip, final_clip)
            
            return True
        except Exception as e:
            raise Exception(f"添加背景音乐失败: {str(e)}")
    
    async def add_background_music_maozibi(self, input_path: str, output_path: str) -> bool:
        """为maozibi视频添加背景音乐，使用jiggy boogy2.mp3"""
        try:
            music_path = str(Path(__file__).parent / "bgm_mbz.mp3")
            if not os.path.exists(music_path):
                raise Exception("背景音乐文件jiggy boogy2.mp3不存在")
            
            # 加载视频和音频
            video_clip = VideoFileClip(input_path)
            audio_clip = AudioFileClip(music_path)
            
            # 如果音频比视频短，循环播放音频
            if audio_clip.duration < video_clip.duration:
                # 计算需要循环的次数
                loops = int(video_clip.duration / audio_clip.duration) + 1
                # 使用 concatenate_audioclips 创建循环效果，确保每个副本都是独立的
                looped_clips = []
                for i in range(loops):
                    # 创建音频的独立副本以避免维度不匹配
                    clip_copy = audio_clip.subclipped(0, audio_clip.duration)
                    looped_clips.append(clip_copy)
                
                try:
                    audio_clip = concatenate_audioclips(looped_clips)
                except Exception as concat_error:
                    # 如果拼接失败，使用简单的重复方法
                    print(f"音频拼接失败，使用备用方法: {concat_error}")
                    # 使用第一个音频片段，重复到所需长度
                    single_duration = audio_clip.duration
                    target_duration = video_clip.duration
                    audio_clip = audio_clip.subclipped(0, min(single_duration, target_duration))
                    if single_duration < target_duration:
                        # 使用音频自身的loop功能
                        audio_clip = audio_clip.loop(duration=target_duration)
                
                # 截取到确切的视频长度
                audio_clip = audio_clip.subclipped(0, video_clip.duration)
                
                # 清理临时片段
                for clip in looped_clips:
                    try:
                        clip.close()
                    except:
                        pass
            else:
                # 如果音频比视频长，截取音频
                audio_clip = audio_clip.subclipped(0, video_clip.duration)
            
            # 将背景音乐添加到视频中
            final_clip = video_clip.with_audio(audio_clip)
            
            # 写入输出文件
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f"{output_path}_temp_audio.m4a",
                remove_temp=True,
                preset='fast',  # 使用 fast preset 提高速度
                ffmpeg_params=['-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'],  # 调整 CRF 平衡质量和速度

                logger=None,
                threads=4  # 使用多线程编码
            )
            
            # 清理资源
            self._cleanup_clips(video_clip, audio_clip, final_clip)
            
            return True
        except Exception as e:
            raise Exception(f"添加背景音乐失败: {str(e)}")
    
    async def create_picture_in_picture(self, main_video_path: str, overlay_video_path: str, 
                                        output_path: str) -> bool:
        """创建画中画效果"""
        try:
            # 加载主视频和覆盖视频
            main_clip = VideoFileClip(main_video_path)
            overlay_clip = VideoFileClip(overlay_video_path)
            
            # 获取主视频的尺寸
            main_width, main_height = main_clip.size
            
            # 计算覆盖视频的大小和位置
            overlay_width = main_width // 4
            overlay_height = main_height // 4
            overlay_x = main_width - overlay_width - 10
            overlay_y = 10
            
            # 调整覆盖视频的大小和位置
            overlay_resized = overlay_clip.resized((overlay_width, overlay_height))
            overlay_positioned = overlay_resized.with_position((overlay_x, overlay_y))
            
            # 创建画中画效果
            final_clip = CompositeVideoClip([main_clip, overlay_positioned])
            
            # 写入输出文件
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f"{output_path}_temp_audio.m4a",
                remove_temp=True,
                preset='fast',  # 使用 fast preset 提高速度
                ffmpeg_params=['-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'],  # 调整 CRF 平衡质量和速度

                logger=None,
                threads=4  # 使用多线程编码
            )
            
            # 清理资源
            self._cleanup_clips(main_clip, overlay_clip, overlay_resized, overlay_positioned, final_clip)
            
            return True
        except Exception as e:
            raise Exception(f"画中画创建失败: {str(e)}")

    async def create_picture_in_picture_with_score(self, main_video_path: str, overlay_video_path: str, 
                                                   output_path: str, score: str) -> bool:
        """创建带分数显示的画中画效果"""
        try:
            # 加载主视频和覆盖视频
            main_clip = VideoFileClip(main_video_path)
            overlay_clip = VideoFileClip(overlay_video_path)
            
            # 获取主视频的尺寸
            main_width, main_height = main_clip.size
            
            # 计算覆盖视频的大小和位置
            overlay_width = main_width // 4
            overlay_height = main_height // 4
            overlay_x = main_width - overlay_width - 10
            overlay_y = 10
            
            # 调整覆盖视频的大小和位置
            overlay_resized = overlay_clip.resized((overlay_width, overlay_height))
            overlay_positioned = overlay_resized.with_position((overlay_x, overlay_y))
            
            # 创建画中画效果
            pip_clip = CompositeVideoClip([main_clip, overlay_positioned])
            
            # 创建分数文本
            font_size = max(24, main_width // 40)
            text_clip = TextClip(
                score,
                fontsize=font_size,
                color='white',
                font='Arial-Bold'
            ).with_position((20, 20)).with_duration(pip_clip.duration)
            
            # 合成最终视频（添加文本）
            final_clip = CompositeVideoClip([pip_clip, text_clip])
            
            # 写入输出文件
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f"{output_path}_temp_audio.m4a",
                remove_temp=True,
                preset='fast',  # 使用 fast preset 提高速度
                ffmpeg_params=['-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'],  # 调整 CRF 平衡质量和速度

                logger=None,
                threads=4  # 使用多线程编码
            )
            
            # 清理资源
            self._cleanup_clips(main_clip, overlay_clip, overlay_resized, overlay_positioned, pip_clip, text_clip, final_clip)
            
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
            
            segment_duration1 = min(10, int(duration1))
            await self.extract_video_segment(video1_path, segment1_path, 0, segment_duration1)
            
            segment_duration2 = min(10, int(duration2))
            start_time2 = max(0, int(duration2) - segment_duration2)
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