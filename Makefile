.PHONY: dev e2e e2e-mailpit e2e-mailpit-stop

dev:
	@trap 'kill 0' INT TERM EXIT; \
	( . backend/.venv/bin/activate && python backend/manage.py migrate && python backend/manage.py runserver ) & \
	( cd frontend && pnpm run dev ) & \
	wait

# Mailpit catches the E2E confirmation emails (SMTP :1025, UI/API http://localhost:8025).
e2e-mailpit:
	@docker inspect -f '{{.State.Running}}' zm-mailpit 2>/dev/null | grep -q true || \
	docker run -d --rm --name zm-mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit

e2e-mailpit-stop:
	-docker stop zm-mailpit

# Playwright happy-path test. Needs STRIPE_TEST_SECRET_KEY (.envrc) and
# VITE_STRIPE_PUBLISHABLE_KEY (frontend/.env) set to Stripe *test* keys.
e2e: e2e-mailpit
	cd frontend && pnpm run e2e
