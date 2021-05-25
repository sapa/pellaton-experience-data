import re
import requests
import json
import dateutil.parser
import pandas as pd
import click

@click.command()
@click.option('--wikidata', is_flag=True, help='get additional data from Wikidata')
class Main(object):
    def __init__(self, wikidata: bool = False):
        self.sapa_pattern = re.compile(r'http:\/\/data\.performing-arts\.ch\/\w\/[0-9a-f\-]{36}')
        self.wikidata_pattern = re.compile(r'http:\/\/www\.wikidata\.org\/entity\/Q\d+')
        entities_df = pd.read_excel('data/edited-entities.xlsx', 'entities', usecols=['name', 'variations', 'type', 'wikidata', 'sapa', 'image'])
        segments_df = pd.read_csv('data/segments.csv')
        export = {'segments': [], 'entities': []}
        entities_dict = dict()
        missing_entities = set()
        duplicate_entities = set()
        duplicate_variations = set()
        for i, r in entities_df.iterrows():
            e = Entity(r, wikidata)
            if e._name not in entities_dict:
                entities_dict[e._name] = e._name
            else:
                duplicate_entities.add(e._name)
            for v in e.variations:
                if v not in entities_dict:
                    entities_dict[v] = e._name
                else:
                    duplicate_variations.add(v)
            export['entities'].append(e.to_object())
        for _, r in segments_df.iterrows():
            s = Segment(r, entities_dict, missing_entities)
            export['segments'].append(s.to_object())
        with open('data/pellaton.json', 'w') as outfile:
            json.dump(export, outfile, indent=4)
        print('--- Missing entities ---')
        print('\n'.join(sorted(list(missing_entities), key = str.lower)))
        print('--- Duplicate entities ---')
        print('\n'.join(sorted(list(duplicate_entities), key = str.lower)))
        print('--- Duplicate variations ---')
        print('\n'.join(sorted(list(duplicate_variations), key = str.lower)))

class Entity(object):
    def __init__(self, r: pd.Series, check_wikidata: bool = False):
        self.check_wikidata = check_wikidata
        self._name = r['name']
        self._type = r['type']
        self.variations = []
        if not pd.isnull(r['variations']) and r['variations'].strip() != '':
            self.variations = re.split(r'\s*;\s*', str(r['variations']))
        if not pd.isnull(r['sapa']) and not re.match(r'http:\/\/data\.performing-arts\.ch\/\w\/[0-9a-f\-]{36}', r['sapa'].strip()):
            print(f'Invalid SAPA identifier: {r.sapa}')
        if not pd.isnull(r['wikidata']) and not re.match(r'http:\/\/www\.wikidata\.org\/entity\/Q\d+', r['wikidata'].strip()):
            print(f'Invalid Wikidata identifier: {r.wikidata}')
        self.wikidata = None if pd.isnull(r['wikidata']) else r['wikidata'].strip()
        self.dob, self.dod, self.theaterlexikon = self.get_wikidata_data(self.wikidata)
        self.sapa = None if pd.isnull(r['sapa']) else r['sapa'].strip()
        self.image = None if pd.isnull(r['image']) else r['image'].strip()

    def get_wikidata_data(self, uri: str = None):
        if uri == None or uri == '' or not self.check_wikidata:
            return None, None, None
        dob, dod, tls = None, None, None
        print(uri);
        q = uri[31:]
        url = f'https://www.wikidata.org/w/api.php?action=wbgetclaims&entity={q}&format=json'
        resp = requests.get(url=url)
        data = WikidataJSON(resp.json())
        if dob := data.get_claim_values('P569'):
            dob = self.format_wikidate(dob)
        if dod := data.get_claim_values('P570'):
            dod = self.format_wikidate(dod)
        if tls := data.get_claim_values('P1362'):
            tls = f'http://tls.theaterwissenschaft.ch/wiki/{tls[0]}'
        return dob, dod, tls

    def format_wikidate(self, wikidates: list) -> str:
        try:
            d = dateutil.parser.isoparse(wikidates[0][1:-1])
            return f'{d.day}.{d.month}.{d.year}'
        except:
            return None

    def to_object(self) -> object:
        r = {'name': self._name, 'type': self._type}
        if self.variations:
            r['variations'] = self.variations
        if self.wikidata:
            r['wikidata'] = self.wikidata
        if self.theaterlexikon:
            r['theaterlexikon'] = self.theaterlexikon
        if self.sapa:
            r['sapa'] = self.sapa
        if self.dob:
            r['dob'] = self.dob
        if self.dod:
            r['dod'] = self.dod
        if self.image:
            r['image'] = self.image
        return r

class Segment(object):

    def __init__(self, r: pd.Series, entities_dict: dict, missing_entities: set):
        self.video = r['video']
        self.start = r['start']
        self.text = r['text']
        self.entities = [] 
        if not pd.isnull(r['entities']):
            for e in re.split(r'\s*;\s*', str(r['entities']).strip()):
                if e in entities_dict:
                    self.entities.append(entities_dict[e])
                elif e != '':
                    missing_entities.add(e)

    def to_object(self) -> object:
        r = {'video': self.video, 'start': self.start}
        if self.text:
            r['text'] = self.text
        if len(self.entities) > 0:
            r['entities'] = self.entities
        return r

class WikidataJSON(object):

    def __init__(self, json_: object):
        self.json = json_

    def get_claim_values(self, p: str, lang: list = None):
        claim_values = []
        if lang:
            claims_dict = dict()
            for l in lang:
                claims_dict[l] = []
        if p in self.json['claims']:
            for c in self.json['claims'][p]:
                if 'snaktype' in c['mainsnak'] and c['mainsnak']['snaktype'] in ['novalue', 'somevalue']:
                    break
                v = c['mainsnak']['datavalue']['value']
                if type(v) is str:
                    claim_values.append(v)
                elif 'id' in v:
                    claim_values.append(v['id'])
                elif 'time' in v:
                    claim_values.append(v['time'])
                elif 'text' in v:
                    if lang:
                        if 'language' in v and v['language'] in lang:
                            claims_dict[v['language']].append(v['text'])
                    else:
                        claim_values.append(v['text'])
        if lang:
            for l in lang:
                if claims_dict[l]:
                    return claims_dict[l]
        return claim_values

if __name__ == '__main__':
    m = Main()