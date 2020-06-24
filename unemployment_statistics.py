import requests
import json
from configparser import ConfigParser
import time
import datetime

import praw
from bs4 import BeautifulSoup

def find_current_month(soup):
    """Pull the list of months from the current BLS EAG page and adjust them
        for the months that are abbreviated."""

    months_soup = soup.findAll('th', 'stubhead')
    months = []
    for month in months_soup[2:]:
        if month.text[:month.text.index(" ")] == "Jan":
            months.append("January")
        elif month.text[:month.text.index(" ")] == "Feb":
            months.append("February")
        elif month.text[:month.text.index(" ")] == "Mar":
            months.append("March")
        elif month.text[:month.text.index(" ")] == "Apr":
            months.append("April")
        elif month.text[:month.text.index(" ")] == "Aug":
            months.append("August")
        elif month.text[:month.text.index(" ")] == "Sept":
            months.append("September")
        elif month.text[:month.text.index(" ")] == "Oct":
            months.append("October")
        elif month.text[:month.text.index(" ")] == "Nov":
            months.append("November")
        elif month.text[:month.text.index(" ")] == "Dec":
            months.append("December")
        else:
            months.append(month.text[:month.text.index(" ")])

    current_month = months[-1]
    prev_month = months[-2]

    return current_month, prev_month

def gen_datavalue_list(soup):
    """Create a list of all the datavalues on the BLS EAG webpage."""

    datavalue_list_soup = soup.findAll('span', 'datavalue')
    datavalue_list = []
    for datavalue in datavalue_list_soup:
        datavalue_list.append(datavalue.text)

    return datavalue_list

def gen_industry_list_identifier(soup):
    """Find the identifier for the list of industries on the page."""

    footnote_list_soup = soup.findAll('tr', 'footnotes')

    location = str(footnote_list_soup).index("Number of jobs") - 8

    return str(footnote_list_soup)[location : location + 3]

def gen_industry_list(soup):
    """Create a list of the industries displayed on the BLS EAG page."""

    identifier = gen_industry_list_identifier(soup)

    industry_list_soup = soup.findAll('p', 'sub0')[2:]

    industry_list = []

    for industry in industry_list_soup:
        if identifier in industry.text:
            industry_list.append(industry.text[:industry.text.index("(")])

    return industry_list

def shorten_dv_list(datavalue_list):
    """Remove any unnecessary characters from datavalues."""

    shortened_dv_list = []

    for datavalue in datavalue_list:
        num = ""
        for character in datavalue:
            if character == ".":
                num = num + character
            if character.isdigit():
                num = num + character

        shortened_dv_list.append(round(float(num), 1))

    return shortened_dv_list

def gen_employment_changes(industry_list, shortened_dv_list):
    """Create dictionaries pairing each industry with its change in employment
    for the current and previous month."""

    employment_change = {}
    prev_month_employment_change = {}

    for industry in industry_list:
        if industry_list.index(industry) == 0:
            change = shortened_dv_list[23 + (6 * (industry_list.index(industry) + 1))] - shortened_dv_list[23 + (5 * (industry_list.index(industry) + 1))]
        else:
            change = shortened_dv_list[(23 + 6) + (12 * (industry_list.index(industry)))] - shortened_dv_list[(23 + 5) + (12 * (industry_list.index(industry)))]

        employment_change[industry] = change

    for industry in industry_list:
        if industry_list.index(industry) == 0:
            change = shortened_dv_list[23 + (5 * (industry_list.index(industry) + 1))] - shortened_dv_list[23 + (4 * (industry_list.index(industry) + 1))]
        else:
            change = shortened_dv_list[(23 + 5) + (12 * (industry_list.index(industry)))] - shortened_dv_list[(23 + 4) + (12 * (industry_list.index(industry)))]
        prev_month_employment_change[industry] = change

    return employment_change, prev_month_employment_change

