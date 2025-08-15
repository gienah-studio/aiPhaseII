# 认证服务模板 - 只导入必需的模型
from shared.models.base_model import BaseModel
from shared.models.login_log import LoginLog
from shared.models.user import User
from shared.models.original_user import OriginalUser
from shared.models.agents import Agents
from shared.models.userinfo import UserInfo

# 虚拟订单系统模型
from shared.models.tasks import Tasks
from shared.models.virtual_order_pool import VirtualOrderPool
from shared.models.virtual_order_reports import VirtualOrderReports
from shared.models.virtual_customer_service import VirtualCustomerService

# 资源库系统模型
from shared.models.resource_categories import ResourceCategories
from shared.models.resource_upload_batches import ResourceUploadBatches
from shared.models.resource_images import ResourceImages

# 学生任务系统模型
from shared.models.studenttask import StudentTask

# 导出所有模型
__all__ = [
    'BaseModel',
    'LoginLog',
    'User',
    'OriginalUser',
    'Agents',
    'UserInfo',
    'Tasks',
    'VirtualOrderPool',
    'VirtualOrderReports',
    'VirtualCustomerService',
    'ResourceCategories',
    'ResourceUploadBatches',
    'ResourceImages',
    'StudentTask',
]
