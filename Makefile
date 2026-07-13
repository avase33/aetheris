.PHONY: install dev test demo gateway vision agents privacy mlops docker compose k8s clean

install:
	pip install -e .

dev:
	pip install -e ".[dev,server]"

test:
	pytest -q

demo:
	python -m aetheris demo

gateway:
	uvicorn aetheris.gateway.api:app --reload
vision:
	uvicorn aetheris.vision.api:app --reload --port 8001
agents:
	uvicorn aetheris.agents.api:app --reload --port 8002
privacy:
	uvicorn aetheris.privacy.api:app --reload --port 8003
mlops:
	uvicorn aetheris.mlops.api:app --reload --port 8004

docker:
	docker build -t aetheris .

compose:
	docker compose -f deploy/docker-compose.yml up --build

k8s:
	kubectl apply -f deploy/k8s/aetheris.yaml

clean:
	rm -f *.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
