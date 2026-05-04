import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json

def get_all_jobs():
    url = "https://jobs.wordpress.net/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    jobs = []
    seen_on_page = set()
    
    # Grab all job links from the page
    for a in soup.find_all('a', href=True):
        if 'jobs.wordpress.net/job/' in a['href'] and a.text.strip():
            link = a['href']
            title = a.text.strip()
            # Deduplicate links (since the site might have multiple clickable areas for one job)
            if link not in seen_on_page:
                seen_on_page.add(link)
                jobs.append({"title": title, "link": link})
    return jobs

def main():
    current_jobs = get_all_jobs()
    if not current_jobs:
        print("Could not find any jobs on the page.")
        return

    state_file = "last_job.json"
    seen_links = []
    
    # Read the history of jobs we've already emailed you about
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            try:
                data = json.load(f)
                # Handle the old format if it exists, or the new list format
                if "seen_links" in data:
                    seen_links = data["seen_links"]
                elif "link" in data:
                    seen_links = [data["link"]]
            except json.JSONDecodeError:
                pass

    # Find jobs that aren't in our history
    new_jobs = [job for job in current_jobs if job["link"] not in seen_links]

    if new_jobs:
        print(f"Found {len(new_jobs)} new job(s)!")
        
        sender = os.environ.get("SENDER_EMAIL")
        password = os.environ.get("SENDER_PASSWORD")
        receiver = os.environ.get("RECEIVER_EMAIL")
        
        if sender and password and receiver:
            # 1. Setup the Email Wrapper
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Alert: {len(new_jobs)} New WordPress Job(s)!"
            msg['From'] = sender
            msg['To'] = receiver
            
            # 2. Build the HTML Content dynamically
            jobs_html = ""
            for job in new_jobs:
                jobs_html += f"""
                <div style="border-left: 4px solid #0073aa; background-color: #f9f9f9; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                  <h2 style="margin: 0 0 10px 0; font-size: 18px; color: #333333;">{job['title']}</h2>
                  <a href="{job['link']}" style="display: inline-block; padding: 10px 20px; background-color: #0073aa; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 14px;">View Job Details &rarr;</a>
                </div>
                """
                
            html_template = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                  <h1 style="color: #333333; border-bottom: 2px solid #0073aa; padding-bottom: 10px; margin-top: 0;">New WordPress Jobs Available!</h1>
                  <p style="color: #555555; font-size: 16px;">We found <strong>{len(new_jobs)}</strong> new job posting(s) since your last check:</p>
                  
                  {jobs_html}
                  
                  <p style="font-size: 12px; color: #999999; margin-top: 30px; text-align: center;">This is an automated alert from your GitHub Jobs Tracker.</p>
                </div>
              </body>
            </html>
            """
            
            # Attach the HTML to the email
            msg.attach(MIMEText(html_template, 'html'))
            
            try:
                # Send the email
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(sender, password)
                    server.send_message(msg)
                print("HTML Email sent successfully.")
                
                # Update the state file with the new links. 
                # We combine the new ones with the old ones, and keep the latest 100 to prevent the file from getting huge.
                updated_history = [job["link"] for job in new_jobs] + seen_links
                updated_history = list(dict.fromkeys(updated_history))[:100] 
                
                with open(state_file, "w") as f:
                    json.dump({"seen_links": updated_history}, f)
                    
            except Exception as e:
                print(f"Failed to send email: {e}")
        else:
            print("Missing email secrets.")
    else:
        print("No new jobs posted since the last check.")

if __name__ == "__main__":
    main()
