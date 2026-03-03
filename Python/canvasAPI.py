import requests
import csv
import os
 
CANVAS_DOMAIN = "https://ohio.instructure.com"
TOKEN = os.getenv("CANVAS_TOKEN")
 
headers = {
    "Authorization": f"Bearer {TOKEN}"
}
 
response = requests.get(
    f"{CANVAS_DOMAIN}/api/v1/users/self",
    headers=headers
)
 
user_data = response.json()
 
response = requests.get(
    f"{CANVAS_DOMAIN}/api/v1/courses?per_page=100",
    headers=headers
)
 
courses = response.json()
 
STUDENT_ID = user_data["id"]
 
for course in courses:
    COURSE_ID = course["id"]
 
    url = f"{CANVAS_DOMAIN}/api/v1/courses/{COURSE_ID}/students/submissions?student_ids[]={STUDENT_ID}"
 
 
    response = requests.get(url, headers=headers)
 
    data = response.json()
    #instead of printing the data, we will write it to a csv file
    if "name" in course:
        with open(f"{course["name"]}_submissions.csv", mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Submission Date"])
            for submission in data:
                if "submitted_at" in submission:
                    submission_date = submission["submitted_at"] 
                else:
                    submission_date = "N/A"
                writer.writerow([submission_date])
    else:
        with open(f"course_{COURSE_ID}_submissions.csv", mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Submission Date"])
            for submission in data:
                if "submitted_at" in submission:
                    submission_date = submission["submitted_at"] 
                else:
                    submission_date = "N/A"
                writer.writerow([submission_date])