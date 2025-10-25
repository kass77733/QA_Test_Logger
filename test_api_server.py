#!/usr/bin/env python3
"""
简单的测试API服务器，用于测试接口获取案例功能
运行此脚本后，可以测试接口获取案例功能
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

class TestAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """处理GET请求"""
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/testarGetCase':
            # 解析查询参数
            params = parse_qs(parsed_url.query)
            project_id = params.get('projectId', [''])[0]
            subtask_name = params.get('subtaskName', [''])[0]
            round_num = params.get('round', [''])[0]
            
            print(f"收到请求参数: projectId={project_id}, subtaskName={subtask_name}, round={round_num}")
            
            # 模拟返回测试数据
            response_data = {
                "status": 200,
                "data": [
                    {
                        "case_id": f"{project_id}_TC001",
                        "caseName": f"{subtask_name}_登录功能测试",
                        "test_steps": "1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮",
                        "expected_result": "用户能够成功登录系统",
                        "priority": "高"
                    },
                    {
                        "case_id": f"{project_id}_TC002", 
                        "caseName": f"{subtask_name}_数据导入测试",
                        "test_steps": "1. 点击导入按钮\n2. 选择文件\n3. 确认导入",
                        "expected_result": "文件能够正确导入并解析",
                        "priority": "中"
                    },
                    {
                        "case_id": f"{project_id}_TC003",
                        "caseName": f"{subtask_name}_报告生成测试_轮次{round_num}",
                        "test_steps": "1. 执行测试用例\n2. 点击生成报告\n3. 查看报告内容",
                        "expected_result": "能够生成完整的测试报告",
                        "priority": "高"
                    }
                ]
            }
            
            # 设置响应头
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送响应数据
            response_json = json.dumps(response_data, ensure_ascii=False, indent=2)
            self.wfile.write(response_json.encode('utf-8'))
            
        else:
            # 404 Not Found
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[API] {format % args}")

def run_test_server():
    """运行测试服务器"""
    server_address = ('127.0.0.1', 80)
    
    try:
        httpd = HTTPServer(server_address, TestAPIHandler)
        print("测试API服务器已启动: http://127.0.0.1/testarGetCase")
        print("按 Ctrl+C 停止服务器")
        httpd.serve_forever()
    except PermissionError:
        print("错误: 无法绑定到端口80，请以管理员权限运行或修改端口")
    except KeyboardInterrupt:
        print("\n服务器已停止")

if __name__ == '__main__':
    run_test_server()