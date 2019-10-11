import requests
import json
from configparser import ConfigParser
import time
import datetime

import praw
from bs4 import BeautifulSoup

def find_current_month(soup):
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
    datavalue_list_soup = soup.findAll('span', 'datavalue')
    datavalue_list = []
    for datavalue in datavalue_list_soup:
        datavalue_list.append(datavalue.text)

    return datavalue_list

def gen_industry_list(soup):
    industry_list_soup = soup.findAll('p', 'sub0')[2:]

    industry_list = []

    for industry in industry_list_soup:
        if "(3)" in industry.text:
            industry_list.append(industry.text[:industry.text.index("(")])

    return industry_list

def shorten_dv_list(datavalue_list):
    shortened_dv_list = []

    for datavalue in datavalue_list:
        if "(p)" in datavalue:
            datavalue = datavalue[datavalue.index(")") + 1:]
        if "(P)" in datavalue:
            datavalue = datavalue[datavalue.index(")") + 1:]
        if "(4)" in datavalue:
            datavalue = datavalue[datavalue.index(")") + 1:]
        if "," in datavalue:
            datavalue = datavalue[:datavalue.index(",") - 1] + datavalue[datavalue.index(",") + 1:]
            if "," in datavalue:
                datavalue = datavalue[:datavalue.index(",") - 1] + datavalue[datavalue.index(",") + 1:]

        shortened_dv_list.append(round(float(datavalue), 1))

    return shortened_dv_list

def gen_employment_changes(industry_list, shortened_dv_list):
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
    try:
        updated = soup.find('span', attrs={'class': 'update'}).text
        updated = updated[updated.index("on:") + 3:].strip()
        title = "Updated " + city_details['city_name'] + " Unemployment Figures | released " + updated
    except AttributeError:
        title = "Updated " + city_details['city_name'] + " Unemployment Figures | released " + datetime.date.today().strftime("%B %d, %Y")

    return title

def gen_topline_employment_change(shortened_dv_list):
    topline_employment_change = round((shortened_dv_list[11] - shortened_dv_list[10]) * 1000)
    prev_topline_employment_change = round((shortened_dv_list[10] - shortened_dv_list[9]) * 1000)

    return topline_employment_change, prev_topline_employment_change

def gen_labor_force_change(shortened_dv_list):
    labor_force_change = round((shortened_dv_list[5] - shortened_dv_list[4]) * 1000)
    prev_labor_force_change = round((shortened_dv_list[4] - shortened_dv_list[3]) * 1000)

    return labor_force_change, prev_labor_force_change

def gen_unemployment_rate_change(shortened_dv_list):
    unemployment_rate_change = round(shortened_dv_list[23] - shortened_dv_list[22], 1)
    prev_unemployment_rate_change = round(shortened_dv_list[22] - shortened_dv_list[21], 1)

    return unemployment_rate_change, prev_unemployment_rate_change

def gen_city_details(city):
    with open("/path/to/" + city + ".json", "r") as f:
        city_details = json.load(f)

    return city_details

def update_city_details(city_details, city, current_month):
    city_details['last_month_updated'] = current_month

    with open("/path/to/" + city + ".json", "w") as f:
        json.dump(city_details, f)

