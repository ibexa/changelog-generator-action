import os
import re

from github import Github

JIRA_PREFIX = "https://ibexa.atlassian.net/browse/"


# TODO: Make sure that we can categorize commits based on JIRA type
def format_messages(message, repo_name):
    # Extract only first line of commit message
    message = message.partition("\n")[0]

    # Add JIRA links
    message = add_jira_links(message)

    # Add PR links
    # Links must be explicit links,
    # because when we will be combining changelogs in one release
    # relative links will be linking to wrong repo/will be not links
    message = add_pr_links(message, repo_name)

    return "- " + message


def add_jira_links(message):
    regex = r"^((?!([A-Z0-9a-z]{1,10})-?$)[A-Z]{1}[A-Z0-9]+-\d+)"
    subst = f"[\\1]({JIRA_PREFIX}\\1)"
    result = re.sub(regex, subst, message, 0, re.MULTILINE)
    return result


def add_pr_links(message, repo_name):
    regex = r"\(#(\d+)\)"
    subst = f"([#\\1](https://github.com/{repo_name}/pull/\\1))"
    message = re.sub(regex, subst, message, 0, re.MULTILINE)
    return message


def prepare_output(txt):
    return txt.replace("\n", "%0A")


def generate_header(repo_name, previous_tag, current_tag):
    tag_link = f"https://github.com/{repo_name}/releases/tag"
    return (
        f"[{repo_name}](https://github.com/{repo_name})"
        + " changes between "
        + f"[{previous_tag}]({tag_link}/{previous_tag})"
        + " and "
        + f"[{current_tag}]({tag_link}/{current_tag})\n\n"
    )


def main():
    bare_output = os.getenv('INPUT_BARE', False)

    current_tag = os.environ["INPUT_CURRENTTAG"]
    previous_tag = os.environ["INPUT_PREVIOUSTAG"]

    github = Github(os.environ["INPUT_GITHUB_TOKEN"])

    repo_name = os.environ["GITHUB_REPOSITORY"]
    repo = github.get_repo(repo_name)

    compare_data = repo.compare(previous_tag, current_tag)
    messages_data = [
        format_messages(o.commit.message, repo_name)
        for o in compare_data.commits
        if len(o.commit.parents) < 2
    ]

    header = generate_header(repo_name, previous_tag, current_tag)

    # %0A is a replacement of \n in github actions output,
    # so that multiline output is parsed properly
    # This is why we invoke prepare_output(): replace all \n with %0A
    messages = header + "\n".join(map(str, messages_data))

    if bare_output:
        print(messages)
    else:
        print(f"::set-output name=changelog::{prepare_output(messages)}")


if __name__ == "__main__":
    main()
