import click, json, logging, os, re, sqlite3, sqlite_dump, sys
from flask import abort, Flask, render_template, request, session, redirect
from flask_session import Session
from utils import MLCDB
from flask_babel import Babel, gettext, lazy_gettext, get_locale

app = Flask(__name__)
app.config.from_pyfile('local.py')

Session(app)

BASE = 'https://ark.lib.uchicago.edu/ark:61001/'
mlc_db = MLCDB(app.config)

# Language switching

def get_locale():
    """Language switching."""
    if not 'language' in session:
        session['language'] = 'en'
    return session.get('language')

babel = Babel(app, default_locale='en', locale_selector=get_locale)

@app.context_processor
def inject_strings():
    return {
        'locale': get_locale(),
        'trans': {
            'collection_title': lazy_gettext(u'Mesoamerican Language Collections')
        }
    }

@app.route('/language-change', methods=['POST'])
def change_language():
    if 'language' in session and session['language'] == 'en':
        session['language'] = 'es'
    else:
        session['language'] = 'en'
    return redirect(request.referrer) 

# CLI

def print_item(item_info):
    sys.stdout.write('{}\n'.format(item_info['ark']))
    sys.stdout.write(('{}: {}\n' * 15 + '\n').format(
        'Panopto Links',
        ' '.join(item_info['panopto_links']),
        'Panopto Identifiers',
        ' '.join(item_info['panopto_identifiers']),
        'Access Rights',
        ' | '.join(item_info['access_rights']),
        'Item Title',
        ' '.join(item_info['titles']),
        'Item Identifier',
        item_info['identifier'][0],
        'Contributor',
        ' | '.join(item_info['contributor']),
        'Indigenous Language',
        ' | '.join(item_info['subject_language']),
        'Language',
        ' | '.join(item_info['primary_language']),
        'Location Where Indigenous Language is Spoken',
        ' | '.join(item_info['location']),
        'Date',
        ' | '.join(item_info['date']),
        'Description',
        ' | '.join(item_info['description']),
        'Linguistic Data Type',
        ' | '.join(item_info['linguistic_data_type']),
        'Discourse Type',
        ' | '.join(item_info['discourse_type']),
        'Item Content Type',
        ' | '.join(item_info['content_type']),
        'Part of Series',
        item_info['is_part_of'][0]
    ))

def print_series(series_info):
    sys.stdout.write('{}\n'.format(series_info['ark']))
    sys.stdout.write(('{}: {}\n' * 8 + '\n').format(
        'Series Title',
        ' '.join(series_info['titles']),
        'Series Identifier',
        series_info['identifier'][0],
        'Collection',
        '',
        'Indigenous Language',
        ' | '.join(series_info['subject_language']),
        'Language',
        ' | '.join(series_info['primary_language']),
        'Location Where Indigenous Language is Spoken',
        ' | '.join(series_info['location']),
        'Date',
        ' | '.join(series_info['date']),
        'Description',
        ' | '.join(series_info['description'])
    ))

@app.cli.command(
    'build-db', 
    short_help='Build or rebuild SQLite database from linked data triples.'
)
def cli_build_db():
    """Build a SQLite database from linked data triples."""
    mlc_db.build_db()

@app.cli.command(
    'get-browse',
    short_help='Get a contributor, creator, date, decade, language or location browse.'
)
@click.argument('browse_type')
def cli_get_browse(browse_type):
    """List browse terms."""
    for row in mlc_db.get_browse(browse_type):
        sys.stdout.write('{} ({})\n'.format(row[0], row[1]))

@app.cli.command(
    'get-browse-term',
    short_help='Get series for a specific browse term.'
)
@click.argument('browse_type')
@click.argument('browse_term')
def cli_get_browse_term(browse_type, browse_term):
    for row in mlc_db.get_browse_term(browse_type, browse_term):
        print_series(row[1])