def post_constructor(city, city_details, soup, current_month, prev_month):
    last_month_updated = city_details["last_month_updated"]
    datavalue_list = gen_datavalue_list(soup)

    if last_month_updated != current_month and "(p)" in datavalue_list[23]:
        industry_list = gen_industry_list(soup)
        shortened_dv_list = shorten_dv_list(datavalue_list)
        employment_change, prev_month_employment_change = gen_employment_changes(industry_list, shortened_dv_list)
        significant_changes, prev_month_significant_changes = gen_significant_changes(employment_change, prev_month_employment_change, shortened_dv_list)
        topline_employment_change, prev_topline_employment_change = gen_topline_employment_change(shortened_dv_list)
        labor_force_change, prev_labor_force_change = gen_labor_force_change(shortened_dv_list)
        unemployment_rate_change, prev_unemployment_rate_change = gen_unemployment_rate_change(shortened_dv_list)
        unemployment_rate = shortened_dv_list[23]
        prev_unemployment_rate = shortened_dv_list[22]

        post = "[Official unemployment figures for the " + city_details['city_name'] + \
        " economy](" + city_details['msa_site'] + \
        ") were updated today. Numbers for " + prev_month + \
        " have been finalized and preliminary figures for " + \
        current_month + " have now been made available.\n\n\n" + "**" + \
        prev_month + "**\n\nThe unemployment rate "
        if prev_unemployment_rate_change > 0:
            post = post + "increased to " + str(prev_unemployment_rate) + "% in " + \
            prev_month + ". "
            if prev_topline_employment_change > 0:
                post = post + "{:,}".format(prev_topline_employment_change) + \
                " positions were added, but " + "{:,}".format(abs(prev_labor_force_change)) + \
                " workers entering the labor force caused the unemployment rate to increase. "
            elif prev_topline_employment_change == 0:
                post = post + "Employment was unchanged, but " + \
                "{:,}".format(abs(prev_labor_force_change)) + \
                " workers entering the labor force caused the unemployment rate to increase. "
            elif prev_topline_employment_change < 0:
                if prev_labor_force_change > 0:
                    post = post + "{:,}".format(abs(prev_topline_employment_change)) + \
                    " positions were lost, and " + "{:,}".format(prev_labor_force_change) + \
                    " workers entered the labor force causing the unemployment rate increase. "
                elif prev_labor_force_change < 0:
                    post = post + "{:,}".format(abs(prev_topline_employment_change)) + \
                    " positions were lost, and " + "{:,}".format(abs(prev_labor_force_change)) + \
                    " workers left the labor force causing the unemployment rate increase. "
                elif prev_labor_force_change == 0:
                    post = post + "{:,}".format(abs(prev_topline_employment_change)) + \
                    " positions were lost, and " + \
                    " the labor force was unchanged so the unemployment rate rose. "
        elif prev_unemployment_rate_change < 0:
            post = post + "fell to " + str(prev_unemployment_rate) + "% in " + \
            prev_month + ". "
            if prev_topline_employment_change < 0:
                post = post + "{:,}".format(abs(prev_topline_employment_change)) + \
                " positions were lost, but " + "{:,}".format(abs(prev_labor_force_change)) + \
                " workers exiting the labor force caused the unemployment rate to decrease. "
            elif prev_topline_employment_change == 0:
                post = post + "Employment was unchanged, but " + \
                "{:,}".format(abs(prev_labor_force_change)) + \
                " workers exiting the labor force caused the unemployment rate to decrease. "
            elif prev_topline_employment_change > 0:
                if prev_labor_force_change > 0:
                    post = post + "{:,}".format(prev_topline_employment_change) + \
                    " positions were added, with only " + "{:,}".format(prev_labor_force_change) + \
                    " workers entering the labor force causing the unemployment rate decrease. "
                elif prev_labor_force_change < 0:
                    post = post + "{:,}".format(prev_topline_employment_change) + \
                    " positions were added, and " + "{:,}".format(abs(prev_labor_force_change)) + \
                    " workers left the labor force causing the unemployment rate decrease. "
                elif prev_labor_force_change == 0:
                    post = post + "{:,}".format(prev_topline_employment_change) + \
                    " positions were added, and " + \
                    " the labor force was unchanged so the unemployment rate fell. "
        elif prev_unemployment_rate_change == 0:
            post = post + "remained flat at " + str(prev_unemployment_rate) + "% in " + \
            prev_month + ". "
            if prev_topline_employment_change < 0:
                post = post + "{:,}".format(abs(prev_topline_employment_change)) + \
                " positions were lost, but " + "{:,}".format(abs(prev_labor_force_change)) + \
                " workers exiting the labor force balanced out the unemployment rate. "
            elif prev_topline_employment_change == 0:
                post = post + "Employment was unchanged, and "
                if prev_labor_force_change > 0:
                    post = post + "{:,}".format(abs(prev_labor_force_change)) + \
                    " workers entering the labor force was not enough to change the unemployment rate. "
                if prev_labor_force_change < 0:
                    post = post + "{:,}".format(abs(prev_labor_force_change)) + \
                    " workers leaving the labor force was not enough to change the unemployment rate. "
                if prev_labor_force_change == 0:
                    post = post + "{:,}".format(abs(prev_labor_force_change)) + \
                    " the labor force figure was also unchanged. "
            elif prev_topline_employment_change > 0:
                post = post + "{:,}".format(abs(prev_topline_employment_change)) + \
                " positions were added, but " + "{:,}".format(abs(prev_labor_force_change)) + \
                " workers entering the labor force balanced out the unemployment rate. "
        if "Total Nonfarm" in prev_month_significant_changes:
            prev_nonfarm_change = round(prev_month_significant_changes.pop("Total Nonfarm") * 1000)
            if prev_nonfarm_change > 0:
                post = post + "Nonfarm payrolls increased by " + "{:,}".format(prev_nonfarm_change) + ". "
            else:
                post = post + "Nonfarm payrolls fell by " + "{:,}".format(abs(prev_nonfarm_change)) + ". "
            prev_sig_industry_list = []
            prev_sig_changes_list = []
            for industry in prev_month_significant_changes:
                prev_sig_industry_list.append(industry)
            for change in prev_month_significant_changes:
                prev_sig_changes_list.append(round(prev_month_significant_changes[change] * 1000))
            if len(prev_month_significant_changes) == 0:
                post = post + "No individual sector saw significant employment changes. "
            elif len(prev_month_significant_changes) == 1:
                post = post + "The only individual sector with significant " + \
                "employment changes was " + prev_sig_industry_list[0] + " "
                if prev_sig_changes_list[0] > 0:
                    post = post + "which added " + "{:,}".format(prev_sig_changes_list[0]) + \
                    " positions. "
                elif prev_sig_changes_list[0] < 0:
                    post = post + "which lost " + "{:,}".format(abs(prev_sig_changes_list[0])) + \
                    " positions. "
            else:
                prev_positive_changes = []
                prev_positive_changes_industries = []
                prev_negative_changes = []
                prev_negative_changes_industries = []
                for industry in prev_sig_industry_list:
                    if prev_sig_changes_list[prev_sig_industry_list.index(industry)] > 0:
                        prev_positive_changes.append(round(prev_sig_changes_list[prev_sig_industry_list.index(industry)]))
                        prev_positive_changes_industries.append(prev_sig_industry_list[prev_sig_industry_list.index(industry)])
                    elif prev_sig_changes_list[prev_sig_industry_list.index(industry)] < 0:
                        prev_negative_changes.append(round(abs(prev_sig_changes_list[prev_sig_industry_list.index(industry)])))
                        prev_negative_changes_industries.append(prev_sig_industry_list[prev_sig_industry_list.index(industry)])

                if len(prev_positive_changes_industries) == 1:
                    post = post +  "The only individual sector with a significant " + \
                    "increase in employment was " + prev_positive_changes_industries[0] + \
                    " adding " + "{:,}".format(prev_positive_changes[0]) + " positions. "
                elif len(prev_positive_changes_industries) > 1:
                    post = post[:len(post)] + "Labor categories with significant additions include "
                    for industry in prev_positive_changes_industries:
                        if industry == prev_positive_changes_industries[-1] and len(prev_positive_changes_industries) == 2:
                            post = post[:len(post) - 2] + " and " + industry + " adding " + \
                            "{:,}".format(prev_positive_changes[-1]) + " positions. "
                        elif industry == prev_positive_changes_industries[-1]:
                            post = post + "and " + industry + " adding " + "{:,}".format(prev_positive_changes[-1]) + \
                            " positions. "
                        else:
                            post = post + industry + " adding " + \
                            "{:,}".format(prev_positive_changes[prev_positive_changes_industries.index(industry)]) + \
                            " positions, "

                if len(prev_negative_changes_industries) == 1:
                    post = post +  "The only individual sector with a significant " + \
                    "losses in employment was " + prev_negative_changes_industries[0] + \
                    " falling by " + "{:,}".format(prev_negative_changes[0]) + " positions. "
                elif len(prev_negative_changes_industries) > 1:
                    post = post[:len(post)] + "Labor categories with significant losses include "
                    for industry in prev_negative_changes_industries:
                        if industry == prev_negative_changes_industries[-1] and len(prev_negative_changes_industries) == 2:
                            post = post[:len(post) - 2] + " and " + industry + " falling by " + \
                            "{:,}".format(prev_negative_changes[-1]) + " positions. "
                        elif industry == prev_negative_changes_industries[-1]:
                            post = post + "and " + industry + " falling by " + "{:,}".format(prev_negative_changes[-1]) + \
                            " positions. "
                        else:
                            post = post + industry + " falling by " + \
                            "{:,}".format(prev_negative_changes[prev_negative_changes_industries.index(industry)]) + \
                            " positions, "
        else:
            post = post + "The overall Nonfarm Payrolls figure did not change significantly. "
            prev_sig_industry_list = []
            prev_sig_changes_list = []
            for industry in prev_month_significant_changes:
                prev_sig_industry_list.append(industry)
            for change in prev_month_significant_changes:
                prev_sig_changes_list.append(round(prev_month_significant_changes[change] * 1000))
            if len(prev_month_significant_changes) == 0:
                post = post[:len(post) - 2] + " and no individual sector saw significant employment changes. "
            elif len(prev_month_significant_changes) == 1:
                post = post + "The only individual sector with significant " + \
                "employment changes was " + prev_sig_industry_list[0] + " "
                if prev_sig_changes_list[0] > 0:
                    post = post + "which added " + "{:,}".format(prev_sig_changes_list[0]) + \
                    " positions. "
                elif prev_sig_changes_list[0] < 0:
                    post = post + "which lost " + "{:,}".format(abs(prev_sig_changes_list[0])) + \
                    " positions. "
            else:
                prev_positive_changes = []
                prev_positive_changes_industries = []
                prev_negative_changes = []
                prev_negative_changes_industries = []
                for industry in prev_sig_industry_list:
                    if prev_sig_changes_list[prev_sig_industry_list.index(industry)] > 0:
                        prev_positive_changes.append(round(prev_sig_changes_list[prev_sig_industry_list.index(industry)]))
                        prev_positive_changes_industries.append(prev_sig_industry_list[prev_sig_industry_list.index(industry)])
                    elif prev_sig_changes_list[prev_sig_industry_list.index(industry)] < 0:
                        prev_negative_changes.append(round(abs(prev_sig_changes_list[prev_sig_industry_list.index(industry)])))
                        prev_negative_changes_industries.append(prev_sig_industry_list[prev_sig_industry_list.index(industry)])

                if len(prev_positive_changes_industries) == 1:
                    post = post +  "The only individual sector with a significant " + \
                    "increase in employment was " + prev_positive_changes_industries[0] + \
                    " adding " + "{:,}".format(prev_positive_changes[0]) + " positions. "
                elif len(prev_positive_changes_industries) > 1:
                    post = post[:len(post)] + "Labor categories with significant additions include "
                    for industry in prev_positive_changes_industries:
                        if industry == prev_positive_changes_industries[-1] and len(prev_positive_changes_industries) == 2:
                            post = post[:len(post) - 2] + " and " + industry + " adding " + \
                            "{:,}".format(prev_positive_changes[-1]) + " positions. "
                        elif industry == prev_positive_changes_industries[-1]:
                            post = post + "and " + industry + " adding " + "{:,}".format(prev_positive_changes[-1]) + \
                            " positions. "
                        else:
                            post = post + industry + " adding " + \
                            "{:,}".format(prev_positive_changes[prev_positive_changes_industries.index(industry)]) + \
                            " positions, "

                if len(prev_negative_changes_industries) == 1:
                    post = post +  "The only individual sector with a significant " + \
                    "losses in employment was " + prev_negative_changes_industries[0] + \
                    " falling by " + "{:,}".format(prev_negative_changes[0]) + " positions. "
                elif len(prev_negative_changes_industries) > 1:
                    post = post[:len(post)] + "Labor categories with significant losses include "
                    for industry in prev_negative_changes_industries:
                        if industry == prev_negative_changes_industries[-1] and len(prev_negative_changes_industries) == 2:
                            post = post[:len(post) - 2] + " and " + industry + " falling by " + \
                            "{:,}".format(prev_negative_changes[-1]) + " positions. "
                        elif industry == prev_negative_changes_industries[-1]:
                            post = post + "and " + industry + " falling by " + "{:,}".format(prev_negative_changes[-1]) + \
                            " positions. "
                        else:
                            post = post + industry + " falling by " + \
                            "{:,}".format(prev_negative_changes[prev_negative_changes_industries.index(industry)]) + \
                            " positions, "
        post = post + "\n\n\n" + "**" + \
        current_month + "** (preliminary)\n\nThe unemployment rate "
        if unemployment_rate_change > 0:
            post = post + "increased to " + str(unemployment_rate) + "% in " + \
            current_month + ". "
            if topline_employment_change > 0:
                post = post + "{:,}".format(topline_employment_change) + \
                " positions were added, but " + "{:,}".format(abs(labor_force_change)) + \
                " workers entering the labor force caused the unemployment rate to increase. "
            elif topline_employment_change == 0:
                post = post + "Employment was unchanged, but " + \
                "{:,}".format(abs(labor_force_change)) + \
                " workers entering the labor force caused the unemployment rate to increase. "
            elif topline_employment_change < 0:
                if labor_force_change > 0:
                    post = post + "{:,}".format(abs(topline_employment_change)) + \
                    " positions were lost, and " + "{:,}".format(labor_force_change) + \
                    " workers entered the labor force causing the unemployment rate increase. "
                elif labor_force_change < 0:
                    post = post + "{:,}".format(abs(topline_employment_change)) + \
                    " positions were lost, and " + "{:,}".format(abs(labor_force_change)) + \
                    " workers left the labor force causing the unemployment rate increase. "
                elif labor_force_change == 0:
                    post = post + "{:,}".format(abs(topline_employment_change)) + \
                    " positions were lost, and " + \
                    " the labor force was unchanged so the unemployment rate rose. "
        elif unemployment_rate_change < 0:
            post = post + "fell to " + str(unemployment_rate) + "% in " + \
            current_month + ". "
            if topline_employment_change < 0:
                post = post + "{:,}".format(abs(topline_employment_change)) + \
                " positions were lost, but " + "{:,}".format(abs(labor_force_change)) + \
                " workers exiting the labor force caused the unemployment rate to decrease. "
            elif topline_employment_change == 0:
                post = post + "Employment was unchanged, but " + \
                "{:,}".format(abs(labor_force_change)) + \
                " workers exiting the labor force caused the unemployment rate to decrease. "
            elif topline_employment_change > 0:
                if labor_force_change > 0:
                    post = post + "{:,}".format(topline_employment_change) + \
                    " positions were added, with only " + "{:,}".format(labor_force_change) + \
                    " workers entering the labor force causing the unemployment rate decrease. "
                elif labor_force_change < 0:
                    post = post + "{:,}".format(topline_employment_change) + \
                    " positions were added, and " + "{:,}".format(abs(labor_force_change)) + \
                    " workers left the labor force causing the unemployment rate decrease. "
                elif labor_force_change == 0:
                    post = post + "{:,}".format(topeline_employment_change) + \
                    " positions were added, and " + \
                    " the labor force was unchanged so the unemployment rate fell. "
        elif unemployment_rate_change == 0:
            post = post + "remained flat at " + str(unemployment_rate) + "% in " + \
            current_month + ". "
            if topline_employment_change < 0:
                post = post + "{:,}".format(abs(topline_employment_change)) + \
                " positions were lost, but " + "{:,}".format(abs(labor_force_change)) + \
                " workers exiting the labor force balanced out the unemployment rate. "
            elif topline_employment_change == 0:
                post = post + "Employment was unchanged, and "
                if labor_force_change > 0:
                    post = post + "{:,}".format(abs(labor_force_change)) + \
                    " workers entering the labor force was not enough to change the unemployment rate. "
                if labor_force_change < 0:
                    post = post + "{:,}".format(abs(labor_force_change)) + \
                    " workers leaving the labor force was not enough to change the unemployment rate. "
                if labor_force_change == 0:
                    post = post + "{:,}".format(abs(labor_force_change)) + \
                    " the labor force figure was also unchanged. "
            elif topline_employment_change > 0:
                post = post + "{:,}".format(abs(topline_employment_change)) + \
                " positions were added, but " + "{:,}".format(abs(labor_force_change)) + \
                " workers entering the labor force balanced out the unemployment rate. "
        if "Total Nonfarm" in significant_changes:
            nonfarm_change = round(significant_changes.pop("Total Nonfarm") * 1000)
            if nonfarm_change > 0:
                post = post + "Nonfarm payrolls increased by " + "{:,}".format(nonfarm_change) + ". "
            else:
                post = post + "Nonfarm payrolls fell by " + "{:,}".format(abs(nonfarm_change)) + ". "
            sig_industry_list = []
            sig_changes_list = []
            for industry in significant_changes:
                sig_industry_list.append(industry)
            for change in significant_changes:
                sig_changes_list.append(round(significant_changes[change] * 1000))
            if len(significant_changes) == 0:
                post = post + "No individual sector saw significant employment changes. "
            elif len(significant_changes) == 1:
                post = post + "The only individual sector with significant " + \
                "employment changes was " + sig_industry_list[0] + " "
                if sig_changes_list[0] > 0:
                    post = post + "which added " + "{:,}".format(sig_changes_list[0]) + \
                    " positions. "
                elif sig_changes_list[0] < 0:
                    post = post + "which lost " + "{:,}".format(abs(sig_changes_list[0])) + \
                    " positions. "
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
                    post = post +  "The only individual sector with a significant " + \
                    "increase in employment was " + positive_changes_industries[0] + \
                    " adding " + "{:,}".format(positive_changes[0]) + " positions. "
                elif len(positive_changes_industries) > 1:
                    post = post[:len(post)] + "Labor categories with significant additions include "
                    for industry in positive_changes_industries:
                        if industry == positive_changes_industries[-1] and len(positive_changes_industries) == 2:
                            post = post[:len(post) - 2] + " and " + industry + " adding " + \
                            "{:,}".format(positive_changes[-1]) + " positions. "
                        elif industry == positive_changes_industries[-1]:
                            post = post + "and " + industry + " adding " + "{:,}".format(positive_changes[-1]) + \
                            " positions. "
                        else:
                            post = post + industry + " adding " + \
                            "{:,}".format(positive_changes[positive_changes_industries.index(industry)]) + \
                            " positions, "

                if len(negative_changes_industries) == 1:
                    post = post +  "The only individual sector with a significant " + \
                    "losses in employment was " + negative_changes_industries[0] + \
                    " falling by " + "{:,}".format(negative_changes[0]) + " positions. "
                elif len(negative_changes_industries) > 1:
                    post = post[:len(post)] + "Labor categories with significant losses include "
                    for industry in negative_changes_industries:
                        if industry == negative_changes_industries[-1] and len(negative_changes_industries) == 2:
                            post = post[:len(post) - 2] + " and " + industry + " falling by " + \
                            "{:,}".format(negative_changes[-1]) + " positions. "
                        elif industry == negative_changes_industries[-1]:
                            post = post + "and " + industry + " falling by " + "{:,}".format(negative_changes[-1]) + \
                            " positions. "
                        else:
                            post = post + industry + " falling by " + \
                            "{:,}".format(negative_changes[negative_changes_industries.index(industry)]) + \
                            " positions, "

        else:
            post = post + "The overall Nonfarm Payrolls figure did not change significantly. "
            sig_industry_list = []
            sig_changes_list = []
            for industry in significant_changes:
                sig_industry_list.append(industry)
            for change in significant_changes:
                sig_changes_list.append(round(significant_changes[change] * 1000))
            if len(significant_changes) == 0:
                post = post[:len(post) - 2] + " and no individual sector saw significant employment changes. "
            elif len(significant_changes) == 1:
                post = post + "The only individual sector with significant " + \
                "employment changes was " + sig_industry_list[0] + " "
                if sig_changes_list[0] > 0:
                    post = post + "which added " + "{:,}".format(sig_changes_list[0]) + \
                    " positions. "
                elif sig_changes_list[0] < 0:
                    post = post + "which lost " + "{:,}".format(abs(sig_changes_list[0])) + \
                    " positions. "
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
                    post = post +  "The only individual sector with a significant " + \
                    "increase in employment was " + positive_changes_industries[0] + \
                    " adding " + "{:,}".format(positive_changes[0]) + " positions. "
                elif len(positive_changes_industries) > 1:
                    post = post[:len(post)] + "Labor categories with significant additions include "
                    for industry in positive_changes_industries:
                        if industry == positive_changes_industries[-1] and len(positive_changes_industries) == 2:
                            post = post[:len(post) - 2] + " and " + industry + " adding " + \
                            "{:,}".format(positive_changes[-1]) + " positions. "
                        elif industry == positive_changes_industries[-1]:
                            post = post + "and " + industry + " adding " + "{:,}".format(positive_changes[-1]) + \
                            " positions. "
                        else:
                            post = post + industry + " adding " + \
                            "{:,}".format(positive_changes[positive_changes_industries.index(industry)]) + \
                            " positions, "

                if len(negative_changes_industries) == 1:
                    post = post +  "The only individual sector with a significant " + \
                    "losses in employment was " + negative_changes_industries[0] + \
                    " falling by " + "{:,}".format(negative_changes[0]) + " positions. "
                elif len(negative_changes_industries) > 1:
                    post = post[:len(post)] + "Labor categories with significant losses include "
                    for industry in negative_changes_industries:
                        if industry == negative_changes_industries[-1] and len(negative_changes_industries) == 2:
                            post = post[:len(post) - 2] + " and " + industry + " falling by " + \
                            "{:,}".format(negative_changes[-1]) + " positions. "
                        elif industry == negative_changes_industries[-1]:
                            post = post + "and " + industry + " falling by " + "{:,}".format(negative_changes[-1]) + \
                            " positions. "
                        else:
                            post = post + industry + " falling by " + \
                            "{:,}".format(negative_changes[negative_changes_industries.index(industry)]) + \
                            " positions, "

        post = post + "\n\n\n^*" + city_details["reddit_account"] + " ^is ^a ^public ^service ^account " + \
                "^committed ^to ^making ^" + city_details["subreddit"] + " ^a ^better ^informed " + \
                "^community."

        return post

