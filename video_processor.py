import numpy as np
import moviepy as mp
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
import os


class VideoProcessor:
    """
    基于MoviePy 2.x的视频处理类
    实现卡点动画、转场效果和时间进度显示
    """

    def __init__(self):
        self.output_size = (1920, 1080)  # 输出视频尺寸
        self.transition_duration = 0.5  # 转场时长
        self.beat_frame_duration = 1.0  # 每个卡点帧显示时长（增加到1秒）

    def create_beat_video(self, video1_path, video2_path, beat_times,
                          output_path="output_beat_video.mp4",
                          speed_factor=1.5, font_size=60):
        """
        创建卡点视频

        参数:
        - video1_path: 第一个视频路径
        - video2_path: 第二个视频路径
        - beat_times: 卡点时间数组 (秒)
        - output_path: 输出文件路径
        - speed_factor: 第二个视频的播放速度倍数
        - font_size: 时间显示字体大小
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

            # 输出视频
            final_video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac'
            )

            # 清理资源
            video1.close()
            video2.close()
            final_video.close()

            print(f"视频处理完成，保存至: {output_path}")

        except Exception as e:
            print(f"视频处理出错: {str(e)}")
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
        """添加简单的缩放效果（不使用fl方法）"""
        try:
            # 创建一个稍微放大的版本，然后调整回原尺寸
            # 这会产生一个微妙的缩放效果
            enlarged_size = (int(self.output_size[0] * 1.1), int(self.output_size[1] * 1.1))

            if hasattr(clip, 'resized'):
                # 先放大
                enlarged_clip = clip.resized(enlarged_size)
                # 再调整回原尺寸（会有裁剪效果）
                zoom_clip = enlarged_clip.resized(self.output_size)
            else:
                enlarged_clip = clip.resize(enlarged_size)
                zoom_clip = enlarged_clip.resize(self.output_size)

            return zoom_clip
        except Exception as e:
            print(f"添加缩放效果失败: {e}")
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
        speed_factor=1.5,  # 第二个视频1.5倍速播放
        font_size=60  # 时间显示字体大小
    )