import os

FILE = "config.txt"

class Config:

    def __init__(self):
        self.file = FILE
        self.api_keys = {}
        self.load_api_keys(self.file)

    def load_api_keys(self, file_path):
        self.api_keys = {}
        try:
            with open(self.file, "r") as file:
                for line in file:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        self.api_keys[key] = value
            return self.api_keys
        except FileNotFoundError:
            print(f"(Config Class Error) FileNotFoundError: [Errno 2] No such file or directory: '{self.file}'")

    def get_key(self, key:str):
        try:
            return self.api_keys[key]
        except KeyError:
            print(f"(Config Class Error) KeyError: '{key}'")