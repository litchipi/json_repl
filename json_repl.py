# Taken from https://coderwall.com/p/w78iva/give-your-python-program-a-shell-with-the-cmd-module

import os
import json
import base64
import argparse
from cmd import Cmd

DEFAULT_FORMAT = "text"
DATA_LOADERS = {
    "text": lambda x: x,
    "int": lambda x: int(x),
    "float": lambda x: float(x),
    "json": lambda x: json.loads(x),
}

FILE_LOADERS = {
    "text": ("r", lambda f: f.read()),
    "json": ("r", lambda f: json.load(f)),
    "binary": ("rb", lambda f: base64.b64encode(f.read()).decode()),
}

# TODO      Tab completion
#       On keys
#       On files to write
#       On formats
class JsonREPL(Cmd):
    def __init__(self, dataf):
        Cmd.__init__(self)
        self.dataf = dataf
        if os.path.isfile(dataf):
            with open(dataf, "r") as f:
                self.inner_data = json.load(f)
        else:
            self.inner_data = dict()

    def save(self):
        with open(self.dataf, "w") as f:
            json.dump(self.inner_data, f)

    def get_value_from_keys(self, keys):
        data = dict.copy(self.inner_data)
        for key in keys:
            if (type(data) != dict) or (key not in data):
                return None
            data = data[key]
        return data

    def unfold_key(self, keys, data=None, set_to=None, rm=False):
        if data is None:
            data = dict.copy(self.inner_data)

        if len(keys) == 0:
            if set_to:
                return set_to
            elif rm:
                return {}
            else:
                return data
        elif keys[0] not in data.keys():
            if set_to:
                new_data = dict()
            elif rm:
                return {}
            else:
                return None
        elif type(data[keys[0]]) == dict:
            new_data = dict.copy(data[keys[0]])
        elif set_to:
            new_data = dict()
        else:
            return data[keys[0]]
        data[keys[0]] = self.unfold_key(keys[1:], data=new_data, set_to=set_to, rm=rm)
        return data

    def update_inner_data(self, key, data, rm=False):
        if "." not in key:
            if rm and key in self.inner_data.keys():
                del self.inner_data[key]
            else:
                self.inner_data[key] = data
        else:
            self.inner_data.update(
                self.unfold_key(key.split("."), set_to=data, rm=rm)    # type: ignore [no-redef]
            )
        self.save()

    # TODO  Finish
    def filepick_completion(self, text):
        if "/" in text:
            print(text)
            start_dir = os.path.join(os.path.curdir, "/".join(text.split("/")[:-1]))
        else:
            start_dir = os.path.curdir
        for root, dirs, files in os.walk(start_dir):
            return [
                p for p in files if p.startswith(text)
            ] + [
                d + "/" for d in dirs if d.startswith(text)
            ]

    def format_completion(self, text, file_loader=False):
        if file_loader:
            return [k for k in FILE_LOADERS if k.startswith(text)]
        else:
            return [k for k in DATA_LOADERS if k.startswith(text)]

    def dotkeys_completion(self, text):
        prefix = text.split(".")[-1]
        past_keys = text.split(".")[:-1]
        data = self.get_value_from_keys(past_keys)
        if not data:
            return []
        poss = [k for k in data if k.startswith(prefix)]
        head = ".".join(past_keys)
        head += "."*(len(head) > 0)
        if len(poss) == 1:
            if type(data[poss[0]]) != dict:
                tail = " "
            else:
                tail = "."
            return [ head + poss[0] + tail ]
        else:
            return [ head + k for k in poss ]

    def do_add(self, args):
        ''' Usage: add <key> <data> [format=fmt]
        '''
        argl = args.split()
        if len(args) < 2:
            self.do_help("add")
            return
        key = argl[0]
        data = args.removeprefix(key).lstrip()
        if "format=" in data.split()[-1]:
            fmt = data.split()[-1].split("=")[1]
            data = data[:-1]
        else:
            fmt = DEFAULT_FORMAT
        if fmt not in DATA_LOADERS.keys():
            print("Format unknwon")
            print("Available data formats: {}".format(
                ", ".join([
                    l + (" (default)"*(l==DEFAULT_FORMAT)) for l in DATA_LOADERS.keys()
                ]))
            )
            return
        try:
            data = DATA_LOADERS[fmt](data)
        except Exception as err:
            print(f"Loading the data failed: {err}")
            return
        self.update_inner_data(key, data)

    def complete_add(self, text, line, begidx, endidx):
        return self.dotkeys_completion(text)

    def complete_get(self, text, line, begidx, endidx):
        return self.dotkeys_completion(text)

    def complete_rm(self, text, line, begidx, endidx):
        return self.dotkeys_completion(text)

    def do_get(self, args):
        ''' Usage: get <key>
        '''
        args = args.split()
        if len(args) < 1:
            print(json.dumps(self.inner_data, indent=2))
            return
        key = args[0].rstrip(".")
        d = self.get_value_from_keys(key.split("."))
        if not d:
            print(f"Key {key} doesn't point to any data yet")
            return
        if type(d) == dict:
            print(json.dumps(d, indent=2))
        else:
            print(d)

    def do_rm(self, args):
        ''' Usage: rm <key>
        '''
        args = args.split()
        if len(args) < 1:
            self.do_help("rm")
            return
        key = args[0]
        self.update_inner_data(key, None, rm=True)

    def complete_from_file(self, text, line, begidx, endidx):
        nargs = len(line.split())
        if line.endswith(" "):
            nargs += 1
        if nargs == 2:  # Complete the key
            return self.dotkeys_completion(text)
        elif nargs == 3:  # Complete the file
            return self.filepick_completion(text)
        elif nargs == 4:    # Complete the format
            return self.format_completion(text, file_loader=True)
        else:
            return []

    def do_from_file(self, args):
        ''' Usage: from_file <key> <file path> <format>
            Format can be: text, binary, json
        '''
        args = args.split()
        if len(args) < 3:
            self.do_help("from_file")
            return
        key = args[0]
        fpath = args[1]
        fmt = args[2]
        if fmt not in FILE_LOADERS.keys():
            print(f"Wrong format {fmt}")
            print("Available file formats: {}".format(", ".join(list(FILE_LOADERS.keys()))))
            return
        if not os.path.isfile(fpath):
            print(f"{fpath}: No such file or directory")
            return
        try:
            with open(fpath, FILE_LOADERS[fmt][0]) as f:
                data = FILE_LOADERS[fmt][1](f)
        except Exception as err:
            print(f"Error while loading from file: {err}")
            return
        self.update_inner_data(key, data)

    def do_EOF(self, args):
        print("")
        raise SystemExit

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", help="JSON file to save the data to")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    prompt = JsonREPL(args.json_file)
    prompt.prompt = '>>> '
    prompt.cmdloop("")
