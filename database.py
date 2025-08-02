import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import DB_PATH
from peewee import *

# 配置日志
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置类"""

    def __init__(self, db_path: str = 'app.db'):
        self.db_path = db_path
        self.database = SqliteDatabase(db_path)

    def get_database(self):
        return self.database


# 全局数据库实例
db_config = DatabaseConfig(DB_PATH)
db = db_config.get_database()


class BaseModel(Model):
    """基础模型类"""
    id = AutoField(primary_key=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """将模型转换为字典"""
        return {
            field.name: getattr(self, field.name)
            for field in self._meta.fields.values()
        }


class CRUDMixin:
    """CRUD操作混入类"""

    @classmethod
    def create_record(cls, **kwargs) -> 'BaseModel':
        """创建记录"""
        try:
            return cls.create(**kwargs)
        except Exception as e:
            logger.error(f"创建记录失败: {str(e)}")
            raise

    @classmethod
    def get_by_id(cls, record_id: int) -> Optional['BaseModel']:
        """根据ID获取记录"""
        try:
            return cls.get_by_id(record_id)
        except cls.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"获取记录失败: {str(e)}")
            raise

    @classmethod
    def get_or_create(cls, **kwargs) -> tuple:
        """获取或创建记录"""
        try:
            return cls.get_or_create(**kwargs)
        except Exception as e:
            logger.error(f"获取或创建记录失败: {str(e)}")
            raise

    @classmethod
    def update_record(cls, record_id: int, **kwargs) -> int:
        """更新记录"""
        try:
            kwargs['updated_at'] = datetime.now()
            return cls.update(**kwargs).where(cls.id == record_id).execute()
        except Exception as e:
            logger.error(f"更新记录失败: {str(e)}")
            raise

    @classmethod
    def delete_record(cls, record_id: int) -> int:
        """删除记录"""
        try:
            return cls.delete().where(cls.id == record_id).execute()
        except Exception as e:
            logger.error(f"删除记录失败: {str(e)}")
            raise

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> List['BaseModel']:
        """获取所有记录"""
        try:
            query = cls.select()
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            return list(query)
        except Exception as e:
            logger.error(f"获取记录列表失败: {str(e)}")
            raise

    @classmethod
    def count_records(cls) -> int:
        """统计记录数量"""
        try:
            return cls.select().count()
        except Exception as e:
            logger.error(f"统计记录失败: {str(e)}")
            raise

    @classmethod
    def filter_records(cls, **conditions) -> List['BaseModel']:
        """根据条件过滤记录"""
        try:
            query = cls.select()
            for field, value in conditions.items():
                if hasattr(cls, field):
                    query = query.where(getattr(cls, field) == value)
            return list(query.dicts())
        except Exception as e:
            logger.error(f"过滤记录失败: {str(e)}")
            raise


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id = CharField(unique=True, max_length=50)
    status = CharField(max_length=20, default='pending')  # pending, processing, completed, error
    message = TextField(default='')
    progress = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)
    completed_at = DateTimeField(null=True)
    video_filename = CharField(max_length=255, null=True)
    video_url = CharField(max_length=500, null=True)
    status_url = CharField(max_length=500, null=True)

    class Meta:
        table_name = 'task_status'

    @classmethod
    def get_task_status(cls, task_id: str) -> dict:
        """获取任务状态"""
        try:
            task = TaskStatus.get(cls.task_id == task_id)
            return {
                "status": task.status,
                "message": task.message,
                "progress": task.progress,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "video_filename": task.video_filename,
                "video_url": task.video_url,
                "status_url": task.status_url
            }
        except cls.DoesNotExist:
            return None

    @classmethod
    def update_task_status(cls, task_id: str, **kwargs):
        """更新任务状态"""
        try:
            task = cls.get(cls.task_id == task_id)
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.save()
            return True
        except cls.DoesNotExist:
            return False

    @classmethod
    def create_task_status(cls, task_id: str, **kwargs):
        """创建新的任务状态"""
        return cls.create(task_id=task_id, **kwargs)

    @classmethod
    def task_exists(cls, task_id: str) -> bool:
        """检查任务是否存在"""
        return cls.select().where(cls.task_id == task_id).exists()


def create_tables():
    """Create database tables if they don't exist"""
    with db:
        db.create_tables([TaskStatus], safe=True)
