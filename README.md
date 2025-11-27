# FreshRSS to Wallabag sync Script

This script was created to help users effortlessly sync their favorite articles from FreshRSS to Wallabag for easier reading on multiple devices - in my case an e-reader with [KOReader](https://github.com/koreader/koreader/wiki) installed.

## Pre-requisites

- [FreshRSS](https://github.com/FreshRSS/FreshRSS) (tested with version 1.27.0 and newer)
- [Wallabag](https://github.com/wallabag/wallabag) (tested with version 2.6.13 and newer)
- A VPS, server or other 24/7 computer capable of running Python scripts

## Description

This script queries FreshRSS's Fever API to retrieve favourited articles. The retrieved articles are compared to a local cache list of synced articles, and any new favourited articles are imported into Wallabag. It is recommended to execute the script every 5-30 minutes using cron or other forms of task schedulers.

## Configuration

### FreshRSS Setup
[Enable API access](https://freshrss.github.io/FreshRSS/en/users/06_Mobile_access.html) in your FreshRSS instance. Note down your user's API password. You can verify if Fever API enabled by going to [https://foo.bar/p/api/](https://foo.bar/p/api/), assuming `https://foo.bar/` is the root path to your FreshRSS instance.

### Wallabag setup
Log in to Wallabag and go to **API clients management** section, where you need to **create a new client**. Note down the Client ID and Client secret.

### Script setup
Test whether the script executes without any issues in your environment. If that's the case, schedule it with your preferred task scheduler, such as cron. My recommendation is to let it run every 5 to 15 minutes, but the execution is fairly fast: with no new items to sync, it's usually under a second. With a few articles to send to Wallabag, it's usually less than 10-15 seconds.

## Limitations
- This script is designed to be a super lightweight, low complexity solution. It is under 300 lines of code, so easily understandable and modifiable by anyone with intermediate Python knowledge.
- Synced articles (their IDs) are stored in a simple JSON file. This is not infinitely scalable, but will be good enough for the first few thousands of articles you sync.

## Notes
- Wallabag seems to have duplicate protection - if you wipe your synced_articles.json and re-run the sync, the script will attempt to add them to Wallabag again, but no duplicate entries will be created in Wallabag. The existing entries also retain their status.

