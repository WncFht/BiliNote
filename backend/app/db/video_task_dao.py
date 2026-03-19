from app.db.models.video_tasks import VideoTask
from app.db.engine import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


# 插入任务
def insert_video_task(video_id: str, platform: str, task_id: str):
    db = next(get_db())
    try:
        task = VideoTask(video_id=video_id, platform=platform, task_id=task_id)
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info(f"Video task inserted successfully. video_id: {video_id}, platform: {platform}, task_id: {task_id}")
    except Exception as e:
        logger.error(f"Failed to insert video task: {e}")
    finally:
        db.close()


# 查询任务（最新一条）
def get_task_by_video(video_id: str, platform: str):
    db = next(get_db())
    try:
        task = (
            db.query(VideoTask)
            .filter_by(video_id=video_id, platform=platform)
            .order_by(VideoTask.created_at.desc())
            .first()
        )
        if task:
            logger.info(f"Task found for video_id: {video_id} and platform: {platform}")
            return task.task_id
        else:
            logger.info(f"No task found for video_id: {video_id} and platform: {platform}")
            return None
    except Exception as e:
        logger.error(f"Failed to get task by video: {e}")
    finally:
        db.close()


def list_video_tasks(limit: int = 50):
    db = next(get_db())
    try:
        return (
            db.query(VideoTask)
            .order_by(VideoTask.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def delete_task_by_id(task_id: str) -> int:
    db = next(get_db())
    try:
        deleted = db.query(VideoTask).filter_by(task_id=task_id).delete()
        db.commit()
        logger.info(f"Task deleted for task_id: {task_id}, deleted={deleted}")
        return deleted
    except Exception as e:
        logger.error(f"Failed to delete task by task_id: {e}")
        raise
    finally:
        db.close()


# 删除任务
def delete_task_by_video(video_id: str, platform: str):
    db = next(get_db())
    try:
        deleted = (
            db.query(VideoTask)
            .filter_by(video_id=video_id, platform=platform)
            .delete()
        )
        db.commit()
        logger.info(f"Task(s) deleted for video_id: {video_id} and platform: {platform}, deleted={deleted}")
        return deleted
    except Exception as e:
        logger.error(f"Failed to delete task by video: {e}")
        raise
    finally:
        db.close()