def gen_significant_changes(employment_change, prev_month_employment_change, shortened_dv_list):
    """Create dictionaries for industries with employment changes representing
    a change greater than 0.5% of the total previous workforce."""

    previous_topline_employment_number = shortened_dv_list[10]
    prev_month_previous_topline_employment_number = shortened_dv_list[9]

    significant_changes = {}
    for change in employment_change:
        if abs(employment_change[change]) > previous_topline_employment_number * 0.005:
            significant_changes[change] = employment_change[change]

    prev_month_significant_changes = {}
    for change in prev_month_employment_change:
        if abs(prev_month_employment_change[change]) > prev_month_previous_topline_employment_number * 0.005:
            prev_month_significant_changes[change] = prev_month_employment_change[change]

    return significant_changes, prev_month_significant_changes

def create_title(soup, city, city_details):
    """Create the title for the post."""

    try:
        updated = soup.find('span', attrs={'class': 'update'}).text
        updated = updated[updated.index("on:") + 3:].strip()
        title = "Updated " + city_details['city_name'] + " Unemployment Figures | released " + updated
    except AttributeError:
        title = "Updated " + city_details['city_name'] + " Unemployment Figures | released " + datetime.date.today().strftime("%B %d, %Y")

    return title

def gen_topline_employment_change(shortened_dv_list):
    """Create variables for the topline employment change for the current and
    previous months."""

    topline_employment_change = round((shortened_dv_list[11] - shortened_dv_list[10]) * 1000)
    prev_topline_employment_change = round((shortened_dv_list[10] - shortened_dv_list[9]) * 1000)

    return topline_employment_change, prev_topline_employment_change

def gen_labor_force_change(shortened_dv_list):
    """Create variables for the change in labor force for the current and
    previous months."""

    labor_force_change = round((shortened_dv_list[5] - shortened_dv_list[4]) * 1000)
    prev_labor_force_change = round((shortened_dv_list[4] - shortened_dv_list[3]) * 1000)

    return labor_force_change, prev_labor_force_change

def gen_unemployment_rate_change(shortened_dv_list):
    """Create variables for the change in the unemployment rate for the current
    and previous months."""

    unemployment_rate_change = round(shortened_dv_list[23] - shortened_dv_list[22], 1)
    prev_unemployment_rate_change = round(shortened_dv_list[22] - shortened_dv_list[21], 1)

    return unemployment_rate_change, prev_unemployment_rate_change

def gen_city_details(city):
    """Retrieve previously saved city details."""

    with open("/path/to/" + city + ".json", "r") as f:
        city_details = json.load(f)

    return city_details

def update_city_details(city_details, city, current_month):
    """Save updated city details after they have been posted."""

    city_details['last_month_updated'] = current_month

    with open("/path/to/" + city + ".json", "w") as f:
        json.dump(city_details, f)

