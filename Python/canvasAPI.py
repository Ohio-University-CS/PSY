import requests
import csv
import os

#placeholder domain for testing
CANVAS_DOMAIN = "https://ohio.instructure.com"
TOKEN = os.getenv("CANVAS_TOKEN")
 
#set up headers for auth
headers = {
    "Authorization": f"Bearer {TOKEN}"
}
 
#get user data - student ID is needed for API calls to get submission data
response = requests.get(
    f"{CANVAS_DOMAIN}/api/v1/users/self",
    headers=headers
)
 
#user data from response
user_data = response.json()
 
#get list of courses the student is enrolled in
response = requests.get(
    f"{CANVAS_DOMAIN}/api/v1/courses?per_page=100",
    headers=headers
)
 
#courses from response
courses = response.json()

#get student ID from user data
STUDENT_ID = user_data["id"]

#loop through courses and get submission data 
for course in courses:
    #get course ID from course data
    COURSE_ID = course["id"]
 
    #API call to get submission data for the student in the course
    url = f"{CANVAS_DOMAIN}/api/v1/courses/{COURSE_ID}/students/submissions?student_ids[]={STUDENT_ID}"
    response = requests.get(url, headers=headers)
 
    #data from response
    data = response.json()
    
    #write submission data to CSV from json response
    
    #check if course has a name, if not, use course ID
    if "name" in course:
        with open(f"{course["name"]}_submissions.csv", mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Submission Date"])
            for submission in data:
                #check if submission has a date, if not, write "N/A"
                if "submitted_at" in submission:
                    submission_date = submission["submitted_at"] 
                else:
                    submission_date = "N/A"
                writer.writerow([submission_date])
    else:
        with open(f"{COURSE_ID}_submissions.csv", mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Submission Date"])
            for submission in data:
                if "submitted_at" in submission:
                    submission_date = submission["submitted_at"] 
                else:
                    submission_date = "N/A"
                writer.writerow([submission_date])