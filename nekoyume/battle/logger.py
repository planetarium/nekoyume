import json
from dataclasses import asdict


class Logger:
    def __init__(self):
        self.logs = []
        self.print = False

    def log(self, log):
        self.logs.append(log)
        if self.print:
            print(log)

    def json_dump(self):
        status = []
        for log in self.logs:
            status.append(asdict(log))
        return json.dumps(
            {'status': status},
            indent=4,
            separators=(',', ': '))

    @property
    def characters(self):
        characters = {}
        for log in self.logs:
            if log.type == 'spawn':
                characters[log.id_] = {
                    'name': log.name,
                    'type': log.character_type,
                }
        return characters
