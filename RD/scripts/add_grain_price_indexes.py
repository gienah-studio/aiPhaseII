#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
添加粮食价格报备表的性能优化索引

此脚本用于向grain_price_approval表添加组合索引，以提高查询性能。
执行此脚本前请确保已备份数据库，并在非生产环境下测试。
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("add_indexes")

# 数据库连接信息
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "password")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "guanglangfa_oa")

# 构建数据库连接URL
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 需要添加的索引列表
INDEXES = [
    # 新索引，避免与已有索引重复
    {
        "name": "idx_enterprise_status",
        "columns": "enterprise_id, status",
        "comment": "企业和状态组合索引"
    },
    {
        "name": "idx_enterprise_create_time",
        "columns": "enterprise_id, create_time",
        "comment": "企业和创建时间组合索引"
    },
    {
        "name": "idx_handler_step_status",
        "columns": "current_handler_id, current_step, status",
        "comment": "处理人、步骤和状态组合索引"
    },
    {
        "name": "idx_applicant_status",
        "columns": "applicant_id, status",
        "comment": "申请人和状态组合索引"
    },
    {
        "name": "idx_upstream_status",
        "columns": "upstream_status",
        "comment": "上游审批状态索引"
    },
    {
        "name": "idx_fill_in_unit",
        "columns": "fill_in_unit",
        "comment": "填报单位索引"
    },
    {
        "name": "idx_batch_no",
        "columns": "batch_no",
        "comment": "批次号索引"
    }
]

def add_index(engine, table_name, index_name, columns, comment):
    """添加索引"""
    try:
        # 检查索引是否已存在
        check_sql = f"""
        SELECT COUNT(*) as count 
        FROM information_schema.statistics 
        WHERE table_schema = '{DB_NAME}' 
        AND table_name = '{table_name}' 
        AND index_name = '{index_name}'
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(check_sql))
            row = result.fetchone()
            
            if row[0] > 0:
                logger.info(f"索引 {index_name} 已存在，跳过创建")
                return True
            
            # 创建索引
            create_index_sql = f"""
            CREATE INDEX {index_name} ON {table_name} ({columns}) COMMENT '{comment}'
            """
            conn.execute(text(create_index_sql))
            conn.commit()
            
            logger.info(f"成功创建索引 {index_name}")
            return True
    except Exception as e:
        logger.error(f"创建索引 {index_name} 失败: {str(e)}")
        return False

def main():
    """主函数"""
    try:
        logger.info("开始添加索引...")
        
        # 创建数据库引擎
        engine = create_engine(DB_URL)
        
        # 添加所有索引
        success_count = 0
        for index in INDEXES:
            if add_index(
                engine,
                "grain_price_approval",
                index["name"],
                index["columns"],
                index["comment"]
            ):
                success_count += 1
        
        logger.info(f"索引添加完成，成功 {success_count}/{len(INDEXES)}")
        
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 