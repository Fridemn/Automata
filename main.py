#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器人客户端
通过WebSocket接收服务端命令并控制机器人执行相应动作
"""

from LOBOROBOT import LOBOROBOT  # 载入机器人库
import RPi.GPIO as GPIO
import asyncio
import websockets
import json
import logging
import sys
import socket

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RobotClient:
    def __init__(self, server_host="115.25.46.11", server_port=8765):
        self.server_host = server_host
        self.server_port = server_port
        self.robot = LOBOROBOT()  # 实例化机器人对象
        self.websocket = None
        self.running = False
        
        # 显示网络信息
        self.show_network_info()
        
        # 动作映射表
        self.action_map = {
            "t_up": self.robot.t_up,           # 前进
            "t_down": self.robot.t_down,       # 后退
            "turnLeft": self.robot.turnLeft,   # 左转
            "turnRight": self.robot.turnRight, # 右转
            "moveLeft": self.robot.moveLeft,   # 左移
            "moveRight": self.robot.moveRight, # 右移
            "forward_Left": self.robot.forward_Left,     # 前左斜
            "forward_Right": self.robot.forward_Right,   # 前右斜
            "backward_Left": self.robot.backward_Left,   # 后左斜
            "backward_Right": self.robot.backward_Right, # 后右斜
            "t_stop": self.robot.t_stop        # 停止
        }
        
    def show_network_info(self):
        """显示网络信息"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            logger.info(f"本机主机名: {hostname}")
            logger.info(f"本机IP地址: {local_ip}")
            logger.info(f"目标服务器: {self.server_host}:{self.server_port}")
        except Exception as e:
            logger.warning(f"获取网络信息失败: {e}")
        
    async def connect_to_server(self):
        """连接到服务器"""
        max_retries = 5
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                uri = f"ws://{self.server_host}:{self.server_port}"
                logger.info(f"正在连接到服务器: {uri} (尝试 {attempt + 1}/{max_retries})")
                
                # 设置连接超时
                self.websocket = await asyncio.wait_for(
                    websockets.connect(uri), 
                    timeout=10
                )
                logger.info("成功连接到服务器")
                self.running = True
                
                # 开始监听消息
                await self.listen_for_commands()
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"连接超时 (尝试 {attempt + 1}/{max_retries})")
            except ConnectionRefusedError:
                logger.error(f"连接被拒绝，服务器可能未启动 (尝试 {attempt + 1}/{max_retries})")
            except Exception as e:
                logger.error(f"连接服务器失败: {e} (尝试 {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:
                logger.info(f"等待 {retry_delay} 秒后重试...")
                await asyncio.sleep(retry_delay)
            
        logger.error("所有连接尝试都失败了")
        return False
            
    async def listen_for_commands(self):
        """监听服务器命令"""
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    command_data = json.loads(message)
                    await self.execute_command(command_data)
                except asyncio.TimeoutError:
                    continue  # 继续监听
                except json.JSONDecodeError:
                    logger.error(f"无法解析命令: {message}")
                except Exception as e:
                    logger.error(f"执行命令时出错: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("与服务器的连接已断开")
        except Exception as e:
            logger.error(f"监听命令时出错: {e}")
        finally:
            self.running = False
            
    async def execute_command(self, command_data):
        """执行接收到的命令"""
        action = command_data.get("action")
        speed = command_data.get("speed", 50)
        duration = command_data.get("duration", 1)
        
        logger.info(f"执行命令: {action}, 速度: {speed}, 持续时间: {duration}秒")
        
        if action in self.action_map:
            try:
                if action == "t_stop":
                    # 停止命令只需要持续时间参数
                    self.action_map[action](duration)
                else:
                    # 其他命令需要速度和持续时间参数
                    self.action_map[action](speed, duration)
                    
                logger.info(f"命令 {action} 执行完成")
                
            except Exception as e:
                logger.error(f"执行命令 {action} 时出错: {e}")
        else:
            logger.warning(f"未知命令: {action}")
            
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            logger.info("已断开与服务器的连接")
            
    def cleanup(self):
        """清理GPIO资源"""
        try:
            self.robot.t_stop(0)  # 停止机器人
            GPIO.cleanup()
            logger.info("GPIO资源已清理")
        except Exception as e:
            logger.error(f"清理GPIO资源时出错: {e}")
            
    async def run(self):
        """运行客户端"""
        try:
            await self.connect_to_server()
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
        except Exception as e:
            logger.error(f"客户端运行出错: {e}")
        finally:
            await self.disconnect()
            self.cleanup()

async def main():
    """主函数"""
    # 可以通过命令行参数指定服务器地址和端口
    server_host = "115.25.46.11"
    server_port = 8765
    
    if len(sys.argv) > 1:
        server_host = sys.argv[1]
    if len(sys.argv) > 2:
        server_port = int(sys.argv[2])
        
    client = RobotClient(server_host, server_port)
    
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序出错: {e}")
    finally:
        client.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"程序出错: {e}")