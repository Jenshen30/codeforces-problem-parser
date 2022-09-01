from bs4 import BeautifulSoup
import requests
from fake_useragent import FakeUserAgent
import os
import urllib3


def connect_to_codeforce(cookie: dict) -> None:
    FAKE_USER = FakeUserAgent(use_cache_server=True).random

    for name, value in cookie.items():
        session.cookies.set(name, value)

    session.verify = False
    session.headers.update({"user-agent": FAKE_USER})


def get_soup(session, URL):
    response = session.get(url=URL)

    if response.status_code != requests.codes.ok:
        raise ConnectionError("I cannot connect to {0)! Code of error is {1}.".format(URL, response.status_code))

    return BeautifulSoup(response.text, "html5lib")


def get_all_contests(session, groupURL) -> list:
    soup = get_soup(session, groupURL)

    s = soup.find("div", "datatable").findAll("td")

    contests = []
    for contest in s:
        if (contest.a is not None) and (contest.a.string is not None) and\
                (contest.a.string.count("Войти") + contest.a.string.count("Enter") > 0):
            name, link = next(contest.a.parent.children).text, contest.a["href"]
            contests.append((name, link, ))
    soup.clear()
    return contests


def contest_name(session, CONTEST_URL): # fixme
    soup = get_soup(session, CONTEST_URL)
    return soup.find("title").text


def get_solution_link(session, CONTEST_URL):
    soup = get_soup(session, CONTEST_URL)

    for solution in soup.find(class_="rtable smaller").findAll("tr"):
        if solution.find(class_="verdict-accepted") is not None:
            return solution.find("a")["href"]


def get_solution_text(session, SOLUTION_URL):
    soup = get_soup(session, SOLUTION_URL)

    #solution = StringIO(initial_value='')
    return soup.find(class_="linenums").text


def get_lang(session, SOLUTION_URL):
    soup = get_soup(session, SOLUTION_URL)
    return soup.find(id="program-source-text")["class"][1].replace("lang-", ".")


def write_into_file(name, text):
    f = open(name, "w")
    f.write(text)
    f.close()


def get_all_contest_task(session, CONTEST_URL) -> list:
    soup = get_soup(session, CONTEST_URL)
    return list(t.a["href"] for t in soup.findAll(class_="accepted-problem"))


def writer(word_search: str, file, parsed, pref, suff, sec=1):
    tmp = parsed.find(class_=word_search)
    file.write(pref + tmp.contents[0].text + "{}".format(": " + tmp.contents[1] if sec == 1 else "") + suff)


def write_all_into(session, CODEFORCES_URL, problems: list, GROUP_NAME: str, ORIG_GROUP_NAME: str):

    # create dir
    if not os.path.isdir(GROUP_NAME):
        os.mkdir(GROUP_NAME)

    # create README.md
    readme = open(os.getcwd() + os.sep + GROUP_NAME + os.sep + "README.md", "w", encoding='utf-8')

    # write Group name
    readme.write("# " + ORIG_GROUP_NAME + "\n")

    for problem in problems:

        # get all info
        soup = get_soup(session, CODEFORCES_URL + problem)
        parsed = soup.find(class_="problem-statement")

        # get/write problem name
        orig_name = parsed.find(class_="title").string
        name = orig_name.replace(" ", "_")
        readme.write("## " + orig_name + '\n')

        # get/write problem limits
        writer("time-limit", readme, parsed, "##### ", "\n")
        writer("memory-limit", readme, parsed, "##### ", "\n")

        # get/write problem IO

        writer("input-file", readme, parsed, " ", "\n\n")
        writer("output-file", readme, parsed, " ", "\n")

        paragrafs = parsed.findAll("p")

        # get/write problem text
        readme.write(">" + paragrafs[0].text + "\n")

        # get/write IO specification
        writer("input-specification", readme, parsed, "\n**", "**\n\n", 0)
        readme.write(paragrafs[1].text + "\n\n")

        writer("output-specification", readme, parsed, "**", "**\n\n", 0)

        readme.write(paragrafs[2].text + "\n\n")

        # get/write examples
        ins = parsed.findAll(class_="input")
        outs = parsed.findAll(class_="output")

        readme.write(parsed.find(class_="sample-tests").next.text + ": \n\n")

        for inp, out in zip(ins, outs):
            readme.write("\>> In:\n```\n" +
                         "".join(list(map(lambda a: a if str(a) != '<br/>' else "\n", inp.pre.children))) +
                         "\n```\n")
            readme.write("\>> Out:\n```\n" +
                         "".join(list(map(lambda a: a if str(a) != '<br/>' else "\n", out.pre.children))) +
                         "\n```\n")

        # solution part
        link = get_solution_link(session, CODEFORCES_URL + problem)
        lang = get_lang(session, CODEFORCES_URL + link)

        full_way = os.getcwd() + os.sep + GROUP_NAME + \
                   os.sep + name.replace("?", "") + lang

        write_into_file(full_way, get_solution_text(session, CODEFORCES_URL + link))

        readme.write("\n[Solution]({})\n\n".format(full_way))

        soup.clear()

    readme.close()


if __name__ == '__main__':

    cookie = json.loads(input("Give me your codeforces cookie in JSON format: "))

    # GROUP OR CONTEST
    # "https://codeforces.com/group/bhlVqqYrFf/contests"
    # "https://codeforces.com/group/bhlVqqYrFf/contest/382401"
    URL = input("URL of contest or group with contests: ").strip()
    CODEFORCES_URL = "https://codeforces.com"

    # init
    session = requests.Session()
    urllib3.disable_warnings()
    connect_to_codeforce(cookie)

    if URL.split("/")[-1] == "contests":
        # keys in contests consists "\n\t " use .strip()
        contests = get_all_contests(session, URL)
        print("Choose ONLY one contest:" + os.linesep)
        i = 1
        for key, v in contests:
            print(str(i) + ") " + key.strip())
            i += 1

        chosen = int(input(os.linesep + "-> "))
    else:
        chosen = 1
        contests = [(contest_name(session, URL), URL.replace("https://codeforces.com", "", 1),)]

    if 0 < chosen <= len(contests):
        acceptedproblem_links = get_all_contest_task(session, CODEFORCES_URL + contests[chosen - 1][1])

        write_all_into(session, CODEFORCES_URL, acceptedproblem_links,
                       (contests[chosen - 1][0].strip()).replace(" ", "_"), contests[chosen - 1][0].strip())
    else:
        print("Bad joke ;-(")
    session.close()