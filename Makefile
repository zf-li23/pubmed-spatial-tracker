.PHONY: all install build serve clean run dev

all: run

install:
	@echo "=> 安装依赖..."
	pip install -r requirements.txt
	cd web_app/frontend && npm install

build:
	@echo "=> 清理并重新构建前端..."
	rm -rf web_app/frontend/dist || true
	cd web_app/frontend && npm run build

stop:
	@echo "=> 温和清理 8000 端口..."
	@PORT_PIDS=$$(lsof -t -i:8000) || true; \
	if [ -n "$$PORT_PIDS" ]; then \
		kill -15 $$PORT_PIDS; \
		sleep 2; \
		PORT_PIDS_REMAINING=$$(lsof -t -i:8000) || true; \
		if [ -n "$$PORT_PIDS_REMAINING" ]; then \
			echo "强制终止 $$PORT_PIDS_REMAINING"; \
			kill -9 $$PORT_PIDS_REMAINING; \
		fi \
	fi

run: stop build
	@echo "=> 启动后端..."
	cd web_app && python -m uvicorn app:app --host 0.0.0.0 --port 8000

dev: stop
	@echo "=> 后端开发模式 (前端请通过 npm run dev 启动以实现热重载)..."
	cd web_app && python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