def topline_body(post, unemployment_rate_change, topline_employment_change,
                labor_force_change, unemployment_rate, month):
    """Builds the language for the first two sentences of the paragraph,
    identifying the topline change in unemployment and explaing what caused it."""

    if unemployment_rate_change > 0:
        post = f"{post} increased to {unemployment_rate}% in {month}."
        if topline_employment_change > 0:
            post = (f"{post} {topline_employment_change:,} positions "
            f"were added, but {labor_force_change:,} workers entering "
            f"the labor force caused the unemployment rate to increase.")
        elif topline_employment_change == 0:
            post = (f"{post} Employment was unchanged, but "
            f"{abs(labor_force_change):,} workers entering the labor "
            f"force caused the unemployment rate to increase.")
        elif topline_employment_change < 0:
            if labor_force_change > 0:
                post = (f"{post} {abs(topline_employment_change):,} "
                f"positions were lost, and {labor_force_change} "
                f"workers entered the labor force causing the unemployment "
                f"rate increase.")
            elif labor_force_change < 0:
                post = (f"{post} {abs(topline_employment_change):,} "
                f"positions were lost, and "
                f"{abs(labor_force_change):,} workers left the labor "
                f"force causing the unemployment rate increase.")
            elif labor_force_change == 0:
                post = (f"{post} {abs(topline_employment_change):,} "
                f"positions were lost, and the labor force was unchanged "
                f"so the unemployment rate increased.")
    elif unemployment_rate_change < 0:
        post = f"{post} fell to {unemployment_rate}% in {month}."
        if topline_employment_change < 0:
            post = (f"{post} {abs(topline_employment_change):,} "
            f"positions were lost, but {abs(labor_force_change):,} "
            f"workers exiting the labor force caused the unemployment rate "
            f"to decrease.")
        elif topline_employment_change == 0:
            post = (f"{post} Employment was unchanged, but "
            f"{labor_force_change:,} workers exiting the labor force "
            f"caused the unemployment rate to decrease.")
        elif topline_employment_change > 0:
            if labor_force_change > 0:
                post = (f"{post} {topline_employment_change:,} "
                f"positions were added, with only "
                f"{labor_force_change:,} workers entering the labor "
                f"force causing the unemployment rate decrease.")
            elif labor_force_change < 0:
                post = (f"{post} {topline_employment_change:,} "
                f"positions were added, and "
                f"{abs(labor_force_change):,} workers left the labor "
                f"force causing the unemployment rate decrease.")
            elif labor_force_change == 0:
                post = (f"{post} {topline_employment_change:,} "
                f"positions were added, and the labor force was unchanged "
                f"so the unemployment rate fell.")
    elif unemployment_rate_change == 0:
        post = (f"{post} remained flat at {unemployment_rate}% in "
        f"{month}.")
        if topline_employment_change < 0:
            post = (f"{post} {abs(topline_employment_change):,} "
            f"positions were lost, but {abs(labor_force_change):,} "
            f"workers exiting the labor force balanced out the "
            f"unemployment rate.")
        elif topline_employment_change == 0:
            post = f"{post} Employment was unchanged, and"
            if labor_force_change > 0:
                post = (f"{post} {labor_force_change:,} workers "
                f"entering the labor force was not enough to change the "
                f"unemployment rate.")
            if labor_force_change < 0:
                post = (f"{post} {abs(labor_force_change):,} workers "
                f"leaving the labor force was not enough to change the "
                f"unemployment rate. ")
            if labor_force_change == 0:
                post = f"{post} the labor force figure was also unchanged."
        elif topline_employment_change > 0:
            post = (f"{post} {topline_employment_change:,} positions "
            f"were added, but {labor_force_change:,} workers "
            f"entering the labor force balanced out the unemployment rate.")

    return post

def sig_changes_section(post, significant_changes):
    """Evaluates changes in each industry for the month and returns language
    identifying any industry that changed by more than 0.5% of the total
    previous month's labor force figure."""

    sig_industry_list = []
    sig_changes_list = []
    for industry in significant_changes:
        sig_industry_list.append(industry)
    for change in significant_changes:
        sig_changes_list.append(round(significant_changes[change] * 1000))
    if len(significant_changes) == 0:
        post = (f"{post} No individual sector saw significant "
        f"employment changes.")
    elif len(significant_changes) == 1:
        post = (f"{post} The only individual sector with significant "
        f"employment changes was {sig_industry_list[0]}")
        if sig_changes_list[0] > 0:
            post = (f"{post} which added {sig_changes_list[0]:,} "
            f"positions.")
        elif sig_changes_list[0] < 0:
            post = (f"{post} which lost "
            f"{abs(sig_changes_list[0]):,} positions.")
    else:
        positive_changes = []
        positive_changes_industries = []
        negative_changes = []
        negative_changes_industries = []
        for industry in sig_industry_list:
            if sig_changes_list[sig_industry_list.index(industry)] > 0:
                positive_changes.append(round(sig_changes_list[sig_industry_list.index(industry)]))
                positive_changes_industries.append(sig_industry_list[sig_industry_list.index(industry)])
            elif sig_changes_list[sig_industry_list.index(industry)] < 0:
                negative_changes.append(round(abs(sig_changes_list[sig_industry_list.index(industry)])))
                negative_changes_industries.append(sig_industry_list[sig_industry_list.index(industry)])

        if len(positive_changes_industries) == 1:
            post = (f"{post} The only individual sector with a "
            f"significant increase in employment was "
            f"{positive_changes_industries[0]} adding "
            f"{positive_changes[0]:,} positions.")
        elif len(positive_changes_industries) > 1:
            post = (f"{post} Labor categories with significant "
            f"additions include")
            for industry in positive_changes_industries:
                if industry == positive_changes_industries[-1] and len(positive_changes_industries) == 2:
                    post = (f"{post[:len(post) - 1]} and {industry} "
                    f"adding {positive_changes[-1]:,} positions.")
                elif industry == positive_changes_industries[-1]:
                    post = (f"{post} and {industry} adding "
                    f"{positive_changes[-1]:,} positions.")
                else:
                    post = (f"{post} {industry} adding "
                    f"{positive_changes[positive_changes_industries.index(industry)]:,} "
                    f"positions,")

        if len(negative_changes_industries) == 1:
            post = (f"{post} The only individual sector with a significant losses "
            f"in employment was {negative_changes_industries[0]} falling by "
            f"{negative_changes[0]:,} positions.")
        elif len(negative_changes_industries) > 1:
            post = f"{post} Labor categories with significant losses include"
            for industry in negative_changes_industries:
                if industry == negative_changes_industries[-1] and len(negative_changes_industries) == 2:
                    post = (f"{post[:len(post) - 1]} and {industry} falling by "
                    f"{negative_changes[-1]:,} positions.")
                elif industry == negative_changes_industries[-1]:
                    post = (f"{post} and {industry} falling by "
                    f"{negative_changes[-1]:,} positions.")
                else:
                    post = (f"{post} {industry} falling by "
                    f"{negative_changes[negative_changes_industries.index(industry)]:,} "
                    f"positions,")
    return post

