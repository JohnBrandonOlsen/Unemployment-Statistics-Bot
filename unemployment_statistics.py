import requests
import json
from configparser import ConfigParser
import time
import datetime

import praw

def find_current_month(json_data):
    """Pull the list of months from the BLS API."""

    current_month = json_data["Results"]["series"][0]["data"][0]["periodName"]
    prev_month = json_data["Results"]["series"][0]["data"][1]["periodName"]

    return current_month, prev_month

def gen_BLS_codes(city_details, industry_codes):
    """Create list of seriesId codes for the BLS API."""

    BLS_codes = ['LAU' + city_details["Area_Type"] + city_details["BLS_code"] + '00000003',
                 'LAU' + city_details["Area_Type"] + city_details["BLS_code"] + '00000004',
                 'LAU' + city_details["Area_Type"] + city_details["BLS_code"] + '00000005',
                 'LAU' + city_details["Area_Type"] + city_details["BLS_code"] + '00000006',
                 'SMU' + city_details["BLS_code"] + industry_codes["Total Nonfarm"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Mining, Logging and Construction"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Manufacturing"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Trade, Transportation, and Utilities"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Information"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Financial Activities"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Professional and Business Services"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Private Education and Health Services"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Leisure and Hospitality"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Other Services"],
                 'SMU' + city_details["BLS_code"] + industry_codes["Government"]]
    
    return BLS_codes

def post_constructor(industry_codes, city_details, json_data, current_month, prev_month):
    """Create the post body based on updated unemployment figures from the BLS API."""

    last_month_updated = city_details["last_month_updated"]

    if last_month_updated != current_month:

        significant_changes, prev_month_significant_changes = gen_significant_changes(json_data, industry_codes)
        
        unemployment_rate_change = float(json_data["Results"]["series"][0]["data"][0]["calculations"]['net_changes']['1'])
        prev_unemployment_rate_change = float(json_data["Results"]["series"][0]["data"][1]["calculations"]['net_changes']['1'])
        topline_employment_change = int(json_data["Results"]["series"][2]["data"][0]["calculations"]['net_changes']['1'])
        prev_topline_employment_change = int(json_data["Results"]["series"][2]["data"][1]["calculations"]['net_changes']['1'])
        labor_force_change = int(json_data["Results"]["series"][3]["data"][0]["calculations"]['net_changes']['1'])
        prev_labor_force_change = int(json_data["Results"]["series"][3]["data"][1]["calculations"]['net_changes']['1'])
        unemployment_rate = json_data["Results"]["series"][0]["data"][0]["value"]
        prev_unemployment_rate = json_data["Results"]["series"][0]["data"][1]["value"]

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

def gen_significant_changes(json_data, industry_codes):
    """Create dictionaries for industries with employment changes representing
    a change greater than 0.5% of the total previous workforce."""
    
    employment_change, prev_month_employment_change = gen_employment_changes(json_data, industry_codes)

    previous_topline_employment_number = int(json_data['Results']['series'][2]['data'][1]['value'])
    prev_month_previous_topline_employment_number = int(json_data['Results']['series'][2]['data'][2]['value'])

    significant_changes = {}
    for change in employment_change:
        if abs(employment_change[change]) > previous_topline_employment_number * 0.005:
            significant_changes[change] = employment_change[change]

    prev_month_significant_changes = {}
    for change in prev_month_employment_change:
        if abs(prev_month_employment_change[change]) > prev_month_previous_topline_employment_number * 0.005:
            prev_month_significant_changes[change] = prev_month_employment_change[change]

    return significant_changes, prev_month_significant_changes

def gen_employment_changes(json_data, industry_codes):
    """Create dictionaries pairing each industry with its change in employment
    for the current and previous month."""

    employment_change = {}
    prev_month_employment_change = {}

    for series in json_data['Results']['series']:
        if industry_codes["Total Nonfarm"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Total Nonfarm"] = float(change) * 1000
            prev_month_employment_change["Total Nonfarm"] = float(prev_change) * 1000
        if industry_codes["Mining, Logging and Construction"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Mining, Logging and Construction"] = float(change)
            prev_month_employment_change["Mining, Logging and Construction"] = float(prev_change)
        if industry_codes["Manufacturing"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Manufacturing"] = float(change)
            prev_month_employment_change["Manufacturing"] = float(prev_change)
        if industry_codes["Trade, Transportation, and Utilities"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Trade, Transportation, and Utilities"] = float(change)
            prev_month_employment_change["Trade, Transportation, and Utilities"] = float(prev_change)
        if industry_codes["Information"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Information"] = float(change)
            prev_month_employment_change["Information"] = float(prev_change)
        if industry_codes["Financial Activities"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Financial Activities"] = float(change)
            prev_month_employment_change["Financial Activities"] = float(prev_change)
        if industry_codes["Professional and Business Services"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Professional and Business Services"] = float(change)
            prev_month_employment_change["Professional and Business Services"] = float(prev_change)
        if industry_codes["Private Education and Health Services"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Private Education and Health Services"] = float(change)
            prev_month_employment_change["Private Education and Health Services"] = float(prev_change)
        if industry_codes["Leisure and Hospitality"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Leisure and Hospitality"] = float(change)
            prev_month_employment_change["Leisure and Hospitality"] = float(prev_change)
        if industry_codes["Other Services"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Other Services"] = float(change)
            prev_month_employment_change["Other Services"] = float(prev_change)
        if industry_codes["Government"] in series['seriesID'] and len(series['data']) > 1:
            change = series['data'][0]['calculations']['net_changes']['1']
            prev_change = series['data'][1]['calculations']['net_changes']['1']
            employment_change["Government"] = float(change)
            prev_month_employment_change["Government"] = float(prev_change)

    return employment_change, prev_month_employment_change

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

def changes_body(post, significant_changes):
    """Builds the Nonfarm Payrolls sections of the post."""

    if "Total Nonfarm" in significant_changes:
        nonfarm_change = round(significant_changes.pop("Total Nonfarm"))
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
            post = (f"{post} The only individual sector with a significant loss "
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

def reddit_login(city_details, city):
    """Logs in to reddit with current city's account and returns a praw instance."""

    config = ConfigParser()
    config.read('/home/closet/Python/UnemploymentStatistics/statistics.config')

    reddit = praw.Reddit(client_id=config[city_details['group']]['client_id'],
                         client_secret=config[city_details['group']]['client_secret'],
                         password=config[city]['password'],
                         user_agent=config['General']['user_agent'],
                         username=config[city]['username'])

    return reddit

def select_flair(reddit, city_details):
    """Identify flair if needed for posting"""
    flairs = reddit.subreddit(city_details['sub']).flair.link_templates

    if flairs != None:
        try:
            for flair in flairs:
                if "Discussion" in flair['text']:
                    return flair['id']
                if "Living Here" in flair['text']:
                    return flair['id']
                if "News" in flair['text']:
                    return flair['id']
        except:
            pass

def update_city_details(city_details, city, current_month):
    """Save updated city details after they have been posted."""

    city_details['last_month_updated'] = current_month

    with open("/path/to/" + city + ".json", "w") as f:
        json.dump(city_details, f)

def post_to_reddit(reddit, city_details, title, post, flair):
    """Submits completed post to relevant city, community, or state subreddit."""

    reddit.subreddit(city_details['sub']).submit(title, selftext = post, send_replies = True, flair_id = flair)
    reddit.redditor('Statistics_Admin').message(subject = f"{datetime.datetime.now()}", message = f"Post submitted to {city_details['subreddit']}")

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

def check_messages(city_details, reddit):
    """Check Reddit for any new messages or comments and send them to
    /u/Statistics_Admin for review."""

    for message in reddit.inbox.unread():
        try:
            reddit.redditor('Statistics_Admin').message(subject = message.author.name, message = message.body)
        except AttributeError:
            reddit.redditor('Statistics_Admin').message(subject = "UNKNOWN SENDER", message = message.body)
        message.mark_read()

def main():
    with open("/path/to/cities.json", "r") as cities_list:
        cities = json.load(cities_list)

    with open("/path/to/special_cases.json", "r") as cities_list:
        special_cases = json.load(cities_list)

    with open("/path/to/BLS.json", "r") as Bureau:
        BLS = json.load(Bureau)

    with open("/path/to/industry_codes.json", "r") as f:
        industry_codes = json.load(f)

    for city in cities:
        
        with open("/path/to/" + city + ".json", "r") as f:
            city_details = json.load(f)

        BLS_codes = gen_BLS_codes(city_details, industry_codes)

        headers = {'Content-type': 'application/json'}
        data = json.dumps({"seriesid": BLS_codes,                          
                                        "endyear": datetime.date.today().year, "startyear": str(int(datetime.date.today().year)-1),
                                        "registrationkey" : BLS["registrationkey"], "calculations":True})
        while True:
            try:
                p = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=data, headers=headers)
            except requests.exceptions.ConnectionError:
                time.sleep(3)
            else:
                break
        
        json_data = json.loads(p.text)
        
        current_month, prev_month = find_current_month(json_data)

        try:
            post = post_constructor(industry_codes, city_details, json_data, current_month, prev_month)
            title = "Updated " + city_details['city_name'] + " Unemployment Figures | released " + datetime.date.today().strftime("%B %d, %Y")
        except TypeError:
            pass

        print("Logging into " + city_details['reddit_account'] + "...")
        reddit = reddit_login(city_details, city)

        if post != None:
            flair = select_flair(reddit, city_details)
            if city in special_cases:
                if city_details['special_case'] == "Quarterly":
                    if      current_month == "March" \
                        or  current_month == "June" \
                        or  current_month == "September" \
                        or  current_month == "December":

                        print("Updating " + city)
                        while True:
                            try:
                                post_to_reddit(reddit, city_details, title, post, flair)
                            except Exception as timer:
                                pause_for_timer(timer)
                            else:
                                break

                        update_city_details(city_details, city, current_month)

                    else:
                        print("No update required at this time.")

                elif city_details['special_case'] == "Manual":
                    print("Sending " + city + " post to /u/Statistics_Admin.")
                    reddit.redditor('Statistics_Admin').message(subject = title, message = post)
                    update_city_details(city_details, city, current_month)

            else:
                print("Updating " + city)
                while True:
                    try:
                        post_to_reddit(reddit, city_details, title, post, flair)
                    except praw.exceptions.RedditAPIException as e:
                        if "SUBREDDIT_NOTALLOWED" in str(e):
                            print(f"{city_details['subreddit']} "
                            f"is not allowing these posts...")
                            reddit.redditor('Statistics_Admin').message(
                            subject = f"{city_details['subreddit']}",
                            message = f"{city_details['subreddit']} is not allowing "
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
