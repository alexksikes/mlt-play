import utils
import copy


class QueryIndex(object):
    def __init__(self, es, index, doc_type, search_fields,
                 more_like_this_params={}, facets=[], verbose=False,
                 explain=True, method='like_text'):
        self.es = es
        self.index = index
        self.doc_type = doc_type
        self.search_fields = search_fields
        self.more_like_this_params = {
            'fields': search_fields,
            'max_query_terms': 25,
            'min_term_freq': 2,
            'min_doc_freq': 5,
            'max_doc_freq': 1000000,
            'min_word_length': 0,
            'max_word_length': 0,
            'stop_words': [""],
            'analyzer': "",
            'boost_terms': 0,
            'minimum_should_match': "0%",
            'include': True,
        }
        self.more_like_this_params.update(more_like_this_params)
        self.facets = facets

        self.body = {}
        self.verbose = verbose
        self.explain = explain
        self.method = method

    def get_mlt_params(self):
        return self.more_like_this_params

    def set_mlt_params(self, params):
        self.more_like_this_params = params

    def get_full_text_query(self, query):
        return {
            'query_string': {
                'fields': self.search_fields,
                'query': query
            }
        }

    def get_more_like_this_query(self, like_text):
        self.more_like_this_params[self.method] = like_text
        return {
            'more_like_this': self.more_like_this_params
        }

    def get_mlt_txt_query(self, like_text, query):
        return {
            'bool': {
                'should': [
                    self.get_more_like_this_query(like_text),
                    self.get_full_text_query(query)
                ],
                'minimum_should_match': 2
            }
        }

    def get_facets_query(self):
        aggs = {}
        for name, field in self.facets:
            aggs[name] = {
                'terms': {
                    'field': field,
                    'size': 10
                },
            }
        return aggs

    def full_text_search(self, query, _from=0, size=20):
        query = self.get_full_text_query(query)
        aggs = self.get_facets_query()
        self.body = {'query': query, 'aggs': aggs, 'explain': self.explain, 'from': _from,
                     'size': size}
        return self.perform_search()

    def more_like_these(self, ids, query=None, _from=0, size=20):
        if self.method == '_mlt':
            return self.more_like_this_endpoint(ids[0], _from, size)
        # get the text in each field
        elif self.method == 'like_text':
            like_text = self.get_document_text(ids)
        else:
            like_text = ids
        # build more like this query with text search if provided
        if query is None:
            query = self.get_more_like_this_query(like_text)
        else:
            query = self.get_mlt_txt_query(like_text, query)
        # perform the actual search
        aggs = self.get_facets_query()
        self.body = {'query': query, 'aggs': aggs, 'explain': self.explain, 'from': _from,
                     'size': size}
        return self.perform_search()

    def get_document_by_ids(self, ids):
        docs = self.es.mget(
            index=self.index, doc_type=self.doc_type, body={'ids': ids},
            fields=self.more_like_this_params['fields'])
        docs = docs['docs']
        return (doc['fields'] for doc in docs if doc['found'])

    def get_document_text(self, ids):
        text = ''
        for doc in self.get_document_by_ids(ids):
            for f in self.more_like_this_params['fields']:
                if f not in doc:
                    continue
                doc[f] = utils.listify(doc[f])
                # keep intact for tagger analyzer
                if f.endswith('.terms') or f.endswith('.raw'):
                    text += ' ' + ' '.join('"%s"' % term for term in doc[f])
                else:
                    text += ' ' + ' '.join(doc[f])
        return text.strip()

    def more_like_this_endpoint(self, id, _from=0, size=20):
        self.body = {'explain': self.explain, 'from': _from, 'size': size}
        if self.verbose:
            print utils.pretty_json(self.body)
        # some parameters have different names
        params = copy.deepcopy(self.more_like_this_params)
        params['mlt_fields'] = params.pop('fields')
        # bug in ES python?
        if params['mlt_fields'] is None:
            params['mlt_fields'] = ''

        params.pop('analyzer')

        aggs = self.get_facets_query()
        self.body['aggs'] = aggs
        return self.es.mlt(
            index=self.index, doc_type=self.doc_type, id=id, body=self.body,
            **params)

    def perform_search(self):
        if self.verbose:
            print utils.pretty_json(self.body)
        return self.es.search(
            index=self.index, doc_type=self.doc_type, body=self.body)

    @classmethod
    def build_query_index(cls, type, verbose=False, explain=True, method='like_text'):
        es = utils.get_es()
        if type == 'tmdb':
            return QueryIndex(
                es,
                'tmdb',
                'movies',
                search_fields=[
                    'alternative_titles.titles.title',
                    'credits.cast.character',
                    'credits.cast.name',
                    'credits.crew.name',
                    'genres.name',
                    'keywords.keywords.name',
                    'original_title',
                    'overview',
                    'production_companies.name',
                    'production_countries.name',
                    'tagline',
                    'title'
                ],
                more_like_this_params={
                    'fields': [
                        'keywords.keywords.name.terms',
                        'title',
                        'overview',
                        'tagline',
                        'genres.name.terms',
                        'credits.cast.name.terms',
                        'credits.crew.name.terms',
                        'alternative_titles.titles.title',
                        # 'credits.cast.character.terms',
                        # 'original_title',
                        # 'production_companies.name.terms',
                        # 'production_countries.name.terms',
                    ],
                    'min_term_freq': 1,
                    'min_doc_freq': 1,
                    # 'max_query_terms': 100000,
                    'minimum_should_match': "0%",
                    'analyzer': 'tag_analyzer'
                },
                verbose=verbose,
                explain=explain,
                method=method
            )
        elif type == 'imdb':
            return QueryIndex(
                es,
                'imdb',
                'movies',
                search_fields=[
                    'title',
                    'also_known_as',
                    'plot',
                    'actors',
                    'writers',
                    'directors',
                    'genres',
                    'plot_keywords',
                    'tagline',
                ],
                more_like_this_params={
                    'fields': [
                        'plot_keywords.terms'
                    ],
                    'min_term_freq': 1,
                    'min_doc_freq': 1,
                    # 'max_query_terms': 100000,
                    'minimum_should_match': "0%",
                    'analyzer': 'tag_analyzer'
                },
                facets=[
                    ('Plot Keywords', 'plot_keywords.terms'),
                    ('Actors', 'actors.terms'),
                    ('Directors', 'directors.terms'),
                    ('Genres', 'genres.terms')
                ],
                verbose=verbose,
                explain=explain,
                method=method
            )
        elif type == 'movielens':
            return QueryIndex(
                es,
                'movielens',
                'movies',
                [
                    'title',
                    'likes'
                ],
                more_like_this_params={
                    'fields': [
                        'likes'
                    ],
                    'min_term_freq': 1,
                    'min_doc_freq': 1,
                    # 'max_query_terms': 100000,
                    'minimum_should_match': "0%",
                    'analyzer': 'tag_analyzer'
                },
                verbose=verbose,
                explain=explain,
                method=method
            )
        elif type == 'mirflickr':
            return QueryIndex(
                es,
                'mirflickr',
                'images',
                [
                    '_all'
                ],
                more_like_this_params={
                    'fields': [
                        'tags_raw.raw',
                        'annotations.potential.raw',
                        'annotations.relevant.raw',
                        'features.colors'
                        # 'features.colors_with_counts'
                    ],
                    'min_term_freq': 1,
                    'min_doc_freq': 1,
                    # 'max_query_terms': 100000,
                    'minimum_should_match': "0%",
                    'analyzer': 'tag_analyzer'
                },
                verbose=verbose,
                explain=explain,
                method=method
            )