def changes_body(post, significant_changes):
    """Builds the Nonfarm Payrolls sections of the post."""

    if "Total Nonfarm" in significant_changes:
        nonfarm_change = round(significant_changes.pop("Total Nonfarm") * 1000)
        if nonfarm_change > 0:
            post = (f"{post} Nonfarm payrolls increased by "
            f"{nonfarm_change:,}.")
            post = sig_changes_section(post, significant_changes)
        else:
            post = (f"{post} Nonfarm payrolls fell by "
            f"{abs(nonfarm_change):,}.")
            post = sig_changes_section(post, significant_changes)
    else:
        post = (f"{post} The overall Nonfarm Payrolls figure did not change "
        f"significantly.")
        post = sig_changes_section(post, significant_changes)

    return post

def post_constructor(city, city_details, soup, current_month, prev_month):
    """Create the post body based on updated unemployment figures found on the
    BLS EAG site."""

    last_month_updated = city_details["last_month_updated"]
    datavalue_list = gen_datavalue_list(soup)

    if last_month_updated != current_month and "(p)" in datavalue_list[23].lower():
        industry_list = gen_industry_list(soup)
        shortened_dv_list = shorten_dv_list(datavalue_list)
        employment_change, prev_month_employment_change = gen_employment_changes(industry_list, shortened_dv_list)
        significant_changes, prev_month_significant_changes = gen_significant_changes(employment_change, prev_month_employment_change, shortened_dv_list)
        topline_employment_change, prev_topline_employment_change = gen_topline_employment_change(shortened_dv_list)
        labor_force_change, prev_labor_force_change = gen_labor_force_change(shortened_dv_list)
        unemployment_rate_change, prev_unemployment_rate_change = gen_unemployment_rate_change(shortened_dv_list)
        unemployment_rate = shortened_dv_list[23]
        prev_unemployment_rate = shortened_dv_list[22]

        post = (f"[Official unemployment figures for the "
        f"{city_details['city_name']} economy]({city_details['msa_site']}) "
        f"were updated today. Numbers for {prev_month} have been finalized "
        f"and preliminary figures for {current_month} have now been made "
        f"available.\n\n\n**{prev_month}**\n\nThe unemployment rate")

        post = topline_body(post, prev_unemployment_rate_change,
        prev_topline_employment_change, prev_labor_force_change,
        prev_unemployment_rate, prev_month)

        post = changes_body(post, prev_month_significant_changes)

        post = (f"{post}\n\n\n**{current_month}** (preliminary)\n\nThe "
        f"unemployment rate")

        post = topline_body(post, unemployment_rate_change,
        topline_employment_change, labor_force_change, unemployment_rate,
        current_month)

        post = changes_body(post, significant_changes)

        post = (f"{post}\n\n\n^*{city_details['reddit_account']} ^is ^a "
        f"^public ^service ^account ^committed ^to ^making "
        f"^{city_details['subreddit']} ^a ^better ^informed ^community.")

        return post

