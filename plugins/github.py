"""github stuff"""

from util import hook, http, timesince
from datetime import datetime

@hook.api_key('github')
@hook.command('git')
@hook.command
def github(inp, api_key=None):
    """ .github <username or username/repo> -- returns info on the github user or repo specified in <query> """

    if not api_key:
        return None

    return respond(inp, api_key)


@hook.api_key('github')
@hook.regex(r'.*github\.com/([\S]*) ?')
# todo: strip after repo/user name-- like in https://github.com/rmmh/skybot/wiki
def show_github(inp, api_key=None):
    """responds to github links in chat"""

    if not api_key:
        return None

    match = inp.group(1)
    return respond(match, api_key)


def respond(inp, api_key):
    if '/' in inp:
        # name/repo
        return respond_repo(inp, api_key)

    else:
        # username
        return respond_user(inp, api_key)


def respond_repo(inp, api_key):
    user, repo = map(unicode.strip, inp.split('/'))
    url_args = {'user': user,
                'repo': repo,
                'api_key': api_key}

    repo_url = 'https://api.github.com/repos/{user}/{repo}?access_token={api_key}'\
        .format(**url_args)
    commits_url = 'https://api.github.com/repos/{user}/{repo}/commits?access_token={api_key}'\
        .format(**url_args)
    contributors_url = 'https://api.github.com/repos/{user}/{repo}/contributors?access_token={api_key}'\
        .format(**url_args)

    try:
        result = try_get(repo_url, commits_url, contributors_url)
    except Exception as e:
        return 'error: ' + e

    (repo, commits, contributors) = result

    return (u'\x02{full_name}\x02: {description} {fork_text}'
            u' | {watchers_count} {watchers_name}, {stargazers_count} {stargazers_name}, {forks_count} {forks_name}'
            u' | written in {language} by {contributors_count} {contributors_name};'
            u' last commit was {last_commit_ago} ago.'
            u' https://github.com/{full_name}')\
        .format(fork_text='| Forked from {parent}'.format(
                    parent=repo.get(u'parent').get(u'full_name')) if repo.get(u'parent') else '',
                watchers_name=pluralise('watcher', repo[u'watchers_count']),
                stargazers_name=pluralise('stargazer', repo[u'stargazers_count']),
                forks_name=pluralise('fork', repo[u'forks_count']),
                contributors_count=len(contributors),
                contributors_name=pluralise('contributor', len(contributors)),
                last_commit_ago=timesince.timesince(
                    datetime.strptime(commits[0][u'commit'][u'author'][u'date'], '%Y-%m-%dT%H:%M:%SZ')),
                **repo)


def respond_user(inp, api_key):
    user = inp.strip()
    url_args = {'user': user,
                'api_key': api_key}

    user_url = 'https://api.github.com/users/{user}?access_token={api_key}'\
        .format(**url_args)
    repos_url = 'https://api.github.com/users/{user}/repos?access_token={api_key}&per_page=100'\
        .format(**url_args)

    try:
        result = try_get(user_url, repos_url)
    except Exception as e:
        return 'error: ' + e

    (user, repos) = result

    stars_count = reduce(lambda t, r: t + r[u'stargazers_count'], repos, 0)

    repos.sort(key=lambda x: x[u'stargazers_count'], reverse=True)
    top_repos = map(lambda x: x[u'name'], repos[:3])

    user[u'name'] = user.get(u'name', u'(no real name given)')

    return (u'{html_url}'
            u' | {name}'
            u' | {public_repos} {repos_name}, {followers} {followers_name}, {stars_count} total {stars_name}'
            u' | top repos: {top_repos}').format(repos_name=pluralise('public repo', user[u'public_repos']),
                                                 followers_name=pluralise('follower', user[u'followers']),
                                                 stars_count=stars_count,
                                                 stars_name=pluralise('star', stars_count),
                                                 top_repos=', '.join(top_repos),
                                                 **user)


def try_get(*urls):
    try:
        return map(http.get_json, urls)

    except http.HTTPError as e:
        errors = {400: 'bad request (rate-limited?)',
                  401: 'unauthorized',
                  403: 'forbidden',
                  404: 'invalid user/id',
                  500: 'github is broken'}

        if e.code == 404:
            raise Exception('error: not found')
        raise Exception(errors.get(e.code, "Unknown Code: %s" % e.code))

    except http.URLError as e:
        raise Exception(str(e.reason))


def pluralise(word, num):
    return word if num is 1 else word + 's'
