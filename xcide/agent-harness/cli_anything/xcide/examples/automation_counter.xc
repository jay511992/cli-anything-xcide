// Copy into a new Debug x64 project; add module_xcgui_class.h with dependencies.
#嵌入代码
#include "../../../automation_bridge.h"
#嵌入代码结束

窗口类 主窗口
编辑框类 输入框
整型 计数 = 0

函数 整型 WINAPI 点击增加(逻辑型 *是否拦截)
	计数 = 计数 + 1
	调试输出("COUNT=", 计数)
	调试输出("TEXT=", 输入框.取文本())
	主窗口.置标题("XC Automation - Clicked")
	返回 0

函数 整型 入口函数_窗口()
	炫彩_初始化(假) // GDI: the background test captures the native completed paint buffer.
	主窗口.创建(100, 100, 480, 320, "XC Automation - Ready", NULL, 炫彩窗口样式_默认)
	如果 主窗口._句柄
		输入框.创建(30, 50, 300, 36, 主窗口._句柄)
		按钮类 增加(30, 115, 180, 50, "增加计数 / Count", 主窗口._句柄)
		增加.注册事件C(元素事件_按钮点击, 点击增加)
		主窗口.调整布局()
		主窗口.显示(SW_SHOW)
		#嵌入代码
		xc_cli_test::install(主窗口.m_hWindow);
		#嵌入代码结束
		调试输出("READY")
		炫彩_运行()
	炫彩_退出()
	返回 0
