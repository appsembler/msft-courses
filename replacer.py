old_ids = []
new_ids = []


with open('old-ids.txt', 'r') as old_ids_file:
    for old_id in old_ids_file.read().splitlines():
        old_id = old_id.replace('course-v1:', '')
        org, code, run = old_id.strip().split('+')
        old_ids.append({
            'org': org,
            'code': code,
            'run': run,
        })

with open('new-filenames.txt', 'r') as new_ids_file:
    for new_id in new_ids_file.read().splitlines():
        print 'READING new id', new_id
        new_id = new_id.replace('.tar.gz', '').replace('.zip', '')
        _, code, run = new_id.strip().rsplit('-', 2)
        new_ids.append({
            'org': 'Microsoft',
            'code': code,
            'run': run,
        })


def old_id_to_new(old_id):
    matches = []

    for new_id in new_ids:
        if new_id['code'] == old_id['code']:
            matches.append(new_id)

    assert len(matches) == 1, (old_id, matches)

    return matches[0]


def dict_to_str(i):
    return '{org}+{code}+{run}'.format(**i)


for old_id in old_ids:
    print dict_to_str(old_id), '=>', dict_to_str(old_id_to_new(old_id))


def replace_input(s):
    for old_id in old_ids:
        new_id = old_id_to_new(old_id)
        s = s.replace(dict_to_str(old_id), dict_to_str(new_id))

    return s


with open('pre.sql', 'r') as pre:
    with open('post.sql', 'w') as post:
        post.write(replace_input(pre.read()))
