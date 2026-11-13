"""Extract an object and apply JSON Schema plus domain constraints."""
import json
import math
from jsonschema import Draft202012Validator, ValidationError


def _ranges(value, key=''):
    if isinstance(value, dict):
        for k, v in value.items():
            _ranges(v, k)
    elif isinstance(value, list):
        for v in value:
            _ranges(v, key)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError('non-finite number')
        if key in ('probability', 'probabilities') and not 0 <= value <= 1:
            raise ValueError('probability outside [0,1]')
        if key in ('weight', 'weights') and value < 0:
            raise ValueError('negative weight')


def parse_response(text, schema):
    decoder = json.JSONDecoder()
    errors = []
    for i, char in enumerate(text):
        if char != '{':
            continue
        try:
            value, _ = decoder.raw_decode(text[i:])
        except ValueError:
            continue
        try:
            Draft202012Validator(schema or {'type': 'object'}).validate(value)
            _ranges(value)
            return value, None
        except (ValueError, ValidationError) as e:
            errors.append(str(e))
            # Do not salvage nested objects from an invalid outer object.
            return None, errors[-1]
    return None, 'No JSON object found'
