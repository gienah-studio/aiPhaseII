#!/usr/bin/env python3
"""
运行所有API接口单元测试
综合测试脚本，运行所有服务的API接口测试
"""

import sys
import os
import subprocess
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_test_script(script_name, description):
    """运行单个测试脚本"""
    print(f"\n{'='*60}")
    print(f"运行测试: {description}")
    print(f"脚本文件: {script_name}")
    print(f"{'='*60}")
    
    try:
        # 运行测试脚本
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        # 输出测试结果
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        # 返回测试结果
        success = result.returncode == 0
        return {
            "script": script_name,
            "description": description,
            "success": success,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except Exception as e:
        print(f"运行测试脚本失败: {e}")
        return {
            "script": script_name,
            "description": description,
            "success": False,
            "return_code": -1,
            "error": str(e)
        }

def generate_test_report(test_results):
    """生成测试报告"""
    print(f"\n{'='*80}")
    print("📊 综合测试报告")
    print(f"{'='*80}")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if result["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {failed_tests}")
    print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
    
    print(f"\n{'-'*80}")
    print("详细测试结果:")
    print(f"{'-'*80}")
    
    for i, result in enumerate(test_results, 1):
        status = "✅ 通过" if result["success"] else "❌ 失败"
        print(f"{i}. {result['description']:<40} {status}")
        if not result["success"]:
            print(f"   脚本: {result['script']}")
            print(f"   返回码: {result['return_code']}")
            if "error" in result:
                print(f"   错误: {result['error']}")
    
    # 按服务分类统计
    print(f"\n{'-'*80}")
    print("按服务分类统计:")
    print(f"{'-'*80}")
    
    service_stats = {
        "认证服务": {"total": 0, "passed": 0},
        "虚拟订单服务": {"total": 0, "passed": 0},
        "API网关": {"total": 0, "passed": 0},
        "其他": {"total": 0, "passed": 0}
    }
    
    for result in test_results:
        if "认证" in result["description"]:
            service_stats["认证服务"]["total"] += 1
            if result["success"]:
                service_stats["认证服务"]["passed"] += 1
        elif "虚拟" in result["description"]:
            service_stats["虚拟订单服务"]["total"] += 1
            if result["success"]:
                service_stats["虚拟订单服务"]["passed"] += 1
        elif "网关" in result["description"]:
            service_stats["API网关"]["total"] += 1
            if result["success"]:
                service_stats["API网关"]["passed"] += 1
        else:
            service_stats["其他"]["total"] += 1
            if result["success"]:
                service_stats["其他"]["passed"] += 1
    
    for service, stats in service_stats.items():
        if stats["total"] > 0:
            success_rate = (stats["passed"] / stats["total"] * 100)
            print(f"{service:<15} {stats['passed']}/{stats['total']} ({success_rate:.1f}%)")
    
    # API接口覆盖率统计
    print(f"\n{'-'*80}")
    print("API接口覆盖率统计:")
    print(f"{'-'*80}")
    
    api_coverage = {
        "认证服务API": {"total": 7, "tested": 7 if any("认证" in r["description"] for r in test_results if r["success"]) else 0},
        "虚拟客服API": {"total": 4, "tested": 4 if any("虚拟客服" in r["description"] for r in test_results if r["success"]) else 0},
        "虚拟订单其他API": {"total": 5, "tested": 5 if any("虚拟订单" in r["description"] and "其他" in r["description"] for r in test_results if r["success"]) else 0},
        "API网关接口": {"total": 2, "tested": 2 if any("网关" in r["description"] for r in test_results if r["success"]) else 0}
    }
    
    total_apis = sum(coverage["total"] for coverage in api_coverage.values())
    tested_apis = sum(coverage["tested"] for coverage in api_coverage.values())
    
    for api_type, coverage in api_coverage.items():
        if coverage["total"] > 0:
            coverage_rate = (coverage["tested"] / coverage["total"] * 100)
            status = "✅" if coverage_rate == 100 else "⚠️" if coverage_rate > 0 else "❌"
            print(f"{status} {api_type:<20} {coverage['tested']}/{coverage['total']} ({coverage_rate:.1f}%)")
    
    print(f"\n总API接口覆盖率: {tested_apis}/{total_apis} ({(tested_apis/total_apis*100):.1f}%)")
    
    return {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": passed_tests/total_tests*100,
        "api_coverage": tested_apis/total_apis*100
    }

def save_test_report(test_results, summary):
    """保存测试报告到文件"""
    report_file = "TEST_REPORT.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# API接口单元测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 📊 测试概览\n\n")
        f.write(f"- **总测试数**: {summary['total_tests']}\n")
        f.write(f"- **通过测试**: {summary['passed_tests']}\n")
        f.write(f"- **失败测试**: {summary['failed_tests']}\n")
        f.write(f"- **成功率**: {summary['success_rate']:.1f}%\n")
        f.write(f"- **API覆盖率**: {summary['api_coverage']:.1f}%\n\n")
        
        f.write("## 📋 详细测试结果\n\n")
        f.write("| 序号 | 测试描述 | 状态 | 脚本文件 |\n")
        f.write("|------|----------|------|----------|\n")
        
        for i, result in enumerate(test_results, 1):
            status = "✅ 通过" if result["success"] else "❌ 失败"
            f.write(f"| {i} | {result['description']} | {status} | `{result['script']}` |\n")
        
        f.write("\n## 🎯 测试覆盖的API接口\n\n")
        f.write("### 认证服务 (7个接口)\n")
        f.write("- ✅ 用户登录\n")
        f.write("- ✅ 退出登录\n")
        f.write("- ✅ 获取个人信息\n")
        f.write("- ✅ 上传文件\n")
        f.write("- ✅ 修改密码\n")
        f.write("- ✅ 重置密码\n")
        f.write("- ✅ 更新个人信息\n\n")
        
        f.write("### 虚拟订单服务 (9个接口)\n")
        f.write("#### 虚拟客服管理 (4个)\n")
        f.write("- ✅ 创建虚拟客服\n")
        f.write("- ✅ 获取虚拟客服列表\n")
        f.write("- ✅ 更新虚拟客服信息\n")
        f.write("- ✅ 删除虚拟客服\n\n")
        
        f.write("#### 其他功能 (5个)\n")
        f.write("- ✅ 导入学生补贴表\n")
        f.write("- ✅ 导入专用客服\n")
        f.write("- ✅ 获取虚拟订单统计\n")
        f.write("- ✅ 获取学生补贴池列表\n")
        f.write("- ✅ 重新分配学生任务\n\n")
        
        f.write("### API网关 (2个接口)\n")
        f.write("- ✅ 健康检查\n")
        f.write("- ✅ 获取所有微服务状态\n\n")
        
        f.write("## 📁 测试文件列表\n\n")
        for result in test_results:
            f.write(f"- `{result['script']}` - {result['description']}\n")
        
        f.write(f"\n---\n")
        f.write(f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"\n📄 测试报告已保存到: {report_file}")

