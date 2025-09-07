import os
import time
from datetime import datetime
from PIL import Image, ImageGrab
from io import BytesIO
import json
from typing import Optional


class ImageUtils:
    """图片处理工具类"""
    
    @staticmethod
    def compress_image(image, max_size_kb=1024, quality=85):
        """
        压缩图片至指定大小以下
        
        Args:
            image: PIL.Image对象
            max_size_kb: 最大文件大小（KB）
            quality: 初始质量值（1-100）
            
        Returns:
            PIL.Image: 压缩后的图片对象
        """
        # 转换为RGB模式（去除透明通道）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 使用BytesIO测试压缩后的大小
        output = BytesIO()
        image.save(output, format='JPEG', quality=quality)
        size_kb = len(output.getvalue()) / 1024
        
        # 如果大小已经小于要求，直接返回
        if size_kb <= max_size_kb:
            return image
        
        # 如果仍然太大，降低质量
        while size_kb > max_size_kb and quality > 10:
            quality -= 5
            output = BytesIO()
            image.save(output, format='JPEG', quality=quality)
            size_kb = len(output.getvalue()) / 1024
        
        # 如果降低质量后仍然太大，则缩小尺寸
        if size_kb > max_size_kb:
            # 计算缩放比例
            scale = (max_size_kb / size_kb) ** 0.5
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)
            
            # 缩放图片
            image = image.resize((new_width, new_height), Image.LANCZOS)
        
        return image
    
    @staticmethod
    def save_image_from_clipboard(case_id, images_dir='images'):
        """
        从剪贴板保存图片
        
        Args:
            case_id: 测试用例ID
            images_dir: 图片保存目录
            
        Returns:
            str: 保存的图片路径，如果没有图片则返回None
        """
        # 确保目录存在
        os.makedirs(images_dir, exist_ok=True)
        
        # 从剪贴板获取图片
        image = ImageGrab.grabclipboard()
        
        if image is None or not isinstance(image, Image.Image):
            return None
        
        # 压缩图片
        compressed_image = ImageUtils.compress_image(image)
        
        # 生成文件名
        timestamp = int(time.time())
        filename = f"{case_id}_{timestamp}.jpg"
        filepath = os.path.join(images_dir, filename)
        
        # 保存图片
        compressed_image.save(filepath, 'JPEG')
        
        return filepath
    
    @staticmethod
    def save_image_from_file(case_id, file_path, images_dir='images'):
        """
        从文件保存图片
        
        Args:
            case_id: 测试用例ID
            file_path: 原图片文件路径
            images_dir: 图片保存目录
            
        Returns:
            str: 保存的图片路径
        """
        # 确保目录存在
        os.makedirs(images_dir, exist_ok=True)
        
        # 打开图片
        image = Image.open(file_path)
        
        # 压缩图片
        compressed_image = ImageUtils.compress_image(image)
        
        # 生成文件名
        timestamp = int(time.time())
        filename = f"{case_id}_{timestamp}.jpg"
        filepath = os.path.join(images_dir, filename)
        
        # 保存图片
        compressed_image.save(filepath, 'JPEG')
        
        return filepath
        
    @staticmethod
    def copy_images_for_export(image_paths, export_dir):
        """
        复制图片到导出目录
        
        Args:
            image_paths: 图片路径列表
            export_dir: 导出目录
            
        Returns:
            dict: 原路径到新路径的映射
        """
        if not image_paths:
            return {}
            
        # 确保导出图片目录存在
        images_export_dir = os.path.join(export_dir, 'images')
        os.makedirs(images_export_dir, exist_ok=True)
        
        path_mapping = {}
        
        for original_path in image_paths:
            if not original_path or not os.path.exists(original_path):
                continue
                
            # 获取文件名
            filename = os.path.basename(original_path)
            new_path = os.path.join(images_export_dir, filename)
            
            # 复制文件
            try:
                from shutil import copy2
                copy2(original_path, new_path)
                path_mapping[original_path] = os.path.join('images', filename)
            except Exception as e:
                print(f"复制图片失败: {e}")
                
        return path_mapping


class DateUtils:
    """日期处理工具类"""
    
    @staticmethod
    def timestamp_to_string(timestamp):
        """
        将时间戳转换为可读字符串
        
        Args:
            timestamp: Unix时间戳
            
        Returns:
            str: 格式化的日期时间字符串
        """
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def string_to_timestamp(date_string):
        """
        将日期字符串转换为时间戳
        
        Args:
            date_string: 日期字符串，格式为'YYYY-MM-DD'
            
        Returns:
            int: Unix时间戳
        """
        try:
            dt = datetime.strptime(date_string, '%Y-%m-%d')
            return int(dt.timestamp())
        except ValueError:
            return None


class SettingsUtils:
    """应用设置读写工具"""
    SETTINGS_PATH = os.path.join('data', 'settings.json')

    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(SettingsUtils.SETTINGS_PATH), exist_ok=True)

    @staticmethod
    def read_settings():
        SettingsUtils._ensure_dir()
        if not os.path.exists(SettingsUtils.SETTINGS_PATH):
            return {}
        try:
            with open(SettingsUtils.SETTINGS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except Exception:
            return {}

    @staticmethod
    def write_settings(data: dict):
        SettingsUtils._ensure_dir()
        try:
            with open(SettingsUtils.SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"写入设置失败: {e}")

    @staticmethod
    def get_last_collection_name():
        data = SettingsUtils.read_settings()
        return data.get('last_collection_name')

    @staticmethod
    def set_last_collection_name(name: Optional[str]):
        data = SettingsUtils.read_settings()
        if name:
            data['last_collection_name'] = name
        SettingsUtils.write_settings(data)