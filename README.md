# The Pellation Experience - Data

This repo contains code for parsing the video transcripts with NER and - in consideration of editorial interventions - renders them into a JSON file.

## Requirements

Install packages via `pip install -r requirements.txt` and download language model with `python -m spacy download de_core_news_sm`.

## Execution of extraction

- add latest `data/edited-entities.xlsx`
    - make sure all ingores are in place (better add ignores instead of cell deletion)
    - make sure all custom types are added in `data/custom,jsonl` (every line is one item)
- run `python parse-transcript.py`
- make sure `data/merged-entities.xlsx` contains all correct data (add new data here before render json)
- run `python render-json.py --wikidata`

## Workflow

Manual changes can (and should) be made in 3 places: 
1. Transcripts at `data/transcript-*.txt`
   - The transcripts need to be cleaned from unwanted comments while additional timecodes should be added for more granular segments.
  
2. **Before parsing**, at Spreadsheet in `data/edited-entities.xlsx` (file contains three sheets).
   - "entities" contains a list of normalized entity labels with alternatives, types, and identifiers for additional information.
   - "additional" contains a list of entity labels with variatons and types that are not found via ENR but should be added and entity labels, which are found but assinged to a wrong type (e.g. "Basel" is classified as "LOC" and "ORG" and hereby defined as "LOC"). 
   - "ignore" contains a list of entity labels that are found via NER but should not be used.
3. **After parsing and before render json** at Spreadsheet in `data/edited-entities.xlsx`.
   - analog to previous

The transformation of the data is done with two scripts:

* `parse-transcript.py` reads the transcript files in `data` and the lists of additional and unwanted entity labels from `data/edited-entities.xlsx` and writes results to `data/entities.csv` and `data/segments.csv`, which get merged to a new spreadsheet at `data/merged-entities.xlsx`

* `render-json.py` reads `data/segments.csv`, matches the entities in there with those in the "entities" sheet of the spreadsheet and writes them to `data/pellaton.json`. Run with the optional parameter `--wikidata` the script fetches additional data from Wikidata.

If necessary, `render-json.py` writes several lists to the console:

* Missing entities: Entities that were found in the transcripts but in the spreadsheet are neither listed in "entities" nor in  "ignore".
* Duplicate entities: Enties that appear more than once in "entities".
* Duplicate variations: Variations that appear more than once in "entities".

It also checks if URIs in the columns "sapa" and "wikidata" in the "entities" are well formed.

`data/pellaton.json` contains two lists:

* "segments" with video ids, starts in seconds, the text, and the list of normalized entities labels
* "entities" with all additional information about the entities