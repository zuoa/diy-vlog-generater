import math
import os
import subprocess
from pathlib import Path

import numpy as np
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, concatenate_audioclips, ColorClip

from ajlog import logger

try:
    import cv2
except ImportError:
    cv2 = None
    logger.warn("警告: cv2未安装，缩放效果将使用回退方案")

# 设置 MoviePy 配置以避免 ffmpeg 问题
try:
    from moviepy.config import check_ffmpeg

    logger.info("MoviePy ffmpeg 检查:", check_ffmpeg())
except ImportError:
    logger.warn("无法导入 MoviePy 配置检查")


class VideoProcessor:
    """
    基于MoviePy 2.x的视频处理类
    实现卡点动画、转场效果和时间进度显示
    """

    def __init__(self):
        self.output_size = (1280, 720)  # 输出视频尺寸
        self.transition_duration = 0.3  # 转场时长
        self.beat_frame_duration = 0.7  # 每个卡点帧显示时长
        self.fade_duration = 0.1  # 淡入淡出时长（秒）
        self._check_ffmpeg_availability()

    def _check_ffmpeg_availability(self):
        """检查 ffmpeg 是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("✓ FFmpeg 可用")
                return True
            else:
                logger.warn("⚠ FFmpeg 不可用 - 可能会遇到视频处理问题")
                return False
        except Exception as e:
            logger.warn(f"⚠ 无法检查 FFmpeg: {e}")
            logger.warn("如果遇到视频处理问题，请确保已安装 FFmpeg")
            return False

    def create_pip_video(self, main_video_path, pip_video_path, output_path, text=None, text_font_size=16, text_position=(0, 0), pip_position='top-right', pip_scale=0.25):
        """
        创建画中画视频

        参数:
        - main_video_path: 主视频路径
        - pip_video_path: 画中画视频路径
        - output_path: 输出文件路径
        - text: 要显示的文本（可选）
        - text_font_size: 文本字体大小
        - text_position: 文本位置 (x, y)
        - pip_position: 画中画视频位置 ('top-right', 'top-left', 'bottom-right', 'bottom-left')
        - pip_scale: 画中画视频缩放比例
        """
        try:
            # 加载主视频和画中画视频
            main_video = VideoFileClip(main_video_path).resized(self.output_size)
            pip_video = VideoFileClip(pip_video_path).resized(self.output_size)

            # 创建画中画效果
            pip_clip = self.create_picture_in_picture(
                main_clip=main_video,
                pip_clip=pip_video,
                pip_position=pip_position,
                pip_scale=pip_scale,
                pip_start_time=0,
                pip_duration=pip_video.duration
            )

            # 添加文本（如果有）
            if text:
                text_clip = TextClip(
                    text=text,
                    font_size=text_font_size,
                    color='white'
                )
                
                # 设置持续时间
                if hasattr(text_clip, 'with_duration'):
                    text_clip = text_clip.with_duration(pip_clip.duration)
                else:
                    text_clip = text_clip.set_duration(pip_clip.duration)
                
                # 创建文本背景
                padding = 10  # 背景边距
                bg_width = text_clip.size[0] + 2 * padding
                bg_height = text_clip.size[1] + 2 * padding
                
                # 创建半透明黑色背景
                text_bg = ColorClip(
                    size=(bg_width, bg_height),
                    color=(0, 0, 0),  # 黑色背景
                    duration=pip_clip.duration
                ).with_opacity(0.7)  # 70%透明度
                
                # 将文本居中放在背景上
                text_clip = text_clip.with_position('center')
                text_with_bg = CompositeVideoClip([text_bg, text_clip])
                
                # 设置整个文本+背景的位置
                if hasattr(text_with_bg, 'with_position'):
                    text_with_bg = text_with_bg.with_position(text_position)
                else:
                    text_with_bg = text_with_bg.set_position(text_position)
                
                final_clip = CompositeVideoClip([pip_clip, text_with_bg])
            else:
                final_clip = pip_clip


            # 保存最终视频
            temp_output_path = output_path.replace(".mp4", "_temp.mp4")
            final_clip.write_videofile(temp_output_path, logger=None)

            success = self._add_music_with_ffmpeg(temp_output_path, output_path, "bgm_mbz.mp3")

            logger.info(f"视频处理完成，保存至: {output_path}")

            # 清理资源
            main_video.close()
            pip_video.close()
            final_clip.close()

        except Exception as e:
            logger.warn(f"视频处理出错: {str(e)}")



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
            video1 = VideoFileClip(video1_path).resized(self.output_size)
            video2 = VideoFileClip(video2_path).resized(self.output_size)

            min_duration = min(video1.duration, video2.duration)

            # 创建卡点片段
            beat_clips = self._create_beat_clips(video1, beat_times)

            left_duration = min_duration - beat_times[-1]
            seg_duration = int(left_duration / 4)
            main_clips = []
            for i in range(0, 4):
                if i % 2 == 0:
                    v_main = video2.subclipped(beat_times[-1] + i * seg_duration, beat_times[-1] + (i + 1) * seg_duration)
                    v_pip = video1.subclipped(beat_times[-1] + i * seg_duration, beat_times[-1] + (i + 1) * seg_duration)
                else:
                    v_main = video1.subclipped(beat_times[-1] + i * seg_duration, beat_times[-1] + (i + 1) * seg_duration)
                    v_pip = video2.subclipped(beat_times[-1] + i * seg_duration, beat_times[-1] + (i + 1) * seg_duration)

                pip_result = self.create_picture_in_picture(
                    main_clip=v_main,
                    pip_clip=v_pip,
                    pip_position='top-right',
                    pip_scale=0.25,
                    pip_start_time=0,
                    pip_duration=3
                )

                main_clips.append(pip_result)

            v_end = self.create_text_video_clip("A Touch of Culture, A Handful of Heart", 3, output_size=video1.size)
            main_clips.append(v_end)
            fade_duration = 1
            transition_clip = ColorClip(size=self.output_size, color=(0, 0, 0), duration=1)
            v_diy = concatenate_videoclips(main_clips, method='compose', transition=transition_clip, bg_color=(0, 0, 0), padding=-fade_duration)
            #
            # # 创建带时间显示的第二个视频
            # video2_with_timer = self._add_timer_to_video(video2, speed_factor, font_size)

            # 组合所有片段
            final_video = self._combine_clips(beat_clips, v_diy)

            # 先保存没有音频的视频
            temp_video_path = output_path.replace('.mp4', '_temp_no_audio.mp4')
            try:
                logger.info("写入临时视频（无音频）...")
                final_video.write_videofile(
                    temp_video_path,
                    logger=None,
                    audio=False  # 明确禁用音频
                )
                logger.info("临时视频写入成功!")
            except Exception as write_error:
                logger.error(f"临时视频写入失败: {write_error}")
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

            logger.info(f"视频处理完成，保存至: {output_path}")

        except Exception as e:
            print(e)
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
                logger.info(f"警告: 卡点时间 {beat_time}s 超出视频长度 {video.duration}s")
                continue

            # 确保截取的片段长度与显示时长一致，避免黑帧
            clip_duration = self.beat_frame_duration  # 使用统一的持续时间
            start_time = max(0, beat_time - 0.05)  # 减少提前时间，更精确对齐卡点
            end_time = min(video.duration, start_time + clip_duration)

            # 确保片段长度足够
            if end_time - start_time < self.beat_frame_duration:
                # 如果到视频末尾长度不够，向前调整起始时间
                start_time = max(0, end_time - self.beat_frame_duration)
                logger.info(f"调整卡点 {i + 1} 时间范围: {start_time:.2f}s - {end_time:.2f}s")

            try:
                frame_clip = video.subclipped(start_time, end_time)
            except AttributeError:
                try:
                    frame_clip = video.subclip(start_time, end_time)
                except AttributeError:
                    logger.warn(f"错误: 无法截取视频片段，跳过卡点 {beat_time}s")
                    continue

            # 强制调整到统一尺寸
            try:
                frame_clip = frame_clip.resized(self.output_size)
            except AttributeError:
                try:
                    frame_clip = frame_clip.resize(self.output_size)
                except:
                    print(f"警告: 无法调整卡点片段尺寸")

            # 验证片段持续时间，只有在需要时才调整
            actual_duration = frame_clip.duration
            if abs(actual_duration - self.beat_frame_duration) > 0.01:  # 允许小的误差
                try:
                    frame_clip = frame_clip.with_duration(self.beat_frame_duration)
                    logger.info(f"调整卡点 {i + 1} 持续时间: {actual_duration:.2f}s -> {self.beat_frame_duration}s")
                except AttributeError:
                    try:
                        frame_clip = frame_clip.set_duration(self.beat_frame_duration)
                        print(f"调整卡点 {i + 1} 持续时间: {actual_duration:.2f}s -> {self.beat_frame_duration}s")
                    except:
                        print(f"警告: 无法设置卡点片段持续时间，使用原始时长: {actual_duration:.2f}s")

            # 添加改进的缩放效果作为转场
            if i > 0:  # 重新启用优化后的缩放效果
                frame_clip = self._add_simple_zoom_effect(frame_clip)

            beat_clips.append(frame_clip)
            logger.info(f"成功创建卡点 {i + 1}: {beat_time}s, 显示时长: {self.beat_frame_duration}s")

        return beat_clips

    def _add_simple_zoom_effect(self, clip):
        """使用 MoviePy 2.x 的 transform 方法添加安全的动态缩放效果"""
        try:
            # 使用 transform 方法来实现基于时间的动态缩放 (MoviePy 2.x 正确 API)
            if hasattr(clip, 'transform') and cv2 is not None:
                def safe_dynamic_zoom(get_frame, t):
                    """安全的基于时间的动态缩放函数"""
                    try:
                        frame = get_frame(t)
                        if frame is None:
                            return frame

                        h, w = frame.shape[:2]

                        # 确保时间在有效范围内
                        duration = clip.duration if hasattr(clip, 'duration') and clip.duration else self.beat_frame_duration
                        if duration <= 0:
                            return frame

                        # 安全的时间进度计算，避免边界问题
                        safe_t = max(0, min(t, duration - 0.001))  # 确保在有效范围内
                        progress = safe_t / duration  # 获取当前时间在片段中的进度 (0-1)

                        # 使用更小的缩放比例避免黑屏：从1.0到1.03再回到1.0
                        scale = 1.0 + 0.03 * math.sin(progress * 2 * math.pi)

                        # 确保缩放比例在安全范围内
                        scale = max(1.0, min(scale, 1.05))

                        new_h, new_w = int(h * scale), int(w * scale)

                        # 确保新尺寸有效
                        if new_h <= 0 or new_w <= 0:
                            return frame

                        # 放大图像
                        resized_frame = cv2.resize(frame, (new_w, new_h))

                        # 安全的中心裁剪，添加边界检查
                        start_x = max(0, (new_w - w) // 2)
                        start_y = max(0, (new_h - h) // 2)
                        end_x = min(new_w, start_x + w)
                        end_y = min(new_h, start_y + h)

                        # 确保裁剪区域有效
                        if end_x <= start_x or end_y <= start_y:
                            return frame

                        cropped_frame = resized_frame[start_y:end_y, start_x:end_x]

                        # 如果裁剪后尺寸不匹配，进行最终调整
                        if cropped_frame.shape[:2] != (h, w):
                            cropped_frame = cv2.resize(cropped_frame, (w, h))

                        return cropped_frame

                    except Exception as e:
                        print(f"缩放效果处理出错: {e}, 返回原始帧")
                        return get_frame(t)  # 出错时返回原始帧

                print("使用优化的 MoviePy 2.x transform 方法添加安全缩放效果")
                zoom_clip = clip.transform(safe_dynamic_zoom)
                return zoom_clip

            # 回退：尝试使用基于PIL的动态缩放 (如果cv2不可用但有PIL)
            elif hasattr(clip, 'transform') and cv2 is None:
                try:
                    from PIL import Image
                    import numpy as np

                    def safe_pil_dynamic_zoom(get_frame, t):
                        """使用PIL的安全动态缩放函数"""
                        try:
                            frame = get_frame(t)
                            if frame is None:
                                return frame

                            img = Image.fromarray(frame)
                            base_size = img.size

                            # 确保时间在有效范围内
                            duration = clip.duration if hasattr(clip, 'duration') and clip.duration else self.beat_frame_duration
                            if duration <= 0:
                                img.close()
                                return frame

                            # 安全的时间进度计算
                            safe_t = max(0, min(t, duration - 0.001))
                            progress = safe_t / duration

                            # 使用更小的缩放比例避免黑屏：从1.0到1.03再回到1.0
                            zoom_ratio = 0.03 * math.sin(progress * 2 * math.pi)
                            scale = 1.0 + zoom_ratio

                            # 确保缩放比例在安全范围内
                            scale = max(1.0, min(scale, 1.05))

                            new_size = [
                                max(1, math.ceil(img.size[0] * scale)),
                                max(1, math.ceil(img.size[1] * scale))
                            ]

                            # 确保新尺寸是偶数且有效
                            new_size[0] = new_size[0] + (new_size[0] % 2)
                            new_size[1] = new_size[1] + (new_size[1] % 2)

                            # 调整图像大小
                            img = img.resize(new_size, Image.LANCZOS)

                            # 安全的裁剪到原始大小
                            x = max(0, (new_size[0] - base_size[0]) // 2)
                            y = max(0, (new_size[1] - base_size[1]) // 2)

                            # 确保裁剪坐标有效
                            x2 = min(new_size[0], x + base_size[0])
                            y2 = min(new_size[1], y + base_size[1])

                            if x2 <= x or y2 <= y:
                                img.close()
                                return frame

                            cropped = img.crop([x, y, x2, y2])

                            # 确保最终尺寸正确
                            if cropped.size != base_size:
                                cropped = cropped.resize(base_size, Image.LANCZOS)

                            result = np.array(cropped)
                            img.close()
                            cropped.close()
                            return result

                        except Exception as e:
                            print(f"PIL缩放效果处理出错: {e}, 返回原始帧")
                            return get_frame(t)  # 出错时返回原始帧

                    print("使用优化的PIL实现安全动态缩放效果")
                    zoom_clip = clip.transform(safe_pil_dynamic_zoom)
                    return zoom_clip

                except ImportError:
                    print("PIL不可用，跳过PIL动态缩放方案")
                    pass

            # 回退：使用 image_transform 方法 (MoviePy 2.x 的正确 API) - 静态缩放
            if hasattr(clip, 'image_transform') and cv2 is not None:
                def safe_zoom_function(frame):
                    """对每一帧应用安全的缩放效果"""
                    try:
                        if frame is None:
                            return frame

                        h, w = frame.shape[:2]
                        scale = 1.03  # 轻微放大3%
                        new_h, new_w = max(1, int(h * scale)), max(1, int(w * scale))

                        # 确保新尺寸有效
                        if new_h <= 0 or new_w <= 0:
                            return frame

                        # 放大图像
                        resized_frame = cv2.resize(frame, (new_w, new_h))

                        # 安全的中心裁剪
                        start_x = max(0, (new_w - w) // 2)
                        start_y = max(0, (new_h - h) // 2)
                        end_x = min(new_w, start_x + w)
                        end_y = min(new_h, start_y + h)

                        if end_x <= start_x or end_y <= start_y:
                            return frame

                        cropped_frame = resized_frame[start_y:end_y, start_x:end_x]

                        # 确保最终尺寸正确
                        if cropped_frame.shape[:2] != (h, w):
                            cropped_frame = cv2.resize(cropped_frame, (w, h))

                        return cropped_frame

                    except Exception as e:
                        print(f"静态缩放处理出错: {e}, 返回原始帧")
                        return frame

                print("使用优化的 image_transform 方法添加安全静态缩放效果")
                zoom_clip = clip.image_transform(safe_zoom_function)
                return zoom_clip

            # 回退到 fl_image 方法（如果存在）
            elif hasattr(clip, 'fl_image') and cv2 is not None:
                def safe_static_zoom_function(frame):
                    """安全的静态缩放函数"""
                    try:
                        if frame is None:
                            return frame

                        h, w = frame.shape[:2]
                        scale = 1.03  # 轻微放大3%
                        new_h, new_w = max(1, int(h * scale)), max(1, int(w * scale))

                        if new_h <= 0 or new_w <= 0:
                            return frame

                        resized_frame = cv2.resize(frame, (new_w, new_h))
                        start_x = max(0, (new_w - w) // 2)
                        start_y = max(0, (new_h - h) // 2)
                        end_x = min(new_w, start_x + w)
                        end_y = min(new_h, start_y + h)

                        if end_x <= start_x or end_y <= start_y:
                            return frame

                        cropped_frame = resized_frame[start_y:end_y, start_x:end_x]

                        if cropped_frame.shape[:2] != (h, w):
                            cropped_frame = cv2.resize(cropped_frame, (w, h))

                        return cropped_frame

                    except Exception as e:
                        print(f"fl_image缩放处理出错: {e}, 返回原始帧")
                        return frame

                print("使用优化的 fl_image 方法添加安全缩放效果")
                zoom_clip = clip.fl_image(safe_static_zoom_function)
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

    def _add_fade_effects(self, clip, fade_duration):
        """
        为视频片段添加淡入淡出效果
        
        参数:
        - clip: 视频片段
        - fade_duration: 淡入淡出时长（秒）
        
        返回:
        - 添加了淡入淡出效果的视频片段
        """
        try:
            # 确保淡入淡出时长不超过片段总时长的一半
            max_fade = clip.duration / 3  # 最多占用片段时长的1/3
            actual_fade = min(fade_duration, max_fade)

            if actual_fade <= 0:
                print(f"警告: 片段时长太短，无法添加淡入淡出效果")
                return clip

            # 添加淡入淡出效果
            if hasattr(clip, 'with_effects'):
                # MoviePy 2.x 新API
                try:
                    from moviepy.video.fx import FadeIn, FadeOut
                    clip_with_fade = clip.with_effects([FadeIn(actual_fade), FadeOut(actual_fade)])
                    print(f"使用 with_effects 添加淡入淡出效果: {actual_fade:.2f}s")
                    return clip_with_fade
                except ImportError:
                    print("MoviePy FadeIn/FadeOut 效果不可用，尝试其他方法")

            # 尝试使用 fadein/fadeout 方法
            if hasattr(clip, 'fadein') and hasattr(clip, 'fadeout'):
                try:
                    clip_with_fade = clip.fadein(actual_fade).fadeout(actual_fade)
                    print(f"使用 fadein/fadeout 方法添加淡入淡出效果: {actual_fade:.2f}s")
                    return clip_with_fade
                except Exception as fade_error:
                    print(f"fadein/fadeout 方法失败: {fade_error}")

            # 尝试使用 crossfadein/crossfadeout
            if hasattr(clip, 'crossfadein') and hasattr(clip, 'crossfadeout'):
                try:
                    clip_with_fade = clip.crossfadein(actual_fade).crossfadeout(actual_fade)
                    print(f"使用 crossfadein/crossfadeout 方法添加淡入淡出效果: {actual_fade:.2f}s")
                    return clip_with_fade
                except Exception as crossfade_error:
                    print(f"crossfadein/crossfadeout 方法失败: {crossfade_error}")

            # 手动实现淡入淡出效果（使用透明度）
            try:
                def fade_function(get_frame, t):
                    frame = get_frame(t)
                    if frame is None:
                        return frame

                    duration = clip.duration
                    alpha = 1.0

                    # 淡入效果
                    if t < actual_fade:
                        alpha = t / actual_fade
                    # 淡出效果
                    elif t > duration - actual_fade:
                        alpha = (duration - t) / actual_fade

                    # 确保alpha在有效范围内
                    alpha = max(0.0, min(1.0, alpha))

                    # 应用透明度
                    if alpha < 1.0:
                        frame = (frame * alpha).astype(np.uint8)

                    return frame

                if hasattr(clip, 'transform'):
                    clip_with_fade = clip.transform(fade_function)
                    print(f"使用手动transform实现淡入淡出效果: {actual_fade:.2f}s")
                    return clip_with_fade
                else:
                    print("无法实现淡入淡出效果，返回原始片段")
                    return clip

            except Exception as manual_error:
                print(f"手动淡入淡出效果失败: {manual_error}")
                return clip

        except Exception as e:
            print(f"添加淡入淡出效果失败: {e}")
            return clip

    def _add_fade_in(self, clip, fade_duration):
        """
        为视频片段添加淡入效果
        
        参数:
        - clip: 视频片段
        - fade_duration: 淡入时长（秒）
        
        返回:
        - 添加了淡入效果的视频片段
        """
        try:
            # 确保淡入时长不超过片段总时长的一半
            max_fade = clip.duration / 2
            actual_fade = min(fade_duration, max_fade)

            if actual_fade <= 0:
                print(f"警告: 片段时长太短，无法添加淡入效果")
                return clip

            # 添加淡入效果
            if hasattr(clip, 'with_effects'):
                # MoviePy 2.x 新API
                try:
                    from moviepy.video.fx import FadeIn
                    clip_with_fade = clip.with_effects([FadeIn(actual_fade)])
                    print(f"使用 with_effects 添加淡入效果: {actual_fade:.2f}s")
                    return clip_with_fade
                except ImportError:
                    print("MoviePy FadeIn 效果不可用，尝试其他方法")

            # 尝试使用 fadein 方法
            if hasattr(clip, 'fadein'):
                try:
                    clip_with_fade = clip.fadein(actual_fade)
                    print(f"使用 fadein 方法添加淡入效果: {actual_fade:.2f}s")
                    return clip_with_fade
                except Exception as fade_error:
                    print(f"fadein 方法失败: {fade_error}")

            # 尝试使用 crossfadein
            if hasattr(clip, 'crossfadein'):
                try:
                    clip_with_fade = clip.crossfadein(actual_fade)
                    print(f"使用 crossfadein 方法添加淡入效果: {actual_fade:.2f}s")
                    return clip_with_fade
                except Exception as crossfade_error:
                    print(f"crossfadein 方法失败: {crossfade_error}")

            # 手动实现淡入效果
            try:
                def fade_in_function(get_frame, t):
                    frame = get_frame(t)
                    if frame is None:
                        return frame

                    # 淡入效果
                    if t < actual_fade:
                        alpha = t / actual_fade
                        alpha = max(0.0, min(1.0, alpha))
                        frame = (frame * alpha).astype(np.uint8)

                    return frame

                if hasattr(clip, 'transform'):
                    clip_with_fade = clip.transform(fade_in_function)
                    print(f"使用手动transform实现淡入效果: {actual_fade:.2f}s")
                    return clip_with_fade
                else:
                    print("无法实现淡入效果，返回原始片段")
                    return clip

            except Exception as manual_error:
                print(f"手动淡入效果失败: {manual_error}")
                return clip

        except Exception as e:
            print(f"添加淡入效果失败: {e}")
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
            # 方法1：创建多个0.1秒的时间片段以实现毫秒滚动效果
            timer_clips = []
            video_duration = video.duration
            time_interval = 0.005  # 100毫秒间隔

            # 计算需要的时间片段数量
            num_segments = int(video_duration / time_interval) + 1

            for i in range(num_segments):
                t = i * time_interval
                minutes = int(t // 60)
                seconds = int(t % 60)
                milliseconds = int((t % 1) * 1000)
                time_text = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

                # 创建0.1秒的时间显示片段（半透明效果）
                timer_segment = TextClip(
                    text=time_text,
                    font_size=font_size,
                    color='white',
                    font='Arial'
                ).with_opacity(0.7)  # 设置70%透明度，实现半透明效果

                # 设置持续时间和位置（居中显示）
                if hasattr(timer_segment, 'with_duration'):
                    timer_segment = timer_segment.with_duration(time_interval)
                else:
                    timer_segment = timer_segment.set_duration(time_interval)

                if hasattr(timer_segment, 'with_position'):
                    timer_segment = timer_segment.with_position('center')
                else:
                    timer_segment = timer_segment.set_position('center')

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
                ).with_opacity(0.7)  # 设置70%透明度，实现半透明效果

                if hasattr(timer_clip, 'with_duration'):
                    timer_clip = timer_clip.with_duration(video.duration)
                else:
                    timer_clip = timer_clip.set_duration(video.duration)

                if hasattr(timer_clip, 'with_position'):
                    timer_clip = timer_clip.with_position('center')
                else:
                    timer_clip = timer_clip.set_position('center')

                result = CompositeVideoClip([video, timer_clip])
                print("使用静态时间显示作为回退方案")
                return result

            except Exception as e2:
                print(f"静态时间显示也失败: {e2}")
                print("返回原始视频（不含时间显示）")
                return video

    def _combine_clips(self, beat_clips, main_video):
        """组合所有视频片段 - 带淡入淡出效果"""
        all_clips = []
        fade_duration = self.fade_duration  # 使用类属性中的淡入淡出时长

        print(f"准备组合 {len(beat_clips)} 个卡点片段和1个主视频，添加淡入淡出效果")

        # 确保所有卡点片段都有相同的尺寸并验证内容，添加淡入淡出效果
        for i, clip in enumerate(beat_clips):
            try:
                # 验证片段是否有效
                if clip.duration <= 0:
                    print(f"警告: 卡点片段 {i + 1} 持续时间无效: {clip.duration}")
                    continue

                # 强制统一尺寸
                clip = clip.resized(self.output_size)

                # 验证片段内容（检查是否为纯黑帧）
                try:
                    # 获取第一帧进行验证
                    first_frame = clip.get_frame(0)
                    if first_frame is not None and first_frame.mean() > 5:  # 避免纯黑帧
                        # 添加淡入淡出效果
                        clip_with_fade = self._add_fade_effects(clip, fade_duration)
                        all_clips.append(clip_with_fade)
                        print(f"卡点片段 {i + 1}: 尺寸 {clip.size}, 持续时间 {clip.duration:.2f}s, 已添加淡入淡出 ✓")
                    else:
                        print(f"警告: 卡点片段 {i + 1} 可能是黑帧，跳过")
                except Exception as frame_e:
                    print(f"无法验证卡点片段 {i + 1} 的帧内容: {frame_e}")
                    # 仍然添加，但标记警告
                    clip_with_fade = self._add_fade_effects(clip, fade_duration)
                    all_clips.append(clip_with_fade)
                    print(f"卡点片段 {i + 1}: 尺寸 {clip.size}, 持续时间 {clip.duration:.2f}s, 已添加淡入淡出 (未验证)")

            except Exception as e:
                print(f"处理卡点片段 {i + 1} 时出错: {e}")
                try:
                    clip = clip.resize(self.output_size)
                    clip_with_fade = self._add_fade_effects(clip, fade_duration)
                    all_clips.append(clip_with_fade)
                except:
                    print(f"跳过卡点片段 {i + 1}")
                    continue

        # 确保主视频也有正确的尺寸，并添加淡入效果
        try:
            main_video = main_video.resized(self.output_size)
            # 只给主视频添加淡入效果（开始时）
            main_video_with_fade = self._add_fade_in(main_video, fade_duration)
            print(f"主视频: 尺寸 {main_video.size}, 持续时间 {main_video.duration:.2f}s, 已添加淡入效果")
        except Exception as e:
            print(f"调整主视频尺寸时出错: {e}")
            try:
                main_video = main_video.resize(self.output_size)
                main_video_with_fade = self._add_fade_in(main_video, fade_duration)
            except:
                print("警告: 无法调整主视频尺寸")
                main_video_with_fade = main_video

        # 添加主视频到片段列表
        all_clips.append(main_video_with_fade)

        print(f"总共 {len(all_clips)} 个片段准备连接（含淡入淡出效果）")

        # 连接所有片段，使用安全的参数避免黑帧
        try:
            # 使用method='compose'确保更好的兼容性，避免黑屏
            final_video = concatenate_videoclips(all_clips, method='compose')
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

            # 再次尝试连接，使用安全参数
            final_video = concatenate_videoclips(fixed_clips, method='compose')
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
                '-i', video_path,  # 输入视频
                '-i', music_path,  # 输入音频
                '-c:v', 'copy',  # 复制视频流（不重新编码）
                '-c:a', 'aac',  # 音频编码为 AAC
                '-map', '0:v:0',  # 使用第一个文件的视频流
                '-map', '1:a:0',  # 使用第二个文件的音频流
                '-shortest',  # 使用最短的流长度
                '-y',  # 覆盖输出文件
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

    def create_picture_in_picture(self, main_clip, pip_clip,
                                  pip_position='bottom-right', pip_scale=0.25,
                                  pip_opacity=1.0, margin=20,
                                  pip_start_time=0, pip_duration=None):
        """
        创建画中画效果
        
        参数:
        - main_clip: 主视频clip（背景）
        - pip_clip: 画中画视频clip（前景小窗口）
        - pip_position: 画中画位置，可选：'top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'
        - pip_scale: 画中画缩放比例 (0.1-1.0)
        - pip_opacity: 画中画透明度 (0.0-1.0)
        - margin: 画中画距离边缘的像素距离
        - pip_start_time: 画中画开始时间（秒）
        - pip_duration: 画中画持续时间（秒），None表示使用pip_clip的完整时长
        
        返回:
        - 合成后的视频clip
        """
        try:
            print(f"创建画中画效果...")
            print(f"主视频: {main_clip.size}, 时长: {main_clip.duration:.2f}s")
            print(f"画中画: {pip_clip.size}, 时长: {pip_clip.duration:.2f}s")

            # 确保pip_scale在有效范围内
            pip_scale = max(0.1, min(1.0, pip_scale))

            # 确保pip_opacity在有效范围内
            pip_opacity = max(0.0, min(1.0, pip_opacity))

            # 计算画中画的尺寸
            main_width, main_height = main_clip.size
            pip_width = int(main_width * pip_scale)
            pip_height = int(main_height * pip_scale)

            # 调整画中画尺寸
            try:
                if hasattr(pip_clip, 'resized'):
                    resized_pip = pip_clip.resized((pip_width, pip_height))
                else:
                    resized_pip = pip_clip.resize((pip_width, pip_height))
                print(f"画中画调整到尺寸: {pip_width}x{pip_height}")
            except Exception as resize_error:
                print(f"调整画中画尺寸失败: {resize_error}")
                return main_clip

            # 设置画中画透明度
            if pip_opacity < 1.0:
                try:
                    if hasattr(resized_pip, 'with_opacity'):
                        resized_pip = resized_pip.with_opacity(pip_opacity)
                    else:
                        resized_pip = resized_pip.set_opacity(pip_opacity)
                    print(f"设置画中画透明度: {pip_opacity}")
                except Exception as opacity_error:
                    print(f"设置透明度失败: {opacity_error}")

            # 计算画中画位置
            if pip_position == 'top-left':
                position = (margin, margin)
            elif pip_position == 'top-right':
                position = (main_width - pip_width - margin, margin)
            elif pip_position == 'bottom-left':
                position = (margin, main_height - pip_height - margin)
            elif pip_position == 'bottom-right':
                position = (main_width - pip_width - margin, main_height - pip_height - margin)
            elif pip_position == 'center':
                position = ((main_width - pip_width) // 2, (main_height - pip_height) // 2)
            else:
                # 如果传入的是元组坐标，直接使用
                if isinstance(pip_position, (tuple, list)) and len(pip_position) == 2:
                    position = pip_position
                else:
                    print(f"未知的位置参数: {pip_position}，使用默认位置 bottom-right")
                    position = (main_width - pip_width - margin, main_height - pip_height - margin)

            print(f"画中画位置: {position}")

            # 设置画中画位置
            try:
                if hasattr(resized_pip, 'with_position'):
                    positioned_pip = resized_pip.with_position(position)
                else:
                    positioned_pip = resized_pip.set_position(position)
            except Exception as position_error:
                print(f"设置位置失败: {position_error}")
                return main_clip

            # 设置画中画的时间参数
            if pip_duration is not None:
                # 限制画中画时长
                pip_duration = min(pip_duration, positioned_pip.duration, main_clip.duration - pip_start_time)
                try:
                    if hasattr(positioned_pip, 'with_duration'):
                        positioned_pip = positioned_pip.with_duration(pip_duration)
                    else:
                        positioned_pip = positioned_pip.set_duration(pip_duration)
                    print(f"设置画中画时长: {pip_duration:.2f}s")
                except Exception as duration_error:
                    print(f"设置时长失败: {duration_error}")

            # 设置画中画开始时间
            if pip_start_time > 0:
                try:
                    if hasattr(positioned_pip, 'with_start'):
                        positioned_pip = positioned_pip.with_start(pip_start_time)
                    else:
                        positioned_pip = positioned_pip.set_start(pip_start_time)
                    print(f"设置画中画开始时间: {pip_start_time:.2f}s")
                except Exception as start_error:
                    print(f"设置开始时间失败: {start_error}")

            # 合成视频
            try:
                # 确保主视频没有audio问题
                if hasattr(main_clip, 'audio') and main_clip.audio is not None:
                    composite_clip = CompositeVideoClip([main_clip, positioned_pip])
                    # 保持主视频的音频
                    composite_clip = composite_clip.with_audio(main_clip.audio)
                else:
                    composite_clip = CompositeVideoClip([main_clip, positioned_pip])

                print(f"画中画合成成功!")
                print(f"最终视频: {composite_clip.size}, 时长: {composite_clip.duration:.2f}s")

                return composite_clip

            except Exception as composite_error:
                print(f"合成视频失败: {composite_error}")
                return main_clip

        except Exception as e:
            print(f"创建画中画效果失败: {str(e)}")
            return main_clip

    def create_advanced_picture_in_picture(self, main_clip, pip_clip,
                                           pip_animations=None, border_width=2,
                                           border_color='white', shadow=True):
        """
        创建高级画中画效果（带动画、边框、阴影等）
        
        参数:
        - main_clip: 主视频clip
        - pip_clip: 画中画视频clip
        - pip_animations: 动画配置字典，包含位置变化、缩放变化等
        - border_width: 边框宽度
        - border_color: 边框颜色
        - shadow: 是否添加阴影效果
        
        返回:
        - 合成后的视频clip
        """
        try:
            print("创建高级画中画效果...")

            # 基础画中画处理
            if pip_animations is None:
                # 使用默认配置
                return self.create_picture_in_picture(main_clip, pip_clip)

            # 处理动画效果
            main_width, main_height = main_clip.size

            # 动态位置动画
            if 'position_keyframes' in pip_animations:
                keyframes = pip_animations['position_keyframes']

                def position_function(t):
                    """根据时间t计算画中画位置"""
                    # 简单的线性插值
                    for i, (time, pos) in enumerate(keyframes):
                        if t <= time:
                            if i == 0:
                                return pos
                            else:
                                prev_time, prev_pos = keyframes[i - 1]
                                progress = (t - prev_time) / (time - prev_time)
                                x = prev_pos[0] + (pos[0] - prev_pos[0]) * progress
                                y = prev_pos[1] + (pos[1] - prev_pos[1]) * progress
                                return (int(x), int(y))
                    return keyframes[-1][1]  # 返回最后一个位置

                # 应用动态位置
                try:
                    if hasattr(pip_clip, 'with_position'):
                        positioned_pip = pip_clip.with_position(position_function)
                    else:
                        positioned_pip = pip_clip.set_position(position_function)
                    print("应用动态位置动画")
                except Exception as pos_error:
                    print(f"动态位置动画失败: {pos_error}")
                    positioned_pip = pip_clip
            else:
                positioned_pip = pip_clip

            # 动态缩放动画
            if 'scale_keyframes' in pip_animations:
                scale_keyframes = pip_animations['scale_keyframes']

                def scale_function(get_frame, t):
                    """根据时间t计算缩放"""
                    # 计算当前时间的缩放比例
                    current_scale = 0.25  # 默认缩放
                    for i, (time, scale) in enumerate(scale_keyframes):
                        if t <= time:
                            if i == 0:
                                current_scale = scale
                                break
                            else:
                                prev_time, prev_scale = scale_keyframes[i - 1]
                                progress = (t - prev_time) / (time - prev_time)
                                current_scale = prev_scale + (scale - prev_scale) * progress
                                break
                    else:
                        current_scale = scale_keyframes[-1][1]

                    # 获取原始帧
                    frame = get_frame(t)
                    if frame is None:
                        return frame

                    # 应用缩放
                    if cv2 is not None:
                        h, w = frame.shape[:2]
                        new_w = int(w * current_scale)
                        new_h = int(h * current_scale)
                        if new_w > 0 and new_h > 0:
                            frame = cv2.resize(frame, (new_w, new_h))

                    return frame

                # 应用动态缩放
                try:
                    if hasattr(positioned_pip, 'transform'):
                        positioned_pip = positioned_pip.transform(scale_function)
                        print("应用动态缩放动画")
                except Exception as scale_error:
                    print(f"动态缩放动画失败: {scale_error}")

            # 合成最终视频
            try:
                composite_clip = CompositeVideoClip([main_clip, positioned_pip])

                if hasattr(main_clip, 'audio') and main_clip.audio is not None:
                    composite_clip = composite_clip.with_audio(main_clip.audio)

                print("高级画中画合成成功!")
                return composite_clip

            except Exception as composite_error:
                print(f"高级画中画合成失败: {composite_error}")
                return main_clip

        except Exception as e:
            print(f"创建高级画中画效果失败: {str(e)}")
            return main_clip

    def create_text_video_clip(self, text, duration,
                               font_size=60, background_color='black',
                               text_color='white', font='Arial',
                               text_position='center', output_size=None):
        """
        创建一个带文字的视频剪辑
        
        参数:
        - text: 文字内容
        - duration: 视频时长（秒）
        - font_size: 文字大小（默认60）
        - background_color: 背景颜色（默认'black'，可以是颜色名称、十六进制颜色或RGB元组）
        - text_color: 文字颜色（默认'white'，可以是颜色名称、十六进制颜色或RGB元组）
        - font: 字体名称（默认'Arial'）
        - text_position: 文字位置（默认'center'，可以是'center', 'top', 'bottom'等或坐标元组）
        - output_size: 输出视频尺寸（默认使用类的output_size）
        
        返回:
        - 生成的视频剪辑对象
        """
        try:
            print(f"创建文字视频剪辑: '{text}'")
            print(f"参数: 时长={duration}s, 字体大小={font_size}, 背景={background_color}, 文字颜色={text_color}")

            # 确定输出尺寸
            if output_size is None:
                output_size = self.output_size

            # 创建文字剪辑
            try:
                text_clip = TextClip(
                    text=text,
                    font_size=font_size,
                    color=text_color,
                    font=font
                )
                print(f"文字剪辑创建成功，尺寸: {text_clip.size}")
            except Exception as text_error:
                print(f"创建文字剪辑失败: {text_error}")
                # 尝试使用更基础的参数
                try:
                    text_clip = TextClip(
                        text=text,
                        font_size=font_size,
                        color=text_color
                    )
                    print("使用基础参数重新创建文字剪辑")
                except Exception as text_error2:
                    print(f"文字剪辑创建完全失败: {text_error2}")
                    raise Exception(f"无法创建文字剪辑: {text_error2}")

            # 设置文字剪辑的持续时间
            try:
                if hasattr(text_clip, 'with_duration'):
                    text_clip = text_clip.with_duration(duration)
                else:
                    text_clip = text_clip.set_duration(duration)
                print(f"设置文字持续时间: {duration}s")
            except Exception as duration_error:
                print(f"设置持续时间失败: {duration_error}")
                raise

            # 设置文字位置
            try:
                if hasattr(text_clip, 'with_position'):
                    text_clip = text_clip.with_position(text_position)
                else:
                    text_clip = text_clip.set_position(text_position)
                print(f"设置文字位置: {text_position}")
            except Exception as position_error:
                print(f"设置文字位置失败: {position_error}")
                # 继续执行，使用默认位置

            # 创建背景颜色剪辑
            try:
                # 处理背景颜色参数
                if isinstance(background_color, str):
                    # 如果是字符串，检查是否是十六进制颜色
                    if background_color.startswith('#'):
                        # 十六进制颜色转RGB
                        hex_color = background_color.lstrip('#')
                        if len(hex_color) == 6:
                            bg_color = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
                        else:
                            print(f"无效的十六进制颜色: {background_color}，使用黑色")
                            bg_color = (0, 0, 0)
                    elif background_color.lower() == 'black':
                        bg_color = (0, 0, 0)
                    elif background_color.lower() == 'white':
                        bg_color = (255, 255, 255)
                    elif background_color.lower() == 'red':
                        bg_color = (255, 0, 0)
                    elif background_color.lower() == 'green':
                        bg_color = (0, 255, 0)
                    elif background_color.lower() == 'blue':
                        bg_color = (0, 0, 255)
                    elif background_color.lower() == 'yellow':
                        bg_color = (255, 255, 0)
                    elif background_color.lower() == 'cyan':
                        bg_color = (0, 255, 255)
                    elif background_color.lower() == 'magenta':
                        bg_color = (255, 0, 255)
                    else:
                        print(f"未知颜色名称: {background_color}，使用黑色")
                        bg_color = (0, 0, 0)
                elif isinstance(background_color, (tuple, list)) and len(background_color) == 3:
                    # RGB元组
                    bg_color = tuple(background_color)
                else:
                    print(f"无效的背景颜色格式: {background_color}，使用黑色")
                    bg_color = (0, 0, 0)

                print(f"背景颜色RGB: {bg_color}")

                # 使用ColorClip创建纯色背景
                try:
                    from moviepy.video.VideoClip import ColorClip
                    background_clip = ColorClip(
                        size=output_size,
                        color=bg_color,
                        duration=duration
                    )
                    print(f"使用ColorClip创建背景，尺寸: {output_size}")
                except ImportError:
                    # 如果ColorClip不可用，尝试使用其他方法
                    try:
                        from moviepy import ColorClip
                        background_clip = ColorClip(
                            size=output_size,
                            color=bg_color,
                            duration=duration
                        )
                        print(f"使用备用ColorClip创建背景")
                    except ImportError:
                        # 最后的回退方案：创建一个纯色的numpy数组视频
                        print("ColorClip不可用，使用numpy数组创建背景")
                        import numpy as np
                        from moviepy.video.VideoClip import VideoClip

                        def make_frame(t):
                            # 创建纯色帧
                            frame = np.full((output_size[1], output_size[0], 3), bg_color, dtype=np.uint8)
                            return frame

                        background_clip = VideoClip(make_frame, duration=duration)
                        background_clip = background_clip.set_fps(24)  # 设置帧率
                        print(f"使用numpy数组创建背景")

            except Exception as bg_error:
                print(f"创建背景剪辑失败: {bg_error}")
                raise

            # 合成文字和背景
            try:
                final_clip = CompositeVideoClip([background_clip, text_clip], size=output_size)
                print(f"合成最终视频剪辑成功，尺寸: {final_clip.size}, 时长: {final_clip.duration:.2f}s")

                # 清理临时资源
                try:
                    background_clip.close()
                    text_clip.close()
                except:
                    pass

                return final_clip

            except Exception as composite_error:
                print(f"合成视频剪辑失败: {composite_error}")

                # 清理资源
                try:
                    background_clip.close()
                    text_clip.close()
                except:
                    pass

                raise

        except Exception as e:
            print(f"创建文字视频剪辑失败: {str(e)}")
            raise

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

    # 示例1：创建卡点视频
    if True:  # 设置为True启用卡点视频示例
        # 定义参数
        video1_path = "/Users/yujian/Downloads/video0_20250802_140017.mp4"  # 第一个视频路径
        video2_path = "/Users/yujian/Downloads/video1_20250802_140017.mp4"  # 第二个视频路径
        beat_times = [0.0, 4.5, 6.5, 9.8, 19, 23]  # 卡点时间数组 (秒)

        processor.create_pip_video(video1_path, video2_path, "output/121212.mp4", "98", 100, (20,20) )

        # 预览卡点 (可选)
        # processor.preview_beat_points(video1_path, beat_times)

        # # 处理视频
        # processor.create_beat_video(
        #     video1_path=video1_path,
        #     video2_path=video2_path,
        #     beat_times=beat_times,
        #     output_path="final_beat_video.mp4",
        #     speed_factor=5,  # 第二个视频1.5倍速播放
        #     font_size=120,  # 时间显示字体大小
        #     background_music_path="jiggy boogy.mp3"  # 使用默认背景音乐 jiggy boogy.mp3，或指定其他音乐文件路径
        # )

    # # 示例2：创建基础画中画视频
    # if True:  # 设置为True启用画中画示例
    #     try:
    #         # 加载两个视频clip
    #         main_video = VideoFileClip("video1.mp4")  # 主视频（背景）
    #         pip_video = VideoFileClip("video2.mp4")  # 画中画视频（前景小窗口）
    #
    #         # 创建基础画中画效果
    #         pip_result = processor.create_picture_in_picture(
    #             main_clip=main_video,
    #             pip_clip=pip_video,
    #             pip_position='bottom-right',  # 画中画位置：右下角
    #             pip_scale=0.3,  # 画中画大小：主视频的30%
    #             pip_opacity=0.9,  # 画中画透明度：90%
    #             margin=30,  # 距离边缘30像素
    #             pip_start_time=2.0,  # 画中画在第2秒开始显示
    #             pip_duration=10.0  # 画中画显示10秒
    #         )
    #
    #         # 保存画中画视频
    #         pip_result.write_videofile("output/pip_video.mp4", logger=None)
    #
    #         # 清理资源
    #         main_video.close()
    #         pip_video.close()
    #         pip_result.close()
    #
    #         print("基础画中画视频创建成功！")
    #
    #     except Exception as e:
    #         print(f"基础画中画示例失败: {e}")
    #
    # # # 示例3：创建高级画中画视频（带动画效果）
    # # if False:  # 设置为True启用高级画中画示例
    # #     try:
    # #         # 加载两个视频clip
    # #         main_video = VideoFileClip("video1.mp4")
    # #         pip_video = VideoFileClip("video2.mp4")
    # #
    # #         # 定义动画配置
    # #         animations = {
    # #             # 位置动画：画中画从左上角移动到右下角
    # #             'position_keyframes': [
    # #                 (0, (50, 50)),  # 第0秒：左上角
    # #                 (5, (400, 200)),  # 第5秒：中间位置
    # #                 (10, (1200, 600))  # 第10秒：右下角
    # #             ],
    # #             # 缩放动画：画中画大小变化
    # #             'scale_keyframes': [
    # #                 (0, 0.2),  # 第0秒：20%大小
    # #                 (5, 0.4),  # 第5秒：40%大小
    # #                 (10, 0.25)  # 第10秒：25%大小
    # #             ]
    # #         }
    # #
    # #         # 创建高级画中画效果
    # #         advanced_pip_result = processor.create_advanced_picture_in_picture(
    # #             main_clip=main_video,
    # #             pip_clip=pip_video,
    # #             pip_animations=animations,
    # #             border_width=3,
    # #             border_color='white',
    # #             shadow=True
    # #         )
    # #
    # #         # 保存高级画中画视频
    # #         advanced_pip_result.write_videofile("output/advanced_pip_video.mp4", logger=None)
    # #
    # #         # 清理资源
    # #         main_video.close()
    # #         pip_video.close()
    # #         advanced_pip_result.close()
    # #
    # #         print("高级画中画视频创建成功！")
    # #
    # #     except Exception as e:
    # #         print(f"高级画中画示例失败: {e}")
    # #
    # # # 示例4：多个不同位置的画中画
    # # if False:  # 设置为True启用多画中画示例
    # #     try:
    # #         # 加载视频clip
    # #         main_video = VideoFileClip("video1.mp4")
    # #         pip_video1 = VideoFileClip("video2.mp4")
    # #         pip_video2 = VideoFileClip("video3.mp4")
    # #
    # #         # 创建第一个画中画（右上角）
    # #         temp_result = processor.create_picture_in_picture(
    # #             main_clip=main_video,
    # #             pip_clip=pip_video1,
    # #             pip_position='top-right',
    # #             pip_scale=0.25,
    # #             pip_start_time=0,
    # #             pip_duration=8
    # #         )
    # #
    # #         # 在第一个画中画的基础上添加第二个画中画（左下角）
    # #         final_result = processor.create_picture_in_picture(
    # #             main_clip=temp_result,
    # #             pip_clip=pip_video2,
    # #             pip_position='bottom-left',
    # #             pip_scale=0.2,
    # #             pip_start_time=3,
    # #             pip_duration=6
    # #         )
    # #
    # #         # 保存多画中画视频
    # #         final_result.write_videofile("output/multi_pip_video.mp4", logger=None)
    # #
    # #         # 清理资源
    # #         main_video.close()
    # #         pip_video1.close()
    # #         pip_video2.close()
    # #         temp_result.close()
    # #         final_result.close()
    # #
    # #         print("多画中画视频创建成功！")
    # #
    # #     except Exception as e:
    # #         print(f"多画中画示例失败: {e}")
