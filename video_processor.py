import math
import numpy as np
import moviepy as mp
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, concatenate_audioclips
import os
import subprocess
from pathlib import Path
try:
    import cv2
except ImportError:
    cv2 = None
    print("警告: cv2未安装，缩放效果将使用回退方案")

# 设置 MoviePy 配置以避免 ffmpeg 问题
try:
    from moviepy.config import check_ffmpeg
    print("MoviePy ffmpeg 检查:", check_ffmpeg())
except ImportError:
    print("无法导入 MoviePy 配置检查")


class VideoProcessor:
    """
    基于MoviePy 2.x的视频处理类
    实现卡点动画、转场效果和时间进度显示
    """

    def __init__(self):
        self.output_size = (1920, 1080)  # 输出视频尺寸
        self.transition_duration = 0.5  # 转场时长
        self.beat_frame_duration = 1.0  # 每个卡点帧显示时长（增加到1秒）
        self._check_ffmpeg_availability()
    
    def _check_ffmpeg_availability(self):
        """检查 ffmpeg 是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✓ FFmpeg 可用")
                return True
            else:
                print("⚠ FFmpeg 不可用 - 可能会遇到视频处理问题")
                return False
        except Exception as e:
            print(f"⚠ 无法检查 FFmpeg: {e}")
            print("如果遇到视频处理问题，请确保已安装 FFmpeg")
            return False

    def create_beat_video(self, video1_path, video2_path, beat_times,
                          output_path="output_beat_video.mp4",
                          speed_factor=1.5, font_size=60, background_music_path=None):
        """
        创建卡点视频

        参数:
        - video1_path: 第一个视频路径
        - video2_path: 第二个视频路径
        - beat_times: 卡点时间数组 (秒)
        - output_path: 输出文件路径
        - speed_factor: 第二个视频的播放速度倍数
        - font_size: 时间显示字体大小
        - background_music_path: 背景音乐文件路径（可选，默认使用jiggy boogy.mp3）
        """
        try:
            # 加载视频
            video1 = VideoFileClip(video1_path)
            video2 = VideoFileClip(video2_path)

            # 创建卡点片段
            beat_clips = self._create_beat_clips(video1, beat_times)

            # 创建带时间显示的第二个视频
            video2_with_timer = self._add_timer_to_video(video2, speed_factor, font_size)

            # 组合所有片段
            final_video = self._combine_clips(beat_clips, video2_with_timer)

            # 先保存没有音频的视频
            temp_video_path = output_path.replace('.mp4', '_temp_no_audio.mp4')
            try:
                print("写入临时视频（无音频）...")
                final_video.write_videofile(
                    temp_video_path,
                    logger=None,
                    audio=False  # 明确禁用音频
                )
                print("临时视频写入成功!")
            except Exception as write_error:
                print(f"临时视频写入失败: {write_error}")
                raise
            
            # 使用 FFmpeg 添加背景音乐
            success = self._add_music_with_ffmpeg(temp_video_path, output_path, background_music_path)
            
            # 清理临时文件
            try:
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
            except:
                pass
            
            if not success:
                # 如果音频添加失败，至少我们有无音频的视频
                print("音频添加失败，保留无音频版本")
                if os.path.exists(temp_video_path):
                    os.rename(temp_video_path, output_path)

            # 清理资源
            try:
                video1.close()
                video2.close()
                final_video.close()
            except Exception as cleanup_error:
                print(f"清理资源时出错: {cleanup_error}")

            print(f"视频处理完成，保存至: {output_path}")

        except Exception as e:
            print(f"视频处理出错: {str(e)}")
            # 确保在出错时也能清理资源
            try:
                if 'video1' in locals():
                    video1.close()
                if 'video2' in locals():
                    video2.close()
                if 'final_video' in locals():
                    final_video.close()
            except:
                pass
            raise

    def _create_beat_clips(self, video, beat_times):
        """创建卡点片段 - 修复版本"""
        beat_clips = []

        for i, beat_time in enumerate(beat_times):
            # 确保时间在视频范围内
            if beat_time >= video.duration:
                print(f"警告: 卡点时间 {beat_time}s 超出视频长度 {video.duration}s")
                continue

            # 截取指定时间点的帧，使用更长的片段时间以获得更好的效果
            clip_duration = 0.5  # 使用0.5秒的片段
            start_time = max(0, beat_time - 0.1)  # 稍微提前开始
            end_time = min(video.duration, beat_time + clip_duration)

            try:
                frame_clip = video.subclipped(start_time, end_time)
            except AttributeError:
                try:
                    frame_clip = video.subclip(start_time, end_time)
                except AttributeError:
                    print(f"错误: 无法截取视频片段，跳过卡点 {beat_time}s")
                    continue

            # 强制调整到统一尺寸
            try:
                frame_clip = frame_clip.resized(self.output_size)
            except AttributeError:
                try:
                    frame_clip = frame_clip.resize(self.output_size)
                except:
                    print(f"警告: 无法调整卡点片段尺寸")

            # 设置卡点片段的显示持续时间（重要！）
            try:
                frame_clip = frame_clip.with_duration(self.beat_frame_duration)
            except AttributeError:
                try:
                    frame_clip = frame_clip.set_duration(self.beat_frame_duration)
                except:
                    print(f"警告: 无法设置卡点片段持续时间")

            # 添加简单的缩放效果作为转场
            if i > 0:  # 从第二个卡点开始添加缩放效果
                frame_clip = self._add_simple_zoom_effect(frame_clip)

            beat_clips.append(frame_clip)
            print(f"成功创建卡点 {i + 1}: {beat_time}s, 显示时长: {self.beat_frame_duration}s")

        return beat_clips

    def _add_simple_zoom_effect(self, clip):
        """使用 MoviePy 2.x 的 transform 方法添加动态缩放效果"""
        try:
            # 使用 transform 方法来实现基于时间的动态缩放 (MoviePy 2.x 正确 API)
            if hasattr(clip, 'transform') and cv2 is not None:
                def dynamic_zoom(get_frame, t):
                    """基于时间的动态缩放函数"""
                    frame = get_frame(t)
                    h, w = frame.shape[:2]
                    
                    # 根据时间计算动态缩放比例
                    # 从1.0逐渐放大到1.05，然后回到1.0，形成一个缩放循环
                    duration = clip.duration if hasattr(clip, 'duration') and clip.duration else self.beat_frame_duration
                    progress = (t % duration) / duration  # 获取当前时间在片段中的进度 (0-1)
                    
                    # 使用正弦波形实现平滑的缩放动画：从1.0到1.05再回到1.0
                    scale = 1.0 + 0.05 * math.sin(progress * 2 * math.pi)
                    
                    new_h, new_w = int(h * scale), int(w * scale)
                    
                    # 放大图像
                    resized_frame = cv2.resize(frame, (new_w, new_h))
                    
                    # 从中心裁剪回原始大小
                    start_x = (new_w - w) // 2
                    start_y = (new_h - h) // 2
                    cropped_frame = resized_frame[start_y:start_y+h, start_x:start_x+w]
                    
                    return cropped_frame
                
                print("使用 MoviePy 2.x transform 方法添加动态缩放效果")
                zoom_clip = clip.transform(dynamic_zoom)
                return zoom_clip
            
            # 回退：尝试使用基于PIL的动态缩放 (如果cv2不可用但有PIL)
            elif hasattr(clip, 'transform') and cv2 is None:
                try:
                    from PIL import Image
                    import numpy as np
                    
                    def pil_dynamic_zoom(get_frame, t):
                        """使用PIL的基于时间的动态缩放函数"""
                        frame = get_frame(t)
                        img = Image.fromarray(frame)
                        base_size = img.size
                        
                        # 根据时间计算动态缩放比例
                        duration = clip.duration if hasattr(clip, 'duration') and clip.duration else self.beat_frame_duration
                        progress = (t % duration) / duration
                        
                        # 使用正弦波形实现平滑的缩放动画
                        zoom_ratio = 0.05 * math.sin(progress * 2 * math.pi)
                        scale = 1.0 + zoom_ratio
                        
                        new_size = [
                            math.ceil(img.size[0] * scale),
                            math.ceil(img.size[1] * scale)
                        ]
                        
                        # 确保新尺寸是偶数
                        new_size[0] = new_size[0] + (new_size[0] % 2)
                        new_size[1] = new_size[1] + (new_size[1] % 2)
                        
                        # 调整图像大小
                        img = img.resize(new_size, Image.LANCZOS)
                        
                        # 裁剪到原始大小
                        x = math.ceil((new_size[0] - base_size[0]) / 2)
                        y = math.ceil((new_size[1] - base_size[1]) / 2)
                        
                        img = img.crop([
                            x, y, new_size[0] - x, new_size[1] - y
                        ]).resize(base_size, Image.LANCZOS)
                        
                        result = np.array(img)
                        img.close()
                        return result
                    
                    print("使用PIL实现动态缩放效果")
                    zoom_clip = clip.transform(pil_dynamic_zoom)
                    return zoom_clip
                    
                except ImportError:
                    print("PIL不可用，跳过PIL动态缩放方案")
                    pass
            
            # 回退：使用 image_transform 方法 (MoviePy 2.x 的正确 API) - 静态缩放
            if hasattr(clip, 'image_transform') and cv2 is not None:
                def zoom_function(frame):
                    """对每一帧应用缩放效果"""
                    h, w = frame.shape[:2]
                    scale = 1.03  # 轻微放大3%
                    new_h, new_w = int(h * scale), int(w * scale)
                    
                    # 放大图像
                    resized_frame = cv2.resize(frame, (new_w, new_h))
                    
                    # 从中心裁剪回原始大小
                    start_x = (new_w - w) // 2
                    start_y = (new_h - h) // 2
                    cropped_frame = resized_frame[start_y:start_y+h, start_x:start_x+w]
                    
                    return cropped_frame
                
                print("使用 image_transform 方法添加静态缩放效果")
                zoom_clip = clip.image_transform(zoom_function)
                return zoom_clip
            
            # 回退到 fl_image 方法（如果存在）
            elif hasattr(clip, 'fl_image') and cv2 is not None:
                def static_zoom_function(frame):
                    """静态缩放函数"""
                    h, w = frame.shape[:2]
                    scale = 1.03  # 轻微放大3%
                    new_h, new_w = int(h * scale), int(w * scale)
                    
                    resized_frame = cv2.resize(frame, (new_w, new_h))
                    start_x = (new_w - w) // 2
                    start_y = (new_h - h) // 2
                    cropped_frame = resized_frame[start_y:start_y+h, start_x:start_x+w]
                    return cropped_frame
                
                print("使用 fl_image 方法添加缩放效果")
                zoom_clip = clip.fl_image(static_zoom_function)
                return zoom_clip
            
            # 最终回退到基本 resize 方法
            elif hasattr(clip, 'resized') or hasattr(clip, 'resize'):
                print("使用基础 resize 方法添加缩放效果")
                scale = 1.03
                enlarged_size = (int(self.output_size[0] * scale), int(self.output_size[1] * scale))
                
                if hasattr(clip, 'resized'):
                    enlarged_clip = clip.resized(enlarged_size)
                    zoom_clip = enlarged_clip.resized(self.output_size)
                else:
                    enlarged_clip = clip.resize(enlarged_size)
                    zoom_clip = enlarged_clip.resize(self.output_size)
                
                return zoom_clip
            
            else:
                print("无法应用任何缩放效果，返回原始片段")
                return clip
                
        except Exception as e:
            print(f"缩放效果失败: {e}")
            return clip

    def _add_timer_to_video(self, video, speed_factor, font_size):
        """为视频添加滚动时间进度显示"""
        # 应用快进效果
        original_duration = video.duration
        if speed_factor != 1.0:
            print(f"应用 {speed_factor}x 播放速度")
            try:
                if hasattr(video, 'with_speed_multiplier'):
                    video = video.with_speed_multiplier(speed_factor)
                elif hasattr(video, 'speedx'):
                    video = video.speedx(speed_factor)
                else:
                    # 手动调整速度
                    new_duration = video.duration / speed_factor
                    video = video.with_duration(new_duration) if hasattr(video, 'with_duration') else video.set_duration(new_duration)
                    print(f"手动调整速度: 原时长 {original_duration:.2f}s -> 新时长 {video.duration:.2f}s")
            except Exception as e:
                print(f"警告: 无法应用 {speed_factor}x 速度: {e}")

        # 确保视频尺寸正确
        try:
            video = video.resized(self.output_size)
        except:
            try:
                video = video.resize(self.output_size)
            except:
                print("警告: 无法调整主视频尺寸")

        # 创建动态滚动时间显示
        print("创建动态时间显示")
        try:
            # 方法1：创建多个1秒的时间片段
            timer_clips = []
            video_duration = int(video.duration) + 1

            for t in range(video_duration):
                minutes = int(t // 60)
                seconds = int(t % 60)
                time_text = f"{minutes:02d}:{seconds:02d}"

                # 创建1秒的时间显示片段
                timer_segment = TextClip(
                    text=time_text,
                    font_size=font_size,
                    color='white',
                    font='Arial'
                )

                # 设置持续时间和位置
                if hasattr(timer_segment, 'with_duration'):
                    timer_segment = timer_segment.with_duration(1.0)
                else:
                    timer_segment = timer_segment.set_duration(1.0)

                if hasattr(timer_segment, 'with_position'):
                    timer_segment = timer_segment.with_position(('right', 'top'))
                else:
                    timer_segment = timer_segment.set_position(('right', 'top'))

                timer_clips.append(timer_segment)

            # 连接所有时间片段
            if timer_clips:
                full_timer = concatenate_videoclips(timer_clips)

                # 调整到视频长度
                if full_timer.duration > video.duration:
                    if hasattr(full_timer, 'with_duration'):
                        full_timer = full_timer.with_duration(video.duration)
                    else:
                        full_timer = full_timer.set_duration(video.duration)

                # 合成视频
                result = CompositeVideoClip([video, full_timer])
                print(f"成功添加动态时间显示，时间范围: 00:00 - {int(video.duration) // 60:02d}:{int(video.duration) % 60:02d}")
                return result
            else:
                raise Exception("无法创建时间片段")

        except Exception as e:
            print(f"动态时间显示失败: {e}")

            # 回退方案：静态时间显示
            try:
                total_minutes = int(video.duration // 60)
                total_seconds = int(video.duration % 60)
                time_text = f"时长: {total_minutes:02d}:{total_seconds:02d}"

                timer_clip = TextClip(
                    text=time_text,
                    font_size=font_size,
                    color='white',
                    font='Arial'
                )

                if hasattr(timer_clip, 'with_duration'):
                    timer_clip = timer_clip.with_duration(video.duration)
                else:
                    timer_clip = timer_clip.set_duration(video.duration)

                if hasattr(timer_clip, 'with_position'):
                    timer_clip = timer_clip.with_position(('right', 'top'))
                else:
                    timer_clip = timer_clip.set_position(('right', 'top'))

                result = CompositeVideoClip([video, timer_clip])
                print("使用静态时间显示作为回退方案")
                return result

            except Exception as e2:
                print(f"静态时间显示也失败: {e2}")
                print("返回原始视频（不含时间显示）")
                return video

    def _combine_clips(self, beat_clips, main_video):
        """组合所有视频片段 - 简化版本"""
        all_clips = []

        print(f"准备组合 {len(beat_clips)} 个卡点片段和1个主视频")

        # 确保所有卡点片段都有相同的尺寸
        for i, clip in enumerate(beat_clips):
            try:
                # 强制统一尺寸
                clip = clip.resized(self.output_size)
                all_clips.append(clip)
                print(f"卡点片段 {i + 1}: 尺寸 {clip.size}, 持续时间 {clip.duration:.2f}s")
            except Exception as e:
                print(f"处理卡点片段 {i + 1} 时出错: {e}")
                try:
                    clip = clip.resize(self.output_size)
                    all_clips.append(clip)
                except:
                    print(f"跳过卡点片段 {i + 1}")
                    continue

        # 确保主视频也有正确的尺寸
        try:
            main_video = main_video.resized(self.output_size)
            print(f"主视频: 尺寸 {main_video.size}, 持续时间 {main_video.duration:.2f}s")
        except Exception as e:
            print(f"调整主视频尺寸时出错: {e}")
            try:
                main_video = main_video.resize(self.output_size)
            except:
                print("警告: 无法调整主视频尺寸")

        # 不添加任何效果，直接使用主视频
        all_clips.append(main_video)

        print(f"总共 {len(all_clips)} 个片段准备连接")

        # 连接所有片段
        try:
            final_video = concatenate_videoclips(all_clips)
            print(f"成功连接所有片段，最终视频长度: {final_video.duration:.2f}s")
            return final_video
        except Exception as e:
            print(f"连接视频时出错: {e}")

            # 尝试逐个检查和修复
            fixed_clips = []
            for i, clip in enumerate(all_clips):
                try:
                    # 再次强制统一尺寸和属性
                    if hasattr(clip, 'resized'):
                        fixed_clip = clip.resized(self.output_size)
                    else:
                        fixed_clip = clip.resize(self.output_size)

                    # 确保有音频轨道（如果原始视频有的话）
                    if hasattr(clip, 'audio') and clip.audio is not None:
                        fixed_clip = fixed_clip.set_audio(clip.audio)

                    fixed_clips.append(fixed_clip)
                    print(f"修复片段 {i + 1} 成功")
                except Exception as fix_e:
                    print(f"修复片段 {i + 1} 失败: {fix_e}")
                    # 如果修复失败，尝试使用原始片段
                    fixed_clips.append(clip)

            # 再次尝试连接
            final_video = concatenate_videoclips(fixed_clips)
            print(f"修复后成功连接，最终视频长度: {final_video.duration:.2f}s")
            return final_video

    def _add_background_music(self, video_clip, music_path=None):
        """
        为视频添加背景音乐
        
        参数:
        - video_clip: 视频剪辑对象
        - music_path: 音乐文件路径（可选，默认使用jiggy boogy.mp3）
        
        返回:
        - 添加了背景音乐的视频剪辑
        """
        try:
            # 确定音乐文件路径
            if music_path is None:
                music_path = str(Path(__file__).parent / "jiggy boogy.mp3")
            
            if not os.path.exists(music_path):
                print(f"警告: 背景音乐文件不存在: {music_path}")
                return video_clip
            
            print(f"添加背景音乐: {music_path}")
            
            # 加载背景音乐
            audio_clip = AudioFileClip(music_path)
            
            # 如果音频比视频短，循环播放音频
            if audio_clip.duration < video_clip.duration:
                print(f"音频时长 {audio_clip.duration:.2f}s 短于视频时长 {video_clip.duration:.2f}s，需要循环播放")
                # 计算需要循环的次数
                loops = int(video_clip.duration / audio_clip.duration) + 1
                # 创建循环音频片段
                looped_clips = []
                for i in range(loops):
                    # 创建音频的独立副本
                    clip_copy = audio_clip.subclipped(0, audio_clip.duration)
                    looped_clips.append(clip_copy)
                
                try:
                    audio_clip = concatenate_audioclips(looped_clips)
                except Exception as concat_error:
                    print(f"音频拼接失败，使用备用方法: {concat_error}")
                    # 使用音频自身的loop功能
                    audio_clip = audio_clip.loop(duration=video_clip.duration)
                
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
                print(f"音频时长 {audio_clip.duration:.2f}s 长于视频时长 {video_clip.duration:.2f}s，截取音频")
                audio_clip = audio_clip.subclipped(0, video_clip.duration)
            
            # 将背景音乐添加到视频中
            try:
                final_clip = video_clip.with_audio(audio_clip)
                print("成功添加背景音乐")
                
                # 清理音频资源
                audio_clip.close()
                
                return final_clip
            except Exception as audio_error:
                print(f"合并音频到视频时出错: {audio_error}")
                # 清理音频资源
                try:
                    audio_clip.close()
                except:
                    pass
                # 返回原始视频
                return video_clip
            
        except Exception as e:
            print(f"添加背景音乐失败: {str(e)}")
            print("返回原始视频（不含背景音乐）")
            return video_clip

    def _add_background_music_simple(self, video_clip, music_path=None):
        """
        简化版背景音乐添加功能
        
        参数:
        - video_clip: 视频剪辑对象
        - music_path: 音乐文件路径（可选，默认使用jiggy boogy.mp3）
        
        返回:
        - 添加了背景音乐的视频剪辑或原始视频剪辑
        """
        try:
            # 确定音乐文件路径
            if music_path is None:
                music_path = str(Path(__file__).parent / "jiggy boogy.mp3")
            
            if not os.path.exists(music_path):
                print(f"警告: 背景音乐文件不存在: {music_path}")
                return video_clip
            
            print(f"添加背景音乐: {music_path}")
            
            # 加载背景音乐
            audio_clip = AudioFileClip(music_path)
            
            # 简单处理：只截取，避免循环操作
            if audio_clip.duration >= video_clip.duration:
                print(f"截取音频: {audio_clip.duration:.2f}s -> {video_clip.duration:.2f}s") 
                audio_clip = audio_clip.subclipped(0, video_clip.duration)
            else:
                print(f"音频较短: {audio_clip.duration:.2f}s < {video_clip.duration:.2f}s，直接使用")
                # 如果音频较短，就只使用现有的音频长度，不循环
            
            # 将背景音乐添加到视频中
            final_clip = video_clip.with_audio(audio_clip)
            print("成功添加背景音乐")
            
            # 清理音频资源
            audio_clip.close()
            
            return final_clip
            
        except Exception as e:
            print(f"添加背景音乐失败: {str(e)}")
            print("返回原始视频（不含背景音乐）")
            return video_clip

    def _add_music_with_ffmpeg(self, video_path, output_path, music_path=None):
        """
        使用 FFmpeg 直接添加背景音乐到视频
        
        参数:
        - video_path: 输入视频路径
        - output_path: 输出视频路径
        - music_path: 音乐文件路径（可选）
        
        返回:
        - bool: 成功返回 True，失败返回 False
        """
        try:
            # 确定音乐文件路径
            if music_path is None:
                music_path = str(Path(__file__).parent / "jiggy boogy.mp3")
            
            if not os.path.exists(music_path):
                print(f"警告: 背景音乐文件不存在: {music_path}")
                return False
            
            print(f"使用 FFmpeg 添加背景音乐: {music_path}")
            
            # 构建 FFmpeg 命令
            cmd = [
                'ffmpeg',
                '-i', video_path,        # 输入视频
                '-i', music_path,        # 输入音频
                '-c:v', 'copy',          # 复制视频流（不重新编码）
                '-c:a', 'aac',           # 音频编码为 AAC
                '-map', '0:v:0',         # 使用第一个文件的视频流
                '-map', '1:a:0',         # 使用第二个文件的音频流
                '-shortest',             # 使用最短的流长度
                '-y',                    # 覆盖输出文件
                output_path
            ]
            
            print(f"FFmpeg 命令: {' '.join(cmd)}")
            
            # 执行 FFmpeg 命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("FFmpeg 添加音频成功!")
                return True
            else:
                print(f"FFmpeg 错误: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("FFmpeg 超时")
            return False
        except Exception as e:
            print(f"FFmpeg 添加音频失败: {str(e)}")
            return False

    def preview_beat_points(self, video_path, beat_times, preview_duration=2.0):
        """预览卡点时间点 (用于调试)"""
        video = VideoFileClip(video_path)

        print(f"视频总长度: {video.duration:.2f}秒")
        print("卡点预览:")

        for i, beat_time in enumerate(beat_times):
            if beat_time < video.duration:
                start_time = max(0, beat_time - preview_duration / 2)
                end_time = min(video.duration, beat_time + preview_duration / 2)
                print(f"卡点 {i + 1}: {beat_time}s (预览: {start_time:.2f}s - {end_time:.2f}s)")
            else:
                print(f"卡点 {i + 1}: {beat_time}s (超出视频长度!)")

        video.close()


# 使用示例
if __name__ == "__main__":
    # 创建处理器实例
    processor = VideoProcessor()

    # 定义参数
    video1_path = "/Users/yujian/Downloads/video0_20250731_161731.mp4"  # 第一个视频路径
    video2_path = "/Users/yujian/Downloads/video1_20250731_161731.mp4"  # 第二个视频路径
    beat_times = [0.0, 4.5, 6.5, 9.8, 19,23]  # 卡点时间数组 (秒)

    # 预览卡点 (可选)
    # processor.preview_beat_points(video1_path, beat_times)

    # 处理视频
    processor.create_beat_video(
        video1_path=video1_path,
        video2_path=video2_path,
        beat_times=beat_times,
        output_path="final_beat_video.mp4",
        speed_factor=5,  # 第二个视频1.5倍速播放
        font_size=120,  # 时间显示字体大小
        background_music_path="jiggy boogy.mp3"  # 使用默认背景音乐 jiggy boogy.mp3，或指定其他音乐文件路径
    )