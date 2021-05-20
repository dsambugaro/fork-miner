import requests
import csv
import random
from itertools import cycle
from time import sleep


tokens = []
tokens_pool = cycle(tokens)
repos = []


def get_headers():
    global tokens
    headers = {'Authorization': 'token ' + next(tokens_pool)}
    return headers


def do_request(url):
    global headers
    response = requests.get(url, headers=headers)
    while response.status_code == 403:
        print('Changing token ... ')
        headers = get_headers()
        response = requests.get(url, headers=headers)
    return response


def get_commits(author, url, since, as_boolean=False):
    page_commit = 1
    count = 0
    response = do_request(f'{url}?author={author}&since={since}&per_page=100&page={page_commit}')
    if as_boolean:
        return True if (response.status_code == 200 and len(response.json()) > 0) else False
    while response.status_code == 200 and len(response.json()) > 0:
        count += len(response.json())
        page_commit += 1
        response = do_request(f'{url}?author={author}&since={since}&per_page=100&page={page_commit}')
    return count


headers = get_headers()
size = 100
for repository in repos:
    page_forks = 1
    repo = do_request(f'https://api.github.com/repos/{repository}')
    if repo.status_code == 404:
        print(f'repository {repository} not found - skipping')
        continue
    print(f'starting fork-miner for repository {repository}...')
    repo = repo.json()
    forks = do_request(f'https://api.github.com/repos/{repository}/forks?per_page={size}&page={page_forks}').json()
    count = 0
    csv_name = f"data/{repository.split('/')[1]}_forks.csv"
    header_control = {csv_name: False}
    while len(forks) > 0:
        try:
            fork = forks.pop()
            username = fork['full_name'].split("/")[0]
            nr_commits_on_fork = get_commits(
                username,
                fork['commits_url'].replace('{/sha}', ''),
                fork['created_at'],
            )
            returned = get_commits(
                username,
                repo['commits_url'].replace('{/sha}', ''),
                fork['created_at'],
                as_boolean=True,
            )
            fork_details = {
                "fork": fork['full_name'],
                "url": fork['html_url'],
                "commits_from_user_on_fork": nr_commits_on_fork,
                "returned": True if returned and nr_commits_on_fork > 0 else False,
                "created_at": fork['created_at'],
                "pushed_at": fork['pushed_at'],
                "user": username,
            }
            with open(csv_name, "a", newline="") as csv_file:
                dict_writer = csv.DictWriter(csv_file, fork_details.keys())
                if not header_control[csv_name]:
                    dict_writer.writeheader()
                    header_control[csv_name] = True
                dict_writer.writerow(fork_details)
            count += 1
            print(f"Page: {page_forks} Fork:{fork['full_name']} - Forks processed: {count}")
            if len(forks) == 0:
                page_forks += 1
                forks = do_request(f'https://api.github.com/repos/{repository}/forks?per_page={size}&page={page_forks}').json()
        except:
            forks.append(fork)
            sleep(2)
            print(f"Error on fork {fork['full_name']}, retrying...")

    print(f'generating suggested review for repository {repository}...')
    with open(csv_name, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        rows = list(csv_reader)
        random_lines = [random.randint(1, len(rows)-1) for n in range(50)]
        review_rows = [rows[row] for row in random_lines]
        csv_suggested_review = csv_name.replace('_forks', '_to_review')
        header_control[csv_suggested_review] = False
        with open(csv_suggested_review, "w", newline="") as csv_file:
            dict_writer = csv.writer(csv_file)
            if not header_control[csv_suggested_review]:
                dict_writer.writerow(rows[0])
                header_control[csv_suggested_review] = True
            dict_writer.writerows(review_rows)

    print(f'ending fork-miner for repository {repository}...')
