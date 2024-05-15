.PHONY : test
test:
	python -m pytest --disable-warnings .

.PHONY : lint
lint:
	ruff format .
	ruff check --fix .

.PHONY : publish
publish:
	poetry publish --build