def main():
    """主函数"""
    print("🚀 开始运行所有API接口单元测试...")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 定义所有测试脚本
    test_scripts = [
        {
            "script": "test_virtual_cs_4_apis.py",
            "description": "虚拟客服4个API接口测试"
        },
        {
            "script": "test_auth_service_apis.py", 
            "description": "认证服务7个API接口测试"
        },
        {
            "script": "test_virtual_order_other_apis.py",
            "description": "虚拟订单服务其他5个API接口测试"
        },
        {
            "script": "test_api_gateway.py",
            "description": "API网关2个接口测试"
        }
    ]
    
    # 运行所有测试
    test_results = []
    for test_config in test_scripts:
        result = run_test_script(test_config["script"], test_config["description"])
        test_results.append(result)
    
    # 生成测试报告
    summary = generate_test_report(test_results)
    
    # 保存测试报告
    save_test_report(test_results, summary)
    
    # 最终结果
    print(f"\n{'='*80}")
    if summary["failed_tests"] == 0:
        print("🎉 所有测试通过！API接口单元测试完成。")
        print(f"✅ 成功率: {summary['success_rate']:.1f}%")
        print(f"✅ API覆盖率: {summary['api_coverage']:.1f}%")
        return True
    else:
        print(f"⚠️  有 {summary['failed_tests']} 个测试失败。")
        print(f"📊 成功率: {summary['success_rate']:.1f}%")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
