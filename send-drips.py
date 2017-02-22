import sendgrid
import os
import json
from datetime import datetime
from sendgrid.helpers.mail import Email, Content, Substitution, Mail
try:
  # Python 3
  import urllib.request as urllib
except ImportError:
  # Python 2
  import urllib2 as urllib

sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SG_API_KEY'))

email_series = [
  {
    "index": 1,
    "sent_at_day": 0,
    "field": "email_1_date",
    "subject": "Subject Line 1",
    "content": "Content 1",
    "template_id": "db6d9991-5136-4fba-82ef-6c5e98649caf"
  },
  {
    "index": 2,
    "sent_at_day": 5,
    "field": "email_2_date",
    "subject": "Subject Line 2",
    "content": "Content 2",
    "template_id": "db6d9991-5136-4fba-82ef-6c5e98649caf"
  },
  {
    "index": 3,
    "sent_at_day": 10,
    "field": "email_3_date",
    "subject": "Subject Line 3",
    "content": "Content 3",
    "template_id": "db6d9991-5136-4fba-82ef-6c5e98649caf"
  }
]

list_id = "1076254"

class Recipient:
  from_email = "hello@sendgrid.com"

  def __init__(self, attributes):
    self.to_email = attributes['email']
    self.first_name = attributes['first_name']
    self.last_name = attributes['last_name']
    self.custom_fields = attributes['custom_fields']
    self.email_1_date = self.__getCustomField('email_1_date')
    self.email_2_date = self.__getCustomField('email_2_date')
    self.email_3_date = self.__getCustomField('email_3_date')

  def __getCustomField(self, field_name):
    for field in self.custom_fields:
      if field['name'] == field_name:
        return field['value']
    return -1

  def sendEmail(self, subject, content, template):
    from_email = Email(self.from_email)
    to_email = Email(self.to_email)
    content = Content("text/html", content)
    mail = Mail(from_email, subject, to_email, content)
    mail.personalizations[0].add_substitution(Substitution("%NAME%", self.first_name))
    mail.set_template_id(template)
    try:
        response = sg.client.mail.send.post(request_body=mail.get())
    except urllib.HTTPError as e:
        print e.read()
        exit()

class DripCampaign:
  def __init__(self, email_series, list_id):
    self.email_series = email_series
    self.list_id = list_id

    # Retrieve recipients of a given list using the following endpoint
    # GET https://api.sendgrid.com/v3/contactdb/lists/{list_id}/recipients?page_size=100&page=1
    params = {'page': 1, 'page_size': 1, 'list_id': str(self.list_id)}
    response = sg.client.contactdb.lists._(self.list_id).recipients.get()
    body = json.loads(response.body)
    list_recipients = body['recipients']
    
    # Create a list of Recipients from the given contacts list
    self.recipients = [];
    for attributes in list_recipients:
      recipient = Recipient(attributes)
      self.recipients.append(recipient)

  def sendDrips(self):
    # Loop through recipients and email series and send email if today equals the set date to send
    for recipient in self.recipients:  
      for email in self.email_series:
        field = email['field']
        field_date = getattr(recipient, field)
        if field_date:
          date = datetime.fromtimestamp(field_date).date()
          today = datetime.today().date()
          if date == today:
            message = 'Sending email ' + str(email['index']) + ' to ' + recipient.first_name + ' ' + recipient.last_name + ' (' + recipient.to_email + ')'
            print message
            recipient.sendEmail(email['subject'], email['content'], email['template_id'])

  # Add recipient to list to receive drips
  # POST https://api.sendgrid.com/v3/contactdb/lists/{list_id}/recipients/{recipient_id}
  def addRecipient(self):
    # TO DO - CREATE RECIPIENT AND ADD TO LIST


myDripCampagin = DripCampaign(email_series, list_id)
myDripCampagin.sendDrips()

  
  