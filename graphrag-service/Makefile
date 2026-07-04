.PHONY: install test demo bootstrap lint format infra-up neo4j-seed neo4j-check qdrant-check ask-graph rmq-worker rmq-query gradio-studio excel-to-md pdf-to-md graph-html graph-view sync-data

CASE_SRC ?= $(CURDIR)/../../Задача 1. Фабрика гипотез/Задача 1
DATA_CASE := $(CURDIR)/data/case
DATA_LIT := $(CURDIR)/data/literature

install:
	python3 -m pip install -r requirements.txt

test:
	python3 -m pytest tests/ -q

sync-data:
	@test -d "$(CASE_SRC)" || (echo "CASE_SRC not found: $(CASE_SRC)" && exit 1)
	mkdir -p "$(DATA_CASE)/Дополнительные материалы/md" "$(DATA_LIT)"
	rsync -a "$(CASE_SRC)/Пример 1/" "$(CASE_SRC)/Пример 2/" "$(CASE_SRC)/Пример 3/" "$(CASE_SRC)/Пример 4/" "$(DATA_CASE)/"
	rsync -a "$(CASE_SRC)/Дополнительные материалы/md/geokniga_"* "$(CASE_SRC)/Дополнительные материалы/md/tehnologiya_"* "$(DATA_CASE)/Дополнительные материалы/md/"
	rsync -a "$(CASE_SRC)/Дополнительные материалы/md/md/" "$(DATA_LIT)/"
	@echo "Synced case + literature → data/"

literature-chunks:
	python3 scripts/monolithic_to_chunks.py

sync-data-full: sync-data literature-chunks

bootstrap:
	python3 scripts/bootstrap_kb.py

excel-to-md:
	python3 scripts/excel_to_md.py

pdf-to-md:
	python3 scripts/pdf_to_md_chunks.py --backend opendataloader --granularity paragraph --clean

compare-granularity:
	python3 scripts/compare_chunk_granularity.py

compare-pdf:
	python3 scripts/compare_pdf_backends.py

demo:
	python3 scripts/demo_graph_rag.py

lint:
	python3 -m black --check graphrag tests scripts
	python3 -m isort --check-only graphrag tests scripts
	python3 -m flake8 graphrag tests scripts
	python3 -m pylint graphrag

format:
	python3 -m isort graphrag tests scripts
	python3 -m black graphrag tests scripts

neo4j-up:
	docker compose -f docker-compose.yml up -d

infra-up:
	docker compose -f docker-compose.yml up -d rabbitmq qdrant neo4j

rmq-worker:
	python3 scripts/rmq_worker.py

rmq-query:
	python3 scripts/rmq_query.py

gradio-studio:
	python3 scripts/gradio_studio.py --host 0.0.0.0 --port 7860

neo4j-seed:
	GRAPH_BACKEND=neo4j python3 scripts/seed_neo4j.py

qdrant-check:
	python3 scripts/check_qdrant.py

neo4j-check:
	python3 scripts/check_neo4j.py

ask-graph:
	python3 scripts/ask_graph.py --examples --cypher

show-chunk:
	python3 scripts/show_chunk.py $(CHUNK)

graph-html:
	python3 scripts/export_graph_html.py --all

graph-view: neo4j-seed graph-html
	@echo "Neo4j Browser: http://localhost:7474"
	@echo "HTML graphs:   output/graph/"
	python3 scripts/export_graph_html.py --view literature --open
