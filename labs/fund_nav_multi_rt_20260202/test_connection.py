#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 AkShare 连接和数据获取的诊断脚本

运行此脚本以验证：
1. AkShare 库是否正确安装
2. 网络连接是否正常
3. 各个数据接口是否可用

用法：
    python test_connection.py
"""

import sys
import time

def test_imports():
    """测试必要的库导入"""
    print("=" * 60)
    print("1. 测试库导入...")
    print("=" * 60)

    try:
        import akshare as ak
        print("✓ akshare 导入成功")
        print(f"  版本: {ak.__version__ if hasattr(ak, '__version__') else '未知'}")
    except ImportError as e:
        print(f"✗ akshare 导入失败: {e}")
        print("  请运行: pip install akshare")
        return False

    try:
        import pandas as pd
        print(f"✓ pandas 导入成功 (版本: {pd.__version__})")
    except ImportError:
        print("✗ pandas 导入失败")
        print("  请运行: pip install pandas")
        return False

    try:
        import numpy as np
        print(f"✓ numpy 导入成功 (版本: {np.__version__})")
    except ImportError:
        print("✗ numpy 导入失败")
        print("  请运行: pip install numpy")
        return False

    try:
        from sklearn.linear_model import LinearRegression
        import sklearn
        print(f"✓ scikit-learn 导入成功 (版本: {sklearn.__version__})")
    except ImportError:
        print("✗ scikit-learn 导入失败")
        print("  请运行: pip install scikit-learn")
        return False

    print()
    return True


def test_fund_data():
    """测试基金数据获取"""
    print("=" * 60)
    print("2. 测试基金数据获取...")
    print("=" * 60)

    try:
        import akshare as ak
        print("尝试获取基金 022485 的净值数据...")

        start = time.time()
        df = ak.fund_open_fund_info_em(symbol="022485", indicator="单位净值走势")
        elapsed = time.time() - start

        print(f"✓ 成功获取数据 (耗时: {elapsed:.2f}秒)")
        print(f"  数据行数: {len(df)}")
        print(f"  数据列: {df.columns.tolist()}")
        print(f"  最新日期: {df.iloc[-1]['净值日期'] if '净值日期' in df.columns else 'N/A'}")
        print()
        return True
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        print()
        return False


def test_index_daily():
    """测试指数日线数据获取"""
    print("=" * 60)
    print("3. 测试指数日线数据获取...")
    print("=" * 60)

    import akshare as ak
    success_count = 0

    # 测试 index_zh_a_hist
    if hasattr(ak, "index_zh_a_hist"):
        try:
            print("尝试使用 index_zh_a_hist 获取沪深300数据...")
            start = time.time()
            df = ak.index_zh_a_hist(
                symbol="000300",
                period="daily",
                start_date="20240101",
                end_date="20240131"
            )
            elapsed = time.time() - start
            print(f"✓ index_zh_a_hist 可用 (耗时: {elapsed:.2f}秒)")
            print(f"  数据行数: {len(df)}")
            success_count += 1
        except Exception as e:
            print(f"✗ index_zh_a_hist 失败: {str(e)[:100]}")
    else:
        print("⊘ index_zh_a_hist 接口不存在")

    print()

    # 测试 stock_zh_index_daily_em
    if hasattr(ak, "stock_zh_index_daily_em"):
        try:
            print("尝试使用 stock_zh_index_daily_em 获取沪深300数据...")
            start = time.time()
            df = ak.stock_zh_index_daily_em(symbol="sh000300")
            elapsed = time.time() - start
            print(f"✓ stock_zh_index_daily_em 可用 (耗时: {elapsed:.2f}秒)")
            print(f"  数据行数: {len(df)}")
            success_count += 1
        except Exception as e:
            print(f"✗ stock_zh_index_daily_em 失败: {str(e)[:100]}")
    else:
        print("⊘ stock_zh_index_daily_em 接口不存在")

    print()
    return success_count > 0


def test_index_realtime():
    """测试实时指数数据获取"""
    print("=" * 60)
    print("4. 测试实时指数数据获取...")
    print("=" * 60)

    try:
        import akshare as ak
        print("尝试获取沪深重要指数实时数据...")

        start = time.time()
        df = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
        elapsed = time.time() - start

        print(f"✓ 成功获取数据 (耗时: {elapsed:.2f}秒)")
        print(f"  指数数量: {len(df)}")
        print(f"  数据列: {df.columns.tolist()}")

        # 显示部分数据
        if len(df) > 0:
            print("\n  示例数据:")
            for idx, row in df.head(3).iterrows():
                name = row.get('名称', 'N/A')
                code = row.get('代码', 'N/A')
                pct = row.get('涨跌幅', 'N/A')
                print(f"    {code}: {name} {pct}%")

        print()
        return True
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        print("  注意: 实时数据仅在交易时段可用")
        print()
        return False


def test_market_status():
    """测试市场时间判断"""
    print("=" * 60)
    print("5. 测试市场状态判断...")
    print("=" * 60)

    try:
        import pandas as pd
        now = pd.Timestamp.now(tz="Asia/Shanghai")

        print(f"当前时间: {now}")

        t = now.time()
        am_open = t >= pd.Timestamp("09:30").time() and t <= pd.Timestamp("11:30").time()
        pm_open = t >= pd.Timestamp("13:00").time() and t <= pd.Timestamp("15:00").time()
        is_open = am_open or pm_open

        weekday = now.weekday()
        is_weekday = weekday < 5

        print(f"星期: {['一', '二', '三', '四', '五', '六', '日'][weekday]}")
        print(f"是否工作日: {'是' if is_weekday else '否'}")
        print(f"是否交易时段: {'是' if is_open else '否'}")

        if is_open and is_weekday:
            print("✓ 当前在 A 股交易时段内")
        else:
            print("⊘ 当前不在 A 股交易时段")
            if not is_weekday:
                print("  (周末不交易)")
            elif t < pd.Timestamp("09:30").time():
                print("  (还未开盘)")
            elif t > pd.Timestamp("15:00").time():
                print("  (已收盘)")
            else:
                print("  (午休时段)")

        print()
        return True
    except Exception as e:
        print(f"✗ 判断失败: {e}")
        print()
        return False


def test_timeout_wrapper():
    """测试超时包装器"""
    print("=" * 60)
    print("6. 测试超时机制...")
    print("=" * 60)

    try:
        import threading
        import time

        def slow_function():
            time.sleep(2)
            return "完成"

        def timeout_test(func, timeout):
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func()
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout)

            if thread.is_alive():
                return None, True  # 超时
            return result[0], False

        # 测试正常完成
        print("测试正常完成 (2秒任务, 3秒超时)...")
        result, timed_out = timeout_test(slow_function, 3)
        if not timed_out and result == "完成":
            print("✓ 正常完成测试通过")
        else:
            print("✗ 正常完成测试失败")

        # 测试超时
        print("测试超时 (2秒任务, 1秒超时)...")
        result, timed_out = timeout_test(slow_function, 1)
        if timed_out:
            print("✓ 超时测试通过")
        else:
            print("✗ 超时测试失败")

        print()
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        print()
        return False


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  AkShare 连接诊断工具".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = []

    # 运行所有测试
    results.append(("库导入", test_imports()))

    if not results[0][1]:
        print("\n✗ 基础库导入失败，无法继续测试")
        print("请先安装所需依赖: pip install akshare pandas numpy scikit-learn")
        return

    results.append(("基金数据", test_fund_data()))
    results.append(("指数日线", test_index_daily()))
    results.append(("实时指数", test_index_realtime()))
    results.append(("市场状态", test_market_status()))
    results.append(("超时机制", test_timeout_wrapper()))

    # 汇总结果
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{name:12s} {status}")

    total = len(results)
    passed = sum(1 for _, s in results if s)

    print()
    print(f"总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("\n✓ 所有测试通过！程序应该可以正常运行。")
    elif passed >= total - 1:
        print("\n⚠ 大部分测试通过，程序应该可以基本运行。")
    else:
        print("\n✗ 多项测试失败，请检查网络连接和 AkShare 安装。")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⊘ 用户中断测试")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
