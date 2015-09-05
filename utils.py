import re
import hashlib
import json
from jsonselect import jsonselect as jselect

import elasticsearch
from flask import g, request, url_for


def listify(l):
    if l is None or isinstance(l, list):
        return l
    else:
        return [l]


def get_es():
    es = getattr(g, '_index', None)
    if es is None:
        es = g._es = elasticsearch.Elasticsearch()
    return es


def generate_md5(s):
    if not s:
        return None
    return hashlib.md5(s).hexdigest()

p = re.compile('weight\(.*?:(.*)\sin\s\d+\)')
p_with_fields = re.compile('weight\((.*?:.*)\sin\s\d+\)')
# output is not consistent, better use a query language


def get_best_features(e, top_k=0, with_fields=False):
    strs = listify(jselect.select(
        '.description:contains("[PerFieldSimilarity]")', e))
    vals = listify(jselect.select(
        '.description:contains("[PerFieldSimilarity]") ~ .value', e))
    if with_fields:
        strs = (p_with_fields.match(str).group(1) for str in strs)
    else:
        strs = (p.match(str).group(1) for str in strs)

    feat = sorted(zip(vals, strs), reverse=True)
    return feat[0:top_k] if top_k else feat


def pretty_json(obj):
    return json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '),
                      ensure_ascii=False, encoding='utf8')


def url_for_other_page(page, **values):
    args = request.view_args.copy()
    args['page'] = page
    args.update(values)
    return url_for(request.endpoint, **args)


def url_for_filter(field, value, **values):
    args = request.view_args.copy()
    args.update(values)

    # import ipdb; ipdb.set_trace()

    field = field.lower().replace(' ', '_')
    if field in args:
        args[field] = '|'.join(args[field])
        args[field] += '|' + value
    else:
        args[field] = value
    return url_for(request.endpoint, **args)


def to_bool(str):
    if isinstance(str, bool):
        return str
    if str in ('true', 'True', '1', 'on'):
        return True
    if isinstance(str, int) or isinstance(str, float):
        return bool(str)
    else:
        return False
