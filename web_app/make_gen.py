makefile_content = """\
.PHONY: all install build serve clean run dev

all: run

install:
\t@echo "=> 安装依赖..."
\tpip install -r requirements.txt
\tcd web_app/frontend && npm install

build:
\t@echo "=> 清理并重新构建前端..."
\trm -rf web_app/frontend/dist || true
\tcd web_app/frontend && npm run build

stop:
\t@echo "=> 温和清理 8000 端口..."
\t@PORT_PIDS=$$(lsof -t -i:8000) || true; \\
\tif [ -n "$$PORT_PIDS" ]; then \\
\t\tkill -15 $$PORT_PIDS; \\
\t\tsleep 2; \\
\t\tPORT_PIDS_REMAINING=$$(lsof -t -i:8000) || true; \\
\t\tif [ -n "$$PORT_PIDS_REMAINING" ]; then \\
\t\t\techo "强制终止 $$PORT_PIDS_REMAINING"; \\
\t\t\tkill -9 $$PORT_PIDS_REMAINING; \\
\t\tfi \\
\tfi

run: stop build
\t@echo "=> 启动后端..."
\tcd web_app && python -m uvicorn app:app --host 0.0.0.0 --port 8000

dev: stop
\t@echo "=> 后端开发模式 (前端请通过 npm run dev 启动以实现热重载)..."
\tcd web_app && python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""
with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/Makefile", "w") as f:
    f.write(makefile_content)