@app.cli.command(
    'get-item',
    short_help='Get item info for an item identifier.'
)
@click.argument('item_identifier')
def cli_get_item(item_identifier):
    print_item(mlc_db.get_item(item_identifier))

@app.cli.command(
    'get-series',
    short_help='Get series info for a series identifier.'
)
@click.argument('series_identifier')
def cli_get_series(series_identifier):
    print_series(mlc_db.get_series(series_identifier))

@app.cli.command(
    'list-items',
    short_help='List item objects.'
)
@click.option('--verbose', '-v', is_flag=True, help='Verbose output.')
def cli_list_items(verbose):
    for i in mlc_db.get_item_list():
        if verbose:
            print_item(mlc_db.get_item(i))
        else:
            sys.stdout.write('{}\n'.format(i))

@app.cli.command(
    'list-series',
    short_help='List series objects.'
)
@click.option('--verbose', '-v', is_flag=True, help='Verbose output.')
def cli_list_series(verbose):
    for i in mlc_db.get_series_list():
        if verbose:
            print_series(mlc_db.get_series(i))
        else:
            sys.stdout.write('{}\n'.format(i))

@app.cli.command(
    'search',
    short_help='Search for term.'
)
@click.argument('term')
@click.argument('facet')
def cli_search(term, facet):
    for i in mlc_db.get_search(term, [facet], 'rank'):
        print(i[0])
        print(i[2])
        sys.stdout.write(('{}: {}\n' * 6 + '\n').format(
            'Series Title',
            ' '.join(i[1]['titles']),
            'Contributor',
            ' | '.join(i[1]['contributor']),
            'Indigenous Language',
            ' | '.join(i[1]['language']),
            'Location',
            ' | '.join(i[1]['location']),
            'Date',
            ' | '.join(i[1]['date']),
            'Resource Type',
            ' | '.join(i[1]['content_type'])
        ))
        print('')

# WEB

access_key = {
    'restricted': {
        'trans': lazy_gettext(u'Restricted'),
        'class': 'warning'
    },
    'public domain':  {
        'trans': lazy_gettext(u'Public Domain'),
        'class': 'success'
    }
}

def get_access_label_obj(item):
    # list of results
        # tuple for item
            # string for url
            # dictionary of data
                # list of values
    ar = item['access_rights']

    # [<string from database>, <translated string>, <bootstrap label class>]
    if( len(ar) > 0 and ar[0].lower() in access_key):
        return [
            ar[0], 
            access_key[ar[0].lower()]['trans'], 
            access_key[ar[0].lower()]['class']
            ]
    else:
        return ['emtpy','By Request','info']

@app.errorhandler(400)
def bad_request(e):
    return (render_template('400.html'), 400)

@app.errorhandler(404)
def not_found(e):
    return (render_template('404.html'), 404)

@app.errorhandler(500)
def bad_request(e):
    return (render_template('500.html'), 500)

@app.route('/')
def home():
    return render_template(
        'home.html'
    )

@app.route('/suggest-corrections/')
def suggest_corrections():
    item_title = request.args.get('ittt')
    rec_id = request.args.get('rcid')
    item_url = request.args.get('iurl')
    page_title = lazy_gettext(u'Suggest Corrections')
    return render_template(
        'suggest-corrections.html',
        item_title = item_title,
        rec_id = rec_id,
        item_url = item_url,
        title_slug = page_title,
        hide_right_column = True
    )

