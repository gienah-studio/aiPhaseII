from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from shared.database.session import Base
from datetime import datetime

class UserInfo(Base):
    """用户信息表模型"""
    __tablename__ = "userinfo"

    roleId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    userId = Column(Integer, ForeignKey("user.id"), nullable=False, comment="用户ID")
    studentId = Column(Integer, nullable=True, comment="学员ID")
    name = Column(String(255), nullable=True, comment="姓名")
    id_card = Column(String(255), nullable=True, comment="身份证号")
    phone_number = Column(String(255), nullable=True, comment="手机号")
    bank_card = Column(String(255), nullable=True, comment="银行卡号")
    account = Column(String(255), nullable=True, comment="账号")
    initial_password = Column(String(255), nullable=True, comment="初始密码")
    avatar_url = Column(Text, nullable=True, comment="头像URL")
    agentId = Column(Integer, ForeignKey("agents.id"), nullable=True, comment="代理ID")
    level = Column(String(255), nullable=True, comment="级别: 0-管理员, 1-一级代理, 2-二级代理, 3-学员, 4-企业代理, 5-个人代理, -1-商业贷款, -2-个体工商户")
    parentId = Column(Integer, nullable=False, default=0, comment="父级ID")
    isDeleted = Column(Boolean, default=False, comment="是否删除")
    material = Column(Text, nullable=True, comment="资料")
    identityDocs = Column(Text, nullable=True, comment="身份证/户口本/居住证明")
    marriageCert = Column(Text, nullable=True, comment="婚姻状况证明(结婚证或单身证明)")
    incomeProof = Column(Text, nullable=True, comment="收入和财产证明")
    creditReport = Column(Text, nullable=True, comment="征信报告")
    houseContract = Column(Text, nullable=True, comment="购房合同和首付款收据")
    businessNames = Column(Text, nullable=True, comment="营业执照名称备选项")
    operatorName = Column(Text, nullable=True, comment="经营者姓名")
    idCardPhotos = Column(Text, nullable=True, comment="身份证照片")
    businessScope = Column(Text, nullable=True, comment="经营范围")
    business_license = Column(Integer, nullable=True, comment="企业证件号")
    personal_license = Column(Integer, nullable=True, comment="个人证件号")
    referralInfo = Column(String(255), nullable=True, comment="填写选项（谁推荐或谁的管理下）")
    packageType = Column(Text, nullable=True, comment="套餐选项（类型—3999类型二18888类型三0元启动）")
    needsComputer = Column(Text, nullable=False, comment="租借电脑选项（是否）")
    orderChannels = Column(Text, nullable=True, comment="接单渠道选项（淘宝，抖音，b站，其他）")
    bank_name = Column(String(255), nullable=True, comment="开户行名称")

    # 关联关系
    agent = relationship("Agents", back_populates="userinfos")
    user = relationship("OriginalUser", back_populates="userinfo")
