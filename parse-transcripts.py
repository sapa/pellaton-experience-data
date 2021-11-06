
import re,csv,spacy,os
from collections import namedtuple
from datetime import datetime
from spacy.pipeline import EntityRuler
import pandas as pd
import numpy as np
from openpyxl import load_workbook

Segment = namedtuple('Segment', ['video', 'start', 'text', 'entities'])

outputSheet=r'data/merged-entities.xlsx'
inputSheet=r'data/edited-entities.xlsx'
extractionSheet=r'data/extracted-entities.xlsx'
entitiesFile=r'data/entities.csv'
segmentsFile=r'data/segments.csv'

class Main(object):
    def __init__(self):
        print('loading model ...')
        self.nlp = spacy.load('de_core_news_lg', exclude = ['ner'])
        self.nlp.add_pipe('ner', source = spacy.load('de_core_news_lg'))
        ruler = self.nlp.add_pipe('entity_ruler', before = 'ner')
        ruler.from_disk("data/custom.jsonl")
        ruler.to_disk("data/.swap/entity_ruler")
        additional_df = pd.read_excel(inputSheet, 'additional', usecols=['entity', 'variations', 'type'])
        self.additional_dict = dict()
        for _, r in additional_df.iterrows():
            k = r['entity']
            t = r['type']
            self.additional_dict[k.lower()] = (k, t)
            if not pd.isnull(r['variations']):
                for v in re.split(r'\s*;\s*', r['variations']):
                    self.additional_dict[v.lower()] = (k, t)
        ignore_df = pd.read_excel(inputSheet, 'ignore', usecols=['entity'])
        self.ignore_set = set([r['entity'].lower() for _, r in ignore_df.iterrows()])
        print('parsing transcripts ...')
        self.timecode_pattern = re.compile(r'[\(\[].{2}:.{2}[\)\]]|[\(\[].{1,2}:.{2}:.{2}[\)\]]')
        self.entities_dict = dict()
        self.segments = []
        self.entities = []
        transcript_id: int = 0
        transcript_path: str = None
        for transcript_id in range(1, 5):
            print(f'... {transcript_id}')
            transcript_path = f'data/transcript-{transcript_id}.txt'
            with open(transcript_path, 'r') as file:
                transcript = file.read()
            starts, segments = self.split_transcript(transcript)
            for i, segment in enumerate(segments):
                entities = self.get_entities(segment)
                for e in entities:
                    if e[0] not in self.entities_dict:
                        self.entities_dict[e[0]] = set()
                    if e[0].lower() in self.additional_dict:
                        # correct category?
                        self.entities_dict[e[0]] = set([self.additional_dict[e[0].lower()][1]])
                    else:
                        self.entities_dict[e[0]].add(e[1])
                entities = [e[0] for e in entities]
                self.segments.append(Segment(transcript_id, starts[i], segment, entities))

        with open(entitiesFile, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['entity', 'type'])
            for e in sorted(self.entities_dict.keys()):
                print(e)
                writer.writerow([e, ';'.join(sorted(list(self.entities_dict[e])))])

        with open(segmentsFile, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['video', 'start', 'text', 'entities'])
            for s in self.segments:
                writer.writerow([s.video, s.start, s.text, ';'.join(sorted(s.entities))])

        dfe = pd.read_csv(entitiesFile)
        dfe.sort_values('type', inplace=True)
        dfe.to_excel(extractionSheet, sheet_name='entities', index=False)

        dfm = pd.DataFrame()
        dfm = dfm.append(pd.read_excel(inputSheet, 'entities', usecols=['entity', 'variations', 'wikidata', 'sapa', 'type', 'image']), ignore_index=True)
        dfm = dfm.append(pd.read_excel(extractionSheet, 'entities', usecols=['entity', 'type']), ignore_index=True)
        dfm.head()
        length2 = len(dfm)
        dfm.sort_values('entity', inplace=True)
        dfm.drop_duplicates(keep='first', inplace=True, subset=['entity'])
        length3 = len(dfm)
        print(f'Total after merge: {length2} | Removed duplications:  {length2 - length3}')
        dfm.to_excel(outputSheet, sheet_name='entities', index=False)

        dfi = pd.DataFrame().append(pd.read_excel(inputSheet, 'ignore', usecols=['entity']))
        dfa = pd.DataFrame().append(pd.read_excel(inputSheet, 'additional', usecols=['entity', 'variations', 'type']))

        with pd.ExcelWriter(outputSheet, engine='openpyxl', mode='a') as writer:
            dfi.to_excel(writer, sheet_name='ignore', index=False)
            dfa.to_excel(writer, sheet_name='additional', index=False)

    def split_transcript(self, transcript: str):
        # Remove all intermediate timestamps (usually appear together with a comment in the middle of a sentence/paragraph)
        transcript = re.sub('\(unv., .{2}:.{2}\)', '(?)', transcript)
        transcript = re.sub(', .{2}:.{2}]', ']', transcript)
        timecodes = self.timecode_pattern.findall(transcript)
        starts = [self.convert_timecode(tc) for tc in timecodes]
        starts.insert(0, 0)
        segments = self.timecode_pattern.split(transcript)
        segments = [self.cleanup_segment(s) for s in segments]
        return starts, segments

    def convert_timecode(self, tc: str) -> int:
        # convert time code like in seconds - '(01:23)' -> 83
        tcl = tc.strip('()[]').split(':')
        return sum([pow(60, len(tcl) - i - 1) * int(x) for i, x in enumerate(tcl)])

    def cleanup_segment(self, segment: str) -> str:
        segment = segment.replace('...', '…').strip()
        # remove '(unv.)' and '(?)'
        segment = re.sub(r'\(unv\.\)', '', segment)
        segment = re.sub(r'\(\?\)', '', segment)
        # add space before eplipsis
        segment = re.sub(r'(?<=\w)…', ' …', segment)
        # delete multiple spaces
        segment = re.sub(r'\s+', ' ', segment)
        # delete spaces before common and period
        segment = re.sub(r'\s+(?=[\,\.])', '', segment)
        return segment

    def get_entities(self, segment: str) -> list:
        # remove speakers "I: "
        segment = re.sub(r'\n\w:\s+', '\n', segment)
        doc = self.nlp(segment)
        entities = [(e.text.strip(','), e.label_) for e in doc.ents if '\n' not in e.text and '…' not in e.text and e.text.lower() not in self.ignore_set]
        found = set([e[0] for e in entities])
        for t in doc:
            w = t.text.strip(',').lower()
            if w in self.additional_dict:
                entities.append(self.additional_dict[w])
        return entities

if __name__ == '__main__':
    m = Main()