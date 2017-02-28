import sendgrid
import os
import json
from datetime import datetime, timedelta
import time
from sendgrid.helpers.mail import Email, Content, Substitution, Mail
try:
  # Python 3
  import urllib.request as urllib
except ImportError:
  # Python 2
  import urllib2 as urllib

sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SG_API_KEY'))

class DripCampaign:
  def __init__(self, email_series, list_id):
    self.email_series = email_series
    self.list_id = list_id
    self.__updateRecipientsList()
    ## TO DO => ADD CUSTOM FIELDS IF THEY DO NOT EXIST

  def __updateRecipientsList(self):
    # Retrieve recipients of a given list using the following endpoint
    # GET https://api.sendgrid.com/v3/contactdb/lists/{list_id}/recipients?page_size=100&page=1
    params = {'page': 1, 'page_size': 1, 'list_id': str(self.list_id)}
    response = sg.client.contactdb.lists._(self.list_id).recipients.get()
    body = json.loads(response.body)
    list_recipients = body['recipients']
    
    # Create a list of Recipients from the given contacts list
    self.recipients = []
    for recipient_attributes in list_recipients:
      recipient = DripRecipient(recipient_attributes, self.email_series)
      self.recipients.append(recipient)

  def sendDrips(self):
    self.__updateRecipientsList()

    # Loop through recipients and email series and send email if today equals the set date to send
    for recipient in self.recipients: 
      print recipient.to_email
      for email in self.email_series:
        field = email['field']
        field_date = getattr(recipient, field)
        if field_date:
          date = datetime.fromtimestamp(field_date).date()
          today = datetime.today().date()
          print date
          print today
          if date == today:
            message = 'Sending email ' + str(email['index']) + ' to (' + recipient.to_email + ')'
            print message
            recipient.sendEmail(email['subject'], email['content'], email['template_id'])

  # Add recipient to list to receive drips
  def addExistingContactToDrip(self, email):
    contact = Contact(email)
    addedToList = contact.addContactToList(self.list_id)
    if addedToList == True:
      date_fields = [{}]
      for email in self.email_series:
        date_fields[0][email['field']] = self.__get_send_date(email['sent_at_day'])
      contact.addFieldsToContact(date_fields)
    elif (addedToList == 'DNE'):
      print 'Contact does not exist. You can create contact and add to drip with addNewContactToDrip method'
    else:
      print 'Contact is already on drip list.  Update contact with updateContactDateFields method'

  def addNewContactToDrip(self, email, first_name="", last_name=""):
    contact = Contact(email)
    if contact.getContactId():
      print 'Contact already exists'
      return False
    else:
      new_contact = contact.createNewContact(first_name, last_name)
      if new_contact['persisted_recipients'][0]:
        new_contact_id = new_contact['persisted_recipients'][0]['id']
        if new_contact_id:
          contact.addContactToList(self.list_id)
          contact.addFieldsToContact(email, date_fields)
        else:
          print 'Error creating contact'      
      else:
        print 'Error creating contact'

  def updateContactDateFields(self, email):
    contact = Contact(email)
    if contact.getContactId():
      date_fields = [{}]
      for email in self.email_series:
        date_fields[0][email['field']] = self.__get_send_date(email['sent_at_day'])
      contact.addFieldsToContact(date_fields)
    else:
      print 'Contact does not exist'

  def __get_send_date(self, sent_at_day):
    today = datetime.today()
    send_date = today + timedelta(days=(sent_at_day+1))
    return send_date.strftime("%m/%d/%y")


class DripRecipient:
  from_email = "sender@example.com"

  def __init__(self, recipient_attributes, email_series):
    self.to_email = recipient_attributes['email']
    self.first_name = recipient_attributes['first_name']
    self.last_name = recipient_attributes['last_name']
    self.custom_fields = recipient_attributes['custom_fields']

    # Set email send date instance variables
    for email in email_series:
      setattr(self, email['field'], self.__getCustomField(email['field']))

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


class Contact:
  def __init__(self, email):
    self.email = email

  def getContactId(self):
    params = {'email': self.email}
    response = sg.client.contactdb.recipients.search.get(query_params=params)
    body = json.loads(response.body)
    if (len(body['recipients']) > 0):
      self.id = body['recipients'][0]['id']
      return self.id
    else:
      print 'ERROR: Contact does not exist'
      return False

  def createNewContact(self, first_name, last_name):
      data = [{ 
        "email": self.email,
        "first_name": first_name,
        "last_name": last_name
      }]
      response = sg.client.contactdb.recipients.post(request_body=data)
      body = json.loads(response.body)
      return body

  def getContactLists(self):
    if self.getContactId():
      response = sg.client.contactdb.recipients._(self.id).lists.get()
      body = json.loads(response.body)
      self.lists = body['lists']
      return self.lists
    else:
      print 'Contact does not exist'
      return False

  def isContactOnList(self, list_id):
    mkting_lists = self.getContactLists()
    if (mkting_lists):
      for mkting_list in mkting_lists:
        if str(mkting_list['id']) == str(list_id):
          return True
      return False
    else:
      print 'Contact does not exist'
      return 'DNE'

  def addContactToList(self, list_id):
    if (self.isContactOnList(list_id) == False):
      response = sg.client.contactdb.lists._(list_id).recipients._(self.id).post()
      print 'Adding contact to list'
      print response.body
      return True
    elif (self.isContactOnList(list_id) == 'DNE'):
      print 'Contact does not exist'
      return 'DNE'
    else:
      print 'Contact is already on list'
      return False

  def addFieldsToContact(self, data):
    data[0]['email'] = self.email
    response = sg.client.contactdb.recipients.patch(request_body=data)
    body = json.loads(response.body)
    if body['updated_count'] == 1:
      print 'Successfully updated contact'
    else:
      print 'Error updating contact'


## Example use of library
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
    "sent_at_day": 20,
    "field": "email_3_date",
    "subject": "Subject Line 3",
    "content": "Content 3",
    "template_id": "db6d9991-5136-4fba-82ef-6c5e98649caf"
  }
]

list_id = "1076254"

WelcomeSeries = DripCampaign(email_series, list_id)
WelcomeSeries.addNewContactToDrip('devin.chas123@sendgrid.com')
# WelcomeSeries.addExistingContactToDrip('devin@sendgrid.com')
# WelcomeSeries.updateContactDateFields('devin@sendgrid.com')
# WelcomeSeries.sendDrips()