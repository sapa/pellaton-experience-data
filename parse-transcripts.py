
import re
import csv
from collections import namedtuple
from datetime import datetime
import spacy
import pandas as pd

Segment = namedtuple('Segment', ['video', 'start', 'text', 'entities'])

class Main(object):
    def __init__(self):
        print('loading model ...')
        self.nlp = spacy.load('de_core_news_sm')
        print('parsing transcripts ...')
        self.timecode_pattern = re.compile(r'\(.{2}:.{2}\)|\(.{1}:.{2}:.{2}\)')
        self.entities_dict = dict()
        self.segments = []
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
                    try:
                        self.entities_dict[e[0]].add(e[1])
                    except:
                        print(e)
                entities = [e[0] for e in entities]
                self.segments.append(Segment(transcript_id, starts[i], segment, entities))

        with open('data/entities.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['entity', 'type'])
            for e in sorted(self.entities_dict.keys()):
                writer.writerow([e, ';'.join(sorted(list(self.entities_dict[e])))])

        with open('data/segments.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['video', 'start', 'text', 'entities'])
            for s in self.segments:
                writer.writerow([s.video, s.start, s.text, ';'.join(sorted(s.entities))])

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
        # convert timecode like in seconds - '(01:23)' -> 83
        tcl = tc.strip('()').split(':')
        return sum([pow(60, len(tcl) - i - 1) * int(x) for i, x in enumerate(tcl)])

    def cleanup_segment(self, segment: str) -> str:
        segment = segment.replace('[Anm. Transkription:', '(').replace(']',')').replace('(unv.)', '(?)').strip()
        return segment

    def get_entities(self, segment: str) -> list:
        doc = self.nlp(segment)
        entities = [(e.text, e.label_) for e in doc.ents]
        return entities

if __name__ == '__main__':
    m = Main()