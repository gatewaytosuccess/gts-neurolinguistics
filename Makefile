BACKEND_DIR := api
VENV_BIN := $(BACKEND_DIR)/.venv/bin

.PHONY: format format-check

format:
	$(VENV_BIN)/ruff check --fix .
	$(VENV_BIN)/ruff format .
	cd web && npx prettier --write .

format-check:
	$(VENV_BIN)/ruff check .
	$(VENV_BIN)/ruff format --check .
	cd web && npx prettier --check .
	
