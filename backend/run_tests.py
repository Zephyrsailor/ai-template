#!/usr/bin/env python3
"""
测试运行脚本

提供多种测试运行选项：
- 运行所有测试
- 运行特定类型的测试
- 生成覆盖率报告
- 并行测试
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd: list[str], description: str = "") -> int:
    """运行命令并返回退出码"""
    if description:
        print(f"\n🚀 {description}")
    
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试运行脚本")
    
    # 测试类型选项
    parser.add_argument("--unit", action="store_true", help="只运行单元测试")
    parser.add_argument("--integration", action="store_true", help="只运行集成测试")
    parser.add_argument("--e2e", action="store_true", help="只运行端到端测试")
    parser.add_argument("--slow", action="store_true", help="运行慢速测试")
    
    # 运行选项
    parser.add_argument("--parallel", "-p", action="store_true", help="并行运行测试")
    parser.add_argument("--coverage", "-c", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--html", action="store_true", help="生成HTML测试报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="遇到第一个失败就停止")
    parser.add_argument("--last-failed", "--lf", action="store_true", help="只运行上次失败的测试")
    
    # 过滤选项
    parser.add_argument("--pattern", "-k", help="按模式过滤测试")
    parser.add_argument("--file", help="运行特定文件的测试")
    parser.add_argument("--durations", type=int, default=10, help="显示最慢的N个测试")
    
    # 其他选项
    parser.add_argument("--no-cov", action="store_true", help="禁用覆盖率")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    
    args = parser.parse_args()
    
    # 构建pytest命令
    cmd = ["python", "-m", "pytest"]
    
    # 添加标记过滤
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.e2e:
        markers.append("e2e")
    if args.slow:
        markers.append("slow")
    
    if markers:
        cmd.extend(["-m", " or ".join(markers)])
    
    # 添加运行选项
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    if args.coverage and not args.no_cov:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    elif args.no_cov:
        cmd.append("--no-cov")
    
    if args.html:
        cmd.extend(["--html=test-report.html", "--self-contained-html"])
    
    if args.verbose:
        cmd.append("-v")
    
    if args.fail_fast:
        cmd.append("-x")
    
    if args.last_failed:
        cmd.append("--lf")
    
    if args.pattern:
        cmd.extend(["-k", args.pattern])
    
    if args.file:
        cmd.append(args.file)
    
    if args.durations:
        cmd.extend(["--durations", str(args.durations)])
    
    if args.debug:
        cmd.extend(["--pdb", "--capture=no"])
    
    # 运行测试
    description = "运行测试套件"
    if markers:
        description += f" (标记: {', '.join(markers)})"
    
    exit_code = run_command(cmd, description)
    
    # 输出结果
    if exit_code == 0:
        print("\n✅ 所有测试通过!")
        if args.coverage and not args.no_cov:
            print("📊 覆盖率报告已生成: htmlcov/index.html")
        if args.html:
            print("📋 HTML测试报告已生成: test-report.html")
    else:
        print(f"\n❌ 测试失败 (退出码: {exit_code})")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main()) 