def check_messages(city_details, reddit):
    for message in reddit.inbox.unread():
        if message.was_comment:
            message.mark_read()
        else:
            if city_details['special_case'] == "Manual":
                reddit.redditor('Statistics_Admin').message(message.author.name, message.body)
            else:
                auto_response = city_details['reddit_account'] + " is an unmonitored account, " + \
                "please contact /u/Statistics_Admin to reach the creator with any comments, " + \
                "complaints, or feedback."
                message.reply(auto_response)
                message.mark_read()

def reddit_login(city_details, city):
    config = ConfigParser()
    config.read('/path/to/statistics.config')

    reddit = praw.Reddit(client_id=config[city_details['group']]['client_id'],
                         client_secret=config[city_details['group']]['client_secret'],
                         password=config[city]['password'],
                         user_agent=config['General']['user_agent'],
                         username=config[city]['username'])

    return reddit

def post_to_reddit(reddit, city_details, title, post):

    reddit.subreddit(city_details['sub']).submit(title, selftext = post, send_replies = False)

def pause_for_timer(timer):
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
            print("Checking " + city + "...")
            post = post_constructor(city, city_details, soup, current_month, prev_month)
            title = create_title(soup, city, city_details)
        except TypeError:
            pass

        reddit = reddit_login(city_details, city)

        if city in special_cases:
            if city_details['special_case'] == "Quarterly":
                if      current_month == "March" \
                    or  current_month == "June" \
                    or  current_month == "September" \
                    or  current_month == "December":

                    if post != None:
                        print("Updating " + city)
                        while True:
                            try:
                                post_to_reddit(reddit, city_details, title, post)
                                break
                            except Exception as timer:
                                pause_for_timer(timer)

            elif city_details['special_case'] == "Manual":
                if post != None:
                    print("Sending " + city + " post to /u/Statistics_Admin.")
                    reddit.redditor('Statistics_Admin').message(title, post)
            else:
                print("No update required at this time.")

        else:
            if post != None:
                print("Updating " + city)
                while True:
                    try:
                        post_to_reddit(reddit, city_details, title, post)
                        break
                    except Exception as timer:
                        pause_for_timer(timer)

                update_city_details(city_details, city, current_month)
            else:
                print("No update required at this time.")

        check_messages(city_details, reddit)

if __name__ == '__main__':
    main()
