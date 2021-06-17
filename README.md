# The Pellation Experience - Data

This repo contains code for parsing the video transcripts with NER and - in consideration of editorial interventions - renders them into a JSON file.

## Requirements

Install packages via `pip install -r requirements.txt` and download language model with `python -m spacy download de_core_news_sm`.

## Workflow

Manual changes can (and should) be made in two places: in the transcript files in `data` and in the spreadsheet `data/edited-entities.xlsx`.

The transcripts need to be cleaned from unwanted comments while additional timecodes should be added for more granular segments.

The spreadsheet file contains three sheets:

* "entities" contains a list of normalized entity labels with alternatives, types, and identifiers for additional information.
* "additional" contains a list of entity labels with variatons and types that are not found via ENR but should be added and entity labels, which are found but assinged to a wrong type (e.g. "Basel" is classified as "LOC" and "ORG" and hereby defined as "LOC").
* "ignore" contains a list of entity labels that are found via NER but should not be used.

The transformation of the data is done with two scripts:

* `parse-transcript.py` reads the transcript files in `data` and the lists of additional and unwanted enty labels from `data/edited-entities.xlsx` and writes results to `data/entities.csv` and `data/segments.csv`. 
* `render-json.py` reads `data/segments.csv`, matches the entities in there with those in the "entities" sheet of the spreadsheet and writes them to `data/pellaton.json`. Run with the optional parameter `--wikidata` the script fetches additional data from Wikidata.

If necessary, `render-json.py` writes several lists to the console:

* Missing entities: Entities that were found in the transcripts but in the spreadsheet are neither listed in "entities" nor in  "ignore".
* Duplicate entities: Enties that appear more than once in "entities".
* Duplicate variations: Variations that appear more than once in "entities".

It also checks if URIs in the columns "sapa" and "wikidata" in the "entities" are well formed.

`data/pellaton.json` contains two lists:

* segments with video ids, starts in seconds, the text, and the list of normalized entities labels
* entities with all additional information about the entities