@app.route('/browse/')
def browse():
    title_slugs = {
        'contributor': lazy_gettext(u'Browse by Contributors'),
        'creator':     lazy_gettext(u'Browse by Creator'),
        'date':        lazy_gettext(u'Browse by Date'),
        'decade':      lazy_gettext(u'Browse by Decade'),
        'language':    lazy_gettext(u'Browse by Language'),
        'location':    lazy_gettext(u'Browse by Location')
    }

    browse_type = request.args.get('type')
    if not browse_type in title_slugs.keys():
        app.logger.debug(
            'in {}(), type parameter not a key in browses dict.'.format(
                sys._getframe().f_code.co_name
            )
        )
        abort(400)

    browse_term = request.args.get('term')

    if browse_term:
        if browse_type:
            title_slug = lazy_gettext(u'Results with')+" "+browse_type+": "+browse_term+""
        else:
            title_slug = lazy_gettext(u'Results for search')+": "+browse_term+""

        sort_field = 'dbid'
        if browse_type == 'decade':
            sort_field = 'date'

        results = mlc_db.get_browse_term(browse_type, browse_term, sort_field)

        mod_results = []
        for item in results:
            item_data = item[1]
            item_data['access_rights'] = get_access_label_obj(item_data)
            mod_results.append( (item[0], item_data ) )

        return render_template(
            'search.html',
            facets = [],
            query = browse_term,
            query_field = browse_type,
            results = mod_results,
            title_slug = title_slug
        )
    else:
        return render_template(
            'browse.html',
            title_slug = title_slugs[browse_type],
            browse_terms = mlc_db.get_browse(browse_type),
            browse_type = browse_type
        )

@app.route('/item/<noid>/')
def item(noid):
    if not re.match('^[a-z0-9]{12}$', noid):
        app.logger.debug(
            'in {}(), user-supplied noid appears invalid.'.format(
                sys._getframe().f_code.co_name
            )
        )
        abort(400)

    item_data = mlc_db.get_item(BASE + noid)

    if item_data['panopto_identifiers']:
        panopto_identifier = item_data['panopto_identifiers'][0]
    else:
        panopto_identifier = ''

    series = [] 
    for s in mlc_db.get_series_for_item(BASE + noid):
        series.append((s, mlc_db.get_series(s)))

    try:
        title_slug = item_data['titles'][0]
    except (IndexError, KeyError):
        title_slug = ''

    breadcrumb = '<a href=\'/series/{}\'>{}</a> &gt; {}'.format(
        series[0][0].replace(BASE, ''),
        series[0][1]['titles'][0],
        item_data['titles'][0]
    )

    return render_template(
        'item.html',
        **(item_data | {'series': series[0],
                        'title_slug': title_slug,
                        'access_rights': get_access_label_obj(item_data),
                        'panopto_identifier': panopto_identifier,
                        'breadcrumb': breadcrumb})
    )

@app.route('/search/')
def search():
    facets = request.args.getlist('facet')
    query = request.args.get('query')
    sort_type = request.args.get('sort', 'rank')

    db_results = mlc_db.get_search(query, facets, sort_type)

    processed_results = []
    for db_series in db_results:
        series_data = mlc_db.get_series(db_series[0])
        series_data['access_rights'] = get_access_label_obj(series_data)
        processed_results.append( (db_series[0], series_data ) )

    if facets:
        title_slug = lazy_gettext(u'Search Results for') + ' ' + facets[0]
    elif query:
        title_slug = lazy_gettext(u'Search Results for') + ' \'' + query + '\''
    else:
        title_slug = lazy_gettext(u'Search Results')

    return render_template(
        'search.html',
        facets = [],
        query = query,
        query_field = '',
        results = processed_results,
        title_slug = title_slug
    )
    
@app.route('/series/<noid>/')
def series(noid):
    if not re.match('^[a-z0-9]{12}$', noid):
        app.logger.debug(
            'in {}(), user-supplied noid appears invalid.'.format(
                sys._getframe().f_code.co_name
            )
        )
        abort(400)

    series_data = mlc_db.get_series(BASE + noid)

    items = []
    for i in mlc_db.get_items_for_series(BASE + noid):
        items.append((
            i,
            mlc_db.get_item(i)
        ))

    try:
        title_slug = series_data['titles'][0]
    except (IndexError, KeyError):
        title_slug = ''

    return render_template(
        'series.html',
        **(series_data | {
            'items': items,
            'title_slug': title_slug,
            'access_rights': get_access_label_obj(series_data)
        })
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0')
