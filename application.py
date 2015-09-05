import string

from flask import Flask, render_template, request, redirect, url_for
from lib import paging
# from flask_debugtoolbar import DebugToolbarExtension

import utils
import models

PER_PAGE = 20
USER_MLT_PARAMS = [
    'fields',
    'percent_terms_to_match',
    'max_query_terms',
    'min_term_freq',
    'min_doc_freq',
    'max_doc_freq',
    'min_word_length',
    'max_word_length',
    'boost_terms',
    # 'boost',
    'analyzer',
    'stop_words',
    'include',
]
EXPLAIN = {
    'enable': True,
    'top_k': 500,
    'toggle_at': 10
}
VERBOSE = True
DEFAULT_METHOD = 'like_text'
METHODS = ['like_text', 'ids', '_mlt']

app = Flask(__name__)


def get_model(dataset):
    verbose = utils.to_bool(request.args.get('verbose', VERBOSE))
    explain = utils.to_bool(request.args.get('explain', EXPLAIN['enable']))
    method = request.args.get('method', DEFAULT_METHOD)
    return models.QueryIndex.build_query_index(
        dataset, verbose=verbose, explain=explain, method=method)


def get_pagination(results, cpage, per_page=PER_PAGE):
    return paging.Pagination(cpage+1, per_page, results['hits']['total'])


def get_methods():
    return METHODS


def to_user_mlt_params(mlt_params):
    params = []
    for k in USER_MLT_PARAMS:
        if k not in mlt_params:
            continue
        v = mlt_params[k]
        if v is None:
            v = ''
        elif k == 'fields' or k == 'stop_words':
            v = ','.join(v)
        else:
            v = str(v)
        params.append((k, v))
    return params


def update_mlt_params(user_mlt_params, params):
    for k, v in user_mlt_params.items():
        if k not in USER_MLT_PARAMS:
            continue
        if not v.strip():
            v = None    # use ES defaults
        elif k == 'fields' or k == 'stop_words':
            v = map(string.strip, v.split(','))
        elif k == 'analyzer':
            pass
        elif k in ('percent_terms_to_match', 'boost_terms'):
            v = float(v)
        elif k == 'include':
            v = utils.to_bool(v)
        else:
            v = int(v)
        params[k] = v


@app.route("/")
@app.route("/<dataset>/")
def index(dataset=''):
    if not dataset:
        return redirect(url_for('index', dataset='tmdb'))

    model = get_model(dataset)
    if model is None:
        return '', 404
    return render_template(
        'index.html', dataset=dataset, mlt_params=model.get_mlt_params())


@app.route("/<dataset>/search/")
@app.route("/<dataset>/search/<query>/")
@app.route("/<dataset>/search/<query>/page/<int:page>/")
def search(dataset, query=None, page=0):
    if query is None:
        query = request.args.get('_q', '')
        if request.args.get('with_mlt') and request.args.get('_ids'):
            ids = '+'.join(request.args.get('_ids', '').split(' '))
            return redirect(url_for('mlt', dataset=dataset, ids=ids, query=query))
        else:
            return redirect(url_for('search', dataset=dataset, query=query))

    model = get_model(dataset)
    if query == '':
        results = []
    else:
        results = model.full_text_search(query, page*PER_PAGE, PER_PAGE)
        pagination = get_pagination(results, page, PER_PAGE)
    return render_template(
        'search.html', dataset=dataset, query=query, results=results,
        pagination=pagination, mlt_params=model.get_mlt_params())


@app.route("/<dataset>/mlt/")
@app.route("/<dataset>/mlt/<ids>/")
@app.route("/<dataset>/mlt/<ids>/page/<int:page>/")
@app.route("/<dataset>/search/<query>/mlt/<ids>/")
@app.route("/<dataset>/search/<query>/mlt/<ids>/page/<int:page>/")
def mlt(dataset, ids=None, query=None, page=0):
    if ids is None:
        ids = '+'.join(request.args.get('_ids', '').split(' '))
        return redirect(url_for('mlt', dataset=dataset, ids=ids,
                        **request.args))

    model = get_model(dataset)
    ids = ids.split('+')
    if not ids:
        results = []
    else:
        update_mlt_params(request.args, model.get_mlt_params())
        results = model.more_like_these(ids, query, page*PER_PAGE, PER_PAGE)
        pagination = get_pagination(results, page, PER_PAGE)
    return render_template(
        'search.html', dataset=dataset, query=query, ids=ids, results=results,
        pagination=pagination, mlt_params=model.get_mlt_params(),
        with_mlt=ids and query, explain=model.explain)

if __name__ == "__main__":
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.globals.update(
        int=int,
        generate_md5=utils.generate_md5,
        get_best_features=utils.get_best_features,
        url_for_other_page=utils.url_for_other_page,
        url_for_filter=utils.url_for_filter,
        to_user_mlt_params=to_user_mlt_params,
        get_methods=get_methods,
        EXPLAIN=EXPLAIN)

    # app.config['SECRET_KEY'] = 'h@ll0!'
    # toolbar = DebugToolbarExtension(app)
    app.run(debug=True, host='0.0.0.0')
