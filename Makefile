default:

.PHONY: reproduce clear data data/tidy data/json

reproduce: clear data

clear: 
	rm -r data
	mkdir -p data/{tidy,json}

data: data/json data/tidy

data/json:
	python -m scripts.parse_pdfs pdfs 2>&1 | tee data/parsing-log.txt

data/tidy:
	python -m scripts.tidify_results
