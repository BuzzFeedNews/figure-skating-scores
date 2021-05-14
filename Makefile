default:

.PHONY: reproduce clear data data/tidy data/json

reproduce: clear data

clear: 
	rm -r data
	mkdir -p data/tidy data/json

data: data/json data/tidy

data/json:
	python3 -m scripts.parse_pdfs pdfs 2>&1 | tee data/parsing-log.txt

data/tidy:
	python3 -m scripts.tidify_results
