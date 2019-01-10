<div align="center">
<a href="https://www.cemac.leeds.ac.uk/">
  <img src="https://github.com/cemac/cemac_generic/blob/master/Images/cemac.png"></a>
  <br>
</div>

# Living Lab Data App

<hr>

[![GitHub release](https://img.shields.io/badge/release-v.1.0-blue.svg)](
https://github.com/cemac/LivingLabDataApp/releases/tag/1.0)

## Description ##

This web app has been created that can read in the data files from the CPC
instruments used by volunteers walking around Campus, retrieve the relevant geolocation
data from the Strava servers, and plot the resulting concentrations on a google base map.
The website is currently live at [https://cemac.leeds.ac.uk/living-lab/](https://cemac.leeds.ac.uk/living-lab/).

## Requirements ##

* [Python3 (anaconda)](https://cemac.leeds.ac.uk/living-lab/)
* Packages outlined in Requirements.txt

## Installation ##

*coming soon*

## USAGE ##

Before running this web app, build the sqlite3 database from the ASCII dump file.
(The database file is binary, so the ASCII file is better for version control).
This is done by typing the following (assumes sqlite3 is installed):
`$ sqlite3 LivingLabDataApp.db < LivingLabDataApp.sql`

Similarly, to update the dump file before committing to the git repo, type:
`$ sqlite3 LivingLabDataApp.db .dump > LivingLabDataApp.sql`

Note that in order for the app to run successfully, the files AppSecretKey.txt and StravaTokens.txt must be in the app's root directory.
These files are not version-controlled as they contains sensitive data.

To run the app in development mode (on localhost), do the following:
* In app.py, change the subdomain variable (subd) near the top of the script from "/living-lab" to "" (i.e. an empty string)
* In app.py, add "debug=True" inside the parentheses in the call to app.run near the bottom of the script
* If on the FOE system, load the appropriate python modules by typing: $ module load python3 python-libs
* Run the application by typing: $ python3 app.py
* Open up a web browser and navigate to localhost:5000

**Don't forget to reset subd and remove from debug mode before committing to GitHub (production mode)**

To make changes to the GitHub repo:
* If you are a collaborator, you can simply push local changes to the main repo
* If you are not a collaborator, follow these instructions:
  * Fork and clone the main repo
  * Configure your local forked repo to sync with the main repo:
    `$ git remote add upstream https://github.com/cemac/LivingLabDataApp.git`
  * You can then keep your local forked repo up-to-date with any changes to the main repo using:
    `$ git fetch upstream; git merge upstream`
    OR
    ``$ git pull upstream master`
  * Make a new branch for a particular new development/bug fix:
    `$ git checkout -b branchName`
  * Commit changes locally as normal, and push to the remote forked repo using:
    `$ git push origin branchName`
  * Once happy with your changes, open a pull request (PR) from your remote forked repo's GitHub page
  * This PR wil be reviewed by one of the code owners and, once any follow-up changes are made, pulled into th main repo
  * It is then good practice to delete the branch in both the remote forked repo (can be done via GitHub) and the local forked repo:
    `$ git branch -d branchName`

To make any code changes take effect on the server, ssh into it, update the git repo, and perform a restart:
```bash
$ ssh -Y cemac-ll-01
$ cd /www/living_lab/
$ git pull
$ sudo systemctl restart httpd
```

**All Secret Key are not version controlled.**

## License Information ##

This App is licensed is currently licensed under the [MIT license](https://choosealicense.com/licenses/mit/). *Subject to change on request*

## Acknowledgements ##
