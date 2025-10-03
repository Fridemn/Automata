#!/usr/bin/env python3
"""
Automata - AI 人格系统
主入口文件
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from automata.core.launcher import main

logo_tmpl = r"""
    \    |   |__ __| _ \   \  |    \ __ __|  \
   _ \   |   |   |  |   | |\/ |   _ \   |   _ \
  ___ \  |   |   |  |   | |   |  ___ \  |  ___ \
_/    _\\___/   _| \___/ _|  _|_/    _\_|_/    _\
Automata - AI 人格系统
"""

if __name__ == "__main__":
    print(logo_tmpl)
    asyncio.run(main())
