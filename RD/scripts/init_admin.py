from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.models.user import User
from shared.models.organization import Organization
from shared.models.department import Department
from shared.models.enterprise_info import EnterpriseInfo
from shared.utils.security import get_password_hash, verify_password
from shared.database.session import Base
from shared.config import settings
import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def init_admin():
    # 创建数据库连接
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 1. 创建默认组织
        org = db.query(Organization).filter_by(id=1).first()
        if not org:
            org = Organization(
                id=1,
                name="默认组织",
                status=True,
                create_time=datetime.datetime.now()
            )
            db.add(org)
            db.flush()
            logger.info("Created default organization")

        # 2. 创建默认企业
        enterprise = db.query(EnterpriseInfo).filter_by(id=1).first()
        if not enterprise:
            enterprise = EnterpriseInfo(
                id=1,
                name="默认企业",
                identification_code="DEFAULT001",
                organization_id=org.id,
                status=True,
                create_time=datetime.datetime.now()
            )
            db.add(enterprise)
            db.flush()
            logger.info("Created default enterprise")

        # 3. 创建根部门
        dept = db.query(Department).filter_by(id=1).first()
        if not dept:
            dept = Department(
                id=1,
                name="总部",
                parent_id=None,
                enterprise_id=enterprise.id,
                organization_id=org.id,
                status=True,
                create_time=datetime.datetime.now()
            )
            db.add(dept)
            db.flush()
            logger.info("Created root department")

        # 4. 创建或更新admin用户
        admin = db.query(User).filter_by(account="admin").first()
        plain_password = "123456"
        hashed_password = get_password_hash(plain_password)
        logger.debug(f"Generated hash for password: {hashed_password}")
        
        # 验证新生成的哈希是否可以正确验证
        test_verify = verify_password(plain_password, hashed_password)
        logger.debug(f"Test verification result: {test_verify}")
        
        if admin:
            # 更新现有admin用户
            admin.name = "系统管理员"
            admin.password = hashed_password
            admin.status = True
            admin.user_type = 2
            admin.organization_id = org.id
            admin.enterprise_id = enterprise.id
            admin.department_id = dept.id
            logger.info("Updated admin user")
        else:
            # 创建新的admin用户
            admin = User(
                name="系统管理员",
                account="admin",
                password=hashed_password,
                status=True,
                user_type=2,
                organization_id=org.id,
                enterprise_id=enterprise.id,
                department_id=dept.id,
                create_time=datetime.datetime.now()
            )
            db.add(admin)
            logger.info("Created new admin user")

        # 提交所有更改
        db.commit()
        logger.info("Admin user initialized successfully!")
        
        # 最后验证一次
        admin = db.query(User).filter_by(account="admin").first()
        final_verify = verify_password(plain_password, admin.password)
        logger.debug(f"Final verification test: {final_verify}")

    except Exception as e:
        logger.error(f"Error initializing admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_admin() 