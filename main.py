import os
import re
import sys

from github import Github, UnknownObjectException
from jira import JIRA, JIRAError
from github_action_utils import set_output

JIRA_SERVER = "https://ibexa.atlassian.net"
JIRA_PREFIX = f"{JIRA_SERVER}/browse/"


def format_messages(message, repo_name, jira):
    # Extract only first line of commit message
    message = message.partition("\n")[0]

    # Add JIRA links
    message, issue_category, jira_id = add_jira_links(message, jira)

    if not jira_id:
        return ""

    # Add PR links
    # Links must be explicit links,
    # because when we will be combining changelogs in one release
    # relative links will be linking to wrong repo/will be not links
    message = add_pr_links(message, repo_name)

    return {"text": "- " + message, "category": issue_category}


def get_components(issue):
    return [o.name for o in issue.fields.components]


def is_bug(issue):
    return issue.fields.issuetype.name == "Bug"


def add_jira_links(message, jira):
    regex = r"^((?!([A-Z0-9a-z]{1,10})-?$)[A-Z]{1}[A-Z0-9]+-\d+)"
    subst = f"[\\1]({JIRA_PREFIX}\\1)"
    result = re.sub(regex, subst, message, 0, re.MULTILINE)
    jira_ids = re.findall(regex, message)
    if jira_ids:
        try:
            jira_issue = jira.issue(id=jira_ids[0])
            if "QA" in get_components(jira_issue):
                category = "Miscellaneous"
            elif is_bug(jira_issue):
                category = "Bugs"
            else:
                category = "Improvements"
        except JIRAError as e:
            # We silently ignore errors, as there were cases when JIRA IDs had typoes
            # print(e.status_code, e.text)
            category = "Improvements"

        jira_id = jira_ids[0]
    else:
        category = None
        jira_id = None

    return result, category, jira_id


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
        + f"[{current_tag}]({tag_link}/{current_tag})\n"
    )


def main():
    bare_output = os.getenv("INPUT_BARE", False)

    current_tag = os.environ["INPUT_CURRENTTAG"]
    previous_tag = os.environ["INPUT_PREVIOUSTAG"]

    github = Github(os.environ["INPUT_GITHUB_TOKEN"])
    jira_token = os.getenv("INPUT_JIRA_TOKEN", "")
    jira = JIRA(
        JIRA_SERVER,
        options={"headers": {"Authorization": f"Bearer {jira_token}"}},
    )

    repo_name = os.environ["GITHUB_REPOSITORY"]
    if repo_name == "ezsystems/payment-core-bundle":
        repo_name = "ezsystems/JMSPaymentCoreBundle"
    elif repo_name == "ezsystems/job-queue-bundle":
        repo_name = "ezsystems/JMSJobQueueBundle"
    elif repo_name == "ezsystems/stash-bundle":
        repo_name = "ezsystems/TedivmStashBundle"
    elif repo_name == "ezsystems/apache-tika-bundle":
        repo_name = "ezsystems/ApacheTikaBundle"
    elif repo_name == "ezsystems/comment-bundle":
        repo_name = "ezsystems/CommentsBundle"
    #print(f"Processing {repo_name}")
    repo = github.get_repo(repo_name)

    try:
        compare_data = repo.compare(previous_tag, current_tag)
        messages_data = [
            format_messages(o.commit.message, repo_name, jira)
            for o in compare_data.commits
            if len(o.commit.parents) < 2
        ]

        messages = list(filter(None, messages_data))

        improvements = [
            d["text"] for d in messages if d["category"] == "Improvements"
        ]
        bugs = [
            d["text"] for d in messages if d["category"] == "Bugs"
        ]
        miscellaneous = [
            d["text"] for d in messages if d["category"] == "Miscellaneous"
        ]

        header = generate_header(repo_name, previous_tag, current_tag)

        # %0A is a replacement of \n in github actions output,
        # so that multiline output is parsed properly
        # This is why prepare_output() is used: replace all \n with %0A
        messages = header
        if improvements:
            messages += "\n\n### Improvements\n\n" + \
                        "\n".join(map(str, improvements))
        if bugs:
            messages += "\n\n### Bugs\n\n" + \
                        "\n".join(map(str, bugs))
        if miscellaneous:
            messages += "\n\n### Misc\n\n" + \
                        "\n".join(map(str, miscellaneous))

        if not (improvements or bugs or miscellaneous):
            messages += "\n\nNo significant changes."

    except UnknownObjectException as e:
        messages = ""

    if bare_output:
        print(messages)
    else:
        print(f"::set-output name=changelog::{prepare_output(messages)}")


if __name__ == "__main__":
    main()
