from getpass import getpass
from bs4 import BeautifulSoup
import mechanize
import time
import json


class Gold(object):

    def __init__(self):
        self.notify_email = None
        self.quarter = None
        self.user = None
        self.pw = None
        self.br = mechanize.Browser()
        self.welcome_msg = "UCSB Class Checker (Exit at any time with Ctrl-C)"
        self.exit_msg = "\n\nThanks for using the UCSB Class Checker!\n"
        # Read search file to get username on login screen
        self.search_params = self.read_search_file("search.json")
        self.start()

    def start(self):
        print("\n%s" % self.welcome_msg)
        # Trick to underline my welcome message with the correct # of =
        print("%s" % ''.join(["=" for i in range(len(self.welcome_msg))]))
        while True:
            try:
                self.login()
                self.search(self.search_params)
                self.wait()
            except KeyboardInterrupt:
                print(self.exit_msg)
                exit()

    def login(self):
        LOGIN_URL = 'https://my.sa.ucsb.edu/gold/Login.aspx'
        USER_FIELD = 'ctl00$pageContent$userNameText'
        PW_FIELD = 'ctl00$pageContent$passwordText'
        CHECKBOX_FIELD = 'ctl00$pageContent$CredentialCheckBox'
        # Sometimes I get random mechanize errors
        # So try to login til successful
        while True:
            try:
                if not self.pw:
                    print("Logging in as: %s" % self.user)
                    self.pw = getpass("UCSB NetID Password: ")
                # Open login page, select login form, modify fields, submit
                self.br.open(LOGIN_URL)
                self.br.select_form(nr=0)
                form = self.br.form
                form[USER_FIELD] = self.user
                form[PW_FIELD] = self.pw
                # Checkbox has weird way of being set
                form[CHECKBOX_FIELD] = ['on']
                # Should not get the login page again after login attempt
                response = self.br.submit()
                soup = BeautifulSoup(response.read())
                if soup.title.string == 'Login':
                    print("> Login unsuccessful. Check credentials.\n")
                    self.pw = None
                else:
                    print("> Login successful.")
                    break
            except KeyboardInterrupt:
                print(self.exit_msg)
                exit()
            except:
                print("Unexpected error logging in. Trying again...")

    def read_search_file(self, path):
        search_params = None
        with open(path) as f:
            search_file = json.load(f)
            self.user = search_file["ucsb_net_id"]
            self.notify_email = search_file["notify_email"]
            self.mins_to_wait = float(search_file["mins_to_wait"])
            self.quarter = search_file["quarter"]
            search_params = search_file["search_params"]

        blank = {"enroll_code": "", "department": "", "course_num": ""}
        while True:
            try:
                search_params.remove(blank)
            except ValueError:
                break
        return search_params

    def search(self, search_params):
        SEARCH_URL = 'https://my.sa.ucsb.edu/gold/CriteriaFindCourses.aspx'
        QUARTER_FIELD = 'ctl00$pageContent$quarterDropDown'
        ENROLL_CODE_FIELD = 'ctl00$pageContent$enrollcodeTextBox'
        DEPARTMENT_FIELD = 'ctl00$pageContent$departmentDropDown'
        COURSE_NUM_FIELD = 'ctl00$pageContent$courseNumberTextBox'
        print("> Starting search...")
        for s in search_params:
            try:
                self.br.open(SEARCH_URL)
                # Select search form
                self.br.select_form(nr=0)
                form = self.br.form
                # Set search params
                form[QUARTER_FIELD] = [self.quarter]
                form[ENROLL_CODE_FIELD] = s['enroll_code']
                form[DEPARTMENT_FIELD] = [s['department']]
                form[COURSE_NUM_FIELD] = s['course_num']
                # Execute search and save result page for parsing
                soup = BeautifulSoup(self.br.submit().read())
                # Parse results
                error_page = soup.findAll("span", attrs={"id": "pageContent_messageLabel"})
                if error_page:
                    print("Class not found. Try searching again.")
                    self.search(search_params)
                class_title = soup.findAll("span", attrs={"class": "tableheader"})
                info_header = soup.findAll("td", attrs={"class": "tableheader"})[0:7]
                info_table = soup.findAll("td", attrs={"class": "clcellprimary"})[0:7]

                info_dict = {}
                for title, detail in zip(info_header, info_table):
                    info_dict[title.string] = detail.string

                # Print class title
                title = class_title[0].string.replace(u'\xa0', u' ')
                title = ' '.join(title.split())
                print("\n%s" % title)
                s = "="
                for i in range(len(title)):
                    s += "="
                print("%s" % s)

                # Check if full
                if info_dict["Space"] == u"Full\xa0":
                    print("Class is full.")
                elif info_dict["Space"] == u"Closed\xa0":
                    print("Class closed. You should search for another class.")
                elif (float(info_dict["Space"]) / float(info_dict["Max"])) > 0:
                    print("Class is OPEN! Sending notification...")
                    self.notify(title)
                else:
                    print("Unknown reason why class is full.")
            except mechanize._form.ControlNotFoundError:
                print("error. skipping for now...\n")

    def notify(self, class_title):
        import smtplib
        fromaddr = self.user + "@umail.ucsb.edu"
        toaddrs = self.notify_email
        msg = "\n[CLASS OPEN!]\n%s" % class_title

        username = fromaddr
        password = self.pw

        server = smtplib.SMTP('pod51019.outlook.com:587')
        server.starttls()
        server.login(username, password)
        server.sendmail(fromaddr, toaddrs, msg)
        server.quit()
        return self

    def wait(self):
        raw_time_delta = time.localtime(time.time() + self.mins_to_wait*60)
        check_time = time.asctime(raw_time_delta)
        print("\n> Checking again at:\n> %s\n" % check_time)
        time.sleep(self.mins_to_wait*60.0)


def main():
    Gold()


if __name__ == "__main__":
    main()
