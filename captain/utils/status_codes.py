import yaml
import os

with open(
    os.path.join(os.path.dirname(__file__), "STATUS_CODES.yml"),
    "r",
    encoding="utf-8",
) as f:
    STATUS_CODES = yaml.safe_load(f)
