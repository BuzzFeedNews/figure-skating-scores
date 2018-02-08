#!/bin/sh
set -e
mkdir -p pdfs
while read -r URL; do
    echo "Fetching $URL"
    FILENAME=$(basename "$URL")
    curl "$URL" > pdfs/$FILENAME 
done < scripts/urls.txt
