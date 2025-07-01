#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器人遥控服务端
带GUI界面，通过WebSocket发送控制命令给机器人客户端
"""

import asyncio
import websockets
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobotServer:
    def __init__(self):
        self.clients = set()
        self.server = None
        self.loop = None
        
        # 创建GUI
        self.setup_gui()
        
    def setup_gui(self):
        """创建GUI界面"""
        self.root = tk.Tk()
        self.root.title("机器人遥控服务端")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        
        # 服务器状态框架
        status_frame = ttk.LabelFrame(self.root, text="服务器状态", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="状态: 未启动", font=("Arial", 10))
        self.status_label.pack(side="left")
        
        self.client_count_label = ttk.Label(status_frame, text="连接数: 0", font=("Arial", 10))
        self.client_count_label.pack(side="right")
        
        # 服务器控制按钮
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        self.start_button = ttk.Button(control_frame, text="启动服务器", command=self.start_server)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="停止服务器", command=self.stop_server, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        # 速度控制
        speed_frame = ttk.LabelFrame(self.root, text="速度控制", padding=10)
        speed_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(speed_frame, text="速度:").pack(side="left")
        self.speed_var = tk.IntVar(value=50)
        self.speed_scale = ttk.Scale(speed_frame, from_=10, to=100, variable=self.speed_var, orient="horizontal")
        self.speed_scale.pack(side="left", fill="x", expand=True, padx=10)
        
        self.speed_label = ttk.Label(speed_frame, text="50")
        self.speed_label.pack(side="right")
        
        # 更新速度显示
        self.speed_var.trace("w", self.update_speed_label)
        
        # 机器人控制面板
        control_panel = ttk.LabelFrame(self.root, text="机器人控制", padding=10)
        control_panel.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 创建方向控制按钮
        self.create_control_buttons(control_panel)
        
        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="日志", padding=5)
        log_frame.pack(fill="x", padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=6, width=50)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_control_buttons(self, parent):
        """创建控制按钮"""
        # 主要方向控制
        main_frame = ttk.Frame(parent)
        main_frame.pack(pady=10)
        
        # 第一行：前左斜、前进、前右斜
        row1 = ttk.Frame(main_frame)
        row1.pack()
        
        ttk.Button(row1, text="前左斜", width=8, command=lambda: self.send_command("forward_Left")).pack(side="left", padx=2)
        ttk.Button(row1, text="前进", width=8, command=lambda: self.send_command("t_up")).pack(side="left", padx=2)
        ttk.Button(row1, text="前右斜", width=8, command=lambda: self.send_command("forward_Right")).pack(side="left", padx=2)
        
        # 第二行：左移、停止、右移
        row2 = ttk.Frame(main_frame)
        row2.pack(pady=5)
        
        ttk.Button(row2, text="左移", width=8, command=lambda: self.send_command("moveLeft")).pack(side="left", padx=2)
        ttk.Button(row2, text="停止", width=8, command=lambda: self.send_command("t_stop"), 
                  style="Accent.TButton").pack(side="left", padx=2)
        ttk.Button(row2, text="右移", width=8, command=lambda: self.send_command("moveRight")).pack(side="left", padx=2)
        
        # 第三行：后左斜、后退、后右斜
        row3 = ttk.Frame(main_frame)
        row3.pack()
        
        ttk.Button(row3, text="后左斜", width=8, command=lambda: self.send_command("backward_Left")).pack(side="left", padx=2)
        ttk.Button(row3, text="后退", width=8, command=lambda: self.send_command("t_down")).pack(side="left", padx=2)
        ttk.Button(row3, text="后右斜", width=8, command=lambda: self.send_command("backward_Right")).pack(side="left", padx=2)
        
        # 转向控制
        turn_frame = ttk.Frame(parent)
        turn_frame.pack(pady=10)
        
        ttk.Label(turn_frame, text="转向控制:").pack()
        turn_buttons = ttk.Frame(turn_frame)
        turn_buttons.pack(pady=5)
        
        ttk.Button(turn_buttons, text="左转", width=10, command=lambda: self.send_command("turnLeft")).pack(side="left", padx=5)
        ttk.Button(turn_buttons, text="右转", width=10, command=lambda: self.send_command("turnRight")).pack(side="left", padx=5)
        
    def update_speed_label(self, *args):
        """更新速度标签"""
        self.speed_label.config(text=str(self.speed_var.get()))
        
    def log_message(self, message):
        """在日志区域添加消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    async def handle_client(self, websocket):
        """处理客户端连接"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        self.log_message(f"客户端连接: {client_addr}")
        self.update_client_count()
        
        try:
            await websocket.wait_closed()
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            self.log_message(f"客户端断开: {client_addr}")
            self.update_client_count()
            
    def update_client_count(self):
        """更新客户端连接数显示"""
        count = len(self.clients)
        self.client_count_label.config(text=f"连接数: {count}")
        
    async def broadcast_command(self, command_data):
        """向所有连接的客户端广播命令"""
        if self.clients:
            message = json.dumps(command_data)
            disconnected = []
            
            for client in self.clients.copy():
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.append(client)
                except Exception as e:
                    self.log_message(f"发送命令失败: {e}")
                    disconnected.append(client)
                    
            # 移除断开的连接
            for client in disconnected:
                self.clients.discard(client)
                
            self.update_client_count()
        else:
            self.log_message("没有客户端连接")
            
    def send_command(self, action):
        """发送命令给机器人"""
        if not self.clients:
            messagebox.showwarning("警告", "没有连接的客户端！")
            return
            
        speed = self.speed_var.get()
        command_data = {
            "action": action,
            "speed": speed,
            "duration": 1  # 默认持续时间1秒
        }
        
        # 在事件循环中执行异步函数
        if self.loop and not self.loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self.broadcast_command(command_data), 
                    self.loop
                )
                self.log_message(f"发送命令: {action} (速度: {speed})")
            except Exception as e:
                self.log_message(f"发送命令失败: {e}")
        else:
            self.log_message("服务器未运行，无法发送命令")
        
    def start_server(self):
        """启动WebSocket服务器"""
        def run_server():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            async def start_websocket_server():
                # 确保服务器监听所有网络接口
                host = "0.0.0.0"  # 监听所有网络接口
                port = 8765
                
                self.server = await websockets.serve(
                    self.handle_client, 
                    host,
                    port,
                    ping_interval=20,  # 20秒发送一次ping
                    ping_timeout=10    # 10秒ping超时
                )
                
                self.log_message(f"服务器启动成功")
                self.log_message(f"监听地址: {host}:{port}")
                self.log_message(f"本机IP可能是: {self.get_local_ip()}")
                self.status_label.config(text="状态: 运行中")
                
                # 等待服务器关闭
                await self.server.wait_closed()
            
            try:
                self.loop.run_until_complete(start_websocket_server())
            except Exception as e:
                self.log_message(f"服务器错误: {e}")
            finally:
                self.log_message("服务器已停止")
                self.status_label.config(text="状态: 已停止")
                
        # 在新线程中运行服务器
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # 更新按钮状态
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "无法获取"
        
    def stop_server(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.server.wait_closed(), 
                    self.loop
                )
            
        # 更新按钮状态
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        self.log_message("正在停止服务器...")
        
    def run(self):
        """运行GUI"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.stop_server()

def main():
    server = RobotServer()
    server.run()

if __name__ == "__main__":
    main()
