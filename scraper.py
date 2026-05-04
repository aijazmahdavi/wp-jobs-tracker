import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import os
import json

def get_latest_job():
    url = "https://jobs.wordpress.net/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look through links to find the first job posting
    for a in soup.find_all('a', href=True):
        if 'jobs.wordpress.net/job/' in a['href'] and a.text.strip():
            return {"title": a.text.strip(), "link": a['href']}
    return None

def main():
    latest_job = get_latest_job()
    if not latest_job:
        print("Could not find any jobs on the page.")
        return

    state_file = "last_job.json"
    last_seen_link = ""
    
    # Read the last checked job from our state file
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            try:
                data = json.load(f)
                last_seen_link = data.get("link", "")
            except json.JSONDecodeError:
                pass

    # If the newest job doesn't match the last seen job, it's new!
    if latest_job["link"] != last_seen_link:
        print(f"New job found: {latest_job['title']}")
        
        sender = os.environ.get("SENDER_EMAIL")
        password = os.environ.get("SENDER_PASSWORD")
        receiver = os.environ.get("RECEIVER_EMAIL")
        
        if sender and password and receiver:
            msg = MIMEText(f"A new job has been posted!\n\nTitle: {latest_job['title']}\nLink: {latest_job['link']}")
            msg['Subject'] = f"New WordPress Job: {latest_job['title']}"
            msg['From'] = sender
            msg['To'] = receiver
            
            try:
                # Send the email via Gmail SMTP
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(sender, password)
                    server.send_message(msg)
                print("Email sent successfully.")
                
                # Update the state file so we don't get duplicate emails
                with open(state_file, "w") as f:
                    json.dump({"link": latest_job["link"]}, f)
            except Exception as e:
                print(f"Failed to send email: {e}")
        else:
            print("Missing email secrets.")
    else:
        print("No new jobs posted since the last check.")

if __name__ == "__main__":
    main()
