"""Usage:
    test_sqlite_db.py get-browse <type>
    test_sqlite_db.py get-item <item-identifier>
    test_sqlite_db.py get-series <series-identifier>
    test_sqlite_db.py list-items [--verbose]
    test_sqlite_db.py list-series [--verbose]
    test_sqlite_db.py search <term>
"""

import docopt, json, sqlite3, sys

def get_browse(cur, browse_type):
    """
    Get browse.

    Parameters:
        cur (sqlite3.Cursor): a cursor instance to query the db.
        browse_type (str): type of browse terms to retrieve. 

    Returns:
        list: a list of browse terms.
    """
    assert browse_type in ('contributor', 'date', 'language', 'location')

    return cur.execute(
        '''
            select term, count(id)
            from browse
            where type=?
            group by term
            order by {}
        '''.format(
            {
                'contributor': 'count(id) desc',
                'date': 'term',
                'language': 'count(id) desc',
                'location': 'count(id) desc'
            }[browse_type]
        ),
        (browse_type,)
    ).fetchall()

def get_item(cur, identifier):
    """
    Get item metadata.

    Parameters:
        cur (sqlite3.Cursor): a cursor instance to query the db.

    Returns:
        dict: a metadata dictionary.
    """
    return json.loads(
        cur.execute(
            'select info from item where id = ?',
            (identifier,)
        ).fetchone()[0]
    )

def get_item_list(cur):
    """
    Get all item identifiers.

    Parameters:
        cur (sqlite3.Cursor): a cursor instance to query the db.

    Returns:
        list: a list of identifier, metadata dict tuples. 
    """
    results = []
    for row in cur.execute('select id, info from item;').fetchall():
        results.append((row[0], json.loads(row[1])))
    return results

def get_series(cur, identifier):
    """
    Get series metadata.

    Parameters:
        cur (sqlite3.Cursor): a cursor instance to query the db.

    Returns:
        dict: a metadata dictionary.
    """
    return json.loads(
        cur.execute(
            'select info from series where id = ?',
            (identifier,)
        ).fetchone()[0]
    )

def get_series_list(cur):
    """
    Get all series identifiers.

    Parameters:
        cur (sqlite3.Cursor): a cursor instance to query the db.

    Returns:
        list: a list of identifier, metadata dict tuples. 
    """
    results = []
    for row in cur.execute('select id, info from series;').fetchall():
        results.append((row[0], json.loads(row[1])))
    return results

if __name__ == '__main__':
    args = docopt.docopt(__doc__)

    con = sqlite3.connect(':memory:')
    cur = con.cursor()
    cur.executescript(sys.stdin.read())

    if args['get-browse']:
        for row in get_browse(cur, args['<type>']):
            print('{} ({})'.format(row[0], row[1]))
    elif args['get-item']:
        i = get_item(cur, args['<item-identifier>'])
        print(args['<item-identifier>'])
        sys.stdout.write(('{}: {}\n' * 12 + '\n').format(
            'Item Title',
            ' '.join(i['title']),
            'Item Identifier',
            i['identifier'][0],
            'Contributor',
            ' | '.join(i['contributor']),
            'Indigenous Language',
            ' | '.join(i['language']),
            'Language',
            ' | '.join(i['language']),
            'Location Where Indigenous Language is Spoken',
            ' | '.join(i['language']),
            'Date',
            ' | '.join(i['date']),
            'Description',
            ' | '.join(i['description']),
            'Linguistic Data Type',
            ' | '.join(i['linguistic_data_type']),
            'Discourse Type',
            ' | '.join(i['discourse_type']),
            'Item Content Type',
            ' | '.join(i['content_type']),
            'Part of Series',
            i['is_part_of'][0]
        ))
    elif args['get-series']:
        i = get_series(cur, args['<series-identifier>'])
        print(args['<series-identifier>'])
        sys.stdout.write(('{}: {}\n' * 8 + '\n').format(
            'Series Title',
            ' '.join(i['title']),
            'Series Identifier',
            i['identifier'][0],
            'Collection',
            '',
            'Indigenous Language',
            ' | '.join(i['language']),
            'Language',
            ' | '.join(i['language']),
            'Location Where Indigenous Language is Spoken',
            ' | '.join(i['location']),
            'Date',
            ' | '.join(i['date']),
            'Description',
            ' | '.join(i['description'])
        ))
    elif args['list-items']:
        for i in get_item_list(cur):
            print(i[0])
            if args['--verbose']:
                sys.stdout.write(('{}: {}\n' * 6 + '\n').format(
                    'Item Title',
                    ' '.join(i[1]['title']),
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
    elif args['list-series']:
        for i in get_series_list(cur):
            print(i[0])
            if args['--verbose']:
                sys.stdout.write(('{}: {}\n' * 6 + '\n').format(
                    'Series Title',
                    ' '.join(i[1]['title']),
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
    elif args['search']:
        for i in get_search(cur):
            print('x')
 
