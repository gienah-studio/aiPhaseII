from datetime import datetime, timezone, timedelta

def convert_datetime_to_utc(dt: datetime) -> datetime:
    """
    将datetime对象转换为UTC时间
    
    Args:
        dt: datetime对象
        
    Returns:
        转换后的UTC datetime对象
    """
    if dt.tzinfo is None:
        # 如果时间没有时区信息,假定是UTC时间
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc) 