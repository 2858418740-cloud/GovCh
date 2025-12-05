# 简化的启动脚本，使用print语句并添加flush确保输出不被缓冲
import sys

def log(message):
    print(message)
    sys.stdout.flush()

def log_error(message, e):
    print(f'{message}: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
    sys.stdout.flush()

log('开始加载应用...')

# 导入必要的模块
try:
    log('导入app模块...')
    from app import create_app
    log('成功导入app模块')
    
    # 创建应用实例
    log('创建应用实例...')
    app = create_app()
    log('应用实例创建成功')
    
    # 启动开发服务器
    log('启动开发服务器...')
    log('服务器将在 http://localhost:5000/ 上运行')
    app.run(debug=True, port=5000, use_reloader=False)
    
except Exception as e:
    log_error('应用启动失败', e)
    
    # 等待用户按Enter键，以便查看错误信息
    input('按Enter键退出...')