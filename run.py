#!/usr/bin/env python3
"""
HIA AI - پروژه چلول
"""

import sys
import os

# د پروژې ریښه لار
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     🤖 HIA AI - هوښیار مرستیال                         ║
    ║                                                          ║
    ║     د حافظې سیسټم سره بشپړ AI مرستیال                  ║
    ║                                                          ║
    ║     Server: http://localhost:5000                       ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)