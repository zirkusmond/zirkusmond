.PHONY: dev

dev:
	@trap 'kill 0' INT TERM EXIT; \
	( . backend/.venv/bin/activate && python backend/manage.py migrate && python backend/manage.py runserver ) & \
	( cd frontend && pnpm run dev ) & \
	wait