def check_messages(city_details, reddit):
    """Check Reddit for any new messages or comments and send them to
    /u/Statistics_Admin for review."""

    for message in reddit.inbox.unread():
        try:
            reddit.redditor('Statistics_Admin').message(message.author.name, message.body)
        except AttributeError:
            reddit.redditor('Statistics_Admin').message("UNKNOWN SENDER", message.body)
        message.mark_read()

def reddit_login(city_details, city):
    """Logs in to reddit with current city's account and returns a praw instance."""

    config = ConfigParser()
    config.read('/path/to/statistics.config')

    reddit = praw.Reddit(client_id=config[city_details['group']]['client_id'],
                         client_secret=config[city_details['group']]['client_secret'],
                         password=config[city]['password'],
                         user_agent=config['General']['user_agent'],
                         username=config[city]['username'])

    return reddit

def post_to_reddit(reddit, city_details, title, post):
    """Submits completed post to relevant city, community, or state subreddit."""

    reddit.subreddit(city_details['sub']).submit(title, selftext = post, send_replies = True)
    reddit.redditor('Statistics_Admin').message(f"{datetime.datetime.now()}", f"Post submitted to {city_details['subreddit']}")


def pause_for_timer(timer):
    """If posting returns a 'You are doing that too much' message, sets a timer
    to wait until the account can submit a post."""

    if "second" in str(timer):
        print("Posting rate limit exceeded, sleeping for 1 minute.")
        time.sleep(60)
    else:
        wait_time = ""
        for x in str(timer):
            if x.isdigit():
                wait_time = wait_time + x
        wait_time = int(wait_time) + 1
        print("Posting rate limit exceeded, sleeping for " + str(wait_time) + " minutes.")
        time.sleep(wait_time * 60)

def main():
    with open("/path/to/cities.json", "r") as cities_list:
        cities = json.load(cities_list)

    with open("/path/to/special_cases.json", "r") as cities_list:
        special_cases = json.load(cities_list)

    for city in cities:
        city_details = gen_city_details(city)
        unemployed = requests.get(city_details['msa_site'])
        soup = BeautifulSoup(unemployed.text, "html5lib")
        current_month, prev_month = find_current_month(soup)

        try:
            post = post_constructor(city, city_details, soup, current_month, prev_month)
            title = create_title(soup, city, city_details)
        except TypeError:
            pass

        print("Logging into " + city_details['reddit_account'] + "...")
        reddit = reddit_login(city_details, city)

        if post != None:
            if city in special_cases:
                if city_details['special_case'] == "Quarterly":
                    if      current_month == "March" \
                        or  current_month == "June" \
                        or  current_month == "September" \
                        or  current_month == "December":

                        print("Updating " + city)
                        while True:
                            try:
                                post_to_reddit(reddit, city_details, title, post)
                            except Exception as timer:
                                pause_for_timer(timer)
                            else:
                                break

                        update_city_details(city_details, city, current_month)

                    else:
                        print("No update required at this time.")

                elif city_details['special_case'] == "Manual":
                    print("Sending " + city + " post to /u/Statistics_Admin.")
                    reddit.redditor('Statistics_Admin').message(title, post)
                    update_city_details(city_details, city, current_month)

            else:
                print("Updating " + city)
                while True:
                    try:
                        post_to_reddit(reddit, city_details, title, post)
                    except praw.exceptions.APIException as e:
                        if "SUBREDDIT_NOTALLOWED" in str(e):
                            print(f"{city_details['subreddit']} "
                            f"is not allowing these posts...")
                            reddit.redditor('Statistics_Admin').message(
                            f"{city_details['subreddit']}",
                            f"{city_details['subreddit']} is not allowing "
                            f"these posts...")
                            break
                        if "timer" in str(e):
                            pause_for_timer(e)
                    else:
                        break

                update_city_details(city_details, city, current_month)
        else:
            print("No update required at this time.")

        check_messages(city_details, reddit)

if __name__ == '__main__':
    main